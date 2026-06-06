import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="wide")
conn = db_manager.init_db()

# --- 1. 중복 데이터 종합 다이얼로그 ---
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
    if st.button("확인 (종합)"):
        conn.execute("UPDATE items SET author=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?",
                     (merged_author, m_upd, m_dtc, m_new, m_adj, m_remark, existing_id))
        conn.commit(); st.session_state.clear(); st.rerun()

# --- 2. 집계 현황 및 엑셀 출력 ---
counts = db_manager.get_completion_counts()
st.markdown(f"#### 📋 출고상태 및 우선순위별 완료 현황 (교체완료: {counts['update']}건, 캘리완료: {counts['cali']}건)")

df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty:
    df_master['VIN'] = df_master['VIN'].astype(str).str.strip()
    
    df_master['출고그룹'] = df_master['현재출고'].astype(str).str.split('출고').str[0].str[-2:]
    df_master['출고그룹'] = pd.Categorical(df_master['출고그룹'], categories=['아산', '울산', '화성'], ordered=True)
    
    order = ['1순위', '2순위', '3순위', '기타']
    df_master['우선순위그룹'] = df_master['우선순위'].apply(lambda p: f"{str(p).replace('위', '').strip()}순위" if str(p).replace('위', '').strip() in ['1', '2', '3'] else "기타")
    df_master['우선순위그룹'] = pd.Categorical(df_master['우선순위그룹'], categories=order, ordered=True)
    
    merged = df_master.merge(df_items[['item_name', 'is_new_zero', 'is_zero_adj', 'author', 'timestamp', 'remark']], left_on='VIN', right_on='item_name', how='left')
    merged['교체완료건'] = merged['is_new_zero'].apply(lambda x: 1 if x == 'Y' else 0)
    merged['캘리완료건'] = merged['is_zero_adj'].apply(lambda x: 1 if x == 'Y' else 0)
    
    summary = merged.groupby(['출고그룹', '우선순위그룹'], observed=False).agg({'VIN': 'count', '교체완료건': 'sum', '캘리완료건': 'sum'}).rename(columns={'VIN': '전체수량'})
    st.dataframe(summary.sort_index(level=['출고그룹', '우선순위그룹']).style.format("{:,}"), use_container_width=True, height=200)

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df_items.to_excel(writer, sheet_name='작업상세내역', index=False)
        writer.sheets['작업상세내역'].freeze_panes(1, 0)
        report_df = merged.copy()
        for col in ['is_new_zero', 'is_zero_adj']:
            if col not in report_df.columns: report_df[col] = 'N'
        report_df['Q_교체완료'] = report_df['is_new_zero'].fillna('N')
        report_df['R_캘리브레이션'] = report_df['is_zero_adj'].fillna('N')
        report_df['S_진행상태'] = report_df['is_zero_adj'].apply(lambda x: '완료' if x == 'Y' else '미완료')
        report_df.to_excel(writer, sheet_name='전체현황', index=False)
        ws = writer.sheets['전체현황']
        ws.freeze_panes(1, 0)
        ws.set_column('C:M', None, None, {'hidden': True})
    st.download_button("📥 통합 리포트 다운로드", data=towrite.getvalue(), file_name="master_report.xlsx")

# --- 3. 입력 폼 ---
with st.form("entry_form", clear_on_submit=False):
    st.subheader("📝 등록 / 수정")
    col1, col2 = st.columns(2)
    author = col1.text_input("이름", value=st.session_state.get("default_author", ""))
    item_name = col2.text_input("VIN 6자리", value=st.session_state.get("default_vin", ""))
    c1, c2, c3, c4 = st.columns(4)
    chk1 = c1.checkbox("교체완료", value=st.session_state.get("default_new", False))
    chk2 = c2.checkbox("캘리브레이션", value=st.session_state.get("default_adj", False))
    chk3 = c3.checkbox("업데이트", value=st.session_state.get("default_upd", False))
    chk4 = c4.checkbox("DTC", value=st.session_state.get("default_dtc", False))
    remark = st.text_area("비고", value=st.session_state.get("default_remark", ""))
    
    if st.form_submit_button("🚀 등록/수정 저장"):
        if not item_name or item_name.strip() == "":
            st.error("⚠️ VIN 6자리를 입력해주세요!")
            st.stop()
        
        edit_id = st.session_state.get("edit_id")
        final_new = 'Y' if (chk1 or chk2) else 'N'
        if edit_id:
            conn.execute("UPDATE items SET author=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?",
                         (author, 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark, edit_id))
            conn.commit(); st.session_state.clear(); st.rerun()
        else:
            existing = conn.execute("SELECT id FROM items WHERE item_name=?", (item_name.strip(),)).fetchone()
            if existing: confirm_update(author, item_name, chk3, chk4, final_new, chk2, remark, existing[0])
            else:
                conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?,?,?,?,?,?,?,?)",
                             (datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M'), author, item_name.strip(), 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark))
                conn.commit(); st.session_state.clear(); st.rerun()

# --- 4. 검색 및 리스트 현황 ---
st.subheader("🔍 작업 리스트 현황")
search_query = st.text_input("VIN 검색", placeholder="VIN 번호로 검색하세요...")
df_list = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
if search_query:
    df_list = df_list[df_list['item_name'].str.contains(search_query, na=False)]

for _, row in df_list.iterrows():
    tags = []
    if row['is_new_zero'] == 'Y': tags.append("✅교체")
    if row['is_zero_adj'] == 'Y': tags.append("⚙️캘리")
    if row['is_update'] == 'Y': tags.append("🔄업뎃")
    if row['is_dtc'] == 'Y': tags.append("⚠️DTC")
    tag_str = " ".join(tags)
    
    c1, c2, c3 = st.columns([6, 1, 1])
    c1.markdown(f"**{row['item_name']}** | {row['author']} | {row['timestamp']} | <small>{tag_str}</small>", unsafe_allow_html=True)
    if c2.button("수정", key=f"edit_{row['id']}"):
        st.session_state.update({"edit_id": row['id'], "default_author": row['author'], "default_vin": row['item_name'], 
                                 "default_upd": row['is_update']=='Y', "default_dtc": row['is_dtc']=='Y', 
                                 "default_new": row['is_new_zero']=='Y', "default_adj": row['is_zero_adj']=='Y', "default_remark": row['remark']})
        st.rerun()
    if c3.button("삭제", key=f"del_{row['id']}"):
        conn.execute("DELETE FROM items WHERE id=?", (row['id'],)); conn.commit(); st.rerun()
