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

def clear_data():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items")
    conn.commit()

def save_image_to_excel(item_name, is_update, is_dtc, uploaded_file):
    excel_filename = "KOSTAL_photo_registry.xlsx"
    wb = openpyxl.load_workbook(excel_filename) if os.path.exists(excel_filename) else openpyxl.Workbook()
    clean_name = "".join(c for c in item_name if c not in r'\/??*[]:').strip()[:30] or "VIN"
    ws = wb[clean_name] if clean_name in wb.sheetnames else wb.create_sheet(title=clean_name)
    if ws.max_row == 1 and ws['A1'].value is None:
        ws.append(["시간", "이름", "VIN 넘버", "업데이트", "DTC", "첨부 사진"])
    
    img = Image.open(uploaded_file)
    img.thumbnail((400, 400))
    img_byte = io.BytesIO()
    img.convert("RGB").save(img_byte, format='JPEG', quality=75)
    img_byte.seek(0)
    
    xl_img = OpenpyxlImage(img_byte)
    next_row = ws.max_row + 1
    ws.append([get_current_kst_time(), st.session_state.form_author, item_name, is_update, is_dtc])
    ws.add_image(xl_img, f'F{next_row}')
    ws.row_dimensions[next_row].height = 160
    wb.save(excel_filename)

@st.dialog("⚠️ 삭제 확인")
def confirm_delete_dialog(item_id, item_name):
    st.write(f"VIN **[{item_name}]**를 삭제할까요?")
    if st.button("삭제", use_container_width=True):
        delete_data(item_id)
        st.rerun()

# --- 3. UI 및 상태 관리 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 시스템")

if "edit_mode" not in st.session_state: st.session_state.edit_mode = False

# 입력 폼
author = st.text_input("👤 이름", value=st.session_state.get("form_author", ""), placeholder="이름")
item_name = st.text_input("📦 VIN 6자리", value=st.session_state.get("form_item_name", ""), max_chars=6, placeholder="123456")
c1, c2, c3 = st.columns(3)
chk_update = c1.checkbox("🔄 업뎃", value=st.session_state.get("form_update", False))
chk_dtc = c2.checkbox("⚠️ DTC", value=st.session_state.get("form_dtc", False))
uploaded_file = st.file_uploader("📸 사진 첨부", type=["png", "jpg", "jpeg"])

# 버튼 로직
if st.session_state.edit_mode:
    if st.button("✅ 수정 완료", type="primary", use_container_width=True):
        update_data(st.session_state.edit_id, author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        if uploaded_file: save_image_to_excel(item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N", uploaded_file)
        st.session_state.edit_mode = False; st.rerun()
else:
    if st.button("🚀 등록", type="primary", use_container_width=True):
        insert_data(author, item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N")
        if uploaded_file: save_image_to_excel(item_name, "Y" if chk_update else "N", "Y" if chk_dtc else "N", uploaded_file)
        st.rerun()

st.write("---")

# 현황 리스트
df = load_data()
st.markdown("##### 📋 마감 현황")
query = st.text_input("", placeholder="🔍 검색", label_visibility="collapsed")
if not df.empty:
    target = df[df['item_name'].str.contains(query, na=False) | df['author'].str.contains(query, na=False)] if query else df
    for _, row in target.iterrows():
        with st.container():
            b_col, i_col = st.columns([2, 8])
            with b_col:
                cols = st.columns(2)
                if cols[0].button("📝", key=f"e{row['id']}"):
                    st.session_state.update({"edit_mode": True, "edit_id": row['id'], "form_author": row['author'], "form_item_name": row['item_name']})
                    st.rerun()
                if cols[1].button("🗑️", key=f"d{row['id']}"): confirm_delete_dialog(row['id'], row['item_name'])
            with i_col:
                st.write(f"**{row['item_name']}** ({row['author']}) / 🕒{row['timestamp']}")
        st.write("---")
