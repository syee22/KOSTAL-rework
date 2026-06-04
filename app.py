import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import db_manager

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

# --- UI 설정 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 세션 상태 초기화
if "edit_id" not in st.session_state: st.session_state.edit_id = None
if "current_author" not in st.session_state: st.session_state.current_author = ""
if "next_vin" not in st.session_state: st.session_state.next_vin = ""
if "next_upd" not in st.session_state: st.session_state.next_upd = False
if "next_dtc" not in st.session_state: st.session_state.next_dtc = False

# --- 수정/삭제 요청 처리 (URL 파라미터 기반) ---
query_params = st.query_params
if "del" in query_params:
    del_id = int(query_params["del"][0])
    row = conn.execute("SELECT item_name FROM items WHERE id=?", (del_id,)).fetchone()
    if row:
        db_manager.delete_all_data_by_vin(conn, del_id, row[0])
        st.query_params.clear()
        st.rerun()

if "edit" in query_params:
    edit_id = int(query_params["edit"][0])
    row = conn.execute("SELECT * FROM items WHERE id=?", (edit_id,)).fetchone()
    if row:
        st.session_state.update({"edit_id": row[0], "current_author": row[2], "next_vin": row[3], "next_upd": (row[4]=='Y'), "next_dtc": (row[5]=='Y')})
        st.query_params.clear()
        st.rerun()

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
                db_manager.save_photos_to_db(conn, item_name, photo_files)
            if st.session_state.edit_id:
                update_data(st.session_state.edit_id, author, item_name, "Y" if chk_u else "N", "Y" if chk_d else "N")
            else:
                insert_data(author, item_name, "Y" if chk_u else "N", "Y" if chk_d else "N")
        
        st.session_state.update({"edit_id": None, "current_author": author, "next_vin": "", "next_upd": False, "next_dtc": False})
        st.rerun()

st.write("---")

# 데이터 로드 및 검색
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
search = st.text_input("🔍 이름 또는 VIN 검색")
if search:
    df = df[df['item_name'].str.contains(search, na=False) | df['author'].str.contains(search, na=False)]

# 통계 및 저장
u_cnt, d_cnt = len(df[df['is_update'] == 'Y']), len(df[df['is_dtc'] == 'Y'])
t_col, b_col1, b_col2 = st.columns([4, 3, 3])
with t_col:
    st.markdown(f"##### 📋 {len(df)}건 <small>| 업뎃:{u_cnt} | DTC:{d_cnt}</small>", unsafe_allow_html=True)
with b_col1:
    df_ex = df.copy()
    df_ex['순번'] = range(1, len(df)+1)
    towrite = io.BytesIO()
    df_ex[['순번', 'timestamp', 'author', 'item_name', 'is_update', 'is_dtc']].to_excel(towrite, index=False)
    st.download_button("📥 VIN 현황 저장", towrite.getvalue(), "list.xlsx", use_container_width=True)
with b_col2:
    if st.button("📥 사진 데이터 준비", use_container_width=True):
        towrite_p = io.BytesIO()
        with pd.ExcelWriter(towrite_p, engine='xlsxwriter') as writer:
            for vin in df['item_name'].unique():
                photos = db_manager.get_photos_by_vin(conn, vin)
                if photos:
                    sheet = writer.book.add_worksheet(name=str(vin))
                    for idx, (img_data,) in enumerate(photos):
                        sheet.insert_image(chr(66+(idx*10))+'2', 'photo.png', {'image_data': io.BytesIO(img_data), 'x_scale': 0.3, 'y_scale': 0.3})
        st.download_button("📥 상세 사진 저장", towrite_p.getvalue(), "photos.xlsx", use_container_width=True)

# 리스트 표시 (텍스트 링크로 가로 정렬)
for row in df.itertuples():
    st.markdown(
        f"<small>{row.timestamp} | **{row.item_name}** | {row.author}<br>"
        f"UPDATE:{row.is_update} / DTC:{row.is_dtc} "
        f"&nbsp;&nbsp;<a href='?edit={row.id}'>[수정]</a> <a href='?del={row.id}'>[삭제]</a></small>", 
        unsafe_allow_html=True
    )
