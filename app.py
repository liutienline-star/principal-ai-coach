import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# --- 1. 系統層級設定 ---
st.set_page_config(page_title="體育課程研究室 | 校長甄試模擬系統", layout="wide", page_icon="🏫")

# --- 2. 高度優化 CSS (視覺降壓與結構優化) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    .block-container {
        max-width: 1150px !important;
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        margin: auto;
    }

    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif; 
        font-weight: 300; 
    }
    
    .stApp { background-color: #1a1d24; color: #eceff4; }

    .main-header {
        text-align: center;
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 2.2rem; margin-bottom: 2rem;
    }

    /* 模擬試題顯示框 */
    .scroll-box { 
        height: auto; min-height: 120px; overflow-y: auto; 
        border: 1px solid #3b4252; padding: 20px; 
        border-radius: 12px; background: #242933; 
        color: #e5e9f0; line-height: 1.8; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;
    }

    /* 建議架構專用微型標題 (取消粗體、縮小字體) */
    .suggestion-content h4 {
        font-size: 1.05rem !important;
        font-weight: 400 !important;
        color: #88c0d0 !important;
        margin-top: 15px !important;
        border-bottom: 1px solid #3b4252;
        padding-bottom: 5px;
    }
    
    .suggestion-scroll {
        max-height: 400px;
        overflow-y: auto;
        padding-right: 10px;
        line-height: 1.7;
    }

    /* 作答區調整 */
    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; font-size: 1.1rem !important; line-height: 1.8 !important; padding: 20px !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 600px !important; background-color: #242933 !important; border-radius: 12px !important;
    }

    .alert-box {
        background: rgba(191, 97, 106, 0.1); border: 1px solid #bf616a;
        color: #e5e9f0; padding: 15px; border-radius: 8px; font-size: 0.95rem; margin-bottom: 20px;
    }

    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 6px 15px; border-radius: 4px; font-size: 0.85rem; border: 1px solid #434c5e; }
    
    .stButton>button { border-radius: 8px; background-color: #2e3440; color: #88c0d0; border: 1px solid #434c5e; width: 100%; height: 3.2rem; font-weight: 500; }
    .stButton>button:hover { background-color: #88c0d0; color: #1a1d24; border: 1px solid #88c0d0; }
    
    .tiny-label { font-size: 0.85rem; color: #81a1c1; margin-bottom: 5px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 狀態初始化 ---
if "init_done" not in st.session_state:
    st.session_state.update({
        "init_done": True,
        "password_correct": False,
        "current_q": "",
        "feedback": "",
        "suggested_structure": "",
        "start_time": None,
        "timer_running": False
    })

# --- 4. 資源初始化 ---
@st.cache_resource(ttl=3600)
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except: pass
        target_model = "models/gemini-1.5-pro"
        if available_models:
            flash = [m for m in available_models if "flash" in m]
            pro = [m for m in available_models if "pro" in m]
            target_model = flash[0] if flash else (pro[0] if pro else available_models[0])
        return genai.GenerativeModel(target_model)
    except Exception as e:
        st.error(f"AI 初始化失敗: {e}")
        return None

@st.cache_resource(ttl=3600)
def init_google_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        return client.open("Education_Exam_Records").sheet1
    except: return None

model = init_ai()
sheet_conn = init_google_sheet()

def stream_generate(prompt_text, container=None):
    if not model: 
        st.error("AI 模型未連接")
        return ""
    placeholder = container.empty() if container else st.empty()
    full_response = ""
    try:
        response = model.generate_content(prompt_text, stream=True, request_options={'timeout': 600})
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(full_response + "▌") 
        placeholder.markdown(full_response)
        return full_response
    except Exception as e:
        st.error(f"❌ 連線異常: {e}")
        return full_response

# --- 資料紀錄 ---
def log_to_google_sheets(topic, score, user_answer, feedback):
    if sheet_conn:
        try:
            row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), topic, score, user_answer[:4000], feedback[:800].replace('\n', ' ') + "...", ""]
            sheet_conn.append_row(row)
        except: pass

def get_records():
    if sheet_conn:
        try: return pd.DataFrame(sheet_conn.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- 5. 權限驗證 ---
if not st.session_state["password_correct"]:
    st.markdown('<h1 class="main-header">🛡️ 體育課程研究室 | 行政登入</h1>', unsafe_allow_html=True)
    col_p = st.columns([1,2,1])[1]
    with col_p:
        pwd = st.text_input("🔑 輸入行政通關密碼：", type="password")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼錯誤。")
    st.stop()

# --- 6. 題庫設定 ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園教育願景、品牌學校形塑、ESG永續經營、韌性領導。",
    "📘 課程發展與課綱領航": "108課綱深綱、雙語教育、SDGs國際教育、跨域課程整合。",
    "📖 教學領航與數位轉型": "GenAI教學倫理、數位公民素養、教師PLC運作、生生用平板。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 7. 主程式頁面 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url, use_container_width=True)
    st.markdown("---")
    news_clip = st.text_area("🔍 欲分析的教育新聞文本：", height=150, placeholder="將新聞文字貼於此處...", key="news_v13")
    if st.button("🎯 執行深度考點轉化"):
        if news_clip:
            st.markdown("### 考點精華分析：")
            stream_generate(f"請以教育行政視角分析考點並給出可能的出題方向：\n{news_clip}")

with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    col_n1, col_n2 = st.columns([1, 1])
    with col_n1:
        note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導", key="nt_t2")
    with col_n2:
        ref_text_note = st.text_area("法規參考文本：", height=68, placeholder="貼上最新法規確保筆記正確...", key="rt_t2")
    if st.button("📖 生成行政戰略架構"):
        if note_t:
            st.markdown("### 戰略行動計畫：")
            p = f"主題：{note_t}\n參考文本：{ref_text_note}\n請依據行政實務撰寫包含前言、核心內涵、推動策略(KPI)、結語的策略筆記。"
            stream_generate(p)

# --- Tab 3: 實戰模擬 (視覺優化核心) ---
with tab3:
    st.markdown("""<div class="alert-box">🎯 <strong>校準機制：</strong> 若有特定法規（如校事會議新制），請務必貼入下方「法規校準座」。</div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([0.8, 1.5, 2, 0.8])
    with c1:
        st.markdown('<p class="tiny-label">⏱️ 計時器</p>', unsafe_allow_html=True)
        if st.button("啟動模擬", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.timer_running = True
            st.success("計時開始")
    with c2:
        st.markdown('<p class="tiny-label">🎯 命題向度</p>', unsafe_allow_html=True)
        sel_choice = st.selectbox("向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    with c3:
        st.markdown('<p class="tiny-label">🖋️ 自訂主題</p>', unsafe_allow_html=True)
        manual_theme = st.text_input("主題", placeholder="不填則依向度命題...", key="cust_theme", label_visibility="collapsed")
    with c4:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        gen_btn = st.button("生成試題", use_container_width=True)

    with st.expander("⚖️ 法規校準座 (貼入最新條文以校準 AI 閱卷標準)"):
        ref_text_sim = st.text_area("校準文本", height=150, placeholder="在此貼上最新的 SOP 或法規條文...", key="sim_ref")

    st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
    q_container = st.container()

    if gen_btn:
        target = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
        q_prompt = f"請針對『{target}』設計一題校長甄試實務申論題。參考法規：{ref_text_sim}。請用「精簡有力」的 150-200 字撰寫一個學校行政領導、課程教學、或經營等題目，請直接輸出題目內容。"
        with q_container:
            with st.markdown('<div class="scroll-box">', unsafe_allow_html=True):
                st.session_state.current_q = stream_generate(q_prompt)
        st.session_state.suggested_structure = ""
    else:
        if st.session_state.get("current_q"):
            q_container.markdown(f'<div class="scroll-box">{st.session_state.current_q}</div>', unsafe_allow_html=True)
        else:
            q_container.markdown(f'<div class="scroll-box">請點擊生成試題...</div>', unsafe_allow_html=True)

    # --- 關鍵優化：收納式黃金架構建議 ---
    if st.session_state.get("current_q"):
        if st.button("💡 獲取黃金架構建議 (收納版)"):
            with st.expander("🏆 黃金三段式答題架構內容", expanded=True):
                st.markdown('<div class="suggestion-content"><div class="suggestion-scroll">', unsafe_allow_html=True)
                s_prompt = f"""
                題目：{st.session_state.current_q}
                校準參考：{ref_text_sim}
                請提供視覺極簡、具備標題層次的答題架構。
                嚴禁粗體大標，請使用以下 Markdown 格式輸出 (使用 #### 作為小標題)：

                #### 📍 一、前言：核心理念 (破題關鍵字)
                * [格局定位]：(2-3 個關鍵字)
                * [願景連結]：(一句話連結)

                #### 🏗️ 二、中段：行動策略 (Who/What/How)
                * 策略 1：[行政領導層次] -> 具體作為 -> 配套機制。
                * 策略 2：[專業教學層次] -> 具體作為 -> 增能手段。
                * 策略 3：[資源整合層次] -> 具體作為 -> 最終目標。

                #### 🌟 三、結語：願景亮點
                * [預期成效]：(量變與質變描述)
                * [教育格言]：(強有力的收尾)
                """
                st.session_state.suggested_structure = stream_generate(s_prompt)
                st.markdown('</div></div>', unsafe_allow_html=True)
        elif st.session_state.get("suggested_structure"):
             with st.expander("🏆 黃金三段式答題架構內容"):
                st.markdown(f'<div class="suggestion-content"><div class="suggestion-scroll">{st.session_state.suggested_structure}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="tiny-label">🖋️ 擬答作答區</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答內容", label_visibility="collapsed", key="ans_sim")

    f1, f2 = st.columns([1, 1])
    with f1: st.markdown(f'<span class="word-count-badge">📝 當前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
    with f2:
        if st.button("⚖️ 提交閱卷評分", use_container_width=True):
            if ans_input:
                st.markdown("### ⚖️ 專業評閱意見")
                eval_prompt = f"題目：{st.session_state.current_q}\n校準參考：{ref_text_sim}\n考生擬答：{ans_input}\n請依據校準文本精準評分（滿分25），指出優點與待改進之處。"
                final_feedback = stream_generate(eval_prompt)
                st.session_state.feedback = final_feedback
                score_match = re.search(r"(\d+)/25", final_feedback)
                score_val = score_match.group(1) if score_match else "N/A"
                log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_val, ans_input, final_feedback)

with tab4:
    st.markdown("### 📊 學習歷程分析")
    df = get_records()
    if not df.empty:
        try:
            df['score_num'] = pd.to_numeric(df.iloc[:, 2], errors='coerce')
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("總練習次數", len(df))
            with c2: st.metric("平均得分", f"{df['score_num'].mean():.1f}")
            with c3: st.metric("最高得分", f"{df['score_num'].max():.0f}")
            st.line_chart(df['score_num'])
        except: pass
        st.dataframe(df, use_container_width=True)
    else: st.info("尚無紀錄。")
