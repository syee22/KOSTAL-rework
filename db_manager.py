import sqlite3

def init_db():
    conn = sqlite3.connect('kostal_data.db', check_same_thread=False)
    
    # 1. 메인 테이블 생성
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            author TEXT,
            item_name TEXT,
            is_update TEXT,
            is_dtc TEXT,
            is_new_zero TEXT DEFAULT 'N',
            is_zero_adj TEXT DEFAULT 'N',
            remark TEXT DEFAULT ''
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
    
    # 3. 컬럼 누락 방지 (기존 테이블이 있다면 컬럼 추가)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(items)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'is_new_zero' not in columns:
        conn.execute("ALTER TABLE items ADD COLUMN is_new_zero TEXT DEFAULT 'N'")
    if 'is_zero_adj' not in columns:
        conn.execute("ALTER TABLE items ADD COLUMN is_zero_adj TEXT DEFAULT 'N'")
    if 'remark' not in columns:
        conn.execute("ALTER TABLE items ADD COLUMN remark TEXT DEFAULT ''")
    
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
    # 아이템 삭제
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    # 해당 VIN의 모든 사진 삭제
    conn.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
