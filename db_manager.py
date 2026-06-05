import sqlite3
import pandas as pd
import streamlit as st
import os

DB_NAME = "kostal_data.db"
MASTER_FILE = "master_vin_list.xlsx" # 파일명 수정 완료

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
        return pd.read_excel(MASTER_FILE)
    else:
        return pd.DataFrame(columns=['VIN', '현재출고', '우선순위'])

def delete_all_data_by_vin(conn, item_id, item_name):
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
