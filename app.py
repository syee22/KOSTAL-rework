import sqlite3
import pandas as pd
import streamlit as st
import io
import pytz
from datetime import datetime

# --- 1. DB 설정 ---
def init_db():
    conn = sqlite3.connect("kostal_rework_v3.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, author TEXT, item_name TEXT, is_update TEXT, is_dtc TEXT)")
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
    conn.execute("DELETE FROM items WHERE id = ?", (id,))
    conn.commit()

# --- 3. UI ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("#### 📱 KOSTAL 리워크 현황")

# 세션 상태 초기화
if "edit_id" not in st.session_state: st.session_state.edit_id = None
if "current_author" not in st.session_state: st.session_state.current_author = ""

# 입력 폼
with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름", value=st.session_state.current_author)
    item_name = st.text_input("VIN 6자리", value=st.session_state.get("next_vin", ""), max_chars=6)
    c1, c2 = st.columns(2)
    chk_u = c1.checkbox("업데이트", value=st.session_state.get("next_upd", False))
    chk_d = c2.checkbox("DTC", value=st.session_state.get("next_dtc", False))
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        st.session_state.current_author = author
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

# 검색 및 데이터 로드
df_all = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)

# 검색창과 결과 개수를 나란히 배치
s_col, n_col = st.columns([3, 1])
with s_col:
    search = st.text_input("🔍 이름 또는 VIN 검색")
with n_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if search:
        df = df_all[df_all['item_name'].str.contains(search, na=False) | df_all['author'].str.contains(search, na=False)]
    else:
        df = df_all
    st.markdown(f"**{len(df)}건**")

# 통계 및 리스트
u_cnt = len(df[df['is_update'] == 'Y'])
d_cnt = len(df[df['is_dtc'] == 'Y'])

t_col, b_col = st.columns([6, 4])
with t_col:
    st.markdown(f"##### 📋 리스트 <span style='color:blue; font-size:12px;'>| 업뎃:{u_cnt} | DTC:{d_cnt}</span>", unsafe_allow_html=True)
with b_col:
    if not df.empty:
        df_ex = df.copy()
        df_ex['순번'] = range(1, len(df)+1)
        # 컬럼명 변경 적용
        df_ex = df_ex[['순번', 'timestamp', 'author', 'item_name', 'is_update', 'is_dtc']]
        df_ex.columns = ['순번', '시간', '이름', 'VIN', '업데이트', 'DTC']
        
        towrite = io.BytesIO()
        df_ex.to_excel(towrite, index=False)
        st.download_button("📥 엑셀 저장", towrite.getvalue(), "list.xlsx", use_container_width=True)

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
