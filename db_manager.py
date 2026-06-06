import sqlite3
import pandas as pd
import os

DB_NAME = "kostal_data.db"
MASTER_FILE = "master_vin_list.xlsx"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
    conn.execute("""
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
    """)
    conn.commit()
    return conn

def get_completion_counts():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
    cursor = conn.cursor()
    # 'is_new_zero'가 'Y'인 경우를 '교체완료', 'is_zero_adj'가 'Y'인 경우를 '캘리완료'로 카운트
    cursor.execute("SELECT COUNT(*) FROM items WHERE is_new_zero = 'Y'")
    update_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM items WHERE is_zero_adj = 'Y'")
    cali_count = cursor.fetchone()[0]
    conn.close()
    return {"update": update_count, "cali": cali_count}

def get_master_data():
    if os.path.exists(MASTER_FILE):
        try:
            df = pd.read_excel(MASTER_FILE)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()
