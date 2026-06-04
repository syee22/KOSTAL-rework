import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import db_manager  # 같은 폴더 내 db_manager.py 파일 필요

# DB 연결
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

# --- UI 설정 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 세션 상태 초기화
if "edit_id" not in st.session_state: st.session_state.edit_id = None
if "current_author" not in st.session_state: st.session_state.current_author = ""
if "next_vin" not in st.session_state: st.session_state.next_vin = ""
if "next_upd" not in st.session_state: st.session_state.next_upd = False
if "next_dtc" not in st.session_state: st.session_state.next_dtc = False

# 입력 폼
with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름", value=st.session_state.current_author)
    item_name = st.text_input("VIN 6자리", value=st.session_state.next_vin, max_chars=6)
    photo_files = st.file_uploader("검사 사진 업로드 (최대 4개)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    c1, c2 = st.columns(2)
    chk_u = c1.checkbox("업데이트", value=st.session_state.next_upd)
    chk_d = c2.checkbox("DTC", value=st.session_state.next_dtc)
    
    submit_btn = st.form_submit_button("🚀 등록 / ✅ 수정 완료")

# 데이터 처리 로직 (폼 바깥)
if submit_btn:
    if item_name:
        if photo_files:
            db_manager.save_photos_to_db(conn, item_name, photo_files)
        
        if st.session_state.edit_id:
            update_data(st.session_state.edit_id, author, item_name, "Y" if chk_u else "N", "Y" if chk_d else "N")
        else:
            insert_data(author, item_name, "Y" if chk_u else "N", "Y" if chk_d else "N")
    
    st.session_state.edit_id = None
    st.session_state.next_vin = ""
    st.session_state.next_upd = False
    st.session_state.next_dtc = False
    st.rerun()

st.write("---")

# 리스트 로드 및 검색
df_all = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
search = st.text_input("🔍 이름 또는 VIN 검색")
df = df_all[df_all['item_name'].str.contains(search, na=False) | df_all['author'].str.contains(search, na=False)] if search else df_all

# 등록 현황 및 엑셀 저장
t_col, b_col = st.columns([6, 4])
with t_col:
    u_cnt, d_cnt = len(df[df['is_update'] == 'Y']), len(df[df['is_dtc'] == 'Y'])
    st.markdown(f"##### 📋 등록 현황 {len(df)}건 <span style='font-size:12px;'>| 업뎃:{u_cnt} | DTC:{d_cnt}</span>", unsafe_allow_html=True)

with b_col:
    if not df.empty:
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            df_ex = df[['timestamp', 'author', 'item_name', 'is_update', 'is_dtc']].copy()
            df_ex.columns = ['시간', '이름', 'VIN', '업데이트', 'DTC']
            df_ex.to_excel(writer, sheet_name='리워크현황', index=False)
            
            for vin in df['item_name'].unique():
                photos = db_manager.get_photos_by_vin(conn, vin)
                if photos:
                    sheet = writer.book.add_worksheet(name=str(vin))
                    for idx, (img_data,) in enumerate(photos):
                        sheet.insert_image(chr(66 + (idx * 10)) + '2', 'photo.png', {'image_data': img_data, 'x_scale': 0.3, 'y_scale': 0.3})
        
        st.download_button("📥 엑셀(사진포함) 저장", towrite.getvalue(), "list_with_photos.xlsx", use_container_width=True)

# 리스트 표시
for row in df.itertuples():
    cols = st.columns([6, 2, 2])
    with cols[0]:
        st.markdown(f"<small>{row.timestamp} | **{row.item_name}** | {row.author}<br>UPDATE:{row.is_update} / DTC:{row.is_dtc}</small>", unsafe_allow_html=True)
    with cols[1]:
        if st.button("수정", key=f"e{row.id}"):
            st.session_state.update({"edit_id": row.id, "current_author": row.author, "next_vin": row.item_name, "next_upd": (row.is_update=='Y'), "next_dtc": (row.is_dtc=='Y')})
            st.rerun()
    with cols[2]:
        if st.button("삭제", key=f"d{row.id}"):
            delete_data(row.id)
            st.rerun()
