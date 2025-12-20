import streamlit as st
import google.generativeai as genai

# 頁面基本設定
st.set_page_config(page_title="桃園校長練功房", page_icon="🏫")

# 1. 讀取 Secrets 設定
if "gemini_api_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_api_key"])
else:
    st.error("🔑 尚未在 Secrets 設定 API 金鑰")
    st.stop()

# 2. 自動偵測可用模型 (解決 404 關鍵點)
@st.cache_resource
def load_model():
    # 按照穩定度排序嘗試
    model_names = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
    for name in model_names:
        try:
            model = genai.GenerativeModel(name)
            # 測試一下模型是否真的能用
            model.generate_content("test", generation_config={"max_output_tokens": 1})
            return model, name
        except:
            continue
    return None, None

model, active_model_name = load_model()

# 3. 介面設計
st.title("🏫 桃園校長甄試 - AI 教練")
if active_model_name:
    st.write(f"目前狀態：系統已連線 ({active_model_name}) ✅")
else:
    st.error("❌ 無法連接 AI 模型。請檢查金鑰是否正確。")
    st.stop()

# 密碼檢查
pwd = st.text_input("請輸入進入密碼", type="password")

if pwd == st.secrets.get("app_password", "641101"):
    st.success("密碼正確，歡迎校長開始練功！")
    
    if st.button("🎲 隨機產生一則口試試題"):
        with st.spinner("AI 考官正在出題..."):
            try:
                prompt = "你是一位專業的校長甄試考官。請出一題針對『桃園市教育政策』（如：數位科技、品格教育、校園安全）的口試題目。請包含：1. 題目背景 2. 核心問題 3. 建議思考方向。"
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("📝 模擬試題")
                st.info(response.text)
            except Exception as e:
                st.error(f"連線異常：{str(e)}")
else:
    if pwd:
        st.error("密碼錯誤。")
