import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time

# 1. 頁面基本設定
st.set_page_config(page_title="18銅人陣：114實戰校準版", layout="wide", page_icon="🏫")

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
    st.title("🛡️ 18 銅人陣：校長甄試實戰系統")
    pwd = st.text_input("🔑 請輸入入陣密碼：", type="password")
    if st.button("確認入陣"):
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

# --- 3. 向度池 ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園「教育善好」願景、品牌學校形塑、ESG 永續經營。",
    "📘 課程發展與新課綱領航": "108 課綱深耕、雙語教育與國際教育 (SDGs)、素養導向教學。",
    "📖 教學領航與數位轉型": "GenAI 教學應用、數位公民素養、教師 PLC 運作實務。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制新制、親師溝通危機處理策略。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理健康韌性、正向管教。"
}

# --- 4. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📰 1. 情報轉化", "📚 2. 專題筆記", "✍️ 3. 模擬練習"])

with tab1:
    st.header("📰 情報獲取與轉化")
    st.markdown("##### 📍 校長必讀資訊來源")
    c = st.columns(4)
    links = [("🏛️ 教育部", "https://www.edu.tw/News.aspx?n=9E7AC85F1954DDA8&sms=169B8E91BB75571F"),
             ("🏫 桃園局", "https://www.tycg.gov.tw/edu/index.jsp"),
             ("📖 e 院", "https://e-naer.naer.edu.tw/"),
             ("🌟 領航", "https://www.tycg.gov.tw/edu/home.jsp?id=69")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)

    st.markdown("---")
    news_clip = st.text_area("在此貼上新聞內容，AI 將為您轉化為練習專題：", height=150)
    if st.button("🎯 轉化為專題"):
        if news_clip and model:
            with st.spinner("分析中..."):
                extracted = model.generate_content(f"將此新聞提取為校長甄試專題標題：\n{news_clip}").text.strip()
                st.session_state.pending_note_topic = extracted
                st.success(f"✅ 已鎖定專題：{extracted}")

with tab2:
    st.header("📚 專題實務筆記")
    note_t = st.text_input("專題名稱", st.session_state.get('pending_note_topic', "數位學習精進方案"))
    if st.button("📖 生成 AI 策略"):
        if model:
            with st.spinner("生成中..."):
                p = f"以教育局長高度針對『{note_t}』提供 Who, What, How, Why 策略及桃園政策連結。"
                st.session_state.last_note = model.generate_content(p).text
    if 'last_note' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state.last_note)

with tab3:
    st.header("⚖️ 37 分鐘限時實戰模擬")
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
        if st.button("🚀 生成 114 年風格試題"):
            if model:
                with st.spinner("命題中..."):
                    q = model.generate_content(f"針對『{THEME_POOL[sel_choice]}』出一題25分申論題。").text
                    st.session_state.current_q = q
                    st.session_state.current_theme = sel_choice
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請生成試題")}</div>', unsafe_allow_html=True)

    with col_r:
        st.subheader("✍️ 答案卷")
        ans_input = st.text_area("在此輸入您的擬答...", height=350, key="ans_box")
        st.markdown(f'<span class="word-count-badge">📝 字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        if st.button("⚖️ 提交 AI 批改"):
            if model and ans_input:
                with st.spinner("閱卷中..."):
                    fb = model.generate_content(f"題目：{st.session_state.current_q}\n作答：{ans_input}\n請給予25分制評分與建議。").text
                    st.session_state.feedback = fb
                    st.markdown(f"### 🤖 AI 回饋\n{fb}")
