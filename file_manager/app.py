from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file, flash
import os
import sqlite3
import hashlib
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import mimetypes

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # 請更改此密鑰
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB限制

# 確保上傳目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('instance', exist_ok=True)

# 資料庫設定
DATABASE = 'instance/database.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        # 創建表格
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                download_id TEXT UNIQUE NOT NULL,
                uploaded_by INTEGER NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                download_count INTEGER DEFAULT 0,
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            );
        ''')

        # 插入預設用戶（需要使用 execute 而不是 executescript）
        conn.execute(
            'INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)',
            ('admin', generate_password_hash('admin123'))
        )


# 允許的檔案類型
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'mp3', 'mp4', 'avi'
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def before_request():
    # 初始化資料庫
    if not os.path.exists(DATABASE):
        init_db()


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                flash('帳號或密碼錯誤')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db() as conn:
        files = conn.execute('''
            SELECT * FROM files WHERE uploaded_by = ? 
            ORDER BY upload_time DESC
        ''', (session['user_id'],)).fetchall()

    return render_template('dashboard.html', files=files)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('未選擇檔案')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('未選擇檔案')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # 生成安全的檔案名
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            filename = f"{uuid.uuid4().hex}.{file_ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # 儲存檔案
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            mime_type = mimetypes.guess_type(original_filename)[0]
            download_id = uuid.uuid4().hex

            # 儲存到資料庫
            with get_db() as conn:
                conn.execute('''
                    INSERT INTO files 
                    (filename, original_filename, file_path, file_size, mime_type, download_id, uploaded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (filename, original_filename, file_path, file_size, mime_type, download_id, session['user_id']))

            flash(f'檔案 {original_filename} 上傳成功！')
            return redirect(url_for('dashboard'))
        else:
            flash('不支援的檔案類型')

    return render_template('upload.html')


@app.route('/download/<download_id>')
def download(download_id):
    with get_db() as conn:
        file_record = conn.execute(
            'SELECT * FROM files WHERE download_id = ?', (download_id,)
        ).fetchone()

        if not file_record:
            return "檔案不存在", 404

        # 更新下載次數
        conn.execute(
            'UPDATE files SET download_count = download_count + 1 WHERE download_id = ?',
            (download_id,)
        )

        file_path = file_record['file_path']
        if not os.path.exists(file_path):
            return "檔案已被刪除", 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_record['original_filename']
        )


@app.route('/delete/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db() as conn:
        file_record = conn.execute(
            'SELECT * FROM files WHERE id = ? AND uploaded_by = ?',
            (file_id, session['user_id'])
        ).fetchone()

        if file_record:
            # 刪除實體檔案
            if os.path.exists(file_record['file_path']):
                os.remove(file_record['file_path'])

            # 刪除資料庫記錄
            conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
            flash('檔案已刪除')
        else:
            flash('檔案不存在或無權限刪除')

    return redirect(url_for('dashboard'))


@app.route('/api/files')
def api_files():
    if 'user_id' not in session:
        return jsonify({'error': '未登入'}), 401

    with get_db() as conn:
        files = conn.execute('''
            SELECT id, original_filename, file_size, upload_time, download_count, download_id
            FROM files WHERE uploaded_by = ? 
            ORDER BY upload_time DESC
        ''', (session['user_id'],)).fetchall()

        return jsonify([dict(row) for row in files])


def format_file_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


app.jinja_env.filters['filesize'] = format_file_size

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)