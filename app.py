import sqlite3
import pandas as pd
import streamlit as st
import io
import os
from datetime import datetime
import pytz

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

# --- 2. 기본 함수 ---
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

def clear_data():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items")
    conn.commit()

# --- 3. UI 및 상태 관리 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 수정 모드용 상태 관리
if "edit_id" not in st.session_state: st.session_state.edit_id = None

# 수정 버튼 클릭 처리 (루프 밖에서 처리)
def enter_edit_mode(row):
    st.session_state.edit_id = row['id']
    st.session_state.edit_author = row['author']
    st.session_state.edit_item = row['item_name']
    st.session_state.edit_upd = (row['is_update'] == 'Y')
    st.session_state.edit_dtc = (row['is_dtc'] == 'Y')

# 입력 폼 (수정 모드일 때만 데이터 채움)
with st.form("entry_form", clear_on_submit=True):
    author = st.text_input("이름", value=st.session_state.get("edit_author", ""))
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("edit_item", ""), max_chars=6)
    c1, c2 = st.columns(2)
    chk_update = c1.checkbox("업데이트", value=st.session_state.get("edit_upd", False))
    chk_dtc = c2.checkbox("DTC", value=st.session_state.get("edit_dtc", False))
    
    submit_btn = st.form_submit_button("🚀 등록 / ✅ 수정 완료")
    
    if submit_btn:
        if st.session_state.edit_id:
            update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
            st.session_state.edit_id = None # 수정 완료 후 ID 초기화
        else:
            insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.rerun()

st.write("---")

# 리스트 표시
df = load_data()
if search := st.text_input("🔍 VIN 또는 이름 검색"):
    df = df[df['item_name'].str.contains(search, na=False) | df['author'].str.contains(search, na=False)]

# ... (타이틀 및 개수 표시 로직 동일) ...
upd_count = len(df[df['is_update'] == 'Y'])
dtc_count = len(df[df['is_dtc'] == 'Y'])

st.markdown(f"##### 📋 KOSTAL 리워크 현황 ({len(df)}) | 업뎃:{upd_count} | DTC:{dtc_count}")

for _, row in df.iterrows():
    cols = st.columns([5, 2.5, 2.5])
    with cols[0]:
        st.write(f"**{row['item_name']}** / {row['author']}")
    with cols[1]:
        if st.button("수정", key=f"e{row['id']}"):
            enter_edit_mode(row)
            st.rerun()
    with cols[2]:
        if st.button("삭제", key=f"d{row['id']}"):
            delete_data(row['id'])
            st.rerun()
