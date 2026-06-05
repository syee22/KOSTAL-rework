import sqlite3
import pandas as pd
import os

def init_db():
    db_path = 'kostal_final_v2.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    conn.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, author TEXT, 
        item_name TEXT, is_update TEXT, is_dtc TEXT, 
        is_new_zero TEXT, is_zero_adj TEXT, remark TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, image BLOB)''')
    
    conn.commit()
    return conn

def get_master_data():
    if os.path.exists('master_vin_list.xlsx'):
        return pd.read_excel('master_vin_list.xlsx')
    return pd.DataFrame()

def save_photos_to_db(conn, item_name, photo_files):
    for photo in photo_files:
        image_data = photo.read()
        conn.execute("INSERT INTO photos (item_name, image) VALUES (?, ?)", (item_name, image_data))
    conn.commit()

def get_photos_by_vin(conn, item_name):
    try: return conn.execute("SELECT image FROM photos WHERE item_name = ?", (item_name,)).fetchall()
    except: return []

def delete_all_data_by_vin(conn, id, item_name):
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.execute("DELETE FROM photos WHERE item_name = ?", (item_name,))
    conn.commit()
