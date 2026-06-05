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
        st.session_state.update({
            "edit_id": row[0], "current_author": row[2], "next_vin": row[3], 
            "next_upd": (row[4]=='Y'), "next_dtc": (row[5]=='Y'),
            "next_new": (row[6]=='Y'), "next_adj": (row[7]=='Y'), "next_remark": row[8]
        })
    st.query_params.clear(); st.rerun()

# 3. 입력 폼
st.markdown("#### 📱 KOSTAL 리워크 현황")

if st.session_state.get("edit_id"):
    st.warning(f"현재 ID {st.session_state['edit_id']} 수정 중")
    if st.button("수정 취소"):
        st.session_state.update({"edit_id": None, "current_author": "", "next_vin": "", "next_upd": False, "next_dtc": False, "next_new": False, "next_adj": False, "next_remark": ""})
        st.rerun()

with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름", value=st.session_state.get("current_author", ""))
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("next_vin", ""), max_chars=6)
    
    c1, c2, c3, c4 = st.columns(4)
    chk_u = c1.checkbox("업데이트", value=st.session_state.get("next_upd", False))
    chk_d = c2.checkbox("DTC", value=st.session_state.get("next_dtc", False))
    chk_new = c3.checkbox("신규영점", value=st.session_state.get("next_new", False))
    chk_adj = c4.checkbox("영점조절", value=st.session_state.get("next_adj", False))
    
    remark = st.text_area("비고 (최대 2줄)", value=st.session_state.get("next_remark", ""), height=70)
    photo_files = st.file_uploader("검사 사진 업로드", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if not item_name:
            st.error("VIN 번호를 입력하세요.")
        else:
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst).strftime('%m-%d %H:%M')
            edit_id = st.session_state.get("edit_id")
            
            vals = (now_kst, author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N', 
                    'Y' if chk_new else 'N', 'Y' if chk_adj else 'N', remark)
            
            if not edit_id:
                existing = conn.execute("SELECT id FROM items WHERE item_name = ?", (item_name,)).fetchone()
                if existing: st.error("이미 등록된 VIN입니다.")
                else:
                    if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
                    conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", vals)
                    conn.commit()
            else:
                if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
                conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?", 
                             (author, item_name, *vals[3:], edit_id))
                conn.commit()
            
            st.session_state.update({"edit_id": None, "current_author": "", "next_vin": "", "next_upd": False, "next_dtc": False, "next_new": False, "next_adj": False, "next_remark": ""})
            st.rerun()

# 4. 데이터 리스트 및 통계
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
search = st.text_input("🔍 이름 또는 VIN 검색")
if search: df = df[df['item_name'].str.contains(search, na=False) | df['author'].str.contains(search, na=False)]

st.markdown(f"<small>📋 총 <b>{len(df)}건</b></small>", unsafe_allow_html=True)

# 5. 리스트 표시
for row in df.itertuples():
    tags = [t for t, cond in [("UP", row.is_update=='Y'), ("DTC", row.is_dtc=='Y'), 
                               ("신규영점", row.is_new_zero=='Y'), ("영점조절", row.is_zero_adj=='Y')] if cond]
    tag_str = " | ".join(tags)
    
    st.markdown(f"""
        <div style="padding: 10px; border-bottom: 1px solid #ddd;">
            <div style="font-size: 13px;"><b>{row.item_name}</b> | {row.author} | {row.timestamp}</div>
            <div style="font-size: 11px; color: #2e86de;">{tag_str}</div>
            <div style="font-size: 12px; color: #555;">{row.remark}</div>
            <div style="text-align: right;">
                <a href="/?edit={row.id}">수정</a> | <a href="/?del={row.id}" style="color:red;">삭제</a>
            </div>
        </div>
    """, unsafe_allow_html=True)
