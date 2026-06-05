import sqlite3

def init_db():
    # 1. 파일명을 바꾸어 기존의 꼬인 DB와 완전히 분리합니다.
    db_path = 'kostal_final.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # 2. 테이블 생성 (IF NOT EXISTS를 사용하여 안전하게)
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
    try:
        return conn.execute("SELECT image FROM photos WHERE item_name = ?", (item_name,)).fetchall()
    except sqlite3.OperationalError:
        # 테이블이 존재하지 않는 경우 빈 리스트 반환
        return []

def delete_all_data_by_vin(conn, id, item_name):
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
