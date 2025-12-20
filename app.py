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

# --- 3. 向度池 ---
THEME_POOL = {
    "🏆 領導願景與 brand 經營": "桃園「教育善好」願景、品牌學校形塑、ESG 永續經營、韌性領導。",
    "📘 課程發展與新課綱領航": "108 課綱深耕、雙語教育、SDGs 國際教育、跨域課程整合能力。",
    "📖 教學領航與數位轉型": "GenAI 教學應用倫理、數位公民素養、教師 PLC 運作實務、生生用平板 2.0。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制條例新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 4. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📰 1. 文章閱讀區", "📚 2. 專題筆記區", "✍️ 3. 模擬練習區"])

# --- Tab 1: 文章閱讀與轉化 ---
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
    news_clip = st.text_area("在此貼上新聞內容，AI 將為您進行深度導讀與考點轉化：", height=150)
    
    if st.button("🎯 重點摘錄與導讀"):
        if news_clip and model:
            with st.spinner("正在進行專業教育分析與導讀..."):
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
                st.success("✅ 已自動鎖定專案標題。")

# --- Tab 2: 專題戰略筆記 ---
with tab2:
    st.header("📚 專題實務戰略矩陣")
    note_t = st.text_input("專題名稱", st.session_state.get('pending_note_topic', "數位學習精進方案"))
    
    if st.button("📖 生成精確策略矩陣"):
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
        st.markdown("---")
        st.markdown(st.session_state.last_note)
        if st.button("📋 清除內容重新輸入"):
            del st.session_state.last_note
            st.rerun()

# --- Tab 3: 限時實戰模擬 (優化命題類型以符合 29 期風格) ---
with tab3:
    st.header("⚖️ 實戰模擬")
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
        
        sel_choice = st.selectbox("選取預設向度", list(THEME_POOL.keys()))
        manual_theme = st.text_input("🖋️ 手動輸入自訂向度（若填寫則優先採用）：", placeholder="例如：校園性別平等、永續校園發展...")
        
        if st.button("🚀 生成考題"):
            if model:
                with st.spinner("教授命題中..."):
                    target_topic = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                    # --- 修正出題 Prompt 以符合第 29 期風格 ---
                    q_prompt = f"""
                    請參考「校長甄試筆試（第29期風格）」命製一題 25 分的申論題。
                    主題為：『{target_topic}』。
                    
                    【命題格式規範】：
                    1.以簡練專業的語言描述一個具體的校園行政困境、政策執行挑戰或教學現況，其中考題包含問題核心內涵、政策分析或理念價值、具體的行政領導作為、推動策略或解決方案(總字數約150字）。
                    ２.語言風格：嚴謹且具備校長治理層級的厚度。
                    """
                    q = model.generate_content(q_prompt).text
                    st.session_state.current_q = q
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請生成試題")}</div>', unsafe_allow_html=True)

    with col_r:
        st.subheader("✍️ 答案卷")
        ans_input = st.text_area("在此輸入您的擬答...", height=350, key="ans_box")
        st.markdown(f'<span class="word-count-badge">📝 字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        
        if st.button("⚖️ 提交教授評審團"):
            if model and ans_input:
                with st.spinner("召集人統整評分中..."):
                    grading_prompt = f"""
                    你現在是「國中校長甄試閱卷召集人」，負責統整多位委員的評分意見。
                    請以「真實閱卷現場的判斷邏輯」審視下列考生擬答，而非以平均理性方式給分。

                    ---
                    【閱卷第一關：快篩判斷（不計分，但將影響總評）】
                    A. 是否明確回應題目核心，未出現偏題或空轉？
                    B. 是否站在「校長決策與治理層級」，而非單一處室或教師視視角？
                    C. 是否具備基本教育政策語言與行政專業表述？

                    ---
                    【正式評分項目（總分 25 分）】
                    1. **核心理念與學理內涵（6 分）**：掌握議題正確學理、轉化為具厚度的論述。
                    2. **校長層級的系統領導與治理視角（6 分）**：跨處室整合、制度建構、資源配置與衝突決策角色。
                    3. **行動矩陣的實務可行性（7 分）**：Who/What/How 具體且可執行、呈現領導節奏與策略。
                    4. **政策連結、績效指標與前瞻洞察（6 分）**：對接桃園「教育善好」、KPI 具體可觀察、具備風險意識。

                    【題目】：{st.session_state.current_q}
                    【考生擬答】：{ans_input}

                    ---
                    【請依下列格式回覆】
                    ### 🎓 校長甄試教授評審委員會評分報告
                    - 核心理念與學理內涵：__/6
                    - 校長層級的系統領導與治理視角：__/6
                    - 行動矩陣的實務可行性：__/7
                    - 政策連結、績效指標與前瞻洞察：__/6
                    **【總分評定：__/25】**

                    ### 🖋️ 委員會導師整體評語
                    請明確指出本答案整體較接近：「行政慣性型回應」或「專業校長型論述」，並說明理由。

                    ### ⚠️ 致命傷診斷（請具體指出）
                    (檢查：名詞堆疊缺乏邏輯、缺乏資源取捨、未呈現校長判斷角色、缺乏治理敘事)

                    ### 💎 格局升級建議
                    請提供一句「可直接補進原答案、能明顯拉高校長高度」的專業論述或關鍵句。
                    """
                    fb = model.generate_content(grading_prompt).text
                    st.session_state.feedback = fb
                    st.markdown(f"{fb}")
