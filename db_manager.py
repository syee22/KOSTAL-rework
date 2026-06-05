import sqlite3

def init_db():
    conn = sqlite3.connect('kostal_data.db', check_same_thread=False)
    
    # 기존 5개 컬럼 구조로 테이블 생성
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            author TEXT,
            item_name TEXT,
            is_update TEXT,
            is_dtc TEXT
        )
    ''')
    
    # 사진 저장용 테이블
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
    # 해당 VIN의 사진만 조회
    return conn.execute("SELECT image FROM photos WHERE item_name = ?", (item_name,)).fetchall()

def delete_all_data_by_vin(conn, id, item_name):
    # 아이템 삭제
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    # 해당 VIN의 모든 사진 삭제
    conn.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
