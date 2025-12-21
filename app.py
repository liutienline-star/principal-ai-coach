import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# 1. 頁面基本設定
st.set_page_config(page_title="體育課程研究室", layout="wide", page_icon="🏫")

# --- 🎨 CSS 加固版：強制鎖定 520px 並修復跑版 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
    .stApp { background-color: #1e2128; color: #cbd5e0; }
    .main-header {
        background: linear-gradient(135deg, #d4c19c 0%, #a88e5a 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 700; font-size: 2.2rem; margin-bottom: 1.2rem;
    }
    
    /* 核心：鎖定題目區與作答區高度完全一致 */
    .scroll-box { 
        height: 520px !important; 
        max-height: 520px !important;
        overflow-y: auto !important; 
        border: 1px solid rgba(212, 193, 156, 0.15); 
        padding: 30px; border-radius: 18px; background: #282c37; color: #e2e8f0; 
        line-height: 1.75; font-size: 1.05rem; box-shadow: 0 12px 30px rgba(0,0,0,0.15);
    }
    
    /* 作答區 Textarea 加固 */
    div[data-baseweb="textarea"] textarea {
        color: #f1f5f9 !important; -webkit-text-fill-color: #f1f5f9 !important;
        font-size: 1.05rem !important; line-height: 1.7 !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 520px !important; 
        min-height: 520px !important;
        background-color: #282c37 !important;
        border-radius: 18px !important; border: 1px solid rgba(212, 193, 156, 0.15) !important;
    }

    .guide-box {
        background: rgba(212, 193, 156, 0.05); border: 1px dashed rgba(212, 193, 156, 0.3);
        padding: 18px; border-radius: 12px; margin-top: 10px; font-size: 0.95rem; color: #d4c19c;
    }
    .tiny-label { font-size: 0.85rem !important; color: #8e99a7; margin-bottom: 8px; font-weight: 500; }
    .stButton>button { border-radius: 10px; background-color: #2d323e; color: #d4c19c; border: 1px solid rgba(212, 193, 156, 0.25); }
    .stButton>button:hover { background-color: #d4c19c; color: #1a1c23; }
    .timer-mini { font-size: 1.3rem; font-weight: 600; color: #f5a9a9; background: rgba(245, 169, 169, 0.05); padding: 8px; border-radius: 10px; }
    .word-count-badge { background: rgba(74, 124, 124, 0.15); color: #81e6d9; padding: 6px 16px; border-radius: 50px; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- ☁️ Google Sheets 串接 ---
def log_to_google_sheets(topic, score, user_answer, feedback):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Education_Exam_Records").sheet1
        row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), topic, score, user_answer, feedback[:250].replace('\n', ' ') + "...", ""]
        sheet.append_row(row)
        return True
    except: return False

def get_records():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Education_Exam_Records").sheet1
        return pd.DataFrame(sheet.get_all_records())
    except: return pd.DataFrame()

# --- 🔐 密碼保護 ---
if "password_correct" not in st.session_state:
    st.markdown('<h1 class="main-header">🛡️ 體育課程研究室</h1>', unsafe_allow_html=True)
    col_p2 = st.columns([1,2,1])[1]
    with col_p2:
        pwd = st.text_input("🔑 請輸入行政通關密碼：", type="password")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼驗證失敗。")
    st.stop()

# --- 2. 核心 AI 初始化 ---
@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in available_models if "gemini-1.5-flash" in m), available_models[0])
        return genai.GenerativeModel(target)
    except: return None

model = init_ai()

# --- 3. 向度池 ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園教育願景、品牌學校形塑、ESG永續經營、韌性領導、校長領導學理。",
    "📘 課程發展與課綱領航": "108課綱深綱、雙語教育、SDGs國際教育、跨域課程整合。",
    "📖 教學領航與數位轉型": "GenAI教學倫理、數位公民素養、教師PLC運作、生生用平板。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制新制、性平法實務、親師衝突溝通、組織正義。",
    "❤️ SEL 與學生輔導": "社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 4. 頂部標題 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)

# --- 5. 功能分頁 ---
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

with tab1:
    st.markdown("### 📍 權威資訊分析")
    news_clip = st.text_area("🔍 欲分析的教育新聞或政策文本：", height=180, key="news_in_v8")
    if st.button("🎯 開始深度考點轉化"):
        if news_clip and model:
            with st.spinner("解析中..."):
                st.markdown(model.generate_content(f"分析考點：\n{news_clip}").text)

with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    note_t = st.text_input("當前鎖定專題：", "數位學習精進方案 2.0")
    if st.button("📖 生成行政戰略架構"):
        if model:
            with st.spinner("煉製中..."):
                st.markdown(model.generate_content(f"針對專題『{note_t}』，提供行動矩陣與 KPI。").text)

# --- Tab 3: 實戰模擬 ---
with tab3:
    c_timer_btn, c_timer_val, c_select, c_input, c_gen = st.columns([0.8, 1, 1.5, 2, 0.8])
    with c_timer_btn:
        if st.button("啟動模擬", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True
    with c_timer_val:
        if st.session_state.get("timer_running", False):
            rem = max(0, 37 * 60 - int(time.time() - st.session_state.start_time))
            st.markdown(f'<div class="timer-mini">{rem//60:02d}:{rem%60:02d}</div>', unsafe_allow_html=True)
        else: st.markdown('<div class="timer-mini" style="color:#666;">37:00</div>', unsafe_allow_html=True)
    with c_select:
        sel_choice = st.selectbox("向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    with c_input:
        manual_theme = st.text_input("自訂主題", placeholder="若不填則依向度命題...", key="v8_custom", label_visibility="collapsed")
    with c_gen:
        if st.button("生成試題", use_container_width=True):
            if model:
                with st.spinner("出題中..."):
                    target_pool = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                    q_prompt = f"請校長甄試命題委員效法第29期風格，針對『{target_pool}』命一題申論題。情境150字內。"
                    st.session_state.current_q = model.generate_content(q_prompt).text
                    st.session_state.suggested_structure = None

    st.markdown("<br>", unsafe_allow_html=True)
    col_q, col_a = st.columns([1, 1.8], gap="large")
    
    with col_q:
        st.markdown('<p class="tiny-label">📍 模擬試題視窗 (520px)</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "試題顯示區")}</div>', unsafe_allow_html=True)
        if st.session_state.get("current_q") and st.button("💡 獲取答題架構建議", use_container_width=True):
            st.session_state.suggested_structure = model.generate_content(f"針對此題提供架構建議：{st.session_state.current_q}").text
        if st.session_state.get("suggested_structure"):
            st.markdown(f'<div class="guide-box">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    with col_a:
        st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (520px)</p>', unsafe_allow_html=True)
        ans_input = st.text_area("作答", label_visibility="collapsed", key="v8_ans", height=500)
        f_count, f_submit = st.columns([1, 1])
        with f_count: st.markdown(f'<span class="word-count-badge">📝 字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        with f_submit:
            if st.button("⚖️ 提交閱卷評分", use_container_width=True):
                if model and ans_input:
                    with st.spinner("閱卷中..."):
                        res = model.generate_content(f"題目：{st.session_state.current_q}\n擬答：{ans_input}\n給予評分(/25)與建議。").text
                        st.session_state.feedback = res
                        score_match = re.search(r"(\d+)/25", res)
                        log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_match.group(1) if score_match else "N/A", ans_input, res)

    if 'feedback' in st.session_state:
        st.markdown(f"<div style='margin-top:30px; padding:25px; background:#2d323e; border-radius:18px; border-left:6px solid #d4c19c;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

with tab4:
    st.markdown("### 📊 學習歷程分析")
    df = get_records()
    if not df.empty:
        df['score_num'] = pd.to_numeric(df['實戰分數'], errors='coerce')
        st.line_chart(df.set_index('紀錄時間')['score_num'])
        st.dataframe(df, use_container_width=True)
    else: st.info("尚無紀錄。")－
