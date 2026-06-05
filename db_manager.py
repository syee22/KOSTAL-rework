import sqlite3

def init_db():
    # 파일명을 바꾸면 서버에 남아있던 이전 꼬인 파일과 무관하게 새 DB가 생성됩니다.
    db_path = 'kostal_final.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
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
    # 안전장치: 테이블이 없는 경우를 대비
    try:
        return conn.execute("SELECT image FROM photos WHERE item_name = ?", (item_name,)).fetchall()
    except:
        return []

def delete_all_data_by_vin(conn, id, item_name):
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
