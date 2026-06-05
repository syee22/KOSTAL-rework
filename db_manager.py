import sqlite3
import pandas as pd
import streamlit as st
import os

# 데이터베이스 파일명
DB_NAME = "kostal_data.db"
# 마스터 파일명 (필요 시 수정하세요)
MASTER_FILE = "master_list.xlsx"

def init_db():
    """데이터베이스 및 테이블 초기화"""
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
    """엑셀 마스터 파일 불러오기"""
    if os.path.exists(MASTER_FILE):
        return pd.read_excel(MASTER_FILE)
    else:
        st.error(f"마스터 파일({MASTER_FILE})을 찾을 수 없습니다.")
        return pd.DataFrame()

def save_photos_to_db(conn, item_name, files):
    """
    사진 파일을 처리하는 함수 (예시)
    현재 프로젝트 구조에 맞춰 사진 저장 경로 로직 등을 여기에 추가하세요.
    """
    # 예: 저장 경로 지정 등
    pass

def delete_all_data_by_vin(conn, item_id, item_name):
    """특정 ID의 작업 내역 삭제"""
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
