import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# --- 1. 系統層級與視覺設定 ---
st.set_page_config(page_title="專業學習社群研究室 | 行政專業發展模擬", layout="wide", page_icon="🏫")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    .block-container {
        max-width: 1100px !important;
        padding-top: 1.5rem !important;
        margin: auto;
    }

    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif; 
        font-weight: 300; 
        letter-spacing: 0.02em;
    }
    
    .stApp { background-color: #1a1d24; color: #eceff4; }

    .main-header {
        text-align: center;
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 1.8rem; margin-bottom: 1.5rem; letter-spacing: 0.05rem;
    }

    /* 試題與建議框 */
    .scroll-box { 
        height: auto; min-height: 120px; overflow-y: auto; 
        border: 1px solid #3b4252; padding: 25px; 
        border-radius: 12px; background: #242933; 
        color: #e5e9f0; line-height: 1.85; 
        font-size: 1.05rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;
    }

    /* 控制生成內容標題大小 */
    .stMarkdown h4 {
        font-size: 1.05rem !important;
        font-weight: 500 !important;
        color: #88c0d0 !important;
        margin-top: 18px !important;
        border-bottom: 1px solid #3b4252;
        padding-bottom: 5px;
    }

    /* 作答區高度設定 */
    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; font-size: 1.05rem !important; line-height: 1.8 !important; padding: 20px !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 650px !important; background-color: #242933 !important; border-radius: 12px !important;
    }

    .alert-box {
        background: rgba(136, 192, 208, 0.05); border: 1px solid #4c566a;
        color: #d8dee9; padding: 12px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 15px;
    }

    .word-count-badge { background: #2e3440; color: #8fbcbb; padding: 6px 12px; border-radius: 4px; font-size: 0.8rem; border: 1px solid #434c5e; }
    .stButton>button { border-radius: 8px; background-color: #2e3440; color: #88c0d0; border: 1px solid #434c5e; width: 100%; height: 3rem; font-weight: 500; font-size: 0.95rem; }
    .stButton>button:hover { background-color: #88c0d0; color: #1a1d24; border: 1px solid #88c0d0; }
    .tiny-label { font-size: 0.85rem; color: #81a1c1; margin-bottom: 5px; font-weight: 500; }
    
    /* 建議內容容器 */
    .suggestion-content { line-height: 1.8; color: #e5e9f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始化 ---
if "init_done" not in st.session_state:
    st.session_state.update({
        "password_correct": False, 
        "current_q": "", 
        "suggested_structure": "", 
        "start_time": None,
        "init_done": True
    })

@st.cache_resource
def init_ai():
    try:
        api_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=api_key)
        # 修復：動態偵測模型解決 404
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in available_models if "flash" in m), available_models[0])
        return genai.GenerativeModel(target)
    except: return None

@st.cache_resource
def init_google_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds).open("Education_Exam_Records").sheet1
    except: return None

model = init_ai()
sheet_conn = init_google_sheet()

def stream_generate(prompt, container=None):
    if not model: return "AI 初始化失敗，請檢查 API Key。"
    placeholder = container.empty() if container else st.empty()
    full_response = ""
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        return full_response
    except Exception as e:
        return f"生成發生錯誤: {str(e)}"

def log_to_google_sheets(topic, score, user_answer, feedback):
    if sheet_conn:
        try:
            row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), topic, score, user_answer[:4000], feedback[:800].replace('\n', ' ') + "..."]
            sheet_conn.append_row(row)
        except: pass

# --- 3. 權限驗證 ---
if not st.session_state["password_correct"]:
    st.markdown('<h1 class="main-header">🛡️ 專業學習社群研究室 | 系統登入</h1>', unsafe_allow_html=True)
    col_p = st.columns([1,2,1])[1]
    with col_p:
        pwd = st.text_input("🔑 輸入行政通關密碼：", type="password", key="login_field")
        if st.button("啟動系統"):
            if pwd == st.secrets.get("app_password"):
                st.session_state["password_correct"] = True
                st.success("驗證成功，正在進入...")
                time.sleep(0.5)
                st.rerun()
            else: st.error("密碼錯誤，請確認輸入法是否為半型。")
    st.stop()

# --- 4. 主分頁 ---
st.markdown('<h1 class="main-header">🏫 學習社群研究室</h1>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["📰 趨勢閱讀", "📚 戰略矩陣", "✍️ 實戰模擬", "📊 歷程紀錄"])

with tab1:
    st.markdown("### 📍 新聞資訊導引")
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    c = st.columns(5)
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url, use_container_width=True)
    
    st.markdown("---")
    news_clip = st.text_area("🔍 趨勢文本分析：", height=150, placeholder="貼上教育新聞以轉化考點...", key="news_clip_tab1")
    if st.button("🎯 執行深度考點轉化"):
        if news_clip: 
            stream_generate(f"請以教育行政視角分析考點並給出可能的發展方向：\n{news_clip}")

with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導", key="nt_t2")
    
    with st.expander("⚖️ 法規/理論參考文本 (點擊展開/縮放)"):
        ref_text_note = st.text_area("輸入參考文本：", height=200, placeholder="貼上最新法規或核心理論確保矩陣正確性...", key="rt_t2", label_visibility="collapsed")
    
    if st.button("📖 生成行政戰略架構"):
        if note_t:
            p = f"""主題：{note_t}
            參考文本：{ref_text_note}
            指令：請撰寫具備行政專業格局的戰略筆記，嚴格遵守以下格式，且標題請使用 #### (小標)：
            #### 一、前言
            描述該專題在當前教育脈動下的重要性。
            #### 二、提供學理
            列出此專題適用的行政理論（如：韌性領導、權變理論、社會情緒學習等）。
            #### 三、行動矩陣 (Who, What, How)
            請使用 Markdown 表格呈現行動矩陣，欄位包含：對象(Who)、行動方案(What)、執行細節(How)。
            #### 四、結語
            總結願景與預期成效。"""
            stream_generate(p)

with tab3:
    st.markdown("""<div class="alert-box">🎯 <strong>平衡命題機制啟動：</strong> 系統將依據主題自動連結社會趨勢（少子化、AI、SDGs、OECD）並生成具深度的實戰試題。</div>""", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([0.8, 3.5, 0.8])
    with c1:
        st.markdown('<p class="tiny-label">⏱️ 計時器</p>', unsafe_allow_html=True)
        if st.button("啟動模擬", key="timer_btn", use_container_width=True):
            st.session_state.start_time = time.time()
            st.success("計時開始")
    with c2:
        st.markdown('<p class="tiny-label">🖋️ 自訂模擬試題主題</p>', unsafe_allow_html=True)
        manual_theme = st.text_input("自訂主題", placeholder="輸入專題、政策或校園痛點 (如：校事會議處理、少子化下的特色招生)...", label_visibility="collapsed", key="manual_theme_tab3")
    with c3:
        st.markdown('<p class="tiny-label">🚀 命題</p>', unsafe_allow_html=True)
        gen_btn = st.button("生成試題", use_container_width=True, key="gen_q_btn")

    with st.expander("⚖️ 法規校準座 (校準 AI 閱卷標準)"):
        ref_text_sim = st.text_area("校準文本", height=150, placeholder="在此貼上最新的行政規範、局端公文或指引...", key="sim_ref")

    q_container = st.container()
    if gen_btn:
        if not manual_theme.strip():
            st.warning("請先輸入主題再生成試題。")
        else:
            p = f"""你現在是高階教育行政評議委員。請針對主題『{manual_theme}』，並參考法規『{ref_text_sim}』設計一則約 180-220 字的情境申論題。

            命題原則：
            1. 情境寫實：設計一個具體的校園行政困境，避免邏輯破碎。
            2. 趨勢融合：請根據主題自動關聯一項最相關的當前社會或國際趨勢（如少子化、OECD 2030、數位轉型、永續發展 SDGs 或 SEL）融入背景。
            3. 核心提問：最後提問必須清晰，要求考生從「行政領導者」角色提出具體行動策略。
            4. 難度控管：確保題目具專業格局，但屬於在考試時間內可完整論述的範疇。

            要求：敘述一體化，禁止條列，直接輸出題目內容。"""
            with q_container:
                st.markdown('<div class="scroll-box">', unsafe_allow_html=True)
                st.session_state.current_q = stream_generate(p)
                st.markdown('</div>', unsafe_allow_html=True)
            st.session_state.suggested_structure = ""
    elif st.session_state.current_q:
        q_container.markdown(f'<div class="scroll-box">{st.session_state.current_q}</div>', unsafe_allow_html=True)

    if st.session_state.current_q:
        if st.button("💡 獲取黃金架構建議"):
            with st.expander("🏆 行政專業答題架構", expanded=True):
                st.markdown('<div class="suggestion-content">', unsafe_allow_html=True)
                s_p = f"""題目：{st.session_state.current_q}\n請提供極簡架構。嚴禁粗體標題集。使用 #### 作為小標：
                #### 📍 一、前言：核心理念 (破題關鍵字)
                #### 🏗️ 二、中段：行動策略 (Who/What/How)
                #### 🌟 三、結語：願景亮點"""
                st.session_state.suggested_structure = stream_generate(s_p)
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (高度 650px)</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答內容", label_visibility="collapsed", key="ans_sim_v2", height=650)

    f1, f2 = st.columns([1, 1])
    with f1: st.markdown(f'<span class="word-count-badge">📝 當前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
    with f2:
        if st.button("⚖️ 提交閱卷評分", use_container_width=True, key="submit_eval"):
            if ans_input:
                st.markdown("### ⚖️ 專業評閱意見")
                eval_p = f"題目：{st.session_state.current_q}\n法規校準：{ref_text_sim}\n考生擬答：{ans_input}\n請依據法規精準評分(滿分25)並給予改進建議。"
                res = stream_generate(eval_p)
                score_match = re.search(r"(\d+)/25", res)
                log_to_google_sheets(manual_theme, score_match.group(1) if score_match else "N/A", ans_input, res)

with tab4:
    st.markdown("### 📊 行政成長歷程分析")
    if sheet_conn:
        try:
            raw_data = sheet_conn.get_all_records()
            if raw_data:
                df = pd.DataFrame(raw_data)
                # 重要：修復 Tab 4 數據格式崩潰
                df['score_num'] = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0)
                
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("總練習次數", len(df))
                with c2: st.metric("平均得分", f"{df['score_num'].mean():.1f}")
                with c3: st.metric("最高得分", f"{df['score_num'].max():.0f}")
                
                st.markdown('<p class="tiny-label">📈 得分趨勢圖</p>', unsafe_allow_html=True)
                st.line_chart(df['score_num'])
                st.dataframe(df.astype(str), use_container_width=True)
            else: st.info("尚無練習紀錄。")
        except: st.error("資料讀取失敗，請確認資料表權限與 GCP 金鑰設定。")
