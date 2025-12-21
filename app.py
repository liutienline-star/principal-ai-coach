import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# 1. 頁面基本設定 (啟動第一順位)
st.set_page_config(page_title="體育課程研究室 - 終極穩定版", layout="wide", page_icon="🏫")

# --- 🎨 核心 CSS：鎖定 520px 高度、確保不跑版 ---
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
    /* 左右視窗固定高度 520px */
    .scroll-box { 
        height: 520px !important; overflow-y: auto !important; border: 1px solid rgba(212, 193, 156, 0.15); 
        padding: 30px; border-radius: 18px; background: #282c37; color: #e2e8f0; 
        line-height: 1.8; font-size: 1.05rem; box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    div[data-baseweb="textarea"] textarea {
        color: #f1f5f9 !important; font-size: 1.05rem !important; line-height: 1.8 !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 520px !important; background-color: #282c37 !important;
        border-radius: 18px !important; border: 1px solid rgba(212, 193, 156, 0.15) !important;
    }
    .guide-box {
        background: rgba(212, 193, 156, 0.05); border: 1px dashed rgba(212, 193, 156, 0.3);
        padding: 18px; border-radius: 12px; margin-top: 10px; font-size: 0.95rem; color: #d4c19c;
    }
    .tiny-label { font-size: 0.85rem !important; color: #8e99a7; margin-bottom: 8px; font-weight: 500; }
    .stButton>button { 
        border-radius: 10px; background-color: #2d323e; color: #d4c19c; 
        border: 1px solid rgba(212, 193, 156, 0.2); transition: 0.2s;
    }
    .stButton>button:hover { background-color: #d4c19c !important; color: #1a1c23 !important; }
    .timer-mini { 
        font-size: 1.3rem; font-weight: 600; color: #f5a9a9; 
        background: rgba(245, 169, 169, 0.05); padding: 8px; border-radius: 10px; border: 1px solid rgba(245, 169, 169, 0.2);
    }
    .word-count-badge { background: rgba(74, 124, 124, 0.15); color: #81e6d9; padding: 6px 16px; border-radius: 50px; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- ☁️ Google Sheets 連線工具 ---
def get_gs_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    return gspread.authorize(creds)

def log_to_google_sheets(topic, score, user_answer, feedback):
    try:
        client = get_gs_client()
        sheet = client.open("Education_Exam_Records").sheet1
        row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), topic, score, user_answer, feedback[:250].replace('\n', ' ') + "...", ""]
        sheet.append_row(row)
    except: pass

def get_records():
    try:
        client = get_gs_client()
        sheet = client.open("Education_Exam_Records").sheet1
        return pd.DataFrame(sheet.get_all_records())
    except: return pd.DataFrame()

# --- 🔐 密碼保護 ---
if "password_correct" not in st.session_state:
    st.markdown('<h1 class="main-header">🛡️ 體育課程研究室</h1>', unsafe_allow_html=True)
    col_p2 = st.columns([1,2,1])[1]
    with col_p2:
        pwd = st.text_input("🔑 輸入行政密碼：", type="password")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼錯誤。")
    st.stop()

# --- 2. 核心 AI 初始化 (🛠️ 雙重模型偵測機制) ---
@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # 如果 v1beta 抽風，我們先獲取最新可用的模型名稱
        return genai.GenerativeModel("gemini-1.5-flash")
    except:
        return None

model = init_ai()

def safe_generate(prompt):
    """防護型生成函數，處理 404 報錯"""
    if not model: return "AI 尚未就緒"
    try:
        # 嘗試第一種路徑
        return model.generate_content(prompt).text
    except Exception as e:
        if "404" in str(e):
            try:
                # 嘗試帶 models/ 的絕對路徑
                alt_model = genai.GenerativeModel("models/gemini-1.5-flash")
                return alt_model.generate_content(prompt).text
            except:
                return f"API 節點暫時失聯，請稍後再試。錯誤代碼: {e}"
        return f"生成出錯: {e}"

# --- 3. 向度池 ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園「教育善好」願景、品牌學校形塑、ESG 永續經營、韌性領導。",
    "📘 課程發展與新課綱領航": "108 課綱深綱、雙語教育、SDGs 國際教育、跨域課程整合能力。",
    "📖 教學領航與數位轉型": "GenAI 教學應用倫理、數位公民素養、教師 PLC 運作實務、生生用平板 2.0。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制條例新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 4. 介面佈局 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

with tab1:
    news_clip = st.text_area("🔍 貼上新聞文本解析：", height=150, placeholder="分析考點...", key="tab1_news")
    if st.button("🎯 執行深度解析"):
        if news_clip:
            with st.spinner("解析中..."):
                st.info(safe_generate(f"分析考點：\n{news_clip}"))

with tab2:
    note_t = st.text_input("專題名稱：", placeholder="桃園數位領導", key="tab2_note")
    if st.button("📖 生成戰略矩陣"):
        if note_t:
            with st.spinner("煉製中..."):
                st.markdown(safe_generate(f"針對『{note_t}』提供行動矩陣與KPI。"))

# --- Tab 3: 實戰模擬 (絕對固定版面) ---
with tab3:
    c_timer_btn, c_timer_val, c_select, c_input, c_gen = st.columns([0.8, 1, 1.5, 2, 0.8])
    with c_timer_btn:
        if st.button("啟動計時", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True
    with c_timer_val:
        if st.session_state.get("timer_running", False):
            rem = max(0, 37 * 60 - int(time.time() - st.session_state.start_time))
            st.markdown(f'<div class="timer-mini">{rem//60:02d}:{rem%60:02d}</div>', unsafe_allow_html=True)
        else: st.markdown('<div class="timer-mini" style="color:#666;">37:00</div>', unsafe_allow_html=True)
    with c_select:
        sel_choice = st.selectbox("命題向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    with c_input:
        # 手動輸入框：絕對保留
        manual_theme = st.text_input("自訂主題", placeholder="若不填則依向度命題...", key="man_input_v6", label_visibility="collapsed")
    with c_gen:
        if st.button("生成試題", use_container_width=True):
            with st.spinner("出題中..."):
                target = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                q_prompt = f"請校長甄試命題委員效法第29期風格，針對『{target}』命一題申論題。直接輸出題目。"
                st.session_state.current_q = safe_generate(q_prompt)
                st.session_state.suggested_structure = None

    st.markdown("<br>", unsafe_allow_html=True)
    col_q, col_a = st.columns([1, 1.8], gap="large")
    with col_q:
        st.markdown('<p class="tiny-label">📍 模擬試題 (29期風)</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "試題顯示區")}</div>', unsafe_allow_html=True)
        if st.session_state.get("current_q") and st.button("💡 架構建議", use_container_width=True):
            st.session_state.suggested_structure = safe_generate(f"提供三段式架構：{st.session_state.current_q}")
        if st.session_state.get("suggested_structure"):
            st.markdown(f'<div class="guide-box">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)
    with col_a:
        st.markdown('<p class="tiny-label">🖋️ 擬答作答區</p>', unsafe_allow_html=True)
        ans_input = st.text_area("作答", label_visibility="collapsed", key="ans_box_v6", height=520)
        f1, f2 = st.columns([1, 1])
        with f1: st.markdown(f'<span class="word-count-badge">📝 字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        with f2:
            if st.button("⚖️ 提交閱卷", use_container_width=True):
                if ans_input:
                    with st.spinner("閱卷中..."):
                        res = safe_generate(f"題目：{st.session_state.current_q}\n擬答：{ans_input}\n給予評分與建議。")
                        st.session_state.feedback = res
                        score_match = re.search(r"(\d+)/25", res)
                        log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_match.group(1) if score_match else "N/A", ans_input, res)

    if 'feedback' in st.session_state:
        st.markdown(f"<div style='margin-top:20px; padding:20px; background:#2d323e; border-radius:12px; border-left:5px solid #d4c19c;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

# --- Tab 4: 歷程紀錄 (完整圖表) ---
with tab4:
    st.markdown("### 📊 學習成長分析")
    df = get_records()
    if not df.empty:
        df['score_num'] = pd.to_numeric(df['實戰分數'], errors='coerce')
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("總練習", f"{len(df)} 次")
        with m2: st.metric("平均分", f"{df['score_num'].mean():.1f}")
        with m3: st.metric("最高分", f"{df['score_num'].max():.0f}")
        st.line_chart(df.set_index('紀錄時間')['score_num'])
        st.dataframe(df[['紀錄時間', '題目主題', '實戰分數', '我的作答', 'AI 評語摘要']], use_container_width=True)
    else: st.info("尚未有練習紀錄。")
