import sqlite3
import pandas as pd
import streamlit as st
import io
import pytz
from datetime import datetime
import db_manager # 별도 파일 import

# DB 연결
conn = db_manager.init_db()

# --- 기타 함수들 (app.py 유지) ---
def get_current_kst_time():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')

def insert_data(a, i, u, d):
    conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)", (get_current_kst_time(), a, i, u, d))
    conn.commit()

def update_data(id, a, i, u, d):
    conn.execute("UPDATE items SET timestamp=?, author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?", (get_current_kst_time(), a, i, u, d, id))
    conn.commit()

def delete_data(id):
    vin = conn.execute("SELECT item_name FROM items WHERE id = ?", (id,)).fetchone()
    if vin:
        conn.execute("DELETE FROM photos WHERE vin = ?", (vin[0],))
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.commit()

# --- UI 및 나머지 로직은 그대로 유지 ---
# (입력 폼 내 저장 부분)
if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
    if item_name:
        if photo_files:
            db_manager.save_photos_to_db(conn, item_name, photo_files) # 별도 파일 함수 호출
        # ... 이하 동일 ...

# (엑셀 저장 부분)
for vin in df['item_name'].unique():
    photos = db_manager.get_photos_by_vin(conn, vin) # 별도 파일 함수 호출
    if photos:
        sheet = writer.book.add_worksheet(name=str(vin))
        for idx, (img_data,) in enumerate(photos):
            cell_loc = chr(66 + (idx * 10)) + '2' 
            sheet.insert_image(cell_loc, 'photo.png', {'image_data': img_data, 'x_scale': 0.3, 'y_scale': 0.3})
