import streamlit as st
import google.generativeai as genai

# 頁面基本設定
st.set_page_config(page_title="桃園校長練功房", page_icon="🏫")

# 1. 讀取 Secrets 設定
if "gemini_api_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_api_key"])
        # 使用最新的穩定標籤，解決 404 找不到模型的問題
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except Exception as e:
        st.error(f"模型初始化失敗：{str(e)}")
        st.stop()
else:
    st.error("🔑 尚未在 Secrets 設定 API 金鑰")
    st.stop()

# 2. 介面設計
st.title("🏫 桃園校長甄試 - AI 教練")
st.write("目前狀態：後台已連結 ✅")

# 密碼檢查
if "app_password" not in st.secrets:
    st.error("請在 Secrets 設定 app_password")
    st.stop()

pwd = st.text_input("請輸入登入密碼", type="password")

if pwd == st.secrets["app_password"]:
    st.success("密碼正確，歡迎校長開始練功！")
    st.markdown("---")
    
    # 功能按鈕
    if st.button("🎲 隨機產生一則口試試題"):
        with st.spinner("AI 考官正在出題..."):
            try:
                # 針對桃園市校長甄試設計的 Prompt
                prompt = "你現在是一位專業的校長甄試考官。請出一題針對『桃園市教育政策』（如：數位科技、品格教育、雙語教學）或『校務領導情境』的口試題目。請包含：1. 題目背景 2. 核心問題 3. 建議思考方向。"
                response = model.generate_content(prompt)
                
                st.subheader("📝 模擬試題")
                st.info(response.text)
                st.success("出題成功！請開始準備您的回答。")
            except Exception as e:
                # 這裡會捕捉 404 等錯誤並給出提示
                st.error(f"連線異常：{str(e)}")
                st.info("💡 提示：如果看到 404，請確認您的 API 金鑰是從 Google AI Studio 申請的。")
else:
    if pwd:
        st.error("密碼錯誤，請再試一次。")
    st.warning("請輸入密碼以開啟考題產生器。")
