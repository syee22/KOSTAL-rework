import sqlite3
import streamlit as st

def init_db():
    conn = sqlite3.connect('kostal_data.db', check_same_thread=False)
    c = conn.cursor()
    # 기존 테이블 구조 유지
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, author TEXT, item_name TEXT, 
                  is_update TEXT, is_dtc TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS photos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  item_name TEXT, photo_data BLOB)''')
    conn.commit()
    return conn

def save_photos_to_db(conn, item_name, photo_files):
    """
    모든 업로드된 파일을 순회하며 DB에 저장합니다.
    photo_files: 업로드된 파일 리스트
    """
    if photo_files:
        for file in photo_files:
            # 파일을 바이너리 데이터로 읽음
            img_data = file.getvalue()
            conn.execute("INSERT INTO photos (item_name, photo_data) VALUES (?, ?)", 
                         (item_name, img_data))
        conn.commit()

def get_photos_by_vin(conn, item_name):
    """
    특정 VIN에 해당하는 모든 사진 데이터를 가져옵니다.
    """
    c = conn.cursor()
    c.execute("SELECT photo_data FROM photos WHERE item_name = ?", (item_name,))
    return c.fetchall()

def delete_all_data_by_vin(conn, item_id, item_name):
    """
    아이템과 관련된 모든 데이터(항목 및 사진)를 삭제합니다.
    """
    c = conn.cursor()
    # 아이템 정보 삭제
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    # 해당 VIN의 모든 사진 삭제
    c.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
