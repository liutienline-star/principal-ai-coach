import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# 1. 頁面基本設定
st.set_page_config(page_title="體育課程研究室 - 最終定稿版", layout="wide", page_icon="🏫")

# --- 🎨 核心 CSS：最終視覺優化 (香檳杏色調、低飽和度、極簡舒適) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
    
    /* 整體背景與基礎字體 */
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
    .stApp { background-color: #1e2128; color: #cbd5e0; }

    /* 漸層標題：降低對比度的杏金色 */
    .main-header {
        background: linear-gradient(135deg, #d4c19c 0%, #a88e5a 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 700; font-size: 2.1rem; margin-bottom: 1.2rem; letter-spacing: 1.2px;
    }

    /* 試題與作答視窗：固定高度防止跑版 */
    .scroll-box { 
        height: 500px; overflow-y: auto; border: 1px solid rgba(212, 193, 156, 0.15); 
        padding: 28px; border-radius: 16px; background: #282c37; color: #e2e8f0; 
        line-height: 1.8; font-size: 1.05rem; box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        margin-bottom: 25px;
    }

    /* 側邊提示框 */
    .guide-box {
        background: rgba(212, 193, 156, 0.04); border: 1px dashed rgba(212, 193, 156, 0.3);
        padding: 16px; border-radius: 12px; margin-top: 10px; font-size: 0.95rem; color: #d4c19c;
    }

    /* 作答區字體與高度同步 */
    div[data-baseweb="textarea"] textarea {
        color: #f1f5f9 !important; font-size: 1.05rem !important; line-height: 1.8 !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 500px !important; background-color: #282c37 !important;
        border-radius: 16px !important; border: 1px solid rgba(212, 193, 156, 0.15) !important;
    }

    /* 標籤文字 */
    .tiny-label { font-size: 0.85rem !important; color: #8e99a7; margin-bottom: 6px; font-weight: 500; }
    
    /* 按鈕樣式：優雅降飽和 */
    .stButton>button { 
        border-radius: 8px; background-color: #2d323e; color: #d4c19c; 
        border: 1px solid rgba(212, 193, 156, 0.2); transition: 0.2s;
    }
    .stButton>button:hover { background-color: #d4c19c; color: #1a1c23; border-color: #d4c19c; }

    /* 計時器與標章 */
    .timer-mini { 
        font-size: 1.2rem; font-weight: 600; color: #f5a9a9; 
        background: rgba(245, 169, 169, 0.05); padding: 8px 12px; border-radius: 10px; border: 1px solid rgba(245, 169, 169, 0.2);
    }
    .word-count-badge { background: rgba(74, 124, 124, 0.15); color: #81e6d9; padding: 6px 15px; border-radius: 50px; font-size: 0.8rem; }
    
    /* Tab 控制項 */
    .stTabs [aria-selected="true"] { color: #d4c19c !important; border-bottom-color: #d4c19c !important; }
    </style>
    """, unsafe_allow_html=True)

# --- ☁️ Google Sheets 核心連線 (穩定版) ---
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
    col_p2 = st.columns([1,2,1])[1]
    with col_p2:
        pwd = st.text_input("🔑 請輸入行政通關密碼：", type="password")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("驗證失敗。")
    st.stop()

# --- 2. 核心 AI 初始化 ---
@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        return genai.GenerativeModel("gemini-1.5-flash")
    except: return None

model = init_ai()

# --- 3. 向度池 (最終優化版：桃園教育願景 & 廣域理論) ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園教育願景、品牌學校、ESG、校長領導學術理論(廣納各種領導模式)。",
    "📘 課程發展與課綱領航": "108課綱深綱、雙語與SDGs、跨域課程整合、課程領導與發展理論。",
    "📖 教學領航與數位轉型": "GenAI應用、數位公民素養、PLC專業學習社群、數位學習領導理論。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌性平新制、親師衝突管理、法治領導與組織正義。",
    "❤️ SEL 與學生輔導": "社會情緒學習(SEL)、心理健康、正向管教、社會資本與關懷倫理。"
}

# --- 4. 頂部標題與功能分頁 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

with tab1:
    st.markdown("### 📍 權威資訊與趨勢轉化")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)
    news_clip = st.text_area("🔍 貼上教育新聞文本：", height=150, placeholder="將文字貼於此處以進行考點轉化...", key="news_in")
    if st.button("🎯 深度轉化命題報告"):
        if news_clip and model:
            with st.spinner("分析中..."):
                res = model.generate_content(f"請以教育行政分析師視角解析此文本，列出核心要義、校長經營對策與潛在考點：\n{news_clip}")
                st.info(res.text)

with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導")
    if st.button("📖 生成行政戰略架構"):
        if model:
            with st.spinner("煉製中..."):
                res = model.generate_content(f"針對專題『{note_t}』，提供學理定義、核心面向、行動矩陣(Who, What, How)與KPI。")
                st.markdown(res.text)

# --- Tab 3: 實戰模擬 (29 期風格精煉版) ---
with tab3:
    c_timer_btn, c_timer_val, c_select, c_input, c_gen = st.columns([0.8, 1, 1.5, 2, 0.8])
    with c_timer_val:
        if st.session_state.get("timer_running", False):
            rem = max(0, 37 * 60 - int(time.time() - st.session_state.start_time))
            st.markdown(f'<div class="timer-mini">⏳ {rem//60:02d}:{rem%60:02d}</div>', unsafe_allow_html=True)
        else: st.markdown('<div class="timer-mini" style="color:#666;">⏳ 37:00</div>', unsafe_allow_html=True)
    with c_select:
        sel_choice = st.selectbox("命題向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    with c_gen:
        if st.button("生成試題", use_container_width=True):
            if model:
                with st.spinner("擬仿真題命題中..."):
                    q_prompt = f"""
                    你現在是「校長甄試命題委員」。請效法「第 29 期試題」風格命題。
                    主題：『{THEME_POOL[sel_choice]}』
                    
                    要求：
                    1. 情境精煉：控制在 100-150 字，直接切入核心困境。
                    2. 學理融合：隨機挑選 1 個相關的教育行政學理(不可侷限於常見三項理論)融入命題。
                    3. 任務導向：明確要求考生以校長身分提出規劃。
                    4. 嚴禁冗贅文字，直接輸出題目主體。
                    """
                    st.session_state.current_q = model.generate_content(q_prompt).text
                    st.session_state.suggested_structure = None
                    st.session_state.start_time = time.time()
                    st.session_state.timer_running = True

    st.markdown("<br>", unsafe_allow_html=True)
    col_q, col_a = st.columns([1, 1.8], gap="large")
    with col_q:
        st.markdown('<p class="tiny-label">📍 模擬試題 (29期精煉風格)</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "點擊上方「生成試題」按鈕開始模擬練習...")}</div>', unsafe_allow_html=True)
        if st.session_state.get("current_q") and st.button("💡 獲取架構建議", use_container_width=True):
            st.session_state.suggested_structure = model.generate_content(f"針對題目：{st.session_state.current_q}\n提供三段式答題建議與學理運用提示。").text
        if st.session_state.get("suggested_structure"):
            st.markdown(f'<div class="guide-box">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    with col_a:
        st.markdown('<p class="tiny-label">🖋️ 擬答作答區</p>', unsafe_allow_html=True)
        ans_input = st.text_area("作答區", label_visibility="collapsed", key="ans_box_final", height=500)
        c_cnt, c_sub = st.columns([1, 1])
        with c_cnt: st.markdown(f'<span class="word-count-badge">📝 字數計數：{len(ans_input)}</span>', unsafe_allow_html=True)
        with c_sub:
            if st.button("⚖️ 提交召集人評分", use_container_width=True):
                if model and ans_input:
                    with st.spinner("閱卷中..."):
                        res = model.generate_content(f"題目：{st.session_state.current_q}\n擬答：{ans_input}\n給予評分(/25)、學理落點分析與深度評語。").text
                        st.session_state.feedback = res
                        score_match = re.search(r"(\d+)/25", res)
                        log_to_google_sheets(sel_choice, score_match.group(1) if score_match else "N/A", ans_input, res)

    if 'feedback' in st.session_state:
        st.markdown(f"<div style='margin-top:25px; padding:25px; background:#2d323e; border-radius:15px; border-left:6px solid #d4c19c; color:#e2e8f0; line-height:1.7;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

with tab4:
    st.markdown("### 📊 歷程紀錄與成長曲線")
    df = get_records()
    if not df.empty:
        df['score_num'] = pd.to_numeric(df['實戰分數'], errors='coerce')
        st.metric("平均得分", f"{df['score_num'].mean():.1f} / 25")
        st.line_chart(df.set_index('紀錄時間')['score_num'])
        st.dataframe(df[['紀錄時間', '題目主題', '實戰分數', '我的作答', 'AI 評語摘要']], use_container_width=True)
    else: st.info("尚無練習紀錄。")
