import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# 1. 頁面基本設定 (置於首行確保穩定)
st.set_page_config(page_title="體育課程研究室", layout="wide", page_icon="🏫")

# --- 🎨 核心 CSS：視覺平衡與置中優化 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    /* 限制最大寬度：解決寬螢幕視線疲勞 */
    .block-container {
        max-width: 1150px !important;
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        margin: auto;
    }

    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif !important; 
        font-weight: 300; 
    }
    
    .stApp { background-color: #1a1d24; color: #eceff4; }

    /* 置中標題與美化 */
    .main-header {
        text-align: center;
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 2.2rem; margin-bottom: 2rem;
    }

    /* 試題區視窗 */
    .scroll-box { 
        height: 250px; overflow-y: auto; border: 1px solid #3b4252; 
        padding: 25px; border-radius: 15px; background: #242933; 
        color: #e5e9f0; line-height: 1.85; font-size: 1.05rem; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.2); margin-bottom: 20px;
    }

    /* 作答區：650px 高度與擬真字體 */
    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; font-size: 1.1rem !important; 
        line-height: 1.8 !important; padding: 20px !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 650px !important; background-color: #242933 !important;
        border-radius: 12px !important; border: 1px solid #434c5e !important;
    }

    /* 提示與評分框 */
    .guide-box-wide {
        background: rgba(136, 192, 208, 0.08); border-left: 5px solid #5e81ac; 
        padding: 25px; border-radius: 10px; margin-top: 20px; 
        font-size: 1.05rem; color: #d8dee9; line-height: 1.9;
    }

    .alert-box {
        background: rgba(191, 97, 106, 0.1); border: 1px solid #bf616a;
        color: #e5e9f0; padding: 15px; border-radius: 10px; font-size: 0.95rem; margin-bottom: 20px;
    }

    .tiny-label { font-size: 0.85rem !important; color: #69788e; margin-bottom: 8px; font-weight: 500; }
    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 5px 15px; border-radius: 6px; border: 1px solid #434c5e; }
    
    /* 按鈕美化 */
    .stButton>button { 
        border-radius: 10px; background-color: #2e3440; color: #88c0d0; 
        border: 1px solid #434c5e; transition: all 0.3s ease;
    }
    .stButton>button:hover { background-color: #88c0d0; color: #1a1d24; }
    </style>
    """, unsafe_allow_html=True)

# --- 🤖 核心資源初始化 (快取以預防連線斷開) ---
@st.cache_resource
def init_services():
    try:
        # AI 初始化
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Google Sheets 初始化
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Education_Exam_Records").sheet1
        return model, sheet
    except Exception as e:
        return None, None

model, sheet_conn = init_services()

def log_to_sheets(topic, score, user_answer, feedback):
    if sheet_conn:
        try:
            row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), topic, score, user_answer, feedback[:300].replace('\n', ' ') + "...", ""]
            sheet_conn.append_row(row)
            return True
        except: return False
    return False

# --- 🔐 存取保護邏輯 ---
if "password_correct" not in st.session_state:
    st.markdown('<h1 class="main-header">🛡️ 系統准入驗證</h1>', unsafe_allow_html=True)
    col_p = st.columns([1,2,1])[1]
    with col_p:
        pwd = st.text_input("🔑 行政通關密碼：", type="password")
        if st.button("啟動系統", use_container_width=True):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("密碼錯誤。")
    st.stop()

# --- 📖 資料庫 ---
THEME_POOL = {
    "🏆 領導願景與品牌經營": "桃園教育願景、品牌學校形塑、ESG永續經營、韌性領導。",
    "📘 課程發展與課綱領航": "108課綱深綱、雙語教育、SDGs國際教育、跨域課程整合。",
    "📖 教學領航與數位轉型": "GenAI教學倫理、數位公民素養、教師PLC運作、生生用平板。",
    "⚖️ 法理實務與危機處理": "校事會議、霸凌防制新制、性平法實務、親師衝突溝通策略。",
    "❤️ SEL 與學生輔導": "社會情緒學習計畫、學生心理健康韌性、正向管教、中輟預防。"
}

# --- 🏢 主介面設計 ---
st.markdown('<h1 class="main-header">🏫 體育課程研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 策略筆記", "✍️ 實戰模擬", "📊 歷程紀錄"])

# --- Tab 1: 趨勢閱讀 ---
with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url, use_container_width=True)
    
    news_clip = st.text_area("🔍 欲分析的教育新聞文本：", height=150, placeholder="將新聞文字貼於此處...", key="news_v12")
    if st.button("🎯 執行深度考點轉化", key="btn_tab1"):
        if news_clip and model:
            with st.spinner("解析中..."): 
                res = model.generate_content(f"請以教育行政視角分析考點與實務對策：\n{news_clip}").text
                st.markdown(res)

# --- Tab 2: 策略筆記 ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    col_n1, col_n2 = st.columns([1, 1])
    with col_n1:
        note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導", key="nt_1")
    with col_n2:
        ref_text_note = st.text_area("參考文本：", height=68, placeholder="貼上最新法規確保筆記正確...", key="rt_1")
    
    if st.button("📖 生成行政戰略架構", key="btn_tab2"):
        if model and note_t:
            with st.spinner("整理中..."):
                p = f"主題：{note_t}\n參考內容：{ref_text_note}\n請依據參考內容撰寫包含前言、內涵、策略KPI表格、結語的架構。"
                st.markdown(model.generate_content(p).text)

# --- Tab 3: 實戰模擬 (雙向校準完全版) ---
with tab3:
    st.markdown("""
    <div class="alert-box">
    🎯 <strong>校準機制已啟動：</strong> 若要練習「校事會議」等主題，請先在「法規校準座」貼上最新條文。AI 將視其為唯一的評分依據。
    </div>
    """, unsafe_allow_html=True)

    # 控制區
    c1, c2, c3, c4 = st.columns([0.8, 1.5, 2, 0.8])
    with c1:
        st.markdown('<p class="tiny-label">⏱️ 計時器</p>', unsafe_allow_html=True)
        if st.button("啟動模擬", use_container_width=True):
            st.session_state.start_time = time.time()
            st.success("計時開始")
    with c2:
        st.markdown('<p class="tiny-label">🎯 命題向度</p>', unsafe_allow_html=True)
        sel_choice = st.selectbox("向度", list(THEME_POOL.keys()), label_visibility="collapsed")
    with c3:
        st.markdown('<p class="tiny-label">🖋️ 自訂主題</p>', unsafe_allow_html=True)
        manual_theme = st.text_input("主題", placeholder="不填則依向度命題...", key="custom_t_v12", label_visibility="collapsed")
    with c4:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        gen_btn = st.button("生成試題", use_container_width=True)

    with st.expander("⚖️ 法規校準座 (貼入最新 SOP 條文)"):
        ref_text_sim = st.text_area("校準文本", height=150, placeholder="在此貼上最新的法規條文...", key="sim_ref_v12")

    if gen_btn and model:
        with st.spinner("校準命題中..."):
            target = manual_theme if manual_theme.strip() else THEME_POOL[sel_choice]
            q_prompt = f"你現在是閱卷委員。請針對『{target}』設計申論題。法規校準文本：{ref_text_sim}。請直接輸出試題情境。"
            st.session_state.current_q = model.generate_content(q_prompt).text
            st.session_state.feedback = None

    st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請先點擊生成試題...")}</div>', unsafe_allow_html=True)

    if st.session_state.get("current_q") and st.button("💡 獲取黃金架構建議"):
        with st.spinner("分析中..."):
            s_prompt = f"題目：{st.session_state.current_q}\n校準參考：{ref_text_sim}\n請提供三段式答題架構建議。"
            st.session_state.suggested_structure = model.generate_content(s_prompt).text

    if st.session_state.get("suggested_structure"):
        st.markdown(f'<div class="guide-box-wide">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (模擬答案卷)</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答內容", label_visibility="collapsed", key="ans_v12")

    f1, f2 = st.columns([1, 1])
    with f1: st.markdown(f'<span class="word-count-badge">📝 目前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
    with f2:
        if st.button("⚖️ 提交閱卷評分 (依據校準文本)", use_container_width=True):
            if model and ans_input:
                with st.spinner("閱卷官評分中..."):
                    eval_prompt = f"【題目】：{st.session_state.current_q}\n【正確法規】：{ref_text_sim}\n【考生擬答】：{ans_input}\n指令：依據校準文本評分(x/25)並給具體修正意見。"
                    res = model.generate_content(eval_prompt).text
                    st.session_state.feedback = res
                    score_match = re.search(r"(\d+)/25", res)
                    log_to_sheets(manual_theme if manual_theme.strip() else sel_choice, score_match.group(1) if score_match else "N/A", ans_input, res)

    if st.session_state.get('feedback'):
        st.markdown(f"<div class='guide-box-wide' style='border-left:5px solid #88c0d0;'><strong>⚖️ 閱卷評語與建議：</strong><br>{st.session_state.feedback}</div>", unsafe_allow_html=True)

# --- Tab 4: 歷程紀錄 ---
with tab4:
    st.markdown("### 📊 學習歷程分析")
    if sheet_conn:
        try:
            data = sheet_conn.get_all_records()
            if data:
                df = pd.DataFrame(data)
                df['score_num'] = pd.to_numeric(df['實戰分數'], errors='coerce')
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("總練習次數", len(df))
                with c2: st.metric("平均得分", f"{df['score_num'].mean():.1f}")
                with c3: st.metric("最高得分", f"{df['score_num'].max():.0f}")
                st.line_chart(df.set_index('紀錄時間')['score_num'])
                st.dataframe(df, use_container_width=True)
            else: st.info("目前尚無練習紀錄。")
        except: st.error("無法讀取紀錄，請檢查 Google Sheets 設定。")
