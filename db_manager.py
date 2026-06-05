import sqlite3
import pandas as pd
import os

def init_db():
    # 기존에 사용하시던 DB 파일명 유지
    db_path = 'kostal_final_v2.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # 1. 리워크 내역 테이블 (기존)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            author TEXT,
            item_name TEXT,
            is_update TEXT,
            is_dtc TEXT,
            is_new_zero TEXT,
            is_zero_adj TEXT,
            remark TEXT
        )
    ''')
    
    # 2. 사진 저장 테이블 (기존)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            image BLOB
        )
    ''')
    
    # 3. 타업체 작업 내역 테이블 (추가)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS external_work (
            vin TEXT PRIMARY KEY,
            company TEXT
        )
    ''')
    
    conn.commit()
    return conn

# --- 마스터 데이터(Git) 로드 함수 ---
def get_master_data():
    if os.path.exists('master_vin_list.xlsx'):
        return pd.read_excel('master_vin_list.xlsx')
    return pd.DataFrame()

# --- 타업체 데이터 업데이트 함수 ---
def update_external_work(conn, df):
    # 업로드 엑셀 컬럼이 [VIN, 업체명] 순서라고 가정합니다.
    df.columns = ['VIN', 'company']
    conn.execute("DELETE FROM external_work")
    df.to_sql('external_work', conn, if_exists='append', index=False)
    conn.commit()

# --- 기존 함수들 (변경 없음) ---
def save_photos_to_db(conn, item_name, photo_files):
    for photo in photo_files:
        image_data = photo.read()
        conn.execute("INSERT INTO photos (item_name, image) VALUES (?, ?)", (item_name, image_data))
    conn.commit()

def get_photos_by_vin(conn, item_name):
    try:
        return conn.execute("SELECT image FROM photos WHERE item_name = ?", (item_name,)).fetchall()
    except:
        return []

def delete_all_data_by_vin(conn, id, item_name):
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
