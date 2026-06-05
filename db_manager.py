import sqlite3

def init_db():
    # 데이터베이스 파일 연결
    conn = sqlite3.connect('kostal_data.db', check_same_thread=False)
    
    # 1. 메인 리워크 테이블 생성 (요청하신 신규 3개 컬럼 포함)
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
    
    # 2. 사진 저장용 테이블 생성
    conn.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            image BLOB
        )
    ''')
    conn.commit()
    return conn

def save_photos_to_db(conn, item_name, photo_files):
    for photo in photo_files:
        image_data = photo.read()
        conn.execute("INSERT INTO photos (item_name, image) VALUES (?, ?)", (item_name, image_data))
    conn.commit()

def get_photos_by_vin(conn, item_name):
    return conn.execute("SELECT image FROM photos WHERE item_name = ?", (item_name,)).fetchall()

def delete_all_data_by_vin(conn, id, item_name):
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
