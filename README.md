# 檔案管理系統 (File Management System)

一個基於 Flask 的現代化檔案上傳與管理系統，提供直觀的使用者介面和完整的檔案管理功能。

## 功能特色

### 🔐 使用者系統
- 使用者註冊與登入
- 密碼加密存儲（使用 Werkzeug）
- 會話管理
- 管理員權限系統
- 線上使用者狀態追蹤

### 📁 檔案管理
- 拖放式檔案上傳
- 支援多種檔案格式：
  - 圖片：JPG, PNG, GIF
  - 文件：PDF, DOC, DOCX, TXT
  - 試算表：XLS, XLSX
  - 簡報：PPT, PPTX
  - 壓縮檔：ZIP, RAR
  - 影音：MP3, MP4, AVI
- 檔案大小限制：50MB
- 檔名智慧處理（自動重命名重複檔案）
- 檔案下載統計
- 檔案分享連結生成

### 🎨 現代化介面
- 深色主題設計
- 響應式佈局（支援手機、平板、桌面）
- 即時進度顯示
- 檔案類型圖示識別
- 智能檔名顯示（副檔名分離顯示）
- 拖放上傳動畫效果

### 📊 系統統計
- 總檔案數統計
- 總下載次數統計
- 總儲存空間統計
- 管理員面板（線上使用者監控）

## 技術架構

### 後端技術
- **Flask 2.3.3** - Web 應用框架
- **SQLite** - 資料庫系統
- **Werkzeug 2.3.7** - WSGI 工具庫（密碼加密、檔案處理）
- **Jinja2 3.1.2** - 模板引擎

### 前端技術
- **Tailwind CSS** - CSS 框架（CDN 版本）
- **Font Awesome 6.0.0** - 圖示庫
- **原生 JavaScript** - 前端互動邏輯

### 資料庫結構
```sql
-- 使用者表
users:
  - id (主鍵)
  - username (使用者名稱，唯一)
  - password_hash (加密密碼)
  - role (角色：admin/user)
  - created_at (建立時間)

-- 檔案表
files:
  - id (主鍵)
  - filename (系統內部檔名)
  - original_filename (原始檔名)
  - file_path (檔案路徑)
  - file_size (檔案大小)
  - mime_type (MIME 類型)
  - download_id (下載唯一識別碼)
  - uploaded_by (上傳者 ID)
  - upload_time (上傳時間)
  - download_count (下載次數)
```

## 安裝與部署

### 1. 環境需求
- Python 3.11 或更高版本
- Docker（可選）

### 2. 本地安裝

```bash
# 克隆專案
git clone <repository-url>
cd file-management-system

# 安裝依賴
pip install -r requirements.txt

# 啟動應用
python app.py
```

應用將在 `http://localhost:5000` 啟動。

### 3. Docker 部署

```bash
# 建立 Docker 映像
docker build -t file-management-system .

# 執行容器
docker run -p 5000:5000 -v ./uploads:/app/uploads -v ./instance:/app/instance file-management-system
```

**重要提示：** 建議掛載 `uploads` 和 `instance` 目錄以保持資料持久性。

## 配置設定

### 應用程式配置
```python
app.secret_key = 'your-secret-key-change-this'  # 請更改此密鑰
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB限制
app.config['MAX_FILENAME_LENGTH'] = 200  # 檔名長度限制
```

### 支援的檔案類型
在 `app.py` 中的 `ALLOWED_EXTENSIONS` 可自定義支援的檔案格式。

## 專案結構

```
file-management-system/
├── app.py                 # 主應用程式
├── requirements.txt       # Python 依賴
├── Dockerfile            # Docker 配置
├── instance/             # 資料庫存放目錄
│   └── database.db      # SQLite 資料庫
├── uploads/              # 檔案上傳目錄
├── templates/            # Jinja2 模板
│   ├── base.html        # 基礎模板
│   ├── login.html       # 登入頁面
│   ├── register.html    # 註冊頁面
│   ├── dashboard.html   # 檔案列表
│   └── upload.html      # 檔案上傳
├── static/               # 靜態資源目錄
│   └── style.css        # 自定義樣式（目前空檔案）
├── auth.py              # 認證模組（目前空檔案）
├── config.py            # 配置模組（目前空檔案）
└── models.py            # 資料模型（目前空檔案）
```

## 功能說明

### 檔案上傳
- 支援拖放上傳和點擊選擇
- 即時檔案預覽和資訊顯示
- 上傳進度模擬顯示
- 自動檔名衝突處理
- 檔名長度自動截斷

### 檔案管理
- 檔案列表瀏覽
- 一鍵複製分享連結
- 檔案下載和刪除
- 檔案大小和下載次數統計
- 檔案類型圖示化顯示

### 管理員功能
- 可刪除所有使用者的檔案
- 線上使用者監控
- 系統統計資訊查看

## API 端點

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首頁重導向 |
| `/login` | GET/POST | 使用者登入 |
| `/register` | GET/POST | 使用者註冊 |
| `/logout` | GET | 使用者登出 |
| `/dashboard` | GET | 檔案列表頁面 |
| `/upload` | GET/POST | 檔案上傳頁面 |
| `/download/<download_id>` | GET | 檔案下載 |
| `/delete/<file_id>` | POST | 刪除檔案 |
| `/api/files` | GET | API 取得檔案列表 |

## 安全特性

- 密碼雜湊存儲
- 檔案類型驗證
- 檔案大小限制
- 會話管理
- SQL 注入防護
- 檔案名稱清理

## 已知問題與限制

1. **空檔案：** `auth.py`、`config.py`、`models.py`、`static/style.css` 為空檔案
2. **上傳進度：** 目前使用模擬進度，非真實上傳進度
3. **檔案儲存：** 檔案直接存儲在本地檔案系統
4. **並發處理：** 未針對高並發場景優化

## 開發建議

### 待完善功能
- 實作真實檔案上傳進度
- 新增檔案預覽功能
- 實作檔案分類和標籤
- 新增批次操作功能
- 實作檔案版本控制
- 新增檔案分享權限控制

### 代碼重構建議
- 將認證邏輯移至 `auth.py`
- 將配置設定移至 `config.py`
- 將資料模型移至 `models.py`
- 新增自定義 CSS 樣式至 `static/style.css`

## 授權

本專案採用 [MIT License](LICENSE)。

## 貢獻指南

歡迎提交 Issue 和 Pull Request！

1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 建立 Pull Request

可以用python腳本更改admin密碼(預設:admin/admin123)
