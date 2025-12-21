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

# --- 🎨 CSS 視覺優化 (北歐護眼配色 / 寬版垂直流配置) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    /* 全局字體設定 */
    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif; 
        font-weight: 300; 
        letter-spacing: 0.02em;
    }
    
    .stApp { background-color: #1a1d24; color: #eceff4; }

    /* 主標題 */
    .main-header {
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500;
        font-size: 1.8rem;
        margin-bottom: 1.0rem;
        letter-spacing: 0.05rem;
    }

    /* 試題區塊 */
    .scroll-box { 
        height: 300px !important; 
        overflow-y: auto !important; 
        border: 1px solid #3b4252; 
        padding: 25px; 
        border-radius: 12px; 
        background: #242933; 
        color: #e5e9f0; 
        line-height: 1.85; 
        font-size: 1.0rem; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }

    /* 作答區優化 */
    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; 
        font-size: 1.0rem !important; 
        line-height: 1.8 !important;
        font-weight: 300 !important;
    }
    /* 強制設定作答區高度為 650px */
    div[data-baseweb="textarea"] > div {
        height: 650px !important; 
        background-color: #242933 !important;
        border-radius: 12px !important; 
        border: 1px solid #3b4252 !important;
    }

    /* 寬版建議區塊 */
    .guide-box-wide {
        background: rgba(129, 161, 193, 0.05); 
        border-left: 3px solid #5e81ac; 
        padding: 25px; 
        border-radius: 8px; 
        margin-top: 20px; 
        font-size: 1.0rem; 
        color: #d8dee9; 
        line-height: 1.9;
    }
    
    .guide-box-wide h1, .guide-box-wide h2, .guide-box-wide h3 {
        font-size: 1.15rem !important; 
        font-weight: 500 !important;   
        margin-top: 15px !important;
        margin-bottom: 10px !important;
        color: #88c0d0 !important;     
        border: none !important;       
    }
    .guide-box-wide strong {
        color: #81a1c1; 
        font-weight: 500;
    }

    /* 警示區塊 (用於法規提醒) */
    .alert-box {
        background: rgba(191, 97, 106, 0.1);
        border: 1px solid #bf616a;
        color: #e5e9f0;
        padding: 15px;
        border-radius: 8px;
        font-size: 0.9rem;
        margin-bottom: 15px;
    }

    /* 標籤與按鈕 */
    .tiny-label { font-size: 0.8rem !important; color: #69788e; margin-bottom: 6px; font-weight: 400; }
    
    .stButton>button { 
        border-radius: 8px; 
        background-color: #2e3440; 
        color: #88c0d0; 
        border: 1px solid #434c5e;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { 
        background-color: #3b4252; 
        color: #eceff4; 
        border-color: #88c0d0; 
    }

    .timer-mini { font-size: 1.2rem; font-weight: 500; color: #bf616a; background: rgba(191, 97, 106, 0.1); padding: 6px 12px; border-radius: 6px; }
    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; border: 1px solid #434c5e; }
    </style>
    """, unsafe_allow_html=True)

# --- ☁️ Google Sheets 連線 ---
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
    col_p = st.columns([1,2,1])[1]
    with col_p:
        pwd = st.text_input("🔑 輸入行政通關密碼：", type="password")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼錯誤。")
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
    "🏆 領導願景與品牌經營": "桃園教育願景、品牌學校形塑、ESG永續經營、韌性領導。",
    "📘 課程發展與課綱領航": "108課綱深綱、雙語教育、SDGs國際教育、跨域課程整合。",
    "📖 教學領航與數位轉型": "GenAI教學倫理、數位公民素養、教師PLC運作、生生用平板。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 4. 介面佈局 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

# --- Tab 1: 趨勢閱讀 ---
with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), 
             ("🏫 教育局", "https://www.tyc.edu.tw/"), 
             ("📖 國教院", "https://www.naer.edu.tw/"), 
             ("🌟 教育評論", "http://www.ater.org.tw/"), 
             ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)
    
    st.markdown("---")
    news_clip = st.text_area("🔍 欲分析的教育新聞文本：", height=150, placeholder="將新聞文字貼於此處...", key="news_v11")
    if st.button("🎯 執行深度考點轉化"):
        if news_clip and model:
            with st.spinner("解析中..."):
                st.markdown(model.generate_content(f"請以教育行政視角分析考點：\n{news_clip}").text)

# --- Tab 2: 策略筆記 (✅ 升級：法規 Grounding 機制) ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    
    # 新增警示說明
    st.markdown("""
    <div class="alert-box">
    ⚠️ <strong>法規精準度提醒：</strong><br>
    涉及「校事會議」、「霸凌防制」等具時效性法規，AI 可能存有舊版資料落差。<br>
    建議在下方「參考文本」欄位貼上最新法規條文或 SOP，AI 將強制依據該文本生成筆記，確保精確度。
    </div>
    """, unsafe_allow_html=True)

    c_topic, c_ref = st.columns([1, 1.5], gap="large")
    
    with c_topic:
        st.markdown('<p class="tiny-label">📌 專題名稱</p>', unsafe_allow_html=True)
        note_t = st.text_input("專題名稱", placeholder="例如：新制校事會議運作流程", label_visibility="collapsed")
    
    with c_ref:
        st.markdown('<p class="tiny-label">⚖️ 法規/SOP 參考文本 (選填，強烈建議填寫)</p>', unsafe_allow_html=True)
        ref_text = st.text_area("參考文本", height=100, placeholder="在此貼上最新法規條文、公文內容或研習講義...", label_visibility="collapsed")

    if st.button("📖 生成行政戰略架構"):
        if model and note_t:
            with st.spinner("依據最新文本分析整理中..."):
                
                # 建構更嚴謹的 Prompt
                base_instruction = f"""
                請針對主題『{note_t}』，以教育行政專家的角度，撰寫一份結構完整的策略筆記。
                """
                
                # 判斷是否有使用者提供的 Ground Truth
                if ref_text.strip():
                    grounding_instruction = f"""
                    【重要指令】
                    使用者已提供以下「參考文本」作為黃金準則 (Ground Truth)：
                    ---
                    {ref_text}
                    ---
                    請**嚴格依據**上述參考文本的內容來撰寫（特別是程序、天數、法條名稱）。
                    若參考文本資訊不足，請標註「需參閱相關法規」，切勿自行編造不確定的數據。
                    """
                else:
                    grounding_instruction = """
                    【重要指令】
                    由於使用者未提供參考文本，若涉及具體法規（如校事會議、霸凌防制），請務必以「目前最新修訂法規」為準。
                    若不確定最新修訂細節，請在內容中加註「(建議再次查核最新教育局公文)」字樣。
                    """

                structure_instruction = """
                內容**必須嚴格包含**以下四個明確章節，請使用 Markdown 格式：
                1. **前言** (破題與背景)
                2. **定義與內涵** (依據參考文本的學理或法理基礎)
                3. **行動矩陣與KPI指標** (請務必使用 Markdown 表格呈現具體策略與衡量指標)
                4. **結語** (展望與總結)
                """
                
                final_prompt = base_instruction + grounding_instruction + structure_instruction
                st.markdown(model.generate_content(final_prompt).text)

# --- Tab 3: 實戰模擬 (垂直寬版流) ---
with tab3:
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
            st.markdown(f'<div class="timer-mini">{rem//60:02d}:{rem%60:02d}</div>', unsafe_allow_html=True)
        else: st.markdown('<div class="timer-mini" style="color:#666;">37:00</div>', unsafe_allow_html=True)
    with c_select:
        st.markdown('<p class="tiny-label">🎯 命題向度</p>', unsafe_allow_html=True)
        sel_choice = st.selectbox("向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    with c_input:
        st.markdown('<p class="tiny-label">🖋️ 自訂主題</p>', unsafe_allow_html=True)
        manual_theme = st.text_input("自訂主題", placeholder="若不填則依向度命題...", key="v11_custom", label_visibility="collapsed")
    with c_gen:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        if st.button("生成試題", use_container_width=True):
            if model:
                with st.spinner("擬真命題中..."):
                    target = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                    q_prompt = f"""
                    你現在是「第29期校長甄試命題委員」。請針對『{target}』設計一題實務申論題。
                    嚴格執行以下規格：
                    1. **情境精煉**：字數控制在 150-200 字，拒絕冗長。
                    2. **單一學理**：隨機隱含「一個」最適合的教育行政理論。
                    3. **結構**：情境描述 + 具體策略任務。
                    4. **輸出**：嚴禁開場白，直接輸出題目。
                    """
                    st.session_state.current_q = model.generate_content(q_prompt).text
                    st.session_state.suggested_structure = None

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 1. 題目顯示區 (全寬) ---
    st.markdown('<p class="tiny-label">📍 模擬試題視窗 (Full Width)</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "試題將顯示於此，請按上方生成按鈕...")}</div>', unsafe_allow_html=True)
    
    if st.session_state.get("current_q"):
        if st.button("💡 獲取黃金架構建議 (將顯示於下方)", use_container_width=True):
            with st.spinner("分析架構中..."):
                struct_prompt = f"針對此題：{st.session_state.current_q}，請提供「黃金三段式」答題架構建議，並特別指出可運用的理論。"
                st.session_state.suggested_structure = model.generate_content(struct_prompt).text
    
    if st.session_state.get("suggested_structure"):
         st.markdown(f'<div class="guide-box-wide">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # --- 2. 作答區 (全寬 + 加高) ---
    st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (Expanded)</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答", label_visibility="collapsed", key="v11_ans") 
    
    f_count, f_submit = st.columns([1, 1])
    with f_count: 
        st.markdown(f'<div style="margin-top:10px;"><span class="word-count-badge">📝 字數：{len(ans_input)}</span></div>', unsafe_allow_html=True)
    with f_submit:
        if st.button("⚖️ 提交閱卷評分", use_container_width=True):
            if model and ans_input:
                with st.spinner("評分中..."):
                    res = model.generate_content(f"題目：{st.session_state.current_q}\n擬答：{ans_input}\n給予評分(滿分25)與具體建議。").text
                    st.session_state.feedback = res
                    score_match = re.search(r"(\d+)/25", res)
                    log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_match.group(1) if score_match else "N/A", ans_input, res)

    # --- 3. 評分結果區 ---
    if 'feedback' in st.session_state:
        st.markdown(f"<div style='margin-top:20px; padding:20px; background:#242933; border-radius:8px; border-left:4px solid #88c0d0; line-height:1.8; color:#e5e9f0;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

# --- Tab 4: 歷程紀錄 ---
with tab4:
    st.markdown("### 📊 學習歷程分析")
    df = get_records()
    if not df.empty:
        df['score_num'] = pd.to_numeric(df['實戰分數'], errors='coerce')
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("總練習次數", len(df))
        with c2: st.metric("平均得分", f"{df['score_num'].mean():.1f}")
        with c3: st.metric("最高得分", f"{df['score_num'].max():.0f}")
        st.line_chart(df.set_index('紀錄時間')['score_num'])
        st.dataframe(df, use_container_width=True)
    else: st.info("尚無紀錄。")
