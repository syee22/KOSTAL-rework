import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="wide")
conn = db_manager.init_db()

# --- 1. 집계 현황 표시 ---
st.markdown("#### 📋 출고상태 및 우선순위별 현황 (캘리브레이션=완료)")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty:
    df_master['VIN'] = df_master['VIN'].astype(str).str.strip()
    df_master['출고그룹'] = df_master['현재출고'].astype(str).str.replace('출고', '').str[-2:]
    df_master['우선순위그룹'] = df_master['우선순위'].apply(lambda p: f"{str(p).replace('위', '').strip()}순위" if str(p).replace('위', '').strip() in ['1', '2', '3'] else "기타")

    if not df_items.empty:
        df_items['진행상태'] = df_items['is_zero_adj'].apply(lambda x: '완료' if x == 'Y' else '미완료')
        merged = df_master.merge(df_items[['item_name', '진행상태']], left_on='VIN', right_on='item_name', how='left')
        merged['진행상태'] = merged['진행상태'].fillna('미완료')
    else:
        merged = df_master.copy()
        merged['진행상태'] = '미완료'

    summary = merged.groupby(['출고그룹', '우선순위그룹', '진행상태']).size().unstack(fill_value=0)
    st.dataframe(summary, use_container_width=True)

# --- 2. 삭제 및 수정 파라미터 처리 ---
params = st.query_params
if "del" in params:
    conn.execute("DELETE FROM items WHERE id=?", (params["del"],))
    conn.commit(); st.query_params.clear(); st.rerun()

if "edit" in params:
    row = conn.execute("SELECT * FROM items WHERE id=?", (params["edit"],)).fetchone()
    if row:
        st.session_state.update({"edit_id": row[0], "default_author": row[2], "default_vin": row[3], 
                                 "default_upd": row[4]=='Y', "default_dtc": row[5]=='Y', 
                                 "default_new": row[6]=='Y', "default_adj": row[7]=='Y', "default_remark": row[8]})
    st.query_params.clear(); st.rerun()

# --- 3. 입력 및 수정 폼 ---
with st.form("entry"):
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
        edit_id = st.session_state.get("edit_id")
        final_new = 'Y' if (chk1 or chk2) else 'N'
        if edit_id:
            conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?",
                         (author, item_name, 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark, edit_id))
            st.session_state.clear()
        else:
            now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')
            conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?,?,?,?,?,?,?,?)",
                         (now, author, item_name, 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark))
        conn.commit(); st.rerun()

# --- 4. 리스트 출력 ---
st.markdown("---")
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
for _, row in df.iterrows():
    r_id = str(row['id'])
    tags = [t for t, cond in [("교체", row['is_new_zero']=='Y'), ("캘리", row['is_zero_adj']=='Y'), ("업뎃", row['is_update']=='Y'), ("DTC", row['is_dtc']=='Y')] if cond]
    st.markdown(f"""<div style="padding: 10px; border-bottom: 1px solid #eee;">
        <b>{row['item_name']}</b> | {row['author']} | {row['timestamp']}<br>
        <small>{' | '.join(tags)}</small><br>{row['remark'] or ""}<br>
        <div style="text-align: right;"><a href="/?edit={r_id}">수정</a> | <a href="/?del={r_id}" style="color:red;">삭제</a></div>
    </div>""", unsafe_allow_html=True)
