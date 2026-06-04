import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import db_manager

# DB 연결
conn = db_manager.init_db()

# --- 도우미 함수 ---
def get_current_kst_time():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')

# --- UI 설정 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 1. 세션 상태 관리 (수정 대상 ID 관리)
if "edit_id" not in st.session_state: st.session_state.edit_id = None
if "current_author" not in st.session_state: st.session_state.current_author = ""
if "next_vin" not in st.session_state: st.session_state.next_vin = ""
if "next_upd" not in st.session_state: st.session_state.next_upd = False
if "next_dtc" not in st.session_state: st.session_state.next_dtc = False

# 2. 파라미터 처리 (수정/삭제 요청 감지)
params = st.query_params

if "del" in params:
    del_id = int(params["del"])
    row = conn.execute("SELECT item_name FROM items WHERE id=?", (del_id,)).fetchone()
    if row:
        db_manager.delete_all_data_by_vin(conn, del_id, row[0])
    st.query_params.clear()
    st.rerun()

if "edit" in params:
    edit_id = int(params["edit"])
    row = conn.execute("SELECT * FROM items WHERE id=?", (edit_id,)).fetchone()
    if row:
        st.session_state.update({
            "edit_id": row[0], "current_author": row[2], 
            "next_vin": row[3], "next_upd": (row[4]=='Y'), "next_dtc": (row[5]=='Y')
        })
    st.query_params.clear()
    st.rerun()

# 3. 입력 폼 (수정/등록 구분)
with st.form("entry_form", clear_on_submit=True):
    author = st.text_input("이름", value=st.session_state.current_author)
    item_name = st.text_input("VIN 6자리", value=st.session_state.next_vin, max_chars=6)
    
    c1, c2 = st.columns(2)
    chk_u = c1.checkbox("업데이트", value=st.session_state.next_upd)
    chk_d = c2.checkbox("DTC", value=st.session_state.next_dtc)
    photo_files = st.file_uploader("검사 사진 업로드 (최대 4개)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if item_name:
            if photo_files:
                db_manager.save_photos_to_db(conn, item_name, photo_files)
            
            # 수정 모드일 때
            if st.session_state.edit_id:
                conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?", 
                             (author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N', st.session_state.edit_id))
            # 신규 등록 모드일 때
            else:
                conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)", 
                             (get_current_kst_time(), author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N'))
            
            conn.commit()
            # 폼 제출 후 상태 초기화
            st.session_state.update({"edit_id": None, "current_author": "", "next_vin": "", "next_upd": False, "next_dtc": False})
            st.rerun()

st.write("---")

# 4. 리스트 표시 (하단 나머지 로직은 동일)
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
# ... (검색 및 통계, 리스트 출력 로직은 이전 코드와 동일하게 유지하세요)
