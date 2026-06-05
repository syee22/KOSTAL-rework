import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="wide")
conn = db_manager.init_db()

# --- 1. 삭제 및 수정 파라미터 처리 ---
params = st.query_params
if "del" in params:
    del_id = params["del"]
    conn.execute("DELETE FROM items WHERE id=?", (del_id,))
    conn.commit()
    st.query_params.clear()
    st.rerun()

# 수정할 데이터를 세션 상태에 저장하는 로직
if "edit" in params:
    edit_id = params["edit"]
    row = conn.execute("SELECT * FROM items WHERE id=?", (edit_id,)).fetchone()
    if row:
        st.session_state["edit_id"] = row[0]
        st.session_state["default_author"] = row[2]
        st.session_state["default_vin"] = row[3]
        st.session_state["default_upd"] = (row[4] == 'Y')
        st.session_state["default_dtc"] = (row[5] == 'Y')
        st.session_state["default_new"] = (row[6] == 'Y')
        st.session_state["default_adj"] = (row[7] == 'Y')
        st.session_state["default_remark"] = row[8]
    st.query_params.clear()
    st.rerun()

# --- 2. 입력 및 수정 폼 ---
with st.form("entry"):
    col1, col2 = st.columns(2)
    author = col1.text_input("이름", value=st.session_state.get("default_author", ""))
    item_name = col2.text_input("VIN 6자리", value=st.session_state.get("default_vin", ""))
    c1, c2, c3, c4 = st.columns(4)
    chk1 = c1.checkbox("교체완료", value=st.session_state.get("default_new", False))
    chk2 = c2.checkbox("캘리브레이션", value=st.session_state.get("default_adj", False))
    chk3 = c3.checkbox("업데이트", value=st.session_state.get("default_upd", False))
    chk4 = c4.checkbox("DTC", value=st.session_state.get("default_dtc", False))
    remark = st.text_area("비고", value=st.session_state.get("default_remark", ""))
    
    if st.form_submit_button("🚀 등록 / 수정 저장"):
        now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')
        edit_id = st.session_state.get("edit_id")
        final_new = 'Y' if (chk1 or chk2) else 'N'
        
        if edit_id:
            conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?",
                         (author, item_name, 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark, edit_id))
            st.session_state["edit_id"] = None
        else:
            conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?,?,?,?,?,?,?,?)",
                         (now, author, item_name, 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark))
        conn.commit(); st.rerun()

# --- 3. 리스트 출력 및 수정/삭제 링크 ---
st.markdown("---")
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
for _, row in df.iterrows():
    r_id = str(row['id'])
    st.markdown(f"""<div style="padding: 10px; border-bottom: 1px solid #eee;">
        <b>{row['item_name']}</b> | {row['author']} | {row['timestamp']}<br>
        <div style="text-align: right;">
            <a href="/?edit={r_id}">수정</a> | 
            <a href="/?del={r_id}" style="color:red;">삭제</a>
        </div>
    </div>""", unsafe_allow_html=True)
