import sqlite3
import pandas as pd
import streamlit as st
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
            # 헤더에 공백이 있을 경우를 대비해 strip() 적용
            df = pd.read_excel(MASTER_FILE)
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            return pd.DataFrame()
    return pd.DataFrame()

def delete_all_data_by_vin(conn, item_id, item_name):
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
