import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time

# 1. 頁面基本設定
st.set_page_config(page_title="教育領航者閱讀專區", layout="wide", page_icon="🏫")

# --- 🎨 進階美化 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;700&display=swap');
    
    /* 全域字體設定 */
    html, body, [class*="css"] {
        font-family: 'Noto Sans TC', sans-serif;
    }

    /* 主背景與卡片 */
    .stApp {
        background-color: #0e1117;
    }
    
    /* 核心試題視窗優化 */
    .scroll-box { 
        height: 520px; 
        overflow-y: auto; 
        border: 1px solid rgba(212, 175, 55, 0.3); 
        padding: 30px; 
        border-radius: 15px; 
        background: linear-gradient(145deg, #1e1e1e, #252525);
        color: #e0e0e0; 
        margin-bottom: 20px; 
        line-height: 1.8;
        font-size: 1.1rem;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.5), 0 5px 15px rgba(0,0,0,0.3);
    }

    /* 頂部標題美化 */
    .main-header {
        background: linear-gradient(90deg, #D4AF37, #Faf0af);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    /* 按鈕美化 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #262730;
        color: #D4AF37;
        border: 1px solid #D4AF37;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #D4AF37;
        color: #1e1e1e;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(212, 175, 55, 0.4);
    }

    /* 計時器樣式 */
    .timer-display { 
        font-size: 2.2rem; 
        font-weight: 700; 
        color: #ff4b4b; 
        text-align: center; 
        background: rgba(255, 75, 75, 0.1);
        border: 1px solid #ff4b4b; 
        padding: 15px; 
        border-radius: 12px; 
        margin-bottom: 20px;
        box-shadow: 0 0 10px rgba(255, 75, 75, 0.2);
    }

    /* 標籤 Badge */
    .word-count-badge { 
        background: linear-gradient(45deg, #008080, #00a0a0); 
        color: white; 
        padding: 8px 18px; 
        border-radius: 50px; 
        font-size: 0.9rem; 
        font-weight: 500;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Tab 字體加大 */
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 🔐 密碼保護 ---
if "password_correct" not in st.session_state:
    st.markdown('<h1 class="main-header">🛡️ 教育領航者研究室</h1>', unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns([1,2,1])
    with col_p2:
        pwd = st.text_input("🔑 請輸入行政通關密碼：", type="password")
        if st.button("啟動系統"):
            if pwd == st.secrets["app_password"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼驗證失敗，請重新輸入。")
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
    "🏆 領導願景與品牌經營": "桃園「教育善好」願景、品牌學校形塑、ESG 永續經營、韌性領導。",
    "📘 課程發展與新課綱領航": "108 課綱深綱、雙語教育、SDGs 國際教育、跨域課程整合能力。",
    "📖 教學領航與數位轉型": "GenAI 教學應用倫理、數位公民素養、教師 PLC 運作實務、生生用平板 2.0。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制條例新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 4. 標題區 ---
st.markdown('<h1 class="main-header">🏫 教育領航者專題研究室</h1>', unsafe_allow_html=True)
st.markdown("*專為教育甄試設計的深度閱讀與模擬系統*")

# --- 5. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬"])

# --- Tab 1: 文章閱讀與轉化 ---
with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(4)
    links = [("🏛️ 教育部新聞", "https://www.edu.tw/News.aspx?n=9E7AC85F1954DDA8&sms=169B8E91BB75571F"),
             ("🏫 桃園教育局", "https://www.tyc.edu.tw/"),
             ("📖 國家教育研究院", "https://www.naer.edu.tw/"),
             ("🌟 臺灣教育評論", "http://www.ater.org.tw/commentmonth.html")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)

    st.markdown("---")
    news_clip = st.text_area("🔍 請貼上欲分析的教育新聞或政策文本：", height=200, placeholder="將文字貼於此處...")
    
    if st.button("🎯 開始深度考點轉化"):
        if news_clip and model:
            with st.spinner("正在以閱卷教授視角解析文本..."):
                reading_prompt = f"""
                你現在是「教育政策高級分析師」。請針對這段新聞，提供一份專門為「校長甄試考生」準備的深層導讀報告。
                【新聞內容】：{news_clip}
                ---
                1. 📌 **轉化專題標題**：(具備申論題氣勢的 15 字以內標題)
                2. 🔍 **核心要義**：(用兩句話總結關鍵政策或教育脈絡)
                3. 💡 **校長經營視角**：(列出 3 個經營關鍵點)
                4. 🔗 **政策對接**：(對接到桃園「教育善好」、SDGs、或 112-114 教育趨勢？)
                5. ❓ **潛在考點命題**：(模擬一個 25 分的申論題大方向)
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
                st.success("✅ 系統已自動鎖定主題，可至「策略筆記」生成矩陣。")

# --- Tab 2: 專題戰略筆記 ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    note_t = st.text_input("當前鎖定專題：", st.session_state.get('pending_note_topic', "數位學習精進方案 2.0"))
    
    if st.button("📖 生成行政戰略架構"):
        if model:
            with st.spinner("煉製核心學理與行動矩陣中..."):
                p = f"""
                你現在是專業教育行政導師。請針對專題『{note_t}』，提供「去頭去尾、直擊精華」的實務戰略。
                嚴禁任何問候或贅述。

                【輸出內容結構】：
                ### 🎯 戰略核心 (Why) — 理念與面向
                1. **主題的核心定義**：
                   - **學理定義**：說明本主題在教育學術上的定義。
                   - **核心價值論述**：提供具備行政厚度的一段話說明本案推動的核心價值。
                2. **主題核心面向**：
                   - 依據相關理論說明其推動之核心面向與內涵。

                ### 🚀 行動矩陣 (Action Matrix)
                請整合以下內容輸出表格：
                - **Who**：具體對應的利害關係人分工。
                - **What**：核心達成目標。
                - **How**：最具體的執行策略行動點（請列出 3-4 個關鍵作法）。
                - **桃園政策連結**：精確對接桃園市「教育善好」政策（包含具體計畫名稱）。
                - **關鍵績效指標 (KPI)**：提供 3 個可觀察、量化的具體績效指標。
                """
                st.session_state.last_note = model.generate_content(p).text
                
    if 'last_note' in st.session_state:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(st.session_state.last_note)
        if st.button("🗑️ 清除內容"):
            del st.session_state.last_note
            st.rerun()

# --- Tab 3: 限時實戰模擬 ---
with tab3:
    col_l, col_r = st.columns([1, 1.2], gap="large")
    with col_l:
        st.subheader("📍 模擬考題視窗")
        timer_placeholder = st.empty()
        
        if st.button("⏱️ 啟動 37 分鐘限時模擬"):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True
        
        if st.session_state.get("timer_running", False):
            rem = max(0, 37 * 60 - int(time.time() - st.session_state.start_time))
            mins, secs = divmod(rem, 60)
            timer_placeholder.markdown(f'<div class="timer-display">⏳ 剩餘時間 {mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
        
        sel_choice = st.selectbox("選擇預設命題向度：", list(THEME_POOL.keys()))
        manual_theme = st.text_input("🖋️ 自訂命題主題（選填）：", placeholder="若不填則依上方選取向度命題")
        
        if st.button("🚀 生成申論試題"):
            if model:
                with st.spinner("閱卷委員命題中..."):
                    target_topic = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                    q_prompt = f"""
                    請參考「校長甄試筆試（第29期風格）」命製一題 25 分的申論題。
                    主題為：『{target_topic}』。
                    
                    【⚠️ 重要指令】：直接開始輸出試題內容，嚴禁包含任何開場白。
                    
                    【命題格式規範】：
                    1. 以簡練專業的語言描述一個具體的校園行政困境、政策執行挑戰或教學現況（約 150 字）。
                    2. 試題需包含：核心價值、行政作為、推動策略三大部分。
                    """
                    q = model.generate_content(q_prompt).text
                    st.session_state.current_q = q
        
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "試題將顯示於此...")}</div>', unsafe_allow_html=True)

    with col_r:
        st.subheader("🖋️ 擬答作答區")
        ans_input = st.text_area("請在此輸入擬答架構或全文...", height=430, key="ans_box", placeholder="建議以：一、核心理念；二、執行策略；三、預期成效為結構...")
        st.markdown(f'<div style="text-align:right"><span class="word-count-badge">📝 當前字數：{len(ans_input)}</span></div>', unsafe_allow_html=True)
        
        if st.button("⚖️ 提交召集人閱卷評分"):
            if model and ans_input:
                with st.spinner("評審委員會評分中..."):
                    grading_prompt = f"""
                    你現在是「國中校長甄試閱卷召集人」。請針對考擬答進行深度評分。
                    
                    【題目】：{st.session_state.current_q}
                    【考生擬答】：{ans_input}
                    ---
                    請依下列格式回覆：
                    ### 🎓 校長甄試教授評分報告
                    - 問題洞察與核心價值：__/6
                    - 系統領導與橫向連結：__/7
                    - 實務執行與政策轉化：__/6
                    - 結構邏輯與行政素養：__/6
                    **【總分評定：__/25】**

                    ### 🖋️ 綜合評語與導師指引
                    ### ⚠️ 行政盲點診斷
                    ### 💎 格局提升金句
                    """
                    fb = model.generate_content(grading_prompt).text
                    st.markdown("---")
                    st.markdown(fb)
