import unicodedata
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
app.config['MAX_FILENAME_LENGTH'] = 200  # 新增檔名長度限制

# 使用字典來追蹤登入中的使用者 {user_id: {'username': 'name', 'login_time': 'time'}}
active_sessions = {}
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


def validate_file_size(file_size):
    """
    驗證檔案大小

    Args:
        file_size (int): 檔案大小（位元組）

    Returns:
        tuple: (is_valid, error_message)
    """
    if file_size == 0:
        return False, "檔案大小不能為 0 bytes，請檢查檔案是否完整"

    max_size = app.config['MAX_CONTENT_LENGTH']  # 50MB
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        current_size_mb = file_size / (1024 * 1024)
        return False, f"檔案大小超過限制，最大允許 {max_size_mb:.0f}MB，您的檔案為 {current_size_mb:.1f}MB"

    return True, ""


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
                session['role'] = user['role']  # <-- 新增：儲存角色

                # --- 新增：記錄登入狀態 ---
                active_sessions[user['id']] = {
                    'username': user['username'],
                    'login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                # --- 新增結束 ---

                return redirect(url_for('dashboard'))
            else:
                flash('帳號或密碼錯誤')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('帳號和密碼不能為空')
            return redirect(url_for('register'))

        with get_db() as conn:
            # --- ↓↓↓ 這是最重要的檢查區塊 ↓↓↓ ---
            # 檢查使用者名稱是否已存在
            user = conn.execute(
                'SELECT id FROM users WHERE username = ?', (username,)
            ).fetchone()

            # 如果 user 不是 None，表示已存在，就顯示提示並返回
            if user:
                flash('此帳號名稱已被註冊，請更換一個')
                return redirect(url_for('register'))
            # --- ↑↑↑ 檢查區塊結束 ↑↑↑ ---

            # 只有在帳號不存在時，才會執行以下新增操作
            conn.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), 'user')
            )
            flash('註冊成功！請使用新帳號登入')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    # --- 新增：移除登入狀態 ---
    if 'user_id' in session and session['user_id'] in active_sessions:
        del active_sessions[session['user_id']]
    # --- 新增結束 ---

    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db() as conn:
        files = conn.execute('''
            SELECT * FROM files 
            ORDER BY upload_time DESC
        ''').fetchall()  # <--- 已修改

    # --- 修改這段 ---
    # 將 active_sessions 傳遞給模板
    return render_template('dashboard.html', files=files, active_sessions=active_sessions)
    # --- 修改結束 ---


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
            # --- 新增：檔案大小驗證 ---
            # 先將檔案儲存到臨時位置以獲取實際大小
            temp_filename = f"temp_{uuid.uuid4().hex}"
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)

            try:
                file.save(temp_path)
                actual_file_size = os.path.getsize(temp_path)

                # 驗證檔案大小
                is_valid, error_message = validate_file_size(actual_file_size)
                if not is_valid:
                    # 刪除臨時檔案
                    os.remove(temp_path)
                    flash(error_message)
                    return redirect(request.url)

                # 如果檔案大小有效，繼續處理
                # 重新讀取檔案內容（因為 file stream 已經被消耗）
                with open(temp_path, 'rb') as temp_file:
                    file_content = temp_file.read()

            except Exception as e:
                # 清理臨時檔案
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                flash(f'檔案處理錯誤：{str(e)}')
                return redirect(request.url)
            # --- 檔案大小驗證結束 ---

            # --- 使用旗標變數，來取代複雜的 flash 判斷 ---
            special_message_flashed = False

            original_filename = unicodedata.normalize('NFC', file.filename)

            if len(original_filename) > app.config['MAX_FILENAME_LENGTH']:
                name_part, extension = os.path.splitext(original_filename)
                name_part = name_part[:app.config['MAX_FILENAME_LENGTH'] - len(extension)]
                original_filename = name_part + extension
                flash(f'檔名過長，已自動截斷為: {original_filename}')
                special_message_flashed = True  # 設定旗標

            final_filename = original_filename
            with get_db() as conn:
                existing_file = conn.execute(
                    'SELECT id FROM files WHERE original_filename = ? AND uploaded_by = ?',
                    (final_filename, session['user_id'])
                ).fetchone()

                if existing_file:
                    counter = 1
                    name_part, extension = os.path.splitext(original_filename)
                    while True:
                        new_name = f"{name_part} ({counter}){extension}"
                        check_again = conn.execute(
                            'SELECT id FROM files WHERE original_filename = ? AND uploaded_by = ?',
                            (new_name, session['user_id'])
                        ).fetchone()
                        if not check_again:
                            final_filename = new_name
                            break
                        counter += 1
                    flash(f'檔案 "{original_filename}" 已存在，已自動重新命名為 "{final_filename}"')
                    special_message_flashed = True  # 設定旗標

            internal_filename = f"{uuid.uuid4().hex}_{final_filename}"
            final_file_path = os.path.join(app.config['UPLOAD_FOLDER'], internal_filename)

            # --- 修改：將臨時檔案移動到最終位置 ---
            try:
                os.rename(temp_path, final_file_path)
                # 或者寫入檔案內容（如果使用 file_content）
                # with open(final_file_path, 'wb') as f:
                #     f.write(file_content)
            except Exception as e:
                # 清理檔案
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                if os.path.exists(final_file_path):
                    os.remove(final_file_path)
                flash(f'檔案儲存錯誤：{str(e)}')
                return redirect(request.url)
            # --- 修改結束 ---

            mime_type = mimetypes.guess_type(final_filename)[0]
            download_id = uuid.uuid4().hex

            with get_db() as conn:
                conn.execute('''
                    INSERT INTO files 
                    (filename, original_filename, file_path, file_size, mime_type, download_id, uploaded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (internal_filename, final_filename, final_file_path, actual_file_size, mime_type, download_id,
                      session['user_id']))

            # --- 使用旗標變數來判斷 ---
            # 如果沒有設定過任何特殊訊息，才顯示通用的成功訊息
            if not special_message_flashed:
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
        # --- 修改開始 ---
        # 移除 uploaded_by 的檢查，只透過 id 尋找檔案
        file_record = conn.execute(
            'SELECT * FROM files WHERE id = ?',
            (file_id,)
        ).fetchone()
        # --- 修改結束 ---

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


def migrate_db():
    """檢查並更新資料庫結構，新增 role 欄位並設定 admin 角色"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 檢查 users 表格中是否已有 role 欄位
        cursor.execute("PRAGMA table_info(users)")
        columns = [row['name'] for row in cursor.fetchall()]

        if 'role' not in columns:
            print("正在新增 'role' 欄位到 users 表格...")
            # 新增 role 欄位，並給予預設值 'user'
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            print("'role' 欄位已新增。")

        # 將 'admin' 使用者的角色設定為 'admin'
        cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
        conn.commit()
        print("已將 'admin' 使用者設定為管理員。")


if __name__ == '__main__':
    init_db()
    migrate_db()  # 執行資料庫結構更新
    app.run(debug=True, host='0.0.0.0', port=5000)