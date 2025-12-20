import streamlit as st
import google.generativeai as genai

# 基本頁面設定
st.set_page_config(page_title="桃園校長練功房", page_icon="🏫")

# 1. 讀取金鑰
if "gemini_api_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_api_key"])
else:
    st.error("🔑 尚未設定金鑰")
    st.stop()

# 2. 核心出題邏輯 (修正 404 關鍵)
def generate_question():
    # 按照優先順序排列模型名稱
    models_to_try = [
        "gemini-1.5-flash",        # 優先：速度快
        "gemini-1.5-pro",          # 備援：更強大
        "models/gemini-1.5-flash"  # 備援：完整路徑
    ]
    
    last_error = ""
    for model_name in models_to_try:
        try:
            # 建立模型實例
            model = genai.GenerativeModel(model_name)
            # 測試出題
            prompt = "你是一位專業的校長甄試考官。請出一題針對『桃園市教育政策』（如：數位科技、品格教育）的口試情境題。請包含：1. 題目背景 2. 核心問題 3. 建議思考方向。"
            response = model.generate_content(prompt)
            return response.text, model_name
        except Exception as e:
            last_error = str(e)
            continue # 失敗就試下一個
            
    return None, last_error

# 3. 介面顯示
st.title("🏫 桃園校長甄試 - AI 教練")

# 密碼檢查 (使用您設定的 641101)
pwd = st.text_input("請輸入登入密碼", type="password")
if pwd == st.secrets.get("app_password", "641101"):
    st.success("密碼正確，歡迎校長開始練功！")
    
    if st.button("🎲 隨機產生一則口試試題"):
        with st.spinner("AI 考官正在思考題目..."):
            result, info = generate_question()
            if result:
                st.markdown("---")
                st.subheader("📝 模擬試題")
                st.info(result)
                st.caption(f"由 AI 模型 {info} 產生")
            else:
                st.error(f"出題失敗，所有模型均無法連線。錯誤訊息：{info}")
                st.info("💡 建議：請檢查 Google AI Studio 是否有顯示任何帳戶警示。")
else:
    if pwd:
        st.error("密碼錯誤。")
