# 使用官方的 Python 輕量級映像作為基礎
FROM python:3.11-slim

# 在容器中設定工作目錄
WORKDIR /app

# 複製 requirements.txt 檔案到工作目錄
# 我們先只複製這個檔案並安裝依賴，這樣可以利用 Docker 的快取機制
# 未來如果只有程式碼變動而依賴不變，就不會重新安裝
COPY requirements.txt .

# 安裝 requirements.txt 中定義的所有 Python 套件
# --no-cache-dir 選項可以減少映像檔的大小
RUN pip install --no-cache-dir -r requirements.txt

# 將專案目錄下的所有檔案複製到容器的工作目錄中
COPY .. .

# 聲明容器將在 5000 連接埠上監聽
EXPOSE 5000

# 容器啟動時要執行的指令
# 執行 app.py 檔案
CMD ["python", "app.py"]