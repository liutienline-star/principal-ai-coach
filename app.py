import streamlit as st
import google.generativeai as genai

# 1. 初始化環境
st.set_page_config(page_title="桃園校長練功房", page_icon="🏫")

# 2. 讀取金鑰並設定模型
if "gemini_api_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("🔑 尚未在 Secrets 設定 API 金鑰")
    st.stop()

# 3. 畫面設計
st.title("🏫 桃園校長甄試 - AI 教練")
st.write("目前狀態：個人帳戶連線中 ✅")

# 簡單的密碼檢查
pwd = st.text_input("請輸入登入密碼", type="password")
if pwd == st.secrets["app_password"]:
    st.success("密碼正確，歡迎校長開始練功！")
    
    if st.button("🎲 隨機產生一則口試試題"):
        with st.spinner("AI 考官正在出題..."):
            try:
                # 這裡直接下達給 AI 的指令
                prompt = "請針對桃園市教育政策（如：品格教育、智慧校園），出一題校長甄試情境題。"
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("📝 模擬試題")
                st.info(response.text)
                st.success("出題完成！")
            except Exception as e:
                st.error(f"連線異常：{str(e)}")
else:
    st.warning("請輸入正確密碼以進入系統")
