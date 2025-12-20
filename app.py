import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="桃園校長練功房", page_icon="🏫")

# 1. 配置金鑰
if "gemini_api_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_api_key"])
else:
    st.error("🔑 尚未設定 API 金鑰")
    st.stop()

# 2. 介面
st.title("🏫 桃園校長甄試 - AI 教練")

# 密碼檢查
pwd = st.text_input("請輸入登入密碼", type="password")
if pwd == st.secrets.get("app_password", "641101"):
    st.success("密碼正確！")
    
    if st.button("🎲 隨機產生口試試題"):
        with st.spinner("正在連線至 Google AI 總部..."):
            try:
                # 重點：加入 models/ 前綴，並嘗試最穩定的名稱
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                
                prompt = "請針對桃園市校長甄試，出一題關於『智慧校園』或『親師溝通』的情境題。"
                response = model.generate_content(prompt)
                
                st.markdown("---")
                st.info(response.text)
                st.success("連線成功！")
            except Exception as e:
                st.error(f"連線異常：{str(e)}")
                st.info("💡 如果依然 404，代表金鑰權限不屬於 AI Studio。")
