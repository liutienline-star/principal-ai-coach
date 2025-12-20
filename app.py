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

# --- 3. 向度池 (融入 114 年核心重點) ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園「教育善好」願景、品牌學校形塑、ESG 永續經營、韌性領導。",
    "📘 課程發展與新課綱領航": "108 課綱深耕、雙語教育、SDGs 國際教育、跨域課程整合能力。",
    "📖 教學領航與數位轉型": "GenAI 教學應用倫理、數位公民素養、教師 PLC 運作、生生用平板 2.0。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制條例新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理韌性、正向管教、中輟預防。"
}

# --- 4. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📰 1. 情報轉化", "📚 2. 專題筆記", "✍️ 3. 模擬練習"])

with tab1:
    st.header("📰 情報獲取與轉化")
    st.markdown("##### 📍 校長必讀資訊來源")
    c = st.columns(4)
    links = [("🏛️ 教育部", "https://www.edu.tw/News.aspx?n=9E7AC85F1954DDA8&sms=169B8E91BB75571F"),
             ("🏫 桃園教育局", "https://www.tyc.edu.tw/"),
             ("📖 國教院", "https://www.naer.edu.tw//"),
             ("🌟 教育評論", "http://www.ater.org.tw/commentmonth.html")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)

   st.markdown("---")
    news_clip = st.text_area("在此貼上新聞內容，AI 將為您轉化為練習專題：", height=150, placeholder="例如：貼上關於桃園教育善好或 AI 輔助教學的新聞內容...")
    
    if st.button("🎯 重點摘錄與導讀"):
        if news_clip and model:
            with st.spinner("正在進行專業教育分析與導讀..."):
                # 建立多層次的導讀提示詞
                reading_prompt = f"""
                你現在是「教育政策高級分析師」。請針對這段新聞，提供一份專門為「校長甄試考生」準備的深層導讀報告。
                
                【新聞內容】：{news_clip}
                
                ---
                請按以下結構輸出（使用 Markdown 格式）：
                1. 📌 **轉化專題標題**：(請給出一個具備申論題氣勢的 15 字以內標題)
                2. 🔍 **核心要義**：(用兩句話總結新聞中最關鍵的政策或教育脈絡)
                3. 💡 **校長經營視角**：(從校長領導角度出發，列出 3 個本新聞對應的「經營關鍵點」)
                4. 🔗 **政策對接**：(本新聞如何對接到桃園「教育善好」、SDGs、或 112-114 教育趨勢？)
                5. ❓ **潛在考點命題**：(根據此新聞，模擬一個 25 分的申論題大方向)
                """
                
                response = model.generate_content(reading_prompt)
                full_analysis = response.text
                
                # 提取標題用於 session_state (為了之後的筆記生成)
                # 假設第一行是標題，簡單處理
                title_line = full_analysis.split('\n')[0].replace('1. 📌 **轉化專題標題**：', '').strip()
                st.session_state.pending_note_topic = title_line
                
                # 在介面上顯示精美的導讀結果
                st.info(f"### 📰 教育趨勢導讀報告")
                st.markdown(full_analysis)
                st.success("✅ 已自動鎖定專題標題，您可切換至「專題筆記」分頁生成完整策略。")

with tab2:
    st.header("📚 專題實務筆記")
    note_t = st.text_input("專題名稱", st.session_state.get('pending_note_topic', "數位學習精進方案"))
    if st.button("📖 生成局長視角策略"):
        if model:
            with st.spinner("策略生成中..."):
                p = f"你現在是桃園教育局長。針對專題『{note_t}』提供 Who, What, How, Why 策略。必須包含『教育善好』政策連結與具體績效指標。"
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
        if st.button("🚀 生成 114 年趨勢試題"):
            if model:
                with st.spinner("教授命題中..."):
                    q_prompt = f"請針對『{THEME_POOL[sel_choice]}』出一題25分申論題。要求：情境化、複合型問題，需測驗考生的決策力與格局。"
                    q = model.generate_content(q_prompt).text
                    st.session_state.current_q = q
                    st.session_state.current_theme = sel_choice
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請生成試題")}</div>', unsafe_allow_html=True)

    with col_r:
        st.subheader("✍️ 答案卷")
        ans_input = st.text_area("在此輸入您的擬答...", height=350, key="ans_box")
        st.markdown(f'<span class="word-count-badge">📝 字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        
        if st.button("⚖️ 提交教授評審團"):
            if model and ans_input:
                with st.spinner("資深教授與評閱委員審查中..."):
                    grading_prompt = f"""
                    你現在是「國立教育大學教育行政教授」兼「校長甄試閱卷召集人」。
                    請用極度嚴謹且具鑑別度的視角評分。

                    【評分權重】：
                    1. 系統領導格局 (20%)：是校長視角還是工頭視角？
                    2. 理論與政策轉譯 (30%)：是否精確對接桃園「教育善好」、SEL、GenAI 等 112-114 趨勢？
                    3. 法理嚴謹度 (30%)：程序是否合法？邏輯是否嚴密？
                    4. 前瞻洞察力 (20%)：有無點、線、面的佈局與教育哲學厚度？

                    【題目】：{st.session_state.current_q}
                    【考生擬答】：{ans_input}

                    ---
                    請回覆以下結構：
                    ### 🎓 教授評審委員會評分報告
                    - **系統領導格局**：/5
                    - **政策與理論轉譯**：/7.5
                    - **法理嚴謹度與邏輯**：/7.5
                    - **前瞻性與洞察力**：/5
                    **【總分評定： /25】** (註：18分以上具競爭力，21分以上為榜首潛力)

                    ### 🖋️ 委員會導師點評 (請直指本答案是「行政慣性」還是「專業領導」)
                    ### ⚠️ 致命傷提醒 (若內容無意義或亂打，請給予極低分並嚴厲指正)
                    ### 💎 優化金句 (提供一個能讓答案瞬間提升格局的專業術語)
                    """
                    fb = model.generate_content(grading_prompt).text
                    st.session_state.feedback = fb
                    st.markdown(f"{fb}")
