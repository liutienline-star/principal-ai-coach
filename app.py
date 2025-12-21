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

# --- 🎨 核心 CSS 終極穩定版 (低對比度/柔和美編) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
    
    /* 基礎底色：深灰藍，降低對比 */
    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif; 
    }
    .stApp { background-color: #1e2128; color: #cbd5e0; }

    /* 標題：改為優雅的漸層杏色 */
    .main-header {
        background: linear-gradient(135deg, #d4c19c 0%, #a88e5a 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 700; font-size: 2.2rem;
        margin-bottom: 1.2rem;
        letter-spacing: 1.2px;
    }

    /* 試題視窗：增加呼吸感與下方間距 */
    .scroll-box { 
        height: 520px; 
        overflow-y: auto; 
        border: 1px solid rgba(212, 193, 156, 0.15); 
        padding: 30px; 
        border-radius: 18px; 
        background: #282c37;
        color: #e2e8f0; 
        line-height: 1.75; 
        font-size: 1.05rem; 
        box-shadow: 0 12px 30px rgba(0,0,0,0.15);
        margin-bottom: 30px; /* ✨ 關鍵修正：確保與按鈕的安全距離 */
    }

    /* 指引方框：柔和邊緣 */
    .guide-box {
        background: rgba(212, 193, 156, 0.05);
        border: 1px dashed rgba(212, 193, 156, 0.3);
        padding: 18px;
        border-radius: 12px;
        margin-top: 10px;
        font-size: 0.95rem;
        color: #d4c19c;
        line-height: 1.65;
    }

    /* 作答區：字體大小與高度對齊左側 */
    div[data-baseweb="textarea"] textarea {
        color: #f1f5f9 !important;
        -webkit-text-fill-color: #f1f5f9 !important;
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 520px !important;
        background-color: #282c37 !important;
        border-radius: 18px !important;
        border: 1px solid rgba(212, 193, 156, 0.15) !important;
    }

    /* 標籤文字：改為低調的灰度 */
    .tiny-label { 
        font-size: 0.85rem !important; 
        color: #8e99a7; 
        margin-bottom: 8px; 
        font-weight: 500; 
    }
    
    /* 按鈕：保持優雅不刺眼 */
    .stButton>button { 
        border-radius: 10px; 
        background-color: #2d323e; 
        color: #d4c19c; 
        border: 1px solid rgba(212, 193, 156, 0.25);
        transition: all 0.2s ease;
    }
    .stButton>button:hover { 
        background-color: #d4c19c; 
        color: #1a1c23; 
        border-color: #d4c19c;
    }

    /* 計時器與字數標章 */
    .timer-mini { 
        font-size: 1.3rem; font-weight: 600; color: #f5a9a9; 
        background: rgba(245, 169, 169, 0.05);
        padding: 8px; border-radius: 10px; border: 1px solid rgba(245, 169, 169, 0.2);
    }
    .word-count-badge { 
        background: rgba(74, 124, 124, 0.15); color: #81e6d9; 
        padding: 6px 16px; border-radius: 50px; font-size: 0.8rem; 
    }
    
    /* 分頁欄位 */
    .stTabs [aria-selected="true"] { color: #d4c19c !important; border-bottom-color: #d4c19c !important; }
    </style>
    """, unsafe_allow_html=True)

# --- ☁️ Google Sheets 串接 (核心邏輯保持不變) ---
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
            target_password = st.secrets.get("app_password")
            if target_password and pwd == target_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼驗證失敗。")
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
    "🏆 領導願景與 brand 品牌經營": "桃園「教育善好」願景、品牌學校形塑、ESG 永續經營、韌性領導。",
    "📘 課程發展與新課綱領航": "108 課綱深綱、雙語教育、SDGs 國際教育、跨域課程整合能力。",
    "📖 教學領航與數位轉型": "GenAI 教學應用倫理、數位公民素養、教師 PLC 運作實務、生生用平板 2.0。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制條例新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "114-118年社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 4. 頂部標題 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)

# --- 5. 功能分頁 ---
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

# --- Tab 1: 趨勢轉化 ---
with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/News.aspx?n=9E7AC85F1954DDA8&sms=169B8E91BB75571F"),
             ("🏫 教育局", "https://www.tyc.edu.tw/"),
             ("📖 國教院", "https://www.naer.edu.tw/"),
             ("🌟 教育評論", "http://www.ater.org.tw/commentmonth.html"),
             ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)
    st.markdown("---")
    news_clip = st.text_area("🔍 請貼上欲分析的教育新聞或政策文本：", height=180, placeholder="將文字貼於此處...", key="news_in")
    if st.button("🎯 開始深度考點轉化"):
        if news_clip and model:
            with st.spinner("正在以閱卷教授視視角解析文本..."):
                p = f"你現在是「教育政策高級分析師」。請針對這段新聞內容，提供轉化專題標題、核心要義、校長經營視角、政策對接及潛在考點命題報告：\n{news_clip}"
                st.info("### 📰 教育趨勢導讀報告")
                st.markdown(model.generate_content(p).text)

# --- Tab 2: 戰略矩陣 ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    note_t = st.text_input("當前鎖定專題：", st.session_state.get('pending_note_topic', "數位學習精進方案 2.0"))
    if st.button("📖 生成行政戰略架構"):
        if model:
            with st.spinner("煉製中..."):
                p = f"請針對專題『{note_t}』，提供學理定義、核心價值、核心面向、行動矩陣(Who, What, How)、桃園政策連結及 KPI。嚴禁贅述。"
                st.session_state.last_note = model.generate_content(p).text
    if 'last_note' in st.session_state:
        st.markdown(st.session_state.last_note)

# --- Tab 3: 實戰模擬 (重點對齊區域) ---
with tab3:
    c_timer_btn, c_timer_val, c_select, c_input, c_gen = st.columns([0.8, 1, 1.5, 2, 0.8])
    with c_timer_btn:
        st.markdown('<p class="tiny-label">⏱️ 模擬計時器</p>', unsafe_allow_html=True)
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
        manual_theme = st.text_input("自訂主題", placeholder="若不填則依向度命題...", key="custom_t", label_visibility="collapsed")
    with c_gen:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        if st.button("生成試題", use_container_width=True):
            if model:
                with st.spinner("命題中..."):
                    target_topic = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                    q_prompt = f"請參考「校長甄試筆試」風格命製一題 25 分的申論題。主題：『{target_topic}』。格式：專業語言描述校園困境與提問(約150-200字)，具備治理層級厚度。嚴禁開場白。"
                    st.session_state.current_q = model.generate_content(q_prompt).text
                    st.session_state.suggested_structure = None

    st.markdown("<br>", unsafe_allow_html=True)
    col_q, col_a = st.columns([1, 1.8], gap="large") # 加大間距確保不跑版
    
    with col_q:
        st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "試題將顯示於此...")}</div>', unsafe_allow_html=True)
        
        if st.session_state.get("current_q"):
            if st.button("💡 獲取黃金答題架構建議", use_container_width=True):
                with st.spinner("分析中..."):
                    struct_p = f"針對題目：{st.session_state.current_q}\n請提供校長甄試『黃金三段式』架構建議：1. 前言破題、2. 中段核心策略、3. 結語願景。簡潔條列。"
                    st.session_state.suggested_structure = model.generate_content(struct_p).text
            if st.session_state.get("suggested_structure"):
                st.markdown(f'<div class="guide-box"><b>📌 答題架構指引：</b><br>{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    with col_a:
        st.markdown('<p class="tiny-label">🖋️ 擬答作答區</p>', unsafe_allow_html=True)
        ans_input = st.text_area("作答區", label_visibility="collapsed", key="ans_box_final", height=500)
        f_count, f_submit = st.columns([1, 1])
        with f_count: st.markdown(f'<span class="word-count-badge">📝 當前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
        with f_submit:
            if st.button("⚖️ 提交召集人閱卷評分", use_container_width=True):
                if model and ans_input:
                    with st.spinner("閱卷評分中..."):
                        grading_p = f"""
                        你現在是「國中校長甄試閱卷召集人」。
                        題目：{st.session_state.get('current_q')}
                        考生擬答：{ans_input}
                        請提供：1. 評分指標總分評定(/25)。2. 關鍵字落點分析(含SEL、數位、ESG等)。3. 深度評語。
                        """
                        res = model.generate_content(grading_p).text
                        st.session_state.feedback = res
                        score_match = re.search(r"(\d+)/25", res)
                        score_val = score_match.group(1) if score_match else "N/A"
                        log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_val, ans_input, res)

    if 'feedback' in st.session_state:
        st.markdown(f"<div style='margin-top:30px; padding:28px; background:#2d323e; border-radius:18px; border-left:6px solid #d4c19c; color:#e2e8f0;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

# --- Tab 4: 歷程紀錄 ---
with tab4:
    st.markdown("### 📊 我的數位考典歷程")
    df = get_records()
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        df['score_num'] = pd.to_numeric(df['實戰分數'], errors='coerce')
        with c1: st.metric("總練習次數", len(df))
        with c2: st.metric("平均得分", f"{df['score_num'].mean():.1f}")
        with c3: st.metric("最後得分", df['實戰分數'].iloc[-1])
        st.line_chart(df.set_index('紀錄時間')['score_num'])
        st.dataframe(df[['紀錄時間', '題目主題', '實戰分數', '我的作答', 'AI 評語摘要']], use_container_width=True)
    else: st.info("尚無紀錄。")
