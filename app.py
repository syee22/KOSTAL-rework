import streamlit as st
import pandas as pd
import io, pytz
from datetime import datetime
import db_manager

st.set_page_config(page_title="KOSTAL 통합 관리", layout="centered")
conn = db_manager.init_db()

# --- 1. 현황 집계 및 다운로드 로직 ---
st.markdown("#### 📋 우선순위별 작업 완료 현황")
df_master = db_manager.get_master_data()
df_items = pd.read_sql_query("SELECT * FROM items", conn)

if not df_master.empty and not df_items.empty:
    vin_col = df_master.columns[0]
    prio_col = df_master.columns[1] if len(df_master.columns) > 1 else df_master.columns[0]
    
    df_master[vin_col] = df_master[vin_col].astype(str).str.strip()
    df_items['item_name'] = df_items['item_name'].astype(str).str.strip()
    
    # 작업 내역 결합 (병합 시 중복 컬럼 제어)
    merged = df_master.merge(df_items, left_on=vin_col, right_on='item_name', how='left')
    merged['상태'] = merged['author'].apply(lambda x: '완료' if pd.notnull(x) else '미완료')
    
    # 화면 요약
    summary = merged.groupby([prio_col, '상태']).size().unstack(fill_value=0)
    st.dataframe(summary, use_container_width=True)
    
    # 2개 시트 엑셀 생성
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        # 시트 1: 작업 상세 내역
        df_log = df_items[['timestamp', 'item_name', 'author', 'is_update', 'is_dtc', 'is_new_zero', 'is_zero_adj', 'remark']]
        df_log.to_excel(writer, sheet_name='작업상세내역', index=False)
        
        # 시트 2: 전체현황 (필수 컬럼 + 작업 상세 내역 명시적 결합)
        # 마스터 컬럼 + 작업 이력 컬럼 지정
        cols = [vin_col, prio_col, '상태', 'timestamp', 'author', 'is_update', 'is_dtc', 'is_new_zero', 'is_zero_adj', 'remark']
        # 병합 데이터 내 해당 컬럼들만 추출
        merged_clean = merged[cols] 
        merged_clean.to_excel(writer, sheet_name='전체현황', index=False)
    
    st.download_button("📥 전체 리포트 다운로드 (2개 시트)", data=towrite.getvalue(), file_name="master_report.xlsx", use_container_width=True)

# --- 2. 파라미터 로직 / 입력 폼 / 리스트 출력은 이전과 동일 ---
# (입력 폼과 리스트 표시 로직은 위에서 공유해드린 것과 동일하게 유지하시면 됩니다.)
