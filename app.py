import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time

# 1. 頁面基本設定
st.set_page_config(page_title="教育閱讀專區", layout="wide", page_icon="🏫")

# --- 🎨 核心 CSS 樣式 ---
st.markdown("""
    <style>
    .scroll-box { height: 260px; overflow-y: auto; border: 2px solid #D4AF37; padding: 20px; border-radius: 10px; background-color: #1e1e1e; color: #f0f0f0; margin-bottom: 20px; }
    .word-count-badge { background-color: #008080; color: white; padding: 6px 15px; border-radius: 20px; font-size: 0.9rem; font-weight: bold; }
    .timer-display { font-size: 2rem; font-weight: bold; color: #ff4b4b; text-align: center; border: 2px solid #ff4b4b; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 🔐 密碼保護 ---
if "password_correct" not in st.session_state:
    st.title("🛡️ 小閱讀、大心情")
    pwd = st.text_input("🔑 請輸入入陣密碼：", type="password")
    if st.button("進來聊聊"):
        if pwd == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("密碼錯誤")
    st.stop()

# --- 2. 核心 AI 初始化 ---
@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in available_models if "gemini-1.5-flash" in m), 
                     next((m for m in available_models if "gemini-pro" in m), 
                     available_models[0] if available_models else None))
        return genai.GenerativeModel(target) if target else None
    except Exception as e:
        st.error(f"⚠️ AI 連線失敗：{e}")
        return None

model = init_ai()

# --- 3. 向度池 (112-114 趨勢校準) ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園「教育善好」願景、品牌學校形塑、ESG 永續經營、韌性領導、校園文化重塑。",
    "📘 課程發展與新課綱領航": "108 課綱深耕、雙語教育、SDGs 國際教育、跨域課程整合、自主學習支持系統。",
    "📖 教學領航與數位轉型": "GenAI 教學應用倫理、數位公民素養、教師 PLC 運作、生生用平板 2.0、數位減量與精進。",
    "⚖️ 法理實務與危機處理": "校事會議流程、霸凌防制條例新制、性平法實務、親師衝突溝通、校園公共關係。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理健康、正向管教、中輟預防、特教融合教育。"
}

# --- 4. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📰 1. 文章閱讀區", "📚 2. 專題筆記區", "✍️ 3. 模擬練習區"])

# --- Tab 1: 文章閱讀與深度導讀 ---
with tab1:
    st.header("📰 文章閱讀與轉化")
    st.markdown("##### 📍 重要必讀資訊來源")
    c = st.columns(4)
    links = [("🏛️ 教育部", "https://www.edu.tw/News.aspx?n=9E7AC85F1954DDA8&sms=169B8E91BB75571F"),
             ("🏫 教育局", "https://www.tyc.edu.tw/"),
             ("📖 國教院", "https://www.naer.edu.tw/"),
             ("🌟 教評月刊", "http://www.ater.org.tw/commentmonth.html")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)

    st.markdown("---")
    news_clip = st.text_area("在此貼上新聞內容，AI 將為您進行深度導讀與考點轉化：", height=150, placeholder="貼上新聞文字...")
    
    if st.button("🎯 重點摘錄與導讀"):
        if news_clip and model:
            with st.spinner("資深分析師導讀中..."):
                reading_prompt = f"""
                你現在是「教育政策高級分析師」。請針對這段新聞，提供一份專門為「校長甄試考生」準備的深層導讀報告。
                
                【新聞內容】：{news_clip}
                
                ---
                請按以下結構輸出（使用 Markdown 格式）：
                1. 📌 **轉化專題標題**：(具備申論題氣勢的 15 字以內標題)
                2. 🔍 **核心要義**：(用兩句話總結關鍵政策或教育脈絡)
                3. 💡 **校長經營視角**：(列出 3 個校長層級的經營關鍵點)
                4. 🔗 **政策對接**：(如何對接到桃園「教育善好」、SDGs、或 112-114 教育趨勢？)
                5. ❓ **潛在考點命題**：(模擬一個 25 分的申論題題目)
                """
                response = model.generate_content(reading_prompt)
                full_analysis = response.text
                
                try:
                    title_line = full_analysis.split('1. 📌 **轉化專題標題**：')[1].split('\n')[0].strip()
                    st.session_state.pending_note_topic = title_line
                except:
                    st.session_state.pending_note_topic = "最新教育專題"
                
                st.info(f"### 📰 教育趨勢導讀報告")
                st.markdown(full_analysis)
                st.success("✅ 已鎖定專題標題，可至「專題筆記區」生成戰略矩陣。")

# --- Tab 2: 專題戰略筆記 (純精華版) ---
with tab2:
    st.header("📚 專題實務戰略筆記")
    note_t = st.text_input("專題名稱", st.session_state.get('pending_note_topic', "數位學習精進方案"))
    
    if st.button("📖 生成校長視角策略"):
        if model:
            with st.spinner("煉製核心矩陣中..."):
                p = f"""
                你現在是教育行政專家。請針對專題『{note_t}』生成一份純粹的「校長經營戰略矩陣」。
                
                【限制要求】：
                1. 嚴禁任何開場白（例如：身為校長我會...）或結束語（例如：綜上所述...）。
                2. 嚴禁散文式論述，僅輸出表格與要點。
                3. 請直接以 Markdown 表格形式輸出。
                
                【表格維度】：
                - **維度 (Dimension)**：Who, What, How, Why
                - **核心策略內容**：精煉的行動方案
                - **桃園政策連結**：對接「教育善好」或局端計畫
                - **績效指標 (KPI)**：量化目標或質性觀察
                """
                st.session_state.last_note = model.generate_content(p).text
                
    if 'last_note' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state.last_note)
        if st.button("📋 重新生成專題"):
            st.session_state.pop('last_note')
            st.rerun()

# --- Tab 3: 模擬練習與教授級評分 ---
with tab3:
    st.header("⚖️ 限時實戰模擬區")
    col_l, col_r = st.columns([1, 1.2], gap="large")
    with col_l:
        st.subheader("📍 模擬命題")
        timer_placeholder = st.empty()
        if st.button("⏱️ 開始計時"):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True
        
        if st.session_state.get("timer_running", False):
            rem = max(0, 37 * 60 - int(time.time() - st.session_state.start_time))
            mins, secs = divmod(rem, 60)
            timer_placeholder.markdown(f'<div class="timer-display">⏳ {mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
        
        sel_choice = st.selectbox("選取向度", list(THEME_POOL.keys()))
        if st.button("🚀 生成 114 年趨勢試題"):
            if model:
                with st.spinner("教授命題中..."):
                    q = model.generate_content(f"請針對『{THEME_POOL[sel_choice]}』出一題25分申論題。要求：情境化、複合型問題，測驗校長領導格局與政策轉化力。").text
                    st.session_state.current_q = q
                    st.session_state.current_theme = sel_choice
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請先生成試題")}</div>', unsafe_allow_html=True)

    with col_r:
        st.subheader("✍️
