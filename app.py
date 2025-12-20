import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time

# 1. 頁面基本設定
st.set_page_config(page_title="閱讀專區", layout="wide", page_icon="🏫")

# --- 🎨 核心 CSS 柔和化美編 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;700&display=swap');
    
    /* 全域設定 */
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
    
    /* 背景改為深石板藍，比純黑更耐看 */
    .stApp { background-color: #1a1c23; color: #ced4da; }
    
    /* 核心試題視窗 (左側題目區) - 邊框改為柔和的莫蘭迪金 */
    .scroll-box { 
        height: 520px; 
        overflow-y: auto; 
        border: 1px solid rgba(193, 174, 148, 0.4); 
        padding: 28px; 
        border-radius: 16px; 
        background: #232731;
        color: #e9ecef; 
        line-height: 1.8;
        font-size: 1.1rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }

    /* 強制調整 Streamlit text_area 高度 */
    div[data-baseweb="textarea"] > div {
        height: 520px !important;
        background-color: #232731 !important;
        border-radius: 16px !important;
        border: 1px solid rgba(193, 174, 148, 0.2) !important;
        color: #e9ecef !important;
    }

    /* 頂部功能列文字 */
    .tiny-label {
        font-size: 0.88rem !important;
        color: #c1ae94; /* 沉穩金 */
        margin-bottom: 4px;
        font-weight: 500;
        letter-spacing: 0.5px;
    }

    /* 標題改為絲綢漸層 */
    .main-header {
        background: linear-gradient(135deg, #e9d5a1 0%, #a88e5a 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 700; font-size: 2.4rem; margin-bottom: 0.8rem;
    }

    /* 計時器改為溫潤的珊瑚色 */
    .timer-mini { 
        font-size: 1.4rem; font-weight: 700; color: #ee8e8e; 
        text-align: center; background: rgba(238, 142, 142, 0.1);
        padding: 6px; border-radius: 10px; border: 1px solid rgba(238, 142, 142, 0.3);
    }

    /* 標籤 Badge 顏色優化 */
    .word-count-badge { 
        background: linear-gradient(45deg, #4a7c7c, #639a9a); 
        color: white; padding: 6px 18px; 
        border-radius: 50px; font-size: 0.85rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    
    /* 按鈕更顯質感 */
    .stButton>button {
        border-radius: 10px;
        height: 3.2em;
        background-color: #2d323e;
        color: #e9d5a1;
        border: 1px solid rgba(233, 213, 161, 0.4);
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #a88e5a;
        color: #1a1c23;
        border-color: #a88e5a;
        box-shadow: 0 5px 15px rgba(168, 142, 90, 0.3);
    }

    /* Tab 導覽列優化 */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { color: #888; font-size: 1.05rem; }
    .stTabs [aria-selected="true"] { color: #e9d5a1 !important; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 🔐 密碼保護 ---
if "password_correct" not in st.session_state:
    st.markdown('<h1 class="main-header">🛡️ 學術研究室</h1>', unsafe_allow_html=True)
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

# --- 4. 頂部標題 ---
st.markdown('<h1 class="main-header">🏫 教育領航者專題研究室</h1>', unsafe_allow_html=True)
st.markdown("<p style='color:#8892b0; margin-top:-10px;'>專為教育甄試設計的深度閱讀與模擬系統</p>", unsafe_allow_html=True)

# --- 5. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬"])

# --- Tab 1: 趨勢轉化 ---
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
    news_clip = st.text_area("🔍 請貼上欲分析的教育新聞或政策文本：", height=180, placeholder="將文字貼於此處...", key="news_in")
    
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

# --- Tab 2: 戰略矩陣 ---
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

# --- Tab 3: 實戰模擬 ---
with tab3:
    # --- A. 上方功能控制列 ---
    c_timer_btn, c_timer_val, c_select, c_input, c_gen = st.columns([0.8, 1, 1.5, 2, 0.8])
    
    with c_timer_btn:
        st.markdown('<p class="tiny-label">⏱️ 計時器</p>', unsafe_allow_html=True)
        if st.button("啟動模擬", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True
    
    with c_timer_val:
        st.markdown('<p class="tiny-label">⏳ 剩餘時間</p>', unsafe_allow_html=True)
        if st.session_state.get("timer_running", False):
            rem = max(0, 37 * 60 - int(time.time() - st.session_state.start_time))
            mins, secs = divmod(rem, 60)
            st.markdown(f'<div class="timer-mini">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="timer-mini" style="color:#666; border-color:#444;">37:00</div>', unsafe_allow_html=True)

    with c_select:
        st.markdown('<p class="tiny-label">🎯 命題向度</p>', unsafe_allow_html=True)
        sel_choice = st.selectbox("向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    
    with c_input:
        st.markdown('<p class="tiny-label">🖋️ 自訂主題 (可選)</p>', unsafe_allow_html=True)
        manual_theme = st.text_input("自訂主題", placeholder="若不填則依向度命題...", label_visibility="collapsed", key="custom_t")
        
    with c_gen:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        if st.button("生成試題", use_container_width=True):
            if model:
                with st.spinner("命題中..."):
                    target_topic = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                    q_prompt = f"""
                    請參考「校長甄試筆試（第29期風格）」命製一題 25 分的申論題。
                    主題為：『{target_topic}』。
                    【⚠️ 重要指令】：直接開始輸出試題內容，嚴禁包含任何開場白。
                    【命題格式規範】：
                    1. 以簡練專業的語言描述一個具體的校園行政困境、政策執行挑戰或教學現況，其中考題包含問題核心內涵、政策分析或理念價值、具體的行政領導作為、推動策略或解決方案(總字數約150字）。
                    2. 語言風格：嚴謹且具備校長治理層級的厚度。
                    """
                    st.session_state.current_q = model.generate_content(q_prompt).text

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # --- B. 平行對稱作戰區 ---
    col_q, col_a = st.columns([1, 1.8], gap="medium")
    
    with col_q:
        st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "試題將顯示於此...")}</div>', unsafe_allow_html=True)

    with col_a:
        st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (與左側高度同步)</p>', unsafe_allow_html=True)
        ans_input = st.text_area("作答區", label_visibility="collapsed", key="ans_box_final", placeholder="請依照：一、核心理念；二、執行策略；三、預期成效之架構書寫...")
        
        f_count, f_submit = st.columns([1, 1])
        with f_count:
            st.markdown(f'<span class="word-count-badge">📝 當前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        with f_submit:
            if st.button("⚖️ 提交召集人閱卷評分", use_container_width=True):
                if model and ans_input:
                    with st.spinner("評審委員會評分中..."):
                        grading_prompt = f"""
                        你現在是「國中校長甄試閱卷召集人」。請針對考擬答進行深度評分。
                        【題目】：{st.session_state.get('current_q')}
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
                        st.session_state.feedback = model.generate_content(grading_prompt).text

    # --- C. 評分顯示區 ---
    if 'feedback' in st.session_state:
        st.markdown("<div style='margin-top:30px; padding:20px; background:#2d323e; border-radius:16px; border-left:5px solid #a88e5a;'>", unsafe_allow_html=True)
        st.markdown(st.session_state.feedback)
        st.markdown("</div>", unsafe_allow_html=True)
        if st.button("🗑️ 清除評分結果"):
            del st.session_state.feedback
            st.rerun()
