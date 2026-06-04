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

# --- 3. UI 및 상태 관리 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 시스템")

if "edit_mode" not in st.session_state: st.session_state.edit_mode = False

# 입력 폼
author = st.text_input("이름", value=st.session_state.get("form_author", ""), key="in_author")
item_name = st.text_input("VIN 6자리", value=st.session_state.get("form_item_name", ""), max_chars=6, key="in_item")
c1, c2 = st.columns(2)
chk_update = c1.checkbox("업데이트", value=st.session_state.get("form_update", False), key="in_upd")
chk_dtc = c2.checkbox("DTC", value=st.session_state.get("form_dtc", False), key="in_dtc")

if st.session_state.edit_mode:
    if st.button("✅ 수정 완료", type="primary", use_container_width=True):
        update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.session_state.edit_mode = False
        st.rerun()
else:
    if st.button("🚀 등록", type="primary", use_container_width=True):
        insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.rerun()

st.write("---")

# 현황 리스트 (전체 개수 빨간 표시)
df = load_data()
count = len(df)
# 빨간색 배지 스타일 적용 (HTML 사용)
st.markdown(f"##### 📋 마감 현황 <span style='color:red; font-size:16px; font-weight:bold;'>({count})</span>", unsafe_allow_html=True)

for _, row in df.iterrows():
    # 정보(5) + 수정버튼(2.5) + 삭제버튼(2.5) 비율
    cols = st.columns([5, 2.5, 2.5])
    
    with cols[0]:
        st.markdown(f"**{row['item_name']}**<br>{row['author']}", unsafe_allow_html=True)
    with cols[1]:
        if st.button("수정", key=f"e{row['id']}", use_container_width=True):
            st.session_state.update({
                "edit_mode": True, "edit_id": row['id'], 
                "form_author": row['author'], "form_item_name": row['item_name'], 
                "form_update": (row['is_update']=="Y"), "form_dtc": (row['is_dtc']=="Y")
            })
            st.rerun()
    with cols[2]:
        if st.button("삭제", key=f"d{row['id']}", use_container_width=True):
            delete_data(row['id'])
            st.rerun()
    
    st.write("---")
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

# --- 3. UI 및 상태 관리 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 시스템")

if "edit_mode" not in st.session_state: st.session_state.edit_mode = False

# 입력 폼
author = st.text_input("이름", value=st.session_state.get("form_author", ""), key="in_author")
item_name = st.text_input("VIN 6자리", value=st.session_state.get("form_item_name", ""), max_chars=6, key="in_item")
c1, c2 = st.columns(2)
chk_update = c1.checkbox("업데이트", value=st.session_state.get("form_update", False), key="in_upd")
chk_dtc = c2.checkbox("DTC", value=st.session_state.get("form_dtc", False), key="in_dtc")

if st.session_state.edit_mode:
    if st.button("✅ 수정 완료", type="primary", use_container_width=True):
        update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.session_state.edit_mode = False
        st.rerun()
else:
    if st.button("🚀 등록", type="primary", use_container_width=True):
        insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        st.rerun()

st.write("---")

# 현황 리스트 (내용 - 수정 - 삭제 한 줄 정렬)
df = load_data()
st.markdown("##### 📋 마감 현황")

for _, row in df.iterrows():
    # 정보(5) + 수정버튼(2.5) + 삭제버튼(2.5) 비율로 강제 고정
    cols = st.columns([5, 2.5, 2.5])
    
    with cols[0]:
        # 이름을 굵게 표시하여 가독성 향상
        st.markdown(f"**{row['item_name']}**<br>{row['author']}", unsafe_allow_html=True)
    with cols[1]:
        if st.button("수정", key=f"e{row['id']}", use_container_width=True):
            st.session_state.update({
                "edit_mode": True, "edit_id": row['id'], 
                "form_author": row['author'], "form_item_name": row['item_name'], 
                "form_update": (row['is_update']=="Y"), "form_dtc": (row['is_dtc']=="Y")
            })
            st.rerun()
    with cols[2]:
        if st.button("삭제", key=f"d{row['id']}", use_container_width=True):
            delete_data(row['id'])
            st.rerun()
    
    st.write("---")
