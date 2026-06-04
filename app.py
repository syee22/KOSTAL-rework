import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import db_manager

# 1. 페이지 설정 및 CSS 최적화
st.set_page_config(page_title="KOSTAL Mobile", layout="centered")
st.markdown("""
    <style>
    /* 버튼을 텍스트 옆에 한 줄로 붙이기 위한 스타일 */
    .row-widget.stButton { display: inline-block; margin-left: 5px; }
    div.stButton > button { 
        padding: 0px 5px !important; 
        font-size: 11px !important; 
        height: 22px !important; 
        border: none !important; 
        background: none !important; 
        color: blue !important; 
    }
    div.stButton > button:hover { text-decoration: underline; }
    </style>
""", unsafe_allow_html=True)

conn = db_manager.init_db()

# 2. 함수
def get_current_kst_time():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m-%d %H:%M')

# 3. 세션 상태 초기화
if "edit_id" not in st.session_state: st.session_state.edit_id = None
if "current_author" not in st.session_state: st.session_state.current_author = ""
if "next_vin" not in st.session_state: st.session_state.next_vin = ""

# 4. 입력 폼
st.markdown("#### 📱 KOSTAL 리워크 현황")
with st.form("entry_form", clear_on_submit=False):
    author = st.text_input("이름", value=st.session_state.current_author)
    item_name = st.text_input("VIN 6자리", value=st.session_state.next_vin, max_chars=6)
    
    c1, c2 = st.columns(2)
    chk_u = c1.checkbox("업데이트", value=st.session_state.get("next_upd", False))
    chk_d = c2.checkbox("DTC", value=st.session_state.get("next_dtc", False))
    
    photo_files = st.file_uploader("검사 사진 업로드 (최대 4개)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    
    if st.form_submit_button("🚀 등록 / ✅ 수정 완료"):
        if item_name:
            if photo_files: db_manager.save_photos_to_db(conn, item_name, photo_files)
            
            if st.session_state.edit_id:
                conn.execute("UPDATE items SET author=?, item_name=?, is_update=?, is_dtc=? WHERE id=?", 
                             (author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N', st.session_state.edit_id))
            else:
                conn.execute("INSERT INTO items (timestamp, author, item_name, is_update, is_dtc) VALUES (?, ?, ?, ?, ?)", 
                             (get_current_kst_time(), author, item_name, 'Y' if chk_u else 'N', 'Y' if chk_d else 'N'))
            conn.commit()
            
            st.session_state.update({"edit_id": None, "current_author": "", "next_vin": "", "next_upd": False, "next_dtc": False})
            st.rerun()

st.write("---")

# 5. 리스트 및 통계
df = pd.read_sql_query("SELECT * FROM items ORDER BY id DESC", conn)
search = st.text_input("🔍 이름 또는 VIN 검색")
if search: df = df[df['item_name'].str.contains(search, na=False) | df['author'].str.contains(search, na=False)]

u_cnt, d_cnt = len(df[df['is_update'] == 'Y']), len(df[df['is_dtc'] == 'Y'])
t_col, b_col1, b_col2 = st.columns([4, 3, 3])

with t_col:
    st.markdown(f"##### 📋 {len(df)}건 <small>| 업뎃:{u_cnt} | DTC:{d_cnt}</small>", unsafe_allow_html=True)

with b_col1:
    df_ex = df.copy()
    df_ex['순번'] = range(1, len(df)+1)
    df_ex = df_ex[['순번', 'timestamp', 'author', 'item_name', 'is_update', 'is_dtc']]
    df_ex.columns = ['순번', '시간', '이름', 'VIN', '업데이트', 'DTC']
    towrite = io.BytesIO()
    df_ex.to_excel(towrite, index=False)
    st.download_button("📥 VIN 현황 저장", towrite.getvalue(), "list.xlsx", use_container_width=True)

with b_col2:
    def create_photos_excel():
        towrite_p = io.BytesIO()
        with pd.ExcelWriter(towrite_p, engine='xlsxwriter') as writer:
            for vin in df['item_name'].unique():
                photos = db_manager.get_photos_by_vin(conn, vin)
                if photos:
                    sheet = writer.book.add_worksheet(name=str(vin))
                    for idx, (img_data,) in enumerate(photos):
                        sheet.insert_image(chr(66+(idx*10))+'2', 'p.png', {'image_data': io.BytesIO(img_data), 'x_scale': 0.3, 'y_scale': 0.3})
        return towrite_p.getvalue()
    
    st.download_button("📥 상세 사진 다운로드", data=create_photos_excel(), file_name="photos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

# 6. 리스트 표시 (텍스트 바로 옆에 버튼 배치)
for row in df.itertuples():
    # 텍스트와 버튼을 포함하는 한 줄 구성
    col_text, col_btn = st.columns([8, 2])
    col_text.markdown(f"<small>{row.timestamp} | **{row.item_name}** | {row.author} (UP:{row.is_update}/DTC:{row.is_dtc})</small>", unsafe_allow_html=True)
    
    # 버튼 영역을 한 줄로 구성
    sub_col1, sub_col2 = col_btn.columns(2)
    if sub_col1.button("수정", key=f"e{row.id}"):
        st.session_state.update({"edit_id": row.id, "current_author": row.author, "next_vin": row.item_name, "next_upd": (row.is_update=='Y'), "next_dtc": (row.is_dtc=='Y')})
        st.rerun()
    if sub_col2.button("삭제", key=f"d{row.id}"):
        db_manager.delete_all_data_by_vin(conn, row.id, row.item_name)
        st.rerun()
