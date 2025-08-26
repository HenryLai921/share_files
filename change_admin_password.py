#!/usr/bin/env python3
"""
直接修改管理員密碼的腳本
使用方式：python change_admin_password.py
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

# 資料庫路徑（與 app.py 中的設定一致）
DATABASE = 'instance/database.db'


def change_admin_password():
    """修改管理員密碼"""

    # 檢查資料庫是否存在
    if not os.path.exists(DATABASE):
        print(f"錯誤：找不到資料庫檔案 {DATABASE}")
        print("請確保您在正確的專案目錄中執行此腳本")
        return

    # 輸入新密碼
    new_password = input("請輸入管理員的新密碼: ").strip()

    if not new_password:
        print("錯誤：密碼不能為空")
        return

    # 確認密碼
    confirm_password = input("請再次確認新密碼: ").strip()

    if new_password != confirm_password:
        print("錯誤：兩次輸入的密碼不一致")
        return

    try:
        # 連接資料庫
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 檢查 admin 使用者是否存在
        cursor.execute("SELECT id, username FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()

        if not admin_user:
            print("錯誤：找不到 admin 使用者")
            conn.close()
            return

        # 產生加密密碼
        hashed_password = generate_password_hash(new_password)

        # 更新密碼
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (hashed_password,)
        )

        # 確認更新成功
        if cursor.rowcount > 0:
            conn.commit()
            print("成功：管理員密碼已更新")
        else:
            print("錯誤：密碼更新失敗")

        conn.close()

    except sqlite3.Error as e:
        print(f"資料庫錯誤：{e}")
    except Exception as e:
        print(f"發生錯誤：{e}")


if __name__ == "__main__":
    print("=== 檔案管理系統 - 管理員密碼修改工具 ===")
    print()
    change_admin_password()
    print()
    print("完成。請重新啟動應用程式使變更生效。")