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

# --- 🎨 視覺平衡與深度優化 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    /* 核心佈局：限制最大寬度讓視覺置中，模擬真實卷面感 */
    .block-container {
        max-width: 1150px !important;
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        margin: auto;
    }

    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif; 
        font-weight: 300; 
        letter-spacing: 0.02em;
    }
    
    .stApp { background-color: #1a1d24; color: #eceff4; }

    /* 主標題：置中漸層美化 */
    .main-header {
        text-align: center;
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 2.2rem; margin-bottom: 1.5rem; letter-spacing: 0.1rem;
    }

    /* 試題顯示區：深色聚焦盒 */
    .scroll-box { 
        height: 250px !important; 
        overflow-y: auto !important; 
        border: 1px solid #3b4252; 
        padding: 30px; 
        border-radius: 15px; 
        background: #242933; 
        color: #e5e9f0; 
        line-height: 1.85; 
        font-size: 1.05rem; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.25);
        margin-bottom: 25px;
    }

    /* 作答區：650px 高度限制與字體優化 */
    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; 
        font-size: 1.1rem !important; 
        line-height: 1.8 !important;
        padding: 20px !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 650px !important; 
        background-color: #242933 !important;
        border-radius: 12px !important; 
        border: 1px solid #434c5e !important;
    }

    /* 提示與評分回饋區 */
    .guide-box-wide {
        background: rgba(136, 192, 208, 0.08); 
        border-left: 5px solid #5e81ac; 
        padding: 25px; border-radius: 10px; margin-top: 20px; 
        font-size: 1.05rem; color: #d8dee9; line-height: 1.9;
    }

    .alert-box {
        background: rgba(191, 97, 106, 0.1);
        border: 1px solid #bf616a;
        color: #e5e9f0; padding: 15px; border-radius: 10px; font-size: 0.95rem; margin-bottom: 20px;
    }

    .tiny-label { font-size: 0.85rem !important; color: #69788e; margin-bottom: 8px; font-weight: 500; }
    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 5px 15px; border-radius: 6px; font-size: 0.85rem; border: 1px solid #434c5e; }
    
    .stButton>button { 
        border-radius: 10px; 
        background-color: #2e3440; 
        color: #88c0d0; 
        border: 1px solid #434c5e; 
        height: 3rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #88c0d0;
        color: #1a1d24;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ☁️ Google Sheets 整合 ---
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

# --- 🔐 系統准入機制 ---
if "password_correct" not in st.session_state:
    st.markdown('<h1 class="main-header">🛡️ 體育課程研究室</h1>', unsafe_allow_html=True)
    col_p = st.columns([1,2,1])[1]
    with col_p:
        pwd = st.text_input("🔑 輸入行政通關密碼：", type="password")
        if st.button("啟動系統", use_container_width=True):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼錯誤。")
    st.stop()

# --- 🤖 AI 核心初始化 ---
@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        return genai.GenerativeModel("gemini-1.5-flash")
    except: return None

model = init_ai()

THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園教育願景、品牌學校形塑、ESG永續經營、韌性領導。",
    "📘 課程發展與課綱領航": "108課綱深綱、雙語教育、SDGs國際教育、跨域課程整合。",
    "📖 教學領航與數位轉型": "GenAI教學倫理、數位公民素養、教師PLC運作、生生用平板。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 主介面 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

# --- Tab 1: 趨勢閱讀 ---
with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url)
    
    news_clip = st.text_area("🔍 欲分析的教育新聞文本：", height=150, placeholder="貼上新聞文字...", key="news_v12")
    if st.button("🎯 執行深度考點轉化"):
        if news_clip and model:
            with st.spinner("解析中..."):
                res = model.generate_content(f"請以教育行政視角分析考點、法規關聯與行政作為：\n{news_clip}")
                st.markdown(res.text)

# --- Tab 2: 策略筆記 (含校準) ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    col_n1, col_n2 = st.columns([1, 1])
    with col_n1:
        note_t = st.text_input("📌 專題名稱：", placeholder="例如：桃園教育願景下之韌性領導")
    with col_n2:
        ref_text_note = st.text_area("⚖️ 法規參考文本：", height=68, placeholder="貼上最新法規確保筆記正確...")
    
    if st.button("📖 生成行政戰略架構"):
        if model and note_t:
            with st.spinner("筆記生成中..."):
                p = f"主題：{note_t}\n參考文本：{ref_text_note}\n請撰寫包含前言、內涵、策略KPI表格、結語的筆記。若有參考文本請嚴格遵守其規範。"
                st.markdown(model.generate_content(p).text)

# --- Tab 3: 實戰模擬 (雙向校準邏輯完全體) ---
with tab3:
    st.markdown("""
    <div class="alert-box">
    🎯 <strong>校準機制已啟動：</strong> 針對法理實務題，請在下方「法規校準座」貼入條文。AI 將優先依據校準文本命題，並將其視為評分唯一的程序真理。
    </div>
    """, unsafe_allow_html=True)

    # 1. 頂部控制列
    c1, c2, c3, c4 = st.columns([0.8, 1.5, 2, 0.8])
    with c1:
        st.markdown('<p class="tiny-label">⏳ 計時器</p>', unsafe_allow_html=True)
        if st.button("啟動模擬", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True
    with c2:
        st.markdown('<p class="tiny-label">🎯 命題向度</p>', unsafe_allow_html=True)
        sel_choice = st.selectbox("向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    with c3:
        st.markdown('<p class="tiny-label">🖋️ 自訂主題</p>', unsafe_allow_html=True)
        manual_theme = st.text_input("主題", placeholder="不填則依向度命題...", label_visibility="collapsed", key="v12_theme")
    with c4:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        gen_btn = st.button("生成試題", use_container_width=True)

    # 2. 法規校準座
    with st.expander("⚖️ 法規校準座 (當考題涉及時效性法規時，請在此貼入文本)"):
        ref_text_sim = st.text_area("校準文本", height=150, placeholder="在此貼上最新的 SOP 或法規條文...", key="v12_ref")

    # 3. 命題觸發
    if gen_btn and model:
        with st.spinner("校準命題中..."):
            target = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
            q_prompt = f"你是校長甄試命題委員。請針對『{target}』設計申論題。法規校準：{ref_text_sim}。請直接輸出題目。"
            st.session_state.current_q = model.generate_content(q_prompt).text
            st.session_state.suggested_structure = None

    # 4. 試題視窗
    st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請點擊生成試題開始模擬...")}</div>', unsafe_allow_html=True)

    if st.session_state.get("current_q") and st.button("💡 獲取架構建議"):
        with st.spinner("分析中..."):
            s_p = f"題目：{st.session_state.current_q}\n校準參考：{ref_text_sim}\n請提供建議架構。"
            st.session_state.suggested_structure = model.generate_content(s_p).text

    if st.session_state.get("suggested_structure"):
        st.markdown(f'<div class="guide-box-wide">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 5. 作答與提交
    st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (模擬答案卷 650px)</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答內容", label_visibility="collapsed", key="v12_ans")

    f1, f2 = st.columns([1, 1])
    with f1: st.markdown(f'<span class="word-count-badge">📝 目前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
    with f2:
        if st.button("⚖️ 提交閱卷評分 (依據校準文本)", use_container_width=True):
            if model and ans_input:
                with st.spinner("閱卷官評分中..."):
                    eval_p = f"題目：{st.session_state.current_q}\n校準文本：{ref_text_sim}\n擬答：{ans_input}\n請依校準文本嚴格評分(x/25)並給建議。"
                    res = model.generate_content(eval_p).text
                    st.session_state.feedback = res
                    score_match = re.search(r"(\d+)/25", res)
                    log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_match.group(1) if score_match else "N/A", ans_input, res)

    if 'feedback' in st.session_state:
        st.markdown(f"<div class='guide-box-wide' style='border-left:5px solid #bf616a;'><strong>⚖️ 閱卷評語：</strong><br>{st.session_state.feedback}</div>", unsafe_allow_html=True)

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
