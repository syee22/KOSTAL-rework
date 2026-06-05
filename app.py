import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="centered")
conn = db_manager.init_db()

# --- 1. Git 마스터 기반 실적 대조 ---
st.markdown("#### 📋 우선순위별 작업 완료 현황")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT item_name, author FROM items", conn)

if not df_master.empty:
    vin_col = df_master.columns[0]
    prio_col = df_master.columns[1] 
    
    merged = df_master.merge(df_items, left_on=vin_col, right_on='item_name', how='left')
    merged['상태'] = merged['author'].apply(lambda x: '완료' if pd.notnull(x) else '미완료')
    
    summary = merged.groupby([prio_col, '상태']).size().unstack(fill_value=0)
    st.dataframe(summary, use_container_width=True)
    
    towrite = io.BytesIO()
    merged.to_excel(towrite, index=False)
    st.download_button("📥 전체 현황 다운로드", data=towrite.getvalue(), file_name="master_report.xlsx", use_container_width=True)

# --- 2. 파라미터 로직 (삭제/수정) ---
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
        st.session_state.update({"edit_id": row[0], "current_author": row[2], "next_vin": row[3], "next_upd": (row[4]=='Y'), "next_dtc": (row[5]=='Y'), "next_new": (row[6]=='Y'), "next_adj": (row[7]=='Y'), "next_remark": row[8]})
    st.query_params.clear(); st.rerun()

# --- 3. 입력 폼 (텍스트 변경 및 자동 체크 로직) ---
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 캘리브레이션 체크 시 교체완료 자동 체크 함수
def sync_checkbox():
    if st.session_state.chk_adj:
        st.session_state.chk_new = True

with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름", value=st.session_state.get("current_author", ""))
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("next_vin", ""), max_chars=6)
    
    c1, c2, c3, c4 = st.columns(4)
    chk_new = c1.checkbox("교체완료", key="chk_new", value=st.session_state.get("next_new", False))
    chk_adj = c2.checkbox("캘리브레이션", key="chk_adj", value=st.session_state.get("next_adj", False), on_change=sync_checkbox)
    chk_u = c3.checkbox("업데이트", value=st.session_state.get("next_upd", False))
    chk_d = c4.checkbox("DTC", value=st.session_state.get("next_dtc", False))
    
    remark = st.text_area("비고 (최대 2줄)", value=st.session_state.get("next_remark", ""), height=70)
    photo_files = st.file_uploader("검사 사진 업로드", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if not item_name: st.error("VIN 번호를 입력하세요.")
        else:
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst).strftime('%m-%d %H:%M')
            # 체크박스 값은 session_state에서 직접 가져옴
            vals = (now, author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N', 
                    'Y' if st.session_state.chk_new else 'N', 'Y' if st.session_state.chk_adj else 'N', remark)
            
            edit_id = st.session_state.get("edit_id")
            if not edit_id:
                if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
                conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", vals)
            else:
                if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
                conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?", (*vals[1:3], *vals[3:], edit_id))
            conn.commit()
            st.session_state.update({"edit_id": None, "current_author": "", "next_vin": "", "next_upd": False, "next_dtc": False, "next_new": False, "next_adj": False, "next_remark": ""})
            st.rerun()

# --- 4. 리스트 표시 (태그 텍스트 변경) ---
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
search = st.text_input("🔍 이름 또는 VIN 검색")
if search: df = df[df['item_name'].str.contains(search, na=False) | df['author'].str.contains(search, na=False)]

for row in df.itertuples():
    tags = [t for t, cond in [("교체완료", row.is_new_zero=='Y'), ("캘리브레이션", row.is_zero_adj=='Y'), ("업뎃", row.is_update=='Y'), ("DTC", row.is_dtc=='Y')] if cond]
    st.markdown(f"""<div style="padding: 10px; border-bottom: 1px solid #eee;">
        <b>{row.item_name}</b> | {row.author} | {row.timestamp}<br>
        <small style="color: #555;">{' | '.join(tags)}</small><br>{row.remark}<br>
        <div style="text-align: right;"><a href="/?edit={row.id}">수정</a> | <a href="/?del={row.id}" style="color:red;">삭제</a></div>
    </div>""", unsafe_allow_html=True)
