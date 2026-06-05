import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="wide")
conn = db_manager.init_db()

# --- 1. 중복 데이터 종합 다이얼로그 (이전과 동일) ---
@st.dialog("중복 데이터 종합!")
def confirm_update(new_author, item_name, new_chk3, new_chk4, new_final_new, new_chk2, new_remark, existing_id):
    row = conn.execute("SELECT author, is_update, is_dtc, is_new_zero, is_zero_adj, remark FROM items WHERE id=?", (existing_id,)).fetchone()
    ex_author, ex_upd, ex_dtc, ex_new, ex_adj, ex_remark = row
    authors = list(set([a.strip() for a in str(ex_author).split('/')] + [new_author]))
    merged_author = "/".join([a for a in authors if a])
    m_upd = 'Y' if (ex_upd == 'Y' or new_chk3) else 'N'
    m_dtc = 'Y' if (ex_dtc == 'Y' or new_chk4) else 'N'
    m_new = 'Y' if (ex_new == 'Y' or new_final_new == 'Y') else 'N'
    m_adj = 'Y' if (ex_adj == 'Y' or new_chk2) else 'N'
    m_remark = f"{ex_remark} / {new_remark}" if (new_remark and ex_remark != new_remark) else (ex_remark or new_remark)

    st.write(f"VIN **{item_name}** 기존 기록과 종합합니다.")
    if st.button("종합하여 저장"):
        conn.execute("UPDATE items SET author=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?",
                     (merged_author, m_upd, m_dtc, m_new, m_adj, m_remark, existing_id))
        conn.commit(); st.session_state.clear(); st.rerun()

# --- 2. 수정/삭제 처리 (URL 파라미터 제거) ---
def handle_action(action, row_id):
    if action == "del":
        conn.execute("DELETE FROM items WHERE id=?", (row_id,))
        conn.commit()
    elif action == "edit":
        row = conn.execute("SELECT * FROM items WHERE id=?", (row_id,)).fetchone()
        if row:
            st.session_state.update({"edit_id": row[0], "default_author": row[2], "default_vin": row[3], "default_upd": row[4]=='Y', 
                                     "default_dtc": row[5]=='Y', "default_new": row[6]=='Y', "default_adj": row[7]=='Y', "default_remark": row[8]})
    st.rerun()

# --- 3. 집계 현황 및 엑셀 출력 ---
st.markdown("#### 📋 출고상태 및 우선순위별 완료 현황")
# ... (집계 로직은 동일)
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)
# ... (병합 로직 및 엑셀 출력은 동일)

# --- 4. 입력 폼 ---
with st.form("entry", clear_on_submit=False):
    col1, col2 = st.columns(2)
    author = col1.text_input("이름", value=st.session_state.get("default_author", ""))
    item_name = col2.text_input("VIN 6자리", value=st.session_state.get("default_vin", ""))
    c1, c2, c3, c4 = st.columns(4)
    chk1, chk2, chk3, chk4 = c1.checkbox("교체완료", value=st.session_state.get("default_new", False)), \
                             c2.checkbox("캘리브레이션", value=st.session_state.get("default_adj", False)), \
                             c3.checkbox("업데이트", value=st.session_state.get("default_upd", False)), \
                             c4.checkbox("DTC", value=st.session_state.get("default_dtc", False))
    remark = st.text_area("비고", value=st.session_state.get("default_remark", ""))
    
    if st.form_submit_button("🚀 등록 / 수정 저장"):
        final_new = 'Y' if (chk1 or chk2) else 'N'
        # 수정 중인 ID가 있다면 Update, 아니면 Insert
        edit_id = st.session_state.get("edit_id")
        if edit_id:
            conn.execute("UPDATE items SET author=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?",
                         (author, 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark, edit_id))
            conn.commit(); st.session_state.clear(); st.rerun()
        else:
            existing = conn.execute("SELECT id FROM items WHERE item_name=?", (item_name.strip(),)).fetchone()
            if existing: confirm_update(author, item_name, chk3, chk4, final_new, chk2, remark, existing[0])
            else:
                now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')
                conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?,?,?,?,?,?,?,?)",
                             (now, author, item_name.strip(), 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark))
                conn.commit(); st.session_state.clear(); st.rerun()

# --- 5. 리스트 출력 (수정/삭제 버튼 콜백 적용) ---
st.markdown("---")
for _, row in pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn).iterrows():
    # 삭제/수정 버튼을 st.button으로 변경하여 페이지 이동 방지
    c1, c2, c3 = st.columns([6, 1, 1])
    c1.markdown(f"<b>{row['item_name']}</b> | {row['author']} | {row['timestamp']}")
    if c2.button("수정", key=f"edit_{row['id']}"): handle_action("edit", row['id'])
    if c3.button("삭제", key=f"del_{row['id']}"): handle_action("del", row['id'])
    st.markdown(f"<small>{row['remark']}</small>", unsafe_allow_html=True)
