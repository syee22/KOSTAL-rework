import sqlite3
import pandas as pd
import streamlit as st
import io
import os
from datetime import datetime
import pytz
from PIL import Image
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage

# --- 1. 데이터베이스 초기화 함수 ---
def init_db():
    conn = sqlite3.connect("kostal_rework_v3.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            author TEXT,
            item_name TEXT,
            is_update TEXT,  
            is_dtc TEXT       
        )
    """
    )
    conn.commit()
    return conn

conn = init_db()

# --- 2. 현재 한국 시간(KST) 구하기 ---
def get_current_kst_time():
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    return now.strftime('%m-%d %H:%M')

# --- 3. 데이터베이스 조작 함수들 ---
def insert_data(author, item_name, is_update, is_dtc):
    current_time = get_current_kst_time()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)",
        (current_time, author, item_name, is_update, is_dtc),
    )
    conn.commit()

def update_data(item_id, author, item_name, is_update, is_dtc):
    current_time = get_current_kst_time()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE items 
        SET timestamp = ?, author = ?, item_name = ?, is_update = ?, is_dtc = ? 
        WHERE id = ?
        """,
        (current_time, author, item_name, is_update, is_dtc, item_id),
    )
    conn.commit()

def delete_data(item_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()

def load_data():
    return pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)

def clear_data():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items")
    conn.commit()

# --- 4. 엑셀 사진 저장 함수 ---
def save_image_to_excel(item_name, is_update, is_dtc, uploaded_file):
    excel_filename = "KOSTAL_photo_registry.xlsx"
    
    if os.path.exists(excel_filename):
        wb = openpyxl.load_workbook(excel_filename)
    else:
        wb = openpyxl.Workbook()
        wb.active.title = "임시_기본시트"
        
    clean_sheet_name = "".join(c for c in item_name if c not in r'\/??*[]:').strip()[:30]
    if not clean_sheet_name:
        clean_sheet_name = "정제된_VIN"
        
    if clean_sheet_name in wb.sheetnames:
        ws = wb[clean_sheet_name]
    else:
        ws = wb.create_sheet(title=clean_sheet_name)
        ws['A1'] = "시간"
        ws['B1'] = "이름"
        ws['C1'] = "VIN 넘버"
        ws['D1'] = "업데이트"
        ws['E1'] = "DTC"
        ws['F1'] = "첨부 사진"
        
    image = Image.open(uploaded_file)
    image.thumbnail((400, 400))
    
    img_byte_arr = io.BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(img_byte_arr, format='JPEG', quality=75, optimize=True)
    img_byte_arr.seek(0)
    
    xl_img = OpenpyxlImage(img_byte_arr)
    next_row = ws.max_row + 1 if ws.max_row > 1 or ws['A1'].value != "시간" else 2
    
    kst = pytz.timezone('Asia/Seoul')
    full_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    ws[f'A{next_row}'] = full_time
    ws[f'B{next_row}'] = st.session_state.form_author
    ws[f'C{next_row}'] = item_name
    ws[f'D{next_row}'] = is_update
    ws[f'E{next_row}'] = is_dtc
    
    ws.add_image(xl_img, f'F{next_row}')
    ws.row_dimensions[next_row].height = 160  
    ws.column_dimensions['F'].width = 45
    
    if "임시_기본시트" in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb["임시_기본시트"]
        
    wb.save(excel_filename)
    return excel_filename

# --- 5. 모달 팝업(Dialog) 정의 ---
@st.dialog("⚠️ 데이터 삭제 확인")
def confirm_delete_dialog(item_id, item_name):
    st.write(f"정말로 VIN 넘버 **[{item_name}]** 항목을 삭제하시겠습니까?")
    st.write("")
    col_pop1, col_pop2 = st.columns(2)
    with col_pop1:
        if st.button("🔴 삭제", use_container_width=True):
            delete_data(item_id)
            st.toast("삭제되었습니다.")
            st.rerun()
    with col_pop2:
        if st.button("취소", use_container_width=True):
            st.rerun()

@st.dialog("🚨 입력 오류")
def validation_error_dialog(message):
    st.error(message)
    st.write("VIN 넘버 자리에 **숫자 6자리**를 정확히 입력해 주세요.")
    if st.button("확인", use_container_width=True):
        st.rerun()

# --- 6. 세션 상태 설정 ---
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None
if "form_author" not in st.session_state:
    st.session_state.form_author = ""
if "form_item_name" not in st.session_state:
    st.session_state.form_item_name = ""
if "form_update" not in st.session_state:
    st.session_state.form_update = False
if "form_dtc" not in st.session_state:
    st.session_state.form_dtc = False

# --- 7. Streamlit 모바일형 UI 세팅 ---
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")

st.markdown("#### 📱 KOSTAL 시스템")

# --- 메인화면 최상단: 데이터 입력/수정 컨트롤 박스 ---
if st.session_state.edit_mode:
    st.warning(f"✏️ ID [{st.session_state.edit_id}] 수정 중")
else:
    st.markdown("##### ✍️ 실시간 현장 등록")

# 💡 [보정 포인트] 이름 입력창에서 '부서' 문구를 전면 제거하여 단순화
author = st.text_input("👤 이름", value=st.session_state.form_author, autocomplete="name", placeholder="이름 입력")
item_name = st.text_input("📦 VIN 6자리", value=st.session_state.form_item_name, max_chars=6, placeholder="123456")

st.markdown("**🛠️ 체크**")
col_chk1, col_chk2, col_chk3 = st.columns(3)
with col_chk1:
    chk_update = st.checkbox("🔄 업뎃", value=st.session_state.form_update)
with col_chk2:
    chk_dtc = st.checkbox("⚠️ DTC", value=st.session_state.form_dtc)

val_update = "Y" if chk_update else "N"
val_dtc = "Y" if chk_dtc else "N"

uploaded_file = st.file_uploader("📸 현장 사진 촬영/첨부", type=["png", "jpg", "jpeg"])

# 입력 및 수정 제출 버튼
if st.session_state.edit_mode:
    col_m_btn1, col_m_btn2 = st.columns(2)
    with col_m_btn1:
        if st.button("✅ 수정", type="primary", use_container_width=True):
            if author and item_name:
                if not item_name.isdigit() or len(item_name) != 6:
                    validation_error_dialog(f"형식이 잘못되었습니다.")
                else:
                    update_data(st.session_state.edit_id, author, item_name, val_update, val_dtc)
                    if uploaded_file is not None:
                        save_image_to_excel(item_name, val_update, val_dtc, uploaded_file)
                    st.toast("수정되었습니다!")
                    
                    st.session_state.edit_mode = False
                    st.session_state.edit_id = None
                    st.session_state.form_author = author 
                    st.session_state.form_item_name = ""
                    st.session_state.form_update = False
                    st.session_state.form_dtc = False
                    st.rerun()
    with col_m_btn2:
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.edit_mode = False
            st.session_state.edit_id = None
            st.session_state.form_author = author
            st.session_state.form_item_name = ""
            st.session_state.form_update = False
            st.session_state.form_dtc = False
            st.rerun()
else:
    if st.button("🚀 현장 리스트에 즉시 등록", type="primary", use_container_width=True):
        if author and item_name:
            if not item_name.isdigit() or len(item_name) != 6:
                validation_error_dialog(f"VIN 넘버는 반드시 숫자 6자리여야 합니다.")
            else:
                insert_data(author, item_name, val_update, val_dtc)
                if uploaded_file is not None:
                    save_image_to_excel(item_name, val_update, val_dtc, uploaded_file)
                st.toast("등록되었습니다!")
                
                st.session_state.form_author = author
                st.session_state.form_item_name = ""
                st.rerun()
        else:
            st.error("작성자와 VIN 넘버는 필수입니다.")

st.write("---")

# --- 8. 하단 모바일 특화 카드형 리스트 및 제어부 ---
df = load_data()

st.markdown("##### 📋 마감 현황")
search_query = st.text_input("", placeholder="🔍 VIN/이름 검색", label_visibility="collapsed")

if not df.empty:
    if search_query:
        filtered_df = df[
            df['item_name'].str.contains(search_query, case=False, na=False) | 
            df['author'].str.contains(search_query, case=False, na=False)
        ]
    else:
        filtered_df = df

    if filtered_df.empty:
        st.warning("검색 결과가 없습니다.")
    else:
        for index, row in filtered_df.iterrows():
            with st.container(border=False):
                st.markdown(f"**📦 {row['item_name']}** ({row['author']}) / 🕒 {row['timestamp']}")
                st.caption(f"업뎃: {row['is_update']} | DTC: {row['is_dtc']}")
                
                col_b1, col_b2, col_b3 = st.columns([1, 1, 8])
                with col_b1:
                    if st.button("📝", key=f"m_edit_{row['id']}"):
                        st.session_state.edit_mode = True
                        st.session_state.edit_id = row['id']
                        st.session_state.form_author = row['author']
                        st.session_state.form_item_name = row['item_name']
                        st.session_state.form_update = True if row['is_update'] == "Y" else False
                        st.session_state.form_dtc = True if row['is_dtc'] == "Y" else False
                        st.rerun()
                with col_b2:
                    if st.button("🗑️", key=f"m_del_{row['id']}"):
                        confirm_delete_dialog(row['id'], row['item_name'])
                st.write(" ") 
else:
    st.info("등록된 내역이 없습니다.")

st.write("---")

# --- 최하단: 다운로드 및 초기화 존 ---
st.markdown("##### 💾 백업/리셋")
col_d1, col_d2 = st.columns(2)

with col_d1:
    if not df.empty:
        export_df = df.copy()
        export_df = export_df[['id', 'timestamp', 'author', 'item_name', 'is_update', 'is_dtc']]
        export_df.columns = ['순번', '시간', '이름', 'VIN 넘버', '업데이트', 'DTC']
        
        towrite = io.BytesIO()
        export_df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button(
            label="📈 일반 저장",
            data=towrite,
            file_name="KOSTAL_rework_list.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

with col_d2:
    if os.path.exists("KOSTAL_photo_registry.xlsx"):
        with open("KOSTAL_photo_registry.xlsx", "rb") as f:
            st.download_button(
                label="📸 사진 저장",
                data=f,
                file_name="KOSTAL_photo_registry.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

if st.button("🚨 전체 마감 리셋", use_container_width=True):
    clear_data()
    if os.path.exists("KOSTAL_photo_registry.xlsx"):
        os.remove("KOSTAL_photo_registry.xlsx")
    st.session_state.edit_mode = False
    st.session_state.form_author = "" 
    st.session_state.form_item_name = ""
    st.rerun()
