import sqlite3
import pandas as pd
import streamlit as st
import io
import os
from datetime import datetime
import pytz

# --- DB 함수 등 생략 (기존과 동일) ---
def init_db():
    conn = sqlite3.connect("kostal_rework_v3.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, author TEXT, item_name TEXT, is_update TEXT, is_dtc TEXT)")
    conn.commit()
    return conn

conn = init_db()

def get_current_kst_time():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')

def insert_data(author, item_name, is_update, is_dtc):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)", (get_current_kst_time(), author, item_name, is_update, is_dtc))
    conn.commit()

def update_data(item_id, author, item_name, is_update, is_dtc):
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET timestamp=?, author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?", (get_current_kst_time(), author, item_name, is_update, is_dtc, item_id))
    conn.commit()

def delete_data(item_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()

def load_data():
    return pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)

# --- UI ---
st.set_page_config(page_title="KOSTAL", layout="centered")
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 수정 모드용 상태 관리
if "edit_id" not in st.session_state: st.session_state.edit_id = None

with st.form("entry_form"):
    author = st.text_input("이름", value=st.session_state.get("edit_author", ""))
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("edit_item", ""), max_chars=6)
    c1, c2 = st.columns(2)
    chk_update = c1.checkbox("업데이트", value=st.session_state.get("edit_upd", False))
    chk_dtc = c2.checkbox("DTC", value=st.session_state.get("edit_dtc", False))
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if st.session_state.edit_id:
            update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
            st.session_state.edit_id = None
        else:
            insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.rerun()

# 리스트 표시
df = load_data()
st.markdown("---")

for i, row in enumerate(df.itertuples(), 1):
    # 컬럼 비율: 정보(7) / 수정(1.5) / 삭제(1.5)
    cols = st.columns([7, 1.5, 1.5])
    
    with cols[0]:
        # 정보 한 줄 정렬: [순번] 시간 | VIN | 이름
        st.markdown(f"<small>{i}. {row.timestamp} | **{row.item_name}** | {row.author}</small>", unsafe_allow_html=True)
    
    with cols[1]:
        if st.button("수정", key=f"e{row.id}", use_container_width=True):
            st.session_state.update({"edit_id": row.id, "edit_author": row.author, "edit_item": row.item_name, "edit_upd": (row.is_update == 'Y'), "edit_dtc": (row.is_dtc == 'Y')})
            st.rerun()
    with cols[2]:
        if st.button("삭제", key=f"d{row.id}", use_container_width=True):
            delete_data(row.id)
            st.rerun()
