import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="centered")
conn = db_manager.init_db()

# --- 1. 현황 집계 및 다운로드 ---
st.markdown("#### 📋 우선순위별 작업 완료 현황")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty:
    # 11개 컬럼 중 'VIN' 컬럼을 기준으로 병합하도록 고정
    vin_key = 'VIN' 
    
    # 마스터 데이터 전처리 (공백 제거)
    df_master[vin_key] = df_master[vin_key].astype(str).str.strip()
    if not df_items.empty:
        df_items['item_name'] = df_items['item_name'].astype(str).str.strip()
        
        # 마스터 리스트에 작업 내역을 'VIN'과 'item_name' 기준으로 병합
        merged = df_master.merge(df_items, left_on=vin_key, right_on='item_name', how='left')
        merged['상태'] = merged['author'].apply(lambda x: '완료' if pd.notnull(x) else '미완료')
    else:
        merged = df_master.copy()
        merged['상태'] = '미완료'

    # 화면 요약 표 (우선순위 컬럼이 있을 경우)
    if '우선순위' in merged.columns and not df_items.empty:
        summary = merged.groupby(['우선순위', '상태']).size().unstack(fill_value=0)
        st.dataframe(summary, use_container_width=True)
    
    # 2개 시트 엑셀 다운로드
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        if not df_items.empty:
            df_log = df_items[['timestamp', 'item_name', 'author', 'is_update', 'is_dtc', 'is_new_zero', 'is_zero_adj', 'remark']]
            df_log.to_excel(writer, sheet_name='작업상세내역', index=False)
        
        # 전체현황에 마스터 데이터와 작업 정보 결합
        merged.to_excel(writer, sheet_name='전체현황', index=False)
    
    st.download_button("📥 전체 리포트 다운로드 (2개 시트)", data=towrite.getvalue(), file_name="master_report.xlsx", use_container_width=True)

# --- 2. 입력 폼 및 리스트 로직 (동일) ---
# (삭제/수정 로직 및 입력 폼 코드는 이전과 동일하게 유지하시면 됩니다.)
