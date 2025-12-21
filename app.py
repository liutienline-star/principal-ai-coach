import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# --- 1. 系統層級設定 (必須在程式碼的第一行) ---
st.set_page_config(page_title="體育課程研究室 (穩定版)", layout="wide", page_icon="🏫")

# --- 2. 狀態變數預先初始化 (防止 Runtime Error 導致斷線) ---
# 這是維持連線穩定的關鍵，確保所有變數在頁面刷新前都已定義
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

# --- 3. CSS 視覺平衡與穩定優化 (1150px 置中) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500&display=swap');
    
    /* 核心佈局：限制最大寬度 (1150px) 並置中，解決寬螢幕疲勞 */
    .block-container {
        max-width: 1150px !important;
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        margin: auto;
    }

    html, body, [class*="css"] { 
        font-family: 'Noto Sans TC', sans-serif !important; 
        font-weight: 300; 
        line-height: 1.7;
    }
    
    .stApp { background-color: #1a1d24; color: #eceff4; }

    /* 標題優化 */
    .main-header {
        text-align: center;
        background: linear-gradient(120deg, #eceff4 0%, #81a1c1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 500; font-size: 2.2rem; margin-bottom: 2rem;
    }

    /* 試題區 (唯讀) */
    .scroll-box { 
        height: 250px; overflow-y: auto; border: 1px solid #3b4252; 
        padding: 25px; border-radius: 15px; background: #242933; 
        color: #e5e9f0; line-height: 1.85; font-size: 1.05rem; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.2); margin-bottom: 20px;
    }

    /* 作答區 (高度 650px - 擬真試卷感) */
    div[data-baseweb="textarea"] textarea {
        color: #eceff4 !important; font-size: 1.1rem !important; 
        line-height: 1.8 !important; padding: 20px !important;
    }
    div[data-baseweb="textarea"] > div {
        height: 650px !important; background-color: #242933 !important;
        border-radius: 12px !important; border: 1px solid #434c5e !important;
    }

    /* 評分回饋區 */
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
    
    /* 按鈕美化與高度統一 */
    .stButton>button { 
        border-radius: 10px; background-color: #2e3440; color: #88c0d0; 
        border: 1px solid #434c5e; transition: all 0.3s ease; height: 3rem;
    }
    .stButton>button:hover { background-color: #88c0d0; color: #1a1d24; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 資源初始化 (分離式架構 + 強力快取) ---

# 4.1 AI 初始化
# ttl=3600 代表連線建立後可維持 1 小時不中斷，避免重複握手
@st.cache_resource(ttl=3600, show_spinner="正在連結 AI 大腦...")
def init_ai_model():
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # 使用 Flash 模型以確保最快的反應速度與連線穩定度 (若需 Pro 可在此切換)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        st.error(f"AI 連線失敗，請檢查 API Key。錯誤: {e}")
        return None

# 4.2 Google Sheets 初始化 (獨立處理)
@st.cache_resource(ttl=3600)
def init_google_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        return client.open("Education_Exam_Records").sheet1
    except:
        return None

model = init_ai_model()
sheet_conn = init_google_sheet()

# 安全寫入函式 (含錯誤保護)
def safe_log_to_sheets(topic, score, user_answer, feedback):
    if sheet_conn:
        try:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                topic, 
                score, 
                user_answer[:4000], # 限制長度防止封包過大導致斷線
                feedback[:500].replace('\n', ' ') + "...", 
                "Stable-Version"
            ]
            sheet_conn.append_row(row)
            return True
        except: return False
    return False

# --- 5. 權限驗證 ---
if not st.session_state["password_correct"]:
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

# --- Tab 1: 趨勢閱讀 ---
with tab1:
    st.markdown("### 📍 權威資訊導引")
    c = st.columns(5)
    links = [("🏛️ 教育部", "https://www.edu.tw/"), ("🏫 教育局", "https://www.tyc.edu.tw/"), ("📖 國教院", "https://www.naer.edu.tw/"), ("🌟 教育評論", "http://www.ater.org.tw/"), ("✨ 親子天下", "https://www.parenting.com.tw/")]
    for i, (name, url) in enumerate(links):
        with c[i]: st.link_button(name, url, use_container_width=True)
    
    st.markdown("---")
    news_clip = st.text_area("🔍 欲分析的教育新聞文本：", height=150, placeholder="將新聞文字貼於此處...", key="news_tab1")
    if st.button("🎯 執行深度考點轉化", key="btn_t1"):
        if news_clip and model:
            with st.spinner("AI 正在分析與轉化考點..."): 
                try:
                    res = model.generate_content(f"請以教育行政視角分析考點：\n{news_clip}").text
                    st.markdown(res)
                except Exception as e: st.error("連線不穩，請重試。")

# --- Tab 2: 策略筆記 ---
with tab2:
    st.markdown("### 📚 實務戰略行動矩陣")
    col_n1, col_n2 = st.columns([1, 1])
    with col_n1:
        note_t = st.text_input("專題名稱：", placeholder="例如：桃園教育願景下之韌性領導", key="nt_tab2")
    with col_n2:
        ref_text_note = st.text_area("法規參考文本：", height=68, placeholder="貼上最新法規確保筆記正確...", key="rt_tab2")
    
    if st.button("📖 生成行政戰略架構", key="btn_t2"):
        if model and note_t:
            with st.spinner("正在整理架構中..."):
                try:
                    p = f"主題：{note_t}\n參考文本：{ref_text_note}\n請依據參考文本(若有)撰寫包含前言、內涵、KPI表格、結語的策略筆記。"
                    st.markdown(model.generate_content(p).text)
                except: st.error("生成失敗，請檢查網路。")

# --- Tab 3: 實戰模擬 (核心功能) ---
with tab3:
    st.markdown("""
    <div class="alert-box">
    🎯 <strong>校準機制已啟動：</strong> 若您要練習「校事會議」等新法規主題，請務必在下方「法規校準座」貼上最新法規條文。AI 將嚴格依據此文本進行閱卷。
    </div>
    """, unsafe_allow_html=True)

    # 上方控制列
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

    # 法規校準座 (隱藏式摺疊或直接顯示)
    with st.expander("⚖️ 法規校準座 (貼入最新條文以校準 AI 閱卷標準)"):
        ref_text_sim = st.text_area("校準文本", height=150, placeholder="在此貼上最新的 SOP 或法規條文...", key="sim_ref")

    # 命題邏輯
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
            except Exception as e: st.error(f"命題失敗，請稍後重試。")

    # 試題顯示
    st.markdown('<p class="tiny-label">📍 模擬試題視窗</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="scroll-box">{st.session_state.get("current_q", "請先點擊生成試題...")}</div>', unsafe_allow_html=True)

    # 架構建議按鈕
    if st.session_state.get("current_q") and st.button("💡 獲取黃金架構建議"):
        with st.spinner("分析中..."):
            try:
                s_prompt = f"題目：{st.session_state.current_q}\n校準參考：{ref_text_sim}\n請提供三段式答題建議。"
                st.session_state.suggested_structure = model.generate_content(s_prompt).text
            except: st.error("連線逾時。")

    if st.session_state.get("suggested_structure"):
        st.markdown(f'<div class="guide-box-wide">{st.session_state.suggested_structure}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 作答區 (650px)
    st.markdown('<p class="tiny-label">🖋️ 擬答作答區 (模擬答案卷)</p>', unsafe_allow_html=True)
    ans_input = st.text_area("作答內容", label_visibility="collapsed", key="ans_sim")

    # 提交區
    f1, f2 = st.columns([1, 1])
    with f1: st.markdown(f'<span class="word-count-badge">📝 目前字數：{len(ans_input)}</span>', unsafe_allow_html=True)
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
                        
                        # 擷取分數並存檔
                        score_match = re.search(r"(\d+)/25", res)
                        score_val = score_match.group(1) if score_match else "N/A"
                        safe_log_to_sheets(manual_theme if manual_theme.strip() else sel_choice, score_val, ans_input, res)
                    except Exception as e: st.error("評分連線失敗，請重試。")

    if st.session_state.get('feedback'):
        st.markdown(f"<div class='guide-box-wide' style='border-left:4px solid #88c0d0;'>{st.session_state.feedback}</div>", unsafe_allow_html=True)

# --- Tab 4: 歷程紀錄 ---
with tab4:
    st.markdown("### 📊 學習歷程分析")
    if sheet_conn:
        try:
            data = sheet_conn.get_all_records()
            if data:
                df = pd.DataFrame(data)
                # 簡單檢查欄位名稱
                valid_cols = [c for c in df.columns if "分數" in str(c)]
                if valid_cols:
                    score_col = valid_cols[0]
                    df['score_num'] = pd.to_numeric(df[score_col], errors='coerce')
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("總練習次數", len(df))
                    with c2: st.metric("平均得分", f"{df['score_num'].mean():.1f}")
                    with c3: st.metric("最高得分", f"{df['score_num'].max():.0f}")
                    
                    st.line_chart(df['score_num'])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.dataframe(df, use_container_width=True)
            else: st.info("目前尚無練習紀錄。")
        except: st.error("無法讀取紀錄，請檢查 Google Sheets 權限。")
    else:
        st.warning("Google Sheets 未連線，僅提供 AI 模擬功能。")
