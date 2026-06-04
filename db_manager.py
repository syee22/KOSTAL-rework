import sqlite3

def init_db():
    conn = sqlite3.connect("kostal_rework_v3.db", check_same_thread=False)
    # 데이터 테이블
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, author TEXT, item_name TEXT, is_update TEXT, is_dtc TEXT)")
    # 사진 테이블: vin과 seq를 조합한 복합키 사용 (VIN당 사진 4장 가능)
    conn.execute("CREATE TABLE IF NOT EXISTS photos (vin TEXT, seq INTEGER, image_data BLOB, PRIMARY KEY (vin, seq))")
    conn.commit()
    return conn

def save_photos_to_db(conn, vin, files):
    conn.execute("DELETE FROM photos WHERE vin = ?", (vin,)) # 기존 사진 삭제 후 재저장
    for idx, file in enumerate(files[:4]): # 최대 4개 제한
        conn.execute("INSERT INTO photos (vin, seq, image_data) VALUES (?, ?, ?)", (vin, idx, file.getvalue()))
    conn.commit()

def get_photos_by_vin(conn, vin):
    return conn.execute("SELECT image_data FROM photos WHERE vin = ? ORDER BY seq", (vin,)).fetchall()

def delete_photos_by_vin(conn, vin):
    conn.execute("DELETE FROM photos WHERE vin = ?", (vin,))
    conn.commit()
