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
st.markdown("#### 📱 KOSTAL 시스템")

if "edit_mode" not in st.session_state: st.session_state.edit_mode = False

# 입력 폼
author = st.text_input("이름", value=st.session_state.get("form_author", ""), key="main_author")
item_name = st.text_input("VIN 6자리", value=st.session_state.get("form_item_name", ""), max_chars=6, key="main_vin")

c1, c2 = st.columns(2)
chk_update = c1.checkbox("업데이트", value=st.session_state.get("form_update", False), key="main_upd")
chk_dtc = c2.checkbox("DTC", value=st.session_state.get("form_dtc", False), key="main_dtc")

uploaded_file = st.file_uploader("📸 현장 사진 촬영/첨부", type=["png", "jpg", "jpeg"])

if st.session_state.edit_mode:
    if st.button("✅ 수정 완료", type="primary", use_container_width=True):
        update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.session_state.update({"edit_mode": False, "form_author": "", "form_item_name": "", "form_update": False, "form_dtc": False})
        st.rerun()
else:
    if st.button("🚀 등록", type="primary", use_container_width=True):
        insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.session_state.update({"form_author": "", "form_item_name": "", "form_update": False, "form_dtc": False})
        st.rerun()

st.write("---")

# 현황 리스트
df = load_data()
st.markdown(f"##### 📋 마감 현황 <span style='color:red; font-size:16px; font-weight:bold;'>({len(df)})</span>", unsafe_allow_html=True)

for _, row in df.iterrows():
    with st.container():
        cols = st.columns([5, 2.5, 2.5])
        with cols[0]:
            st.markdown(f"**{row['item_name']}**<br>{row['author']}", unsafe_allow_html=True)
        with cols[1]:
            if st.button("수정", key=f"btn_e_{row['id']}", use_container_width=True):
                st.session_state.update({
                    "edit_mode": True, "edit_id": row['id'], 
                    "form_author": row['author'], "form_item_name": row['item_name'], 
                    "form_update": (row['is_update']=="Y"), "form_dtc": (row['is_dtc']=="Y")
                })
                st.rerun()
        with cols[2]:
            if st.button("삭제", key=f"btn_d_{row['id']}", use_container_width=True):
                delete_data(row['id'])
                st.rerun()
    st.write("---")

# --- 4. 하단 다운로드 및 리셋 ---
st.markdown("##### 💾 백업 및 리셋")
col_d1, col_d2 = st.columns(2)

with col_d1:
    if not df.empty:
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button("📈 일반 저장", towrite, "KOSTAL_list.xlsx", use_container_width=True)

with col_d2:
    if os.path.exists("KOSTAL_photo_registry.xlsx"):
        with open("KOSTAL_photo_registry.xlsx", "rb") as f:
            st.download_button("📸 사진 저장", f, "KOSTAL_photo_registry.xlsx", use_container_width=True)

if st.button("🚨 전체 마감 리셋", use_container_width=True):
    clear_data()
    if os.path.exists("KOSTAL_photo_registry.xlsx"): os.remove("KOSTAL_photo_registry.xlsx")
    st.rerun()
