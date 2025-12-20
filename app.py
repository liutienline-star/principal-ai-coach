import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

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

# --- 2. 核心初始化 (智慧偵測版：解決 404 錯誤) ---
@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # 自動列出目前 API Key 可用的所有模型
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 優先順序：1.5-flash -> 1.5-pro -> 任何可用模型
        target = ""
        for m in available_models:
            if "gemini-1.5-flash" in m: target = m; break
        if not target:
            for m in available_models:
                if "gemini-pro" in m: target = m; break
        if not target and available_models: target = available_models[0]
        
        if target:
            return genai.GenerativeModel(target)
        return None
    except Exception as e:
        st.error(f"⚠️ AI 初始化失敗，請檢查 API Key 權限：{e}")
        return None

model = init_ai()
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. 核心向度池 ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園「教育善好」願景、品牌學校形塑、校長轉型領導策略、ESG 永續經營。",
    "📘 課程發展與新課綱領航": "108 課綱深耕、雙語教育與國際教育 (SDGs)、在地國際化願景、素養導向教學。",
    "📖 教學領航與數位轉型": "GenAI 教學應用、數位公民素養、教師 PLC、數位學習精進方案實務。",
    "⚖️ 法理實務與危機處理": "校事會議不適任教師處理、霸凌防制新制、性平事件、親師溝通與危機處理策略。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理健康韌性、正向管教、三級輔導機制。"
}

# --- 4. 功能主介面 ---
tab1, tab2, tab3 = st.tabs(["📰 1. 情報轉化", "📚 2. 專題筆記", "✍️ 3. 模擬練習"])

# --- Tab 1: 情報獲取與轉化 ---
with tab1:
    st.header("📰 情報獲取與轉化")
    st.markdown("##### 📍 校長必讀資訊來源")
    
    c = st.columns(4)
    links = [
        ("🏛️ 教育部", "https://www.edu.tw/News.aspx?n=9E7AC85F1954DDA8&sms=169B8E91BB75571F"),
        ("🏫 桃園局", "https://www.tycg.gov.tw/edu/index.jsp"),
        ("📖 e 院", "https://e-naer.naer.edu.tw/"),
        ("🌟 領航", "https://www.tycg.gov.tw/edu/home.jsp?id=69")
    ]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)

    st.markdown("---")
    news_clip = st.text_area("貼上新聞或政策內容，AI 將為您轉化為考試專題：", height=150)
    if st.button("🎯 轉化為專題標題"):
        if news_clip and model:
            with st.spinner("轉化中..."):
                prompt = f"請根據此新聞提取一個適合校長甄試的練習專題名稱：\n{news_clip}"
                extracted = model.generate_content(prompt).text.strip()
                st.session_state.pending_note_topic = extracted
                st.success(f"✅ 已鎖定專題：{extracted}")

# --- Tab 2: 專題筆記 ---
with tab2:
    st.header("📚 專題實務筆記")
    note_t = st.text_input("專題名稱", st.session_state.get('pending_note_topic', "數位學習精進方案"))
    if st.button("📖 生成 AI 策略建議"):
        if model:
            with st.spinner("策略生成中..."):
                p = f"請以教育局長高度，針對『{note_t}』提供 Who, What, How, Why 實務策略，並結合桃園『教育善好』政策。"
                st.session_state.last_note = model.generate_content(p).text
    
    if 'last_note' in st.session_state: 
        st.markdown("---")
        st.markdown(st.session_state.last_note)
        if st.button("🎯 將此筆記轉化為實戰題目"):
            st.session_state.pending_exam_topic = note_t
            st.success("✅ 題目已就緒，請移步至 Tab 3！")

# --- Tab 3: 模擬練習 ---
with tab3:
    st.header("⚖️ 37 分鐘限時實戰模擬")
    col_l, col_r = st.columns([1, 1.2], gap="large")

    with col_l:
        st.subheader("📍 模擬命題")
        timer_placeholder = st.empty()
        
        if st.button("⏱️ 開始 37 分鐘倒數"):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True

        if st.session_state.get("timer_running", False):
            elapsed = time.time() - st.session_state.start_time
            rem = max(0, 37 * 60 - int(elapsed))
            mins, secs = divmod(rem, 60)
            timer_placeholder.markdown(f'<div class="timer-display">⏳ 剩餘：{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            if rem <= 0: st.session_state.timer_running = False; st.error("⏰ 時間到！")
        else:
            timer_placeholder.markdown(f'<div class="timer-display" style="color:#aaa;">⏳ 37:00</div>', unsafe_allow_html=True)

        sel_choice = st.selectbox("選取命題向度", list(THEME_POOL.keys()))
        if st.button("🚀 生成 114 年實戰風格試題"):
            if model:
                with st.spinner("命題中..."):
                    topic = st.session_state.get('pending_exam_topic', THEME_POOL[sel_choice])
                    p = f"請針對『{topic}』出一題25分的申論題，須符合桃園最新教育脈動。"
                    st.session_state.current_q = model.generate_content(p).text
                    st.session_state.current_theme = sel_choice
                    st.rerun()

        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請點擊按鈕生成試題。")}</div>', unsafe_allow_html=True)

    with col_r:
        st.subheader("✍️ 答案卷")
        ans_input = st.text_area("在此輸入您的擬答內容...", height=400, key="ans_box")
        st.markdown(f'<span class="word-count-badge">📝 目前字數：{len(ans_input)} 字</span>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⚖️ 提交 AI 批改"):
                if model and ans_input:
                    with st.spinner("評析中..."):
                        eval_p = f"題目：{st.session_state.current_q}\n作答：{ans_input}\n請給予25分制評分，並提供建議與桃園政策連結。"
                        st.session_state.feedback = model.generate_content(eval_p).text
                        st.markdown(f"### 🤖 AI 閱卷回饋\n{st.session_state.feedback}")
        
        with c2:
            if st.button("💾 儲存紀錄至 Sheet"):
                try:
                    new_rec = pd.DataFrame([{
                        "時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "向度": st.session_state.get('current_theme', '未分類'),
                        "題目": st.session_state.get('current_q', ''),
                        "擬答": ans_input,
                        "AI評析": st.session_state.get('feedback', '尚未批改')
                    }])
                    existing_df = conn.read(spreadsheet=st.secrets["gsheet_url"])
                    updated_df = pd.concat([existing_df, new_rec], ignore_index=True)
                    conn.update(spreadsheet=st.secrets["gsheet_url"], data=updated_df)
                    st.success("✅ 練功紀錄已同步！")
                except Exception as e:
                    st.error(f"儲存失敗：{e}")
