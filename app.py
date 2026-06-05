import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="wide")
conn = db_manager.init_db()

# --- 1. 현황 집계 ---
st.markdown("#### 📋 전체 현황 (VIN 기준 매칭)")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty:
    # VIN을 기준으로 매칭 (이미지 헤더 'VIN' 사용)
    df_master['VIN'] = df_master['VIN'].astype(str).str.strip()
    
    # '현재출고' 처리
    if '현재출고' in df_master.columns:
        df_master['출고상태'] = df_master['현재출고'].astype(str).str.replace('출고', '').str[-2:]
    else:
        df_master['출고상태'] = '기타'
        
    # '우선순위' 처리
    if '우선순위' in df_master.columns:
        df_master['우선순위그룹'] = df_master['우선순위'].apply(lambda x: str(x) if str(x).isdigit() and int(x) <= 3 else '기타')
    else:
        df_master['우선순위그룹'] = '기타'

    if not df_items.empty:
        df_items['item_name'] = df_items['item_name'].astype(str).str.strip()
        merged = df_master.merge(df_items, left_on='VIN', right_on='item_name', how='left')
        merged['상태'] = merged['author'].apply(lambda x: '완료' if pd.notnull(x) else '미완료')
    else:
        merged = df_master.copy()
        merged['상태'] = '미완료'

    # 요약 집계
    summary = merged.groupby(['우선순위그룹', '출고상태', '상태']).size().unstack(fill_value=0)
    st.dataframe(summary, use_container_width=True)
    
    # 엑셀 다운로드 (C:M 숨김, 1행 고정)
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        merged.to_excel(writer, sheet_name='전체현황', index=False)
        worksheet = writer.sheets['전체현황']
        worksheet.set_column('C:M', None, None, {'hidden': True})
        worksheet.freeze_panes(1, 0)
    st.download_button("📥 전체 리포트 다운로드", data=towrite.getvalue(), file_name="master_report.xlsx")

# --- 2. 입력 폼 ---
with st.form("entry_form"):
    c1, c2 = st.columns(2)
    author = c1.text_input("이름")
    item_name = c2.text_input("VIN 6자리")
    
    # 작업 상태 체크박스
    cols = st.columns(4)
    chk_new = cols[0].checkbox("교체완료")
    chk_adj = cols[1].checkbox("캘리브레이션")
    chk_u = cols[2].checkbox("업데이트")
    chk_d = cols[3].checkbox("DTC")
    remark = st.text_area("비고")
    
    if st.form_submit_button("🚀 등록"):
        now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')
        conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc, is_new_zero, is_zero_adj, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                     (now, author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N', 'Y' if (chk_new or chk_adj) else 'N', 'Y' if chk_adj else 'N', remark))
        conn.commit(); st.rerun()

# --- 3. 리스트 출력 (오류 방지) ---
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
for _, row in df.iterrows():
    d = row.to_dict()
    st.markdown(f"""
    <div style="padding: 10px; border-bottom: 1px solid #eee;">
        <b>{str(d.get('item_name') or "")}</b> | {str(d.get('author') or "")} | {str(d.get('timestamp') or "")}<br>
        <div style="text-align: right;"><a href="/?del={d.get('id')}">삭제</a></div>
    </div>
    """, unsafe_allow_html=True)
