import sqlite3
import pandas as pd
import streamlit as st
import io
import pytz
from datetime import datetime

# --- 1. DB 설정 ---
def init_db():
    conn = sqlite3.connect("kostal_rework_v3.db", check_same_thread=False)
    # 리워크 데이터 테이블
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, author TEXT, item_name TEXT, is_update TEXT, is_dtc TEXT)")
    # 사진 저장용 테이블 (VIN별, 순번별 저장 - 복합 기본키 사용)
    conn.execute("CREATE TABLE IF NOT EXISTS photos (vin TEXT, seq INTEGER, image_data BLOB, PRIMARY KEY (vin, seq))")
    conn.commit()
    return conn

conn = init_db()

# --- 2. 함수 ---
def get_current_kst_time():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')

def insert_data(a, i, u, d):
    conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)", (get_current_kst_time(), a, i, u, d))
    conn.commit()

def update_data(id, a, i, u, d):
    conn.execute("UPDATE items SET timestamp=?, author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?", (get_current_kst_time(), a, i, u, d, id))
    conn.commit()

def delete_data(id):
    # 아이템 삭제 시 해당 VIN의 사진도 함께 삭제
    vin = conn.execute("SELECT item_name FROM items WHERE id = ?", (id,)).fetchone()
    if vin:
        conn.execute("DELETE FROM photos WHERE vin = ?", (vin[0],))
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.commit()

def save_photos(vin, files):
    conn.execute("DELETE FROM photos WHERE vin = ?", (vin,))
    for idx, file in enumerate(files[:4]): # 최대 4개까지만 저장
        conn.execute("INSERT INTO photos (vin, seq, image_data) VALUES (?, ?, ?)", (vin, idx, file.getvalue()))
    conn.commit()

# --- 3. UI ---
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
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if item_name:
            if photo_files:
                save_photos(item_name, photo_files)
            
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

# 데이터 로드 및 검색
df_all = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
search = st.text_input("🔍 이름 또는 VIN 검색")
df = df_all[df_all['item_name'].str.contains(search, na=False) | df_all['author'].str.contains(search, na=False)] if search else df_all

u_cnt = len(df[df['is_update'] == 'Y'])
d_cnt = len(df[df['is_dtc'] == 'Y'])

# 등록 현황 및 엑셀 저장
t_col, b_col = st.columns([6, 4])
with t_col:
    st.markdown(f"##### 📋 등록 현황 <span style='color:black;'>{len(df)}건</span> <span style='color:blue; font-size:12px;'>| 업뎃:{u_cnt} | DTC:{d_cnt}</span>", unsafe_allow_html=True)
with b_col:
    if not df.empty:
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            df_ex = df.copy()
            df_ex['순번'] = range(1, len(df)+1)
            df_ex = df_ex[['순번', 'timestamp', 'author', 'item_name', 'is_update', 'is_dtc']]
            df_ex.columns = ['순번', '시간', '이름', 'VIN', '업데이트', 'DTC']
            df_ex.to_excel(writer, sheet_name='리워크현황', index=False)
            
            # 각 VIN 시트 생성 및 사진 삽입
            for vin in df['item_name'].unique():
                photos = conn.execute("SELECT image_data FROM photos WHERE vin = ? ORDER BY seq", (vin,)).fetchall()
                if photos:
                    sheet = writer.book.add_worksheet(name=str(vin))
                    for idx, (img_data,) in enumerate(photos):
                        # B2, L2, V2, AF2 순으로 사진 배치
                        cell_loc = chr(66 + (idx * 10)) + '2' 
                        sheet.insert_image(cell_loc, 'photo.png', {'image_data': img_data, 'x_scale': 0.3, 'y_scale': 0.3})
        
        st.download_button("📥 엑셀(사진포함) 저장", towrite.getvalue(), "list_with_photos.xlsx", use_container_width=True)

# 리스트 표시
for row in df.itertuples():
    cols = st.columns([6, 2, 2])
    with cols[0]:
        info_text = f"<small>{row.timestamp} | **{row.item_name}** | {row.author}<br>UPDATE:{row.is_update} / DTC:{row.is_dtc}</small>"
        st.markdown(info_text, unsafe_allow_html=True)
    with cols[1]:
        if st.button("수정", key=f"e{row.id}", use_container_width=True):
            st.session_state.update({"edit_id": row.id, "current_author": row.author, "next_vin": row.item_name, "next_upd": (row.is_update=='Y'), "next_dtc": (row.is_dtc=='Y')})
            st.rerun()
    with cols[2]:
        if st.button("삭제", key=f"d{row.id}", use_container_width=True):
            delete_data(row.id)
            st.rerun()
