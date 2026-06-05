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
    st.info(f"종합 예정 작성자: {merged_author}")
    
    if st.button("종합하여 저장"):
        conn.execute("UPDATE items SET author=?, is_update=?, is_dtc=?, is_new_zero=?, is_zero_adj=?, remark=? WHERE id=?",
                     (merged_author, m_upd, m_dtc, m_new, m_adj, m_remark, existing_id))
        conn.commit(); st.session_state.clear(); st.rerun()
    if st.button("취소"): st.rerun()

# --- 2. 수정/삭제/조회 파라미터 ---
params = st.query_params
if "del" in params:
    conn.execute("DELETE FROM items WHERE id=?", (params["del"],))
    conn.commit(); st.query_params.clear(); st.rerun()
if "edit" in params:
    row = conn.execute("SELECT * FROM items WHERE id=?", (params["edit"],)).fetchone()
    if row:
        st.session_state.update({"default_author": row[2], "default_vin": row[3], "default_upd": row[4]=='Y', 
                                 "default_dtc": row[5]=='Y', "default_new": row[6]=='Y', "default_adj": row[7]=='Y', "default_remark": row[8]})
    st.query_params.clear(); st.rerun()

# --- 3. 집계 현황 및 엑셀 출력 ---
st.markdown("#### 📋 출고상태 및 우선순위별 현황 (캘리브레이션=완료)")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty:
    df_master['VIN'] = df_master['VIN'].astype(str).str.strip()
    df_master['출고그룹'] = df_master['현재출고'].astype(str).str.replace('출고', '').str[-2:]
    
    # 1순위, 2순위, 3순위, 기타 정렬 적용
    order = ['1순위', '2순위', '3순위', '기타']
    df_master['우선순위그룹'] = df_master['우선순위'].apply(lambda p: f"{str(p).replace('위', '').strip()}순위" if str(p).replace('위', '').strip() in ['1', '2', '3'] else "기타")
    df_master['우선순위그룹'] = pd.Categorical(df_master['우선순위그룹'], categories=order, ordered=True)

    if not df_items.empty:
        df_items['진행상태'] = df_items['is_zero_adj'].apply(lambda x: '완료' if x == 'Y' else '미완료')
        merged = df_master.merge(df_items[['item_name', '진행상태', 'is_new_zero', 'is_zero_adj', 'author', 'timestamp', 'remark']], left_on='VIN', right_on='item_name', how='left')
        merged['진행상태'] = merged['진행상태'].fillna('미완료')
    else:
        merged = df_master.copy()
        merged['진행상태'] = '미완료'

    # 정렬 적용하여 출력
    summary = merged.groupby(['출고그룹', '우선순위그룹', '진행상태'], observed=False).size().unstack(fill_value=0)
    st.dataframe(summary.sort_index(level='우선순위그룹'), use_container_width=True, height=200)

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df_items.to_excel(writer, sheet_name='작업상세내역', index=False)
        report_df = merged.copy()
        for col in ['is_new_zero', 'is_zero_adj']:
            if col not in report_df.columns: report_df[col] = 'N'
        report_df['Q_교체완료'] = report_df['is_new_zero'].fillna('N')
        report_df['R_캘리브레이션'] = report_df['is_zero_adj'].fillna('N')
        report_df['S_진행상태'] = report_df['진행상태']
        report_df.to_excel(writer, sheet_name='전체현황', index=False)
        ws = writer.sheets['전체현황']
        ws.set_column('C:M', None, None, {'hidden': True})
    st.download_button("📥 통합 리포트 다운로드", data=towrite.getvalue(), file_name="master_report.xlsx")

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
    
    if st.form_submit_button("🚀 등록"):
        final_new = 'Y' if (chk1 or chk2) else 'N'
        existing = conn.execute("SELECT id FROM items WHERE item_name=?", (item_name.strip(),)).fetchone()
        if existing:
            confirm_update(author, item_name, chk3, chk4, final_new, chk2, remark, existing[0])
        else:
            now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')
            conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?,?,?,?,?,?,?,?)",
                         (now, author, item_name.strip(), 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', final_new, 'Y' if chk2 else 'N', remark))
            conn.commit(); st.session_state.clear(); st.rerun()

# --- 5. 리스트 출력 ---
st.markdown("---")
for _, row in pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn).iterrows():
    tags = [t for t, cond in [("교체", row['is_new_zero']=='Y'), ("캘리", row['is_zero_adj']=='Y'), ("업뎃", row['is_update']=='Y'), ("DTC", row['is_dtc']=='Y')] if cond]
    st.markdown(f"""<div style="padding: 10px; border-bottom: 1px solid #eee;">
        <b>{row['item_name']}</b> | {row['author']} | {row['timestamp']}<br>
        <small>{' | '.join(tags)}</small><br>{row['remark'] or ""}<br>
        <div style="text-align: right;"><a href="/?edit={row['id']}">수정</a> | <a href="/?del={row['id']}" style="color:red;">삭제</a></div>
    </div>""", unsafe_allow_html=True)
