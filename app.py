import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# --- 1. 系統層級設定 ---
st.set_page_config(page_title="體育課程研究室 (A4 視覺版)", layout="wide", page_icon="🏫")

# --- 2. 關鍵修正：預先宣告 Session State (防止重新整理時當機) ---
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

# --- 3. CSS 視覺優化 (包含您指定的 1150px 收納) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    /* [核心修改] 強制將寬版介面收納為 1150px 置中，減少閱讀疲勞 */
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

    .main-header {
        text-align: center; /* 標題置中更美觀 */
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 2rem; margin-bottom: 2rem; letter-spacing: 0.05rem;
    }

    /* 試題區塊 */
    .scroll-box { 
        height: 250px !important; overflow-y: auto !important; 
        border: 1px solid #3b4252; padding: 25px; 
        border-radius: 12px; background: #242933; 
        color: #e5e9f0; line-height: 1.85; font-size: 1.05rem; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;
    }

    /* 作答區高度 650px */
    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; font-size: 1.1rem !important; line-height: 1.8 !important; padding: 20px !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 650px !important; background-color: #242933 !important; border-radius: 12px !important;
    }

    .guide-box-wide {
        background: rgba(129, 161, 193, 0.05); border-left: 3px solid #5e81ac; 
        padding: 25px; border-radius: 8px; margin-top: 15px; 
        font-size: 1.0rem; color: #d8dee9; line-height: 1.9;
    }

    .alert-box {
        background: rgba(191, 97, 106, 0.08); border: 1px solid #bf616a;
        color: #e5e9f0; padding: 12px; border-radius: 8px; font-size: 0.9rem; margin-bottom: 15px;
    }

    .tiny-label { font-size: 0.85rem !important; color: #69788e; margin-bottom: 6px; font-weight: 500; }
    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; border: 1px solid #434c5e; }
    
    .stButton>button { border-radius: 8px; background-color: #2e3440; color: #88c0d0; border: 1px solid #434c5e; width: 100%; }
    .stButton>button:hover { background-color: #88c0d0; color: #1a1d24; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 資源初始化 (加強版：增加 TTL 快取鎖定) ---
@st.cache_resource(ttl=3600)
def init_ai():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # 這裡參照您的版本，確保使用 Flash 模型
        return genai.GenerativeModel("gemini-1.5-flash")
    except: return None

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

# --- Google Sheets 寫入函式 (參照您的版本並加入錯誤處理) ---
def log_to_google_sheets(topic, score, user_answer, feedback):
    if sheet_conn:
        try:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                topic, score, user_answer[:4000], 
                feedback[:500].replace('\n', ' ') + "...", ""
            ]
            sheet_conn.append_row(row)
            return True
        except: return False
    return False

def get_records():
    if sheet_conn:
        try:
            return pd.DataFrame(sheet_conn.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- 5. 權限驗證 ---
if not st.session_state["password_correct"]:
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

# --- 6. 題庫定義 ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園教育願景、品牌學校形塑、ESG永續經營、韌性領導。",
    "📘 課程發展與課綱領航": "108課綱深綱、雙語教育、SDGs國際教育、跨域課程整合。",
    "📖 教學領航與數位轉型": "GenAI教學倫理、數位公民素養、教師PLC運作、生生用平板。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 7. 主程式介面 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

# --- Tab 1 ---
with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url, use_container_width=True)
    st.markdown("---")
    news_clip = st.text_area("🔍 欲分析的教育新聞文本：", height=150, placeholder="將新聞文字貼於此處...", key="news_v11")
    if st.button("🎯 執行深度考點轉化"):
        if news_clip and model:
            with st.spinner("解析中..."): 
                try: st.markdown(model.generate_content(f"請以教育行政視角分析考點：\n{news_clip}").text)
                except: st.error("連線忙碌中，請重試。")

# --- Tab 2 ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    col_n1, col_n2 = st.columns([1, 1])
    with col_n1:
        note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導", key="nt_t2")
    with col_n2:
        ref_text_note = st.text_area("法規參考文本：", height=68, placeholder="貼上最新法規確保筆記正確...", key="rt_t2")
    
    if st.button("📖 生成行政戰略架構"):
        if model and note_t:
            with st.spinner("整理中..."):
                try:
                    p = f"主題：{note_t}\n參考文本：{ref_text_note}\n請依據參考文本(若有)撰寫包含前言、內涵、KPI表格、結語的策略筆記。"
                    st.markdown(model.generate_content(p).text)
                except: st.error("連線忙碌中，請重試。")

# --- Tab 3 (維持您的架構，加上錯誤處理) ---
with tab3:
    st.markdown("""
    <div class="alert-box">
    🎯 <strong>校準機制已啟動：</strong> 若您要練習「校事會議」等新法規主題，請務必在下方「法規校準座」貼上最新法規條文。AI 將嚴格依據此文本進行閱卷。
    </div>
    """, unsafe_allow_html=True)

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

    if gen_btn and model:
        with st.spinner("正在校準並命題中..."):
            try:
                target = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
                q_prompt = f"""
                你現在是校長甄試命題委員。
                請針對『{target}』設計一題實務申論題。
                【校準參考】：{ref_text_sim}
                指令：
                1. 若有校準參考，請從中提取最新的流程或規定作為命題情境。
                2. 情境 150 字內，需包含行政理論與實務任務。
                3. 直接輸出題目。
                """
                st.session_state.current_q = model.generate_content(q_prompt).text
                st.session_state.suggested_structure = None
            except: st.error("連線逾時，請再試一次。")

    st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請先點擊生成試題...")}</div>', unsafe_allow_html=True)

    if st.session_state.get("current_q") and st.button("💡 獲取黃金架構建議"):
        with st.spinner("分析中..."):
            try:
                s_prompt = f"題目：{st.session_state.current_q}\n校準參考：{ref_text_sim}\n請提供三段式答題建議。"
                st.session_state.suggested_structure = model.generate_content(s_prompt).text
            except: st.error("AI 思考逾時。")

    if st.session_state.get("suggested_structure"):
        st.markdown(f'<div class="guide-box-wide">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (A4 寬度優化)</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答內容", label_visibility="collapsed", key="ans_sim")

    f1, f2 = st.columns([1, 1])
    with f1: st.markdown(f'<span class="word-count-badge">📝 字數：{len(ans_input)}</span>', unsafe_allow_html=True)
    with f2:
        if st.button("⚖️ 提交閱卷評分 (依據校準文本)", use_container_width=True):
            if model and ans_input:
                with st.spinner("正在依據最新法規進行精準評分..."):
                    try:
                        eval_prompt = f"""
                        你現在是閱卷委員。請評分以下作答。
                        【題目】：{st.session_state.current_q}
                        【正確法規依據（校準文本）】：{ref_text_sim}
                        【考生擬答】：{ans_input}
                        
                        指令：
                        1. 必須以「校準文本」為唯一的程序真理。若考生擬答與校準文本衝突，請扣分並指出錯誤。
                        2. 評分標準：滿分 25 分。
                        3. 給予具體建議。
                        """
                        res = model.generate_content(eval_prompt).text
                        st.session_state.feedback = res
                        
                        score_match = re.search(r"(\d+)/25", res)
                        score_val = score_match.group(1) if score_match else "N/A"
                        log_to_google_sheets(manual_theme if manual_theme.strip() else sel_choice, score_val, ans_input, res)
                    except: st.error("評分連線失敗。")

    if st.session_state.get('feedback'):
        st.markdown(f"<div class='guide-box-wide' style='border-left:4px solid #88c0d0;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

# --- Tab 4 ---
with tab4:
    st.markdown("### 📊 學習歷程分析")
    df = get_records()
    if not df.empty:
        # 安全檢查欄位
        valid_cols = [c for c in df.columns if "分數" in str(c) or "score" in str(c).lower()]
        if valid_cols or len(df.columns) > 2:
            # 嘗試抓取分數欄位，通常是第3欄 (index 2)
            try:
                score_col = df.columns[2] 
                df['score_num'] = pd.to_numeric(df[score_col], errors='coerce')
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("總練習次數", len(df))
                with c2: st.metric("平均得分", f"{df['score_num'].mean():.1f}")
                with c3: st.metric("最高得分", f"{df['score_num'].max():.0f}")
                st.line_chart(df['score_num'])
            except: pass
        st.dataframe(df, use_container_width=True)
    else: st.info("尚無紀錄。")
