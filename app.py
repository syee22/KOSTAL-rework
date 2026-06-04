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

def enter_edit_mode(row):
    st.session_state.edit_id = row['id']
    st.session_state.edit_author = row['author']
    st.session_state.edit_item = row['item_name']
    st.session_state.edit_upd = (row['is_update'] == 'Y')
    st.session_state.edit_dtc = (row['is_dtc'] == 'Y')

# 입력 폼
with st.form("entry_form"):
    author = st.text_input("이름", value=st.session_state.get("edit_author", ""))
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("edit_item", ""), max_chars=6)
    c1, c2 = st.columns(2)
    chk_update = c1.checkbox("업데이트", value=st.session_state.get("edit_upd", False))
    chk_dtc = c2.checkbox("DTC", value=st.session_state.get("edit_dtc", False))
    
    submit_btn = st.form_submit_button("🚀 등록 / ✅ 수정 완료")
    if submit_btn:
        if st.session_state.edit_id:
            update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
            st.session_state.edit_id = None
        else:
            insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.rerun()

st.write("---")

# 리스트 표시 영역
df = load_data()
search = st.text_input("🔍 VIN 또는 이름 검색")
if search:
    df = df[df['item_name'].str.contains(search, na=False) | df['author'].str.contains(search, na=False)]

upd_count = len(df[df['is_update'] == 'Y'])
dtc_count = len(df[df['is_dtc'] == 'Y'])

# 타이틀 + 엑셀 저장 버튼 영역
t_col, b_col = st.columns([6, 4])
with t_col:
    st.markdown(f"##### 📋 리스트 <span style='color:red;'>({len(df)})</span> <span style='color:blue; font-size:12px;'>| 업뎃:{upd_count} | DTC:{dtc_count}</span>", unsafe_allow_html=True)
with b_col:
    if not df.empty:
        export_df = df.copy()
        export_df['순번'] = range(1, len(df) + 1)
        export_df = export_df[['순번', 'timestamp', 'author', 'item_name', 'is_update', 'is_dtc']]
        export_df.columns = ['순번', '시간', '이름', 'VIN 넘버', '업데이트', 'DTC']
        towrite = io.BytesIO()
        export_df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button("📥 엑셀 저장", towrite, "KOSTAL_list.xlsx", use_container_width=True)

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
    st.write("---")
