import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import db_manager

# 1. 페이지 설정
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
conn = db_manager.init_db()

# 2. 파라미터 로직 (수정/삭제)
params = st.query_params
if "del" in params:
    del_id = int(params["del"])
    row = conn.execute("SELECT item_name FROM items WHERE id=?", (del_id,)).fetchone()
    if row: db_manager.delete_all_data_by_vin(conn, del_id, row[0])
    st.query_params.clear(); st.rerun()

if "edit" in params:
    edit_id = int(params["edit"])
    row = conn.execute("SELECT * FROM items WHERE id=?", (edit_id,)).fetchone()
    if row:
        st.session_state.update({"edit_id": row[0], "current_author": row[2], "next_vin": row[3], "next_upd": (row[4]=='Y'), "next_dtc": (row[5]=='Y')})
    st.query_params.clear(); st.rerun()

# 3. 입력 폼
st.markdown("#### 📱 KOSTAL 리워크 현황")
with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름", value=st.session_state.get("current_author", ""))
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("next_vin", ""), max_chars=6)
    c1, c2 = st.columns(2)
    chk_u = c1.checkbox("업데이트", value=st.session_state.get("next_upd", False))
    chk_d = c2.checkbox("DTC", value=st.session_state.get("next_dtc", False))
    photo_files = st.file_uploader("검사 사진 업로드", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if item_name:
            if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
            edit_id = st.session_state.get("edit_id")
            if edit_id:
                conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?", (author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N', edit_id))
            else:
                conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)", (datetime.now().strftime('%m-%d %H:%M'), author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N'))
            conn.commit()
            st.session_state.update({"edit_id": None, "current_author": "", "next_vin": "", "next_upd": False, "next_dtc": False})
            st.rerun()

# 4. 데이터 리스트 및 통계
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
search = st.text_input("🔍 이름 또는 VIN 검색")
if search: df = df[df['item_name'].str.contains(search, na=False) | df['author'].str.contains(search, na=False)]

u_cnt, d_cnt = len(df[df['is_update'] == 'Y']), len(df[df['is_dtc'] == 'Y'])
st.markdown(f"<small>📋 <b>{len(df)}건</b> | 업뎃: {u_cnt} | DTC: {d_cnt}</small>", unsafe_allow_html=True)

# 다운로드 버튼 영역
col_d1, col_d2 = st.columns(2)
with col_d1:
    df_ex = df[['timestamp', 'author', 'item_name', 'is_update', 'is_dtc']]
    towrite = io.BytesIO()
    df_ex.to_excel(towrite, index=False)
    st.download_button("📥 현황 저장", towrite.getvalue(), "list.xlsx", use_container_width=True)
with col_d2:
    def get_photos():
        towrite_p = io.BytesIO()
        with pd.ExcelWriter(towrite_p, engine='xlsxwriter') as writer:
            for vin in df['item_name'].unique():
                photos = db_manager.get_photos_by_vin(conn, vin)
                if photos:
                    s = writer.book.add_worksheet(name=str(vin))
                    for i, (img,) in enumerate(photos):
                        s.insert_image(chr(66+(i*10))+'2', 'p.png', {'image_data': io.BytesIO(img), 'x_scale': 0.3, 'y_scale': 0.3})
        return towrite_p.getvalue()
    st.download_button("📥 사진 저장", data=get_photos(), file_name="photos.xlsx", use_container_width=True)

# 5. 리스트 표시 (텍스트 링크 방식)
for row in df.itertuples():
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee;">
            <div style="font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 10px;">
                {row.timestamp} | <b>{row.item_name}</b> | {row.author} (UP:{row.is_update}/DTC:{row.is_dtc})
            </div>
            <div style="font-size: 11px; flex-shrink: 0;">
                <a href="/?edit={row.id}" style="color: blue; text-decoration: none; margin-right: 10px;">수정</a>
                <a href="/?del={row.id}" style="color: red; text-decoration: none;">삭제</a>
            </div>
        </div>
    """, unsafe_allow_html=True)
