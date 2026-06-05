import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="wide")
conn = db_manager.init_db()

# --- 1. 현황 집계 및 엑셀 다운로드 ---
st.markdown("#### 📋 전체 현황 (VIN 기준 매칭)")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty:
    # VIN 기준 매칭 처리
    df_master['VIN'] = df_master['VIN'].astype(str).str.strip()
    
    # 11개 헤더 대응 (현재출고, 우선순위 처리)
    df_master['출고상태'] = df_master['현재출고'].astype(str).str.replace('출고', '').str[-2:] if '현재출고' in df_master.columns else '기타'
    df_master['우선순위그룹'] = df_master['우선순위'].apply(lambda x: str(x) if str(x).isdigit() and int(x) <= 3 else '기타') if '우선순위' in df_master.columns else '기타'

    # 매칭
    df_items['item_name'] = df_items['item_name'].astype(str).str.strip()
    merged = df_master.merge(df_items, left_on='VIN', right_on='item_name', how='left')
    merged['상태'] = merged['author'].apply(lambda x: '완료' if pd.notnull(x) else '미완료')

    # 엑셀 파일 생성 로직 (요청하신 기능 반영)
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        merged.to_excel(writer, sheet_name='전체현황', index=False)
        ws = writer.sheets['전체현황']
        ws.set_column('C:M', None, None, {'hidden': True}) # C~M열 숨김
        ws.freeze_panes(1, 0) # 1행 고정
    st.download_button("📥 전체 리포트 다운로드", data=towrite.getvalue(), file_name="master_report.xlsx")

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

# --- 3. 리스트 출력 (안전한 문자열 변환) ---
st.markdown("---")
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
for _, row in df.iterrows():
    # 데이터를 안전하게 추출 (결측치 방지)
    r_id = str(row.get('id', ''))
    name = str(row.get('item_name') or "")
    author = str(row.get('author') or "")
    time = str(row.get('timestamp') or "")
    remark = str(row.get('remark') or "")
    
    tags = []
    if row.get('is_new_zero') == 'Y': tags.append("교체완료")
    if row.get('is_zero_adj') == 'Y': tags.append("캘리브레이션")
    if row.get('is_update') == 'Y': tags.append("업뎃")
    if row.get('is_dtc') == 'Y': tags.append("DTC")
    
    st.markdown(f"""<div style="padding: 10px; border-bottom: 1px solid #eee;">
        <b>{name}</b> | {author} | {time}<br>
        <small>{' | '.join(tags)}</small><br>{remark}<br>
        <div style="text-align: right;"><a href="/?del={r_id}">삭제</a></div>
    </div>""", unsafe_allow_html=True)
