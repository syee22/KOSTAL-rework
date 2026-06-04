import sqlite3
import pandas as pd
import streamlit as st
import io
import os
from datetime import datetime
import pytz
from PIL import Image
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage

# --- 1. 데이터베이스 초기화 ---
def init_db():
    conn = sqlite3.connect("kostal_rework_v3.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, author TEXT, item_name TEXT,
            is_update TEXT, is_dtc TEXT       
        )
    """)
    conn.commit()
    return conn

conn = init_db()

# --- 2. 함수들 ---
def get_current_kst_time():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')

def insert_data(author, item_name, is_update, is_dtc):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)",
                   (get_current_kst_time(), author, item_name, is_update, is_dtc))
    conn.commit()

def update_data(item_id, author, item_name, is_update, is_dtc):
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET timestamp=?, author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?",
                   (get_current_kst_time(), author, item_name, is_update, is_dtc, item_id))
    conn.commit()

def delete_data(item_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()

def load_data():
    return pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)

# --- 3. UI 및 상태 관리 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 시스템")

# 세션 상태 초기화
if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
if "edit_id" not in st.session_state: st.session_state.edit_id = None

# 수정 모드일 때 기존 데이터 불러오기 로직
if st.session_state.edit_mode:
    st.warning(f"✏️ ID [{st.session_state.edit_id}] 수정 중")
    # 세션에 저장된 값을 폼에 반영
    author_val = st.session_state.get("form_author", "")
    item_val = st.session_state.get("form_item_name", "")
    upd_val = st.session_state.get("form_update", False)
    dtc_val = st.session_state.get("form_dtc", False)
else:
    author_val = ""
    item_val = ""
    upd_val = False
    dtc_val = False

# 입력 폼
author = st.text_input("👤 이름", value=author_val, key="in_author")
item_name = st.text_input("📦 VIN 6자리", value=item_val, max_chars=6, key="in_item")
c1, c2 = st.columns(2)
chk_update = c1.checkbox("🔄 업뎃", value=upd_val, key="in_upd")
chk_dtc = c2.checkbox("⚠️ DTC", value=dtc_val, key="in_dtc")

# 버튼 로직
if st.session_state.edit_mode:
    if st.button("✅ 수정 완료", type="primary", use_container_width=True):
        update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.session_state.edit_mode = False
        st.rerun()
    if st.button("❌ 취소"):
        st.session_state.edit_mode = False
        st.rerun()
else:
    if st.button("🚀 등록", type="primary", use_container_width=True):
        insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.rerun()

st.write("---")

# 현황 리스트
df = load_data()
st.markdown("##### 📋 마감 현황")
for _, row in df.iterrows():
    with st.container():
        b_col, i_col = st.columns([2, 8])
        with b_col:
            cols = st.columns(2)
            if cols[0].button("📝", key=f"e{row['id']}"):
                # 수정 버튼 클릭 시 세션에 정보 저장 후 리런
                st.session_state.update({
                    "edit_mode": True, 
                    "edit_id": row['id'], 
                    "form_author": row['author'], 
                    "form_item_name": row['item_name'],
                    "form_update": (row['is_update'] == "Y"),
                    "form_dtc": (row['is_dtc'] == "Y")
                })
                st.rerun()
            if cols[1].button("🗑️", key=f"d{row['id']}"):
                delete_data(row['id'])
                st.rerun()
        with i_col:
            st.write(f"**{row['item_name']}** ({row['author']}) / 🕒{row['timestamp']}")
    st.write("---")
