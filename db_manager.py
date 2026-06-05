import sqlite3
import pandas as pd
import os

DB_NAME = "kostal_data.db"
MASTER_FILE = "master_vin_list.xlsx"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
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

def get_master_data():
    if os.path.exists(MASTER_FILE):
        try:
            df = pd.read_excel(MASTER_FILE)
            # 모든 컬럼명을 문자열로 변환하고 공백 제거 (매칭 오류 방지)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()
