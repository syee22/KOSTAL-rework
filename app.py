import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
conn = db_manager.init_db()

# 수정/삭제 파라미터 처리
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

st.markdown("#### 📱 KOSTAL 리워크 현황")

# 수정 모드 폼
with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름", value=st.session_state.get("current_author", ""))
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("next_vin", ""), max_chars=6)
    
    c1, c2, c3, c4 = st.columns(4)
    chk_new = c1.checkbox("신규영점", value=st.session_state.get("next_new", False))
    chk_adj = c2.checkbox("영점조절", value=st.session_state.get("next_adj", False))
    chk_u = c3.checkbox("업데이트", value=st.session_state.get("next_upd", False))
    chk_d = c4.checkbox("DTC", value=st.session_state.get("next_dtc", False))
    
    remark = st.text_area("비고 (최대 2줄)", value=st.session_state.get("next_remark", ""), height=70)
    photo_files = st.file_uploader("검사 사진 업로드", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if not item_name:
            st.error("VIN 번호를 입력하세요.")
        else:
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst).strftime('%m-%d %H:%M')
            vals = (now, author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N', 
                    'Y' if chk_new else 'N', 'Y' if chk_adj else 'N', remark)
            
            edit_id = st.session_state.get("edit_id")
            if not edit_id:
                if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
                conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", vals)
            else:
                if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
                conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?", 
                             (author, item_name, *vals[3:], edit_id))
            conn.commit()
            st.session_state.update({"edit_id": None, "current_author": "", "next_vin": "", "next_upd": False, "next_dtc": False, "next_new": False, "next_adj": False, "next_remark": ""})
            st.rerun()

# --- 집계 섹션 ---
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
if not df.empty:
    cnt_new = len(df[df['is_new_zero'] == 'Y'])
    cnt_adj = len(df[df['is_zero_adj'] == 'Y'])
    cnt_upd = len(df[df['is_update'] == 'Y'])
    cnt_dtc = len(df[df['is_dtc'] == 'Y'])
    st.info(f"📊 총 {len(df)}건 | 신규영점:{cnt_new} | 영점조절:{cnt_adj} | 업뎃:{cnt_upd} | DTC:{cnt_dtc}")

# 리스트 표시
for row in df.itertuples():
    tag_list = [t for t, cond in [("신규영점", row.is_new_zero=='Y'), ("영점조절", row.is_zero_adj=='Y'), ("업뎃", row.is_update=='Y'), ("DTC", row.is_dtc=='Y')] if cond]
    st.markdown(f"""
        <div style="padding: 10px; border-bottom: 1px solid #eee;">
            <div style="font-size: 13px;"><b>{row.item_name}</b> | {row.author} | {row.timestamp}</div>
            <div style="font-size: 11px; color: #555;">{' | '.join(tag_list)}</div>
            <div style="font-size: 12px; margin-top: 5px;">{row.remark}</div>
            <div style="text-align: right;"><a href="/?edit={row.id}">수정</a> | <a href="/?del={row.id}" style="color:red;">삭제</a></div>
        </div>
    """, unsafe_allow_html=True)
