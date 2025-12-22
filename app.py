import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# --- 1. 系統層級與視覺設定 ---
st.set_page_config(page_title="體育課程研究室 | 行政專業發展模擬", layout="wide", page_icon="🏫")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    .block-container { max-width: 1100px !important; padding-top: 1.5rem !important; margin: auto; }
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; font-weight: 300; letter-spacing: 0.02em; }
    .stApp { background-color: #1a1d24; color: #eceff4; }
    .main-header {
        text-align: center; background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 1.8rem; margin-bottom: 1.5rem;
    }
    .scroll-box { 
        height: auto; min-height: 120px; overflow-y: auto; border: 1px solid #3b4252; padding: 25px; 
        border-radius: 12px; background: #242933; color: #e5e9f0; line-height: 1.85; font-size: 1.05rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;
    }
    .alert-box {
        background: rgba(136, 192, 208, 0.05); border: 1px solid #4c566a;
        color: #d8dee9; padding: 12px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 15px;
    }
    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 6px 12px; border-radius: 4px; font-size: 0.8rem; border: 1px solid #434c5e; }
    .stButton>button { border-radius: 8px; background-color: #2e3440; color: #88c0d0; border: 1px solid #434c5e; width: 100%; height: 3rem; font-weight: 500; }
    .stButton>button:hover { background-color: #88c0d0; color: #1a1d24; border: 1px solid #88c0d0; }
    .tiny-label { font-size: 0.85rem; color: #81a1c1; margin-bottom: 5px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始化功能 ---
if "init_done" not in st.session_state:
    st.session_state.update({
        "password_correct": False, 
        "current_q": "", 
        "suggested_structure": "", 
        "init_done": True
    })

@st.cache_resource
def init_ai():
    try:
        # 修正：確保從 secrets 的正確層級讀取
        api_key = st.secrets.get("gemini", {}).get("api_key")
        if not api_key:
            return "ERROR: Missing API Key in Secrets"
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        return f"ERROR: {str(e)}"

@st.cache_resource
def init_google_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds).open("Education_Exam_Records").sheet1
    except: return None

model = init_ai()
sheet_conn = init_google_sheet()

def stream_generate(prompt, container=None):
    if isinstance(model, str): # 如果 model 初始化時回傳的是錯誤字串
        st.error(model)
        return ""
    
    placeholder = container.empty() if container else st.empty()
    full_response = ""
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        return full_response
    except Exception as e:
        st.error(f"AI 生成出錯，請檢查網路或 API Key：{str(e)}")
        return ""

def log_to_google_sheets(topic, score, user_answer, feedback):
    if sheet_conn:
        try:
            row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), topic, score, user_answer[:4000], feedback[:800].replace('\n', ' ') + "..."]
            sheet_conn.append_row(row)
        except: pass

# --- 3. 穩定版權限驗證 ---
if not st.session_state["password_correct"]:
    st.markdown('<h1 class="main-header">🛡️ 行政專業發展 | 系統登入</h1>', unsafe_allow_html=True)
    col_p = st.columns([1,2,1])[1]
    with col_p:
        pwd = st.text_input("🔑 輸入行政通關密碼：", type="password", key="login_field")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.success("驗證成功！正在載入...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("密碼錯誤。")
    st.stop()

# --- 4. 主程式頁面 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 戰略矩陣", "✍️ 實戰模擬", "📊 歷程紀錄"])

with tab1:
    st.markdown("### 📍 權威資訊導引")
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    c = st.columns(5)
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url, use_container_width=True)
    
    news_clip = st.text_area("🔍 趨勢文本分析：", height=150, placeholder="貼上教育新聞內容...")
    if st.button("🎯 執行深度考點轉化"):
        if news_clip:
            stream_generate(f"請以高階教育行政視角分析此文本之核心考點，並給出三個申論命題方向：\n{news_clip}")

with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    note_t = st.text_input("專題名稱：", placeholder="例如：少子化浪潮下之特色學校經營", key="nt_t2")
    ref_text_note = st.text_area("參考文本：", height=150, placeholder="貼上最新法規或教育理論...", key="rt_t2")
    if st.button("📖 生成行政戰略矩陣"):
        if note_t:
            p = f"主題：{note_t}\n參考資料：{ref_text_note}\n請撰寫行政戰略筆記：一、前言。二、學理。三、行動矩陣(表格)。四、結語。"
            stream_generate(p)

with tab3:
    st.markdown("""<div class="alert-box">🎯 <strong>平衡命題機制啟動</strong></div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([0.8, 3.5, 0.8])
    with c2:
        manual_theme = st.text_input("🖋️ 指定試題主題", placeholder="例如：校事會議處理、少子化下的特色招生...")
    with c3:
        st.write("") # 補齊間距
        gen_btn = st.button("🚀 生成試題")

    if gen_btn and manual_theme:
        p = f"你現在是教育行政評閱委員。請針對『{manual_theme}』，設計一則 200 字左右的情境申論題，要求考生以行政領導者角色提出策略。"
        st.markdown('<div class="scroll-box">', unsafe_allow_html=True)
        st.session_state.current_q = stream_generate(p)
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state.current_q:
        st.markdown(f'<div class="scroll-box">{st.session_state.current_q}</div>', unsafe_allow_html=True)

    if st.session_state.current_q:
        if st.button("💡 獲取黃金架構建議"):
            with st.expander("🏆 答題架構建議", expanded=True):
                stream_generate(f"針對題目：{st.session_state.current_q}\n提供前言、中段、結語之極簡架構。")

    ans_input = st.text_area("🖋️ 擬答作答區", height=450, key="ans_main")
    if st.button("⚖️ 提交閱卷評分"):
        if ans_input:
            eval_p = f"題目：{st.session_state.current_q}\n擬答：{ans_input}\n請依據法規精準評分(滿分25)並給予改進建議。"
            res = stream_generate(eval_p)
            score_match = re.search(r"(\d+)/25", res)
            log_to_google_sheets(manual_theme, score_match.group(1) if score_match else "N/A", ans_input, res)

with tab4:
    st.markdown("### 📊 行政成長歷程分析")
    if sheet_conn:
        try:
            data = sheet_conn.get_all_records()
            if data:
                df = pd.DataFrame(data)
                # --- 修正 PyArrow 錯誤：確保分數欄位是數字，並處理 N/A ---
                df.iloc[:, 2] = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0)
                
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("總練習次數", len(df))
                with c2: st.metric("平均得分", f"{df.iloc[:, 2].mean():.1f}")
                with c3: st.metric("最高得分", f"{df.iloc[:, 2].max():.0f}")
                
                st.line_chart(df.iloc[:, 2])
                st.dataframe(df.astype(str), use_container_width=True) # 轉字串顯示防止格式崩潰
            else: st.info("尚無紀錄。")
        except Exception as e:
            st.error(f"數據載入失敗：{str(e)}")
