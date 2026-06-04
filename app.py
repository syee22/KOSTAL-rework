import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import db_manager

conn = db_manager.init_db()

# --- 함수 ---
def get_current_kst_time():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')

def insert_data(a, i, u, d):
    conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)", (get_current_kst_time(), a, i, u, d))
    conn.commit()

def update_data(id, a, i, u, d):
    conn.execute("UPDATE items SET timestamp=?, author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?", (get_current_kst_time(), a, i, u, d, id))
    conn.commit()

def delete_data(id):
    vin = conn.execute("SELECT item_name FROM items WHERE id = ?", (id,)).fetchone()
    if vin:
        db_manager.delete_photos_by_vin(conn, vin[0])
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.commit()

# --- UI ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 입력 폼
with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름")
    item_name = st.text_input("VIN 6자리", max_chars=6)
    photo_files = st.file_uploader("검사 사진 업로드 (최대 4개)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    c1, c2 = st.columns(2)
    chk_u, chk_d = c1.checkbox("업데이트"), c2.checkbox("DTC")
    
    if st.form_submit_button("🚀 등록"):
        if item_name:
            if photo_files:
                db_manager.save_photos_to_db(conn, item_name, photo_files)
            insert_data(author, item_name, "Y" if chk_u else "N", "Y" if chk_d else "N")
            st.rerun()

# 엑셀 저장
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
if not df.empty:
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        # 1. 메인 리스트 시트
        df[['timestamp', 'author', 'item_name', 'is_update', 'is_dtc']].to_excel(writer, sheet_name='리워크현황', index=False)
        
        # 2. 각 VIN 시트 생성 및 사진 배치
        for vin in df['item_name'].unique():
            photos = db_manager.get_photos_by_vin(conn, vin)
            if photos:
                sheet = writer.book.add_worksheet(name=str(vin))
                for idx, (img_data,) in enumerate(photos):
                    # B2, L2, V2, AF2 순으로 사진 배치
                    sheet.insert_image(chr(66 + (idx * 10)) + '2', 'photo.png', {'image_data': img_data, 'x_scale': 0.3, 'y_scale': 0.3})
    
    st.download_button("📥 엑셀(사진포함) 저장", towrite.getvalue(), "list_with_photos.xlsx", use_container_width=True)

# 리스트 표시 로직... (이전과 동일하게 유지)
