import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# --- 1. 系統層級設定 ---
st.set_page_config(page_title="體育課程研究室 | 校長甄試趨勢模擬", layout="wide", page_icon="🏫")

# --- 2. 視覺優化 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    .block-container {
        max-width: 1150px !important;
        padding-top: 2rem !important;
        margin: auto;
    }

    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif; 
        font-weight: 300; 
    }
    
    .stApp { background-color: #1a1d24; color: #eceff4; }

    .main-header {
        text-align: center;
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 2.2rem; margin-bottom: 2rem;
    }

    .scroll-box { 
        height: auto; min-height: 120px; overflow-y: auto; 
        border: 1px solid #3b4252; padding: 25px; 
        border-radius: 12px; background: #242933; 
        color: #e5e9f0; line-height: 1.8; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;
    }

    .suggestion-content h4 {
        font-size: 1rem !important;
        font-weight: 400 !important;
        color: #88c0d0 !important;
        margin-top: 15px !important;
        border-bottom: 1px solid #3b4252;
        padding-bottom: 3px;
    }
    
    .suggestion-scroll {
        max-height: 400px;
        overflow-y: auto;
        padding: 15px;
        line-height: 1.7;
        background: #2e3440;
        border-radius: 8px;
    }

    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; font-size: 1.1rem !important; line-height: 1.8 !important; padding: 20px !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 600px !important; background-color: #242933 !important; border-radius: 12px !important;
    }

    .alert-box {
        background: rgba(136, 192, 208, 0.05); border: 1px solid #4c566a;
        color: #d8dee9; padding: 15px; border-radius: 8px; font-size: 0.9rem; margin-bottom: 15px;
    }

    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 6px 15px; border-radius: 4px; font-size: 0.85rem; border: 1px solid #434c5e; }
    .stButton>button { border-radius: 8px; background-color: #2e3440; color: #88c0d0; border: 1px solid #434c5e; width: 100%; height: 3.2rem; font-weight: 500; }
    .stButton>button:hover { background-color: #88c0d0; color: #1a1d24; border: 1px solid #88c0d0; }
    .tiny-label { font-size: 0.85rem; color: #81a1c1; margin-bottom: 5px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 狀態初始化 ---
if "init_done" not in st.session_state:
    st.session_state.update({
        "init_done": True,
        "password_correct": False,
        "current_q": "",
        "feedback": "",
        "suggested_structure": "",
        "start_time": None
    })

# --- 4. 資源初始化 ---
@st.cache_resource(ttl=3600)
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in available_models if "flash" in m), available_models[0])
        return genai.GenerativeModel(target_model)
    except: return None

@st.cache_resource(ttl=3600)
def init_google_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds).open("Education_Exam_Records").sheet1
    except: return None

model = init_ai()
sheet_conn = init_google_sheet()

def stream_generate(prompt_text, container=None):
    if not model: return ""
    placeholder = container.empty() if container else st.empty()
    full_response = ""
    try:
        response = model.generate_content(prompt_text, stream=True, request_options={'timeout': 600})
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(full_response + "▌") 
        placeholder.markdown(full_response)
        return full_response
    except: return full_response

def log_to_google_sheets(topic, score, user_answer, feedback):
    if sheet_conn:
        try:
            row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), topic, score, user_answer[:4000], feedback[:800].replace('\n', ' ') + "..."]
            sheet_conn.append_row(row)
        except: pass

# --- 5. 權限驗證 ---
if not st.session_state["password_correct"]:
    st.markdown('<h1 class="main-header">🛡️ 體育課程研究室 | 行政登入</h1>', unsafe_allow_html=True)
    col_p = st.columns([1,2,1])[1]
    with col_p:
        pwd = st.text_input("🔑 輸入通關密碼：", type="password")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼錯誤。")
    st.stop()

# --- 6. 主程式頁面 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url, use_container_width=True)
    news_clip = st.text_area("🔍 欲分析的教育新聞文本：", height=150, placeholder="貼上新聞文字以轉化考點...", key="news_v13")
    if st.button("🎯 執行趨勢考點轉化"):
        if news_clip: stream_generate(f"請以教育行政視角分析考點並給出可能的出題方向：\n{news_clip}")

with tab2:
    st.markdown("### 📚 實務戰略筆記")
    note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導", key="nt_t2")
    ref_text_note = st.text_area("參考法規/文本：", height=100, placeholder="貼上相關法條以確保準確性...", key="rt_t2")
    if st.button("📖 生成行政戰略架構"):
        if note_t: stream_generate(f"主題：{note_t}\n參考文本：{ref_text_note}\n請依實務撰寫包含前言、核心策略與結語之筆記。")

# --- Tab 3: 實戰模擬 (趨勢命題核心修正) ---
with tab3:
    st.markdown("""<div class="alert-box">🎯 <strong>2025 趨勢命題：</strong> 系統將結合當前社會現況與政策脈動，模擬第 29 期校長筆試風格。</div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        st.markdown('<p class="tiny-label">⏱️ 計時器</p>', unsafe_allow_html=True)
        if st.button("啟動模擬計時"):
            st.session_state.start_time = time.time()
            st.success("計時開始")
    with c2:
        st.markdown('<p class="tiny-label">🖋️ 演練專題主題 (請輸入欲演練之核心概念)</p>', unsafe_allow_html=True)
        manual_theme = st.text_input("主題輸入", placeholder="例如：校事會議新制、GenAI教學轉型、親師衝突危機處理...", key="cust_theme", label_visibility="collapsed")
    with c3:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        gen_btn = st.button("生成趨勢試題", use_container_width=True)

    with st.expander("⚖️ 最新法規/SOP 校準座 (若有特定新修正條文請貼入)"):
        ref_text_sim = st.text_area("校準文本", height=100, placeholder="例如：113年霸凌防制準則新制內容...", key="sim_ref")

    st.markdown('<p class="tiny-label">📍 實務模擬試題 (精煉情境與雙段提問)</p>', unsafe_allow_html=True)
    q_container = st.container()

    if gen_btn:
        target_topic = manual_theme if manual_theme.strip() else "學校行政領導與經營轉型"
        # --- 趨勢感 Prompt 優化邏輯 ---
        trend_prompt = f"""
        你現在是校長甄試閱卷委員。請針對『{target_topic}』，參考法規『{ref_text_sim}』，
        設計一題具備「行政決斷高度」與「2025 趨勢感」的申論題。
        
        【命題規範】：
        1. 風格：參照第29期校長筆試風格，不堆砌詞藻，直擊行政痛點。
        2. 題幹：字數約 150-200 字。請描述一個結合「最新政策」與「複雜社會現況（如媒體、網路輿論、家長壓力）」的行政衝突情境。
        3. 提問格式：
           (一) 請就校長領導視角，分析本案的核心爭點、法律風險與組織挑戰為何？
           (二) 請擬定具體的經營策略與轉化作為，以達成學校永續發展之目標。
        
        請直接輸出題目內容。
        """
        with q_container:
            with st.markdown('<div class="scroll-box">', unsafe_allow_html=True):
                st.session_state.current_q = stream_generate(trend_prompt)
        st.session_state.suggested_structure = ""
    else:
        if st.session_state.get("current_q"):
            q_container.markdown(f'<div class="scroll-box">{st.session_state.current_q}</div>', unsafe_allow_html=True)

    # --- 黃金架構建議 ---
    if st.session_state.get("current_q"):
        if st.button("💡 獲取黃金架構建議 (收納版)"):
            with st.expander("🏆 黃金三段式答題架構", expanded=True):
                st.markdown('<div class="suggestion-content"><div class="suggestion-scroll">', unsafe_allow_html=True)
                s_prompt = f"題目：{st.session_state.current_q}\n請提供視覺極簡的答題架構。嚴禁粗體標題。使用 #### 作為小標題：一、前言(破題關鍵字)；二、行動策略(行政/教學/整合)；三、結語(預期成效)。"
                st.session_state.suggested_structure = stream_generate(s_prompt)
                st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="tiny-label">🖋️ 擬答作答區</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答內容", label_visibility="collapsed", key="ans_sim", height=500)

    f1, f2 = st.columns([1, 1])
    with f1: st.markdown(f'<span class="word-count-badge">📝 當前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
    with f2:
        if st.button("⚖️ 提交閱卷評分", use_container_width=True):
            if ans_input:
                st.markdown("### ⚖️ 專業評閱意見")
                eval_prompt = f"題目：{st.session_state.current_q}\n考生擬答：{ans_input}\n請依據行政實務精準評分（滿分25），並給予改進建議。"
                final_feedback = stream_generate(eval_prompt)
                score_match = re.search(r"(\d+)/25", final_feedback)
                log_to_google_sheets(manual_theme, score_match.group(1) if score_match else "N/A", ans_input, final_feedback)

with tab4:
    st.markdown("### 📊 學習歷程分析")
    if sheet_conn:
        try:
            df = pd.DataFrame(sheet_conn.get_all_records())
            st.dataframe(df, use_container_width=True)
        except: st.info("尚無練習紀錄。")
