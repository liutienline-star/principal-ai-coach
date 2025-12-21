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

# --- 🎨 CSS 強制排版加固 (520px 高度鎖定 / 香檳金配色 / 寬版閱讀優化) ---
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
    .scroll-box { 
        height: 520px !important; overflow-y: auto !important; border: 1px solid rgba(212, 193, 156, 0.15); 
        padding: 30px; border-radius: 18px; background: #282c37; color: #e2e8f0; 
        line-height: 1.75; font-size: 1.05rem; box-shadow: 0 12px 30px rgba(0,0,0,0.15);
    }
    div[data-baseweb="textarea"] textarea {
        color: #f1f5f9 !important; font-size: 1.05rem !important; line-height: 1.7 !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 520px !important; background-color: #282c37 !important;
        border-radius: 18px !important; border: 1px solid rgba(212, 193, 156, 0.15) !important;
    }
    /* --- 優化後的寬版建議區塊 CSS --- */
    .guide-box-wide {
        background: rgba(212, 193, 156, 0.05); 
        border: 1px dashed rgba(212, 193, 156, 0.3);
        padding: 25px; 
        border-radius: 12px; 
        margin-top: 20px; 
        font-size: 1.05rem; /* 字體適中 */
        color: #d4c19c; 
        line-height: 1.8;
    }
    /* 強制縮小建議區塊內的標題大小，避免過大 */
    .guide-box-wide h1, .guide-box-wide h2, .guide-box-wide h3 {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
        color: #e2e8f0 !important;
        border-left: 4px solid #d4c19c;
        padding-left: 10px;
    }
    .tiny-label { font-size: 0.85rem !important; color: #8e99a7; margin-bottom: 8px; font-weight: 500; }
    .stButton>button { 
        border-radius: 10px; background-color: #2d323e; color: #d4c19c; 
        border: 1px solid rgba(212, 193, 156, 0.25);
    }
    .stButton>button:hover { background-color: #d4c19c; color: #1a1c23; border-color: #d4c19c; }
    .timer-mini { font-size: 1.3rem; font-weight: 600; color: #f5a9a9; background: rgba(245, 169, 169, 0.05); padding: 8px; border-radius: 10px; }
    .word-count-badge { background: rgba(74, 124, 124, 0.15); color: #81e6d9; padding: 6px 16px; border-radius: 50px; font-size: 0.8rem; }
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

# --- Tab 2: 策略筆記 ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導")
    if st.button("📖 生成行政戰略架構"):
        if model and note_t:
            with st.spinner("整理中..."):
                st.markdown(model.generate_content(f"針對『{note_t}』，提供行動矩陣與KPI指標。").text)

# --- Tab 3: 實戰模擬 (版面與結構優化版) ---
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
                with st.spinner("擬真命題中 (第29期風格)..."):
                    target = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                    q_prompt = f"""
                    你現在是「第29期校長甄試命題委員」。請針對『{target}』設計一題實務申論題。
                    嚴格執行以下規格：
                    1. **情境精煉**：字數控制在 120-150 字，拒絕冗長。
                    2. **單一學理**：隨機隱含「一個」最適合的教育行政理論。
                    3. **結構**：情境描述 + 具體策略任務。
                    4. **輸出**：嚴禁開場白，直接輸出題目。
                    """
                    st.session_state.current_q = model.generate_content(q_prompt).text
                    st.session_state.suggested_structure = None

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 左右欄位佈局
    col_q, col_a = st.columns([1, 1.8], gap="large")
    
    with col_q:
        st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "試題顯示於此...")}</div>', unsafe_allow_html=True)
        
        # 增加間距 (Spacer)
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        if st.session_state.get("current_q") and st.button("💡 獲取黃金架構建議 (顯示於下方)", use_container_width=True):
            with st.spinner("分析架構中..."):
                struct_prompt = f"針對此題：{st.session_state.current_q}，請提供「黃金三段式」答題架構建議，並特別指出可運用的理論。"
                st.session_state.suggested_structure = model.generate_content(struct_prompt).text

    with col_a:
        st.markdown('<p class="tiny-label">🖋️ 擬答作答區</p>', unsafe_allow_html=True)
        ans_input = st.text_area("作答", label_visibility="collapsed", key="v11_ans", height=500)
        f_count, f_submit = st.columns([1, 1])
        with f_count: st.markdown(f'<span class="word-count-badge">📝 字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        with f_submit:
            if st.button("⚖️ 提交閱卷評分", use_container_width=True):
                if model and ans_input:
                    with st.spinner("評分中..."):
                        res = model.generate_content(f"題目：{st.session_state.current_q}\n擬答：{ans_input}\n給予評分(滿分25)與具體建議。").text
                        st.session_state.feedback = res
                        score_match = re.search(r"(\d+)/25", res)
                        log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_match.group(1) if score_match else "N/A", ans_input, res)

    # --- 寬版架構建議區 (移出 col_q，改為獨立寬版) ---
    if st.session_state.get("suggested_structure"):
        st.markdown("---")
        st.markdown("### 💡 答題架構導航")
        st.markdown(f'<div class="guide-box-wide">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    # --- 評分結果區 ---
    if 'feedback' in st.session_state:
        st.markdown(f"<div style='margin-top:20px; padding:20px; background:#2d323e; border-radius:12px; border-left:5px solid #d4c19c;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

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
