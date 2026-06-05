import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="wide")
conn = db_manager.init_db()

# --- 1. 집계 현황 및 엑셀 다운로드 ---
st.markdown("#### 📋 출고상태 및 우선순위별 현황")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty:
    df_master['VIN'] = df_master['VIN'].astype(str).str.strip()
    
    # 11개 헤더 중 '현재출고'와 '우선순위'를 이용해 그룹화
    # 출고상태: '출고' 글자 제외하고 끝 2자리
    df_master['출고그룹'] = df_master['현재출고'].astype(str).str.replace('출고', '').str[-2:]
    df_master['우선순위그룹'] = df_master['우선순위'].astype(str)

    # 요약 표 생성
    summary = df_master.groupby(['출고그룹', '우선순위그룹']).size().unstack(fill_value=0)
    st.dataframe(summary, use_container_width=True)

    # 엑셀 다운로드 (2개 시트)
    df_items['item_name'] = df_items['item_name'].astype(str).str.strip()
    merged = df_master.merge(df_items, left_on='VIN', right_on='item_name', how='left')
    
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df_items.to_excel(writer, sheet_name='작업상세내역', index=False)
        merged.to_excel(writer, sheet_name='전체현황', index=False)
        ws = writer.sheets['전체현황']
        ws.set_column('C:M', None, None, {'hidden': True})
        ws.freeze_panes(1, 0)
    st.download_button("📥 통합 리포트 다운로드 (2개 시트)", data=towrite.getvalue(), file_name="master_report.xlsx")

# --- 2. 입력 폼 ---
with st.form("entry"):
    col1, col2 = st.columns(2)
    author = col1.text_input("이름")
    item_name = col2.text_input("VIN 6자리")
    c1, c2, c3, c4 = st.columns(4)
    chk1, chk2, chk3, chk4 = c1.checkbox("교체완료"), c2.checkbox("캘리브레이션"), c3.checkbox("업데이트"), c4.checkbox("DTC")
    remark = st.text_area("비고")
    if st.form_submit_button("🚀 등록"):
        now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')
        conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?,?,?,?,?,?,?,?)",
                     (now, author, item_name, 'Y' if chk3 else 'N', 'Y' if chk4 else 'N', 'Y' if (chk1 or chk2) else 'N', 'Y' if chk2 else 'N', remark))
        conn.commit(); st.rerun()

# --- 3. 리스트 출력 ---
st.markdown("---")
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
for _, row in df.iterrows():
    r_id = str(row.get('id', ''))
    name = str(row.get('item_name') or "")
    author = str(row.get('author') or "")
    time = str(row.get('timestamp') or "")
    remark = str(row.get('remark') or "")
    tags = [t for t, cond in [("교체", row.get('is_new_zero')=='Y'), ("캘리", row.get('is_zero_adj')=='Y'), ("업뎃", row.get('is_update')=='Y'), ("DTC", row.get('is_dtc')=='Y')] if cond]
    
    st.markdown(f"""<div style="padding: 10px; border-bottom: 1px solid #eee;">
        <b>{name}</b> | {author} | {time}<br>
        <small>{' | '.join(tags)}</small><br>{remark}<br>
        <div style="text-align: right;"><a href="/?del={r_id}">삭제</a></div>
    </div>""", unsafe_allow_html=True)
