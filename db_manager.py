import sqlite3

def init_db():
    conn = sqlite3.connect("kostal_rework_v3.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, author TEXT, item_name TEXT, is_update TEXT, is_dtc TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS photos (vin TEXT, seq INTEGER, image_data BLOB, PRIMARY KEY (vin, seq))")
    conn.commit()
    return conn

def save_photos_to_db(conn, vin, files):
    conn.execute("DELETE FROM photos WHERE vin = ?", (vin,))
    for idx, file in enumerate(files[:4]):
        conn.execute("INSERT INTO photos (vin, seq, image_data) VALUES (?, ?, ?)", (vin, idx, file.getvalue()))
    conn.commit()

def get_photos_by_vin(conn, vin):
    return conn.execute("SELECT image_data FROM photos WHERE vin = ? ORDER BY seq", (vin,)).fetchall()
def delete_photos_by_vin(conn, vin):
    conn.execute("DELETE FROM photos WHERE vin = ?", (vin,))
    conn.commit()
