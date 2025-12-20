import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="桃園校長練功房", page_icon="🏫")

# 1. 讀取金鑰
if "gemini_api_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_api_key"])
else:
    st.error("🔑 尚未設定 API 金鑰")
    st.stop()

# 2. 自動偵測可用模型 (解決 404 的終極招式)
@st.cache_resource
def find_available_model():
    try:
        # 抓取您這把金鑰能看見的所有模型
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 優先順序：1.5-flash -> 1.5-pro -> 1.0-pro
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for p in priority:
            if p in available_models:
                return p
        return available_models[0] if available_models else None
    except Exception as e:
        return str(e)

# 執行偵測
target_model = find_available_model()

# 3. 介面
st.title("🏫 桃園校長甄試 - AI 教練")

if "models/" in str(target_model):
    st.write(f"✅ 系統就緒 (已連線至：{target_model})")
else:
    st.error(f"❌ 偵測失敗：{target_model}")
    st.info("💡 這代表金鑰可能尚未啟用。請確認在 AI Studio 點擊了 'Create API Key'。")
    st.stop()

# 密碼檢查
pwd = st.text_input("請輸入登入密碼", type="password")
if pwd == st.secrets.get("app_password", "641101"):
    st.success("密碼正確！")
    
    if st.button("🎲 隨機產生口試試題"):
        with st.spinner("AI 考官出題中..."):
            try:
                model = genai.GenerativeModel(target_model)
                prompt = "請針對桃園市校長甄試，出一題情境試題，並提供三個引導思考方向。"
                response = model.generate_content(prompt)
                st.markdown("---")
                st.info(response.text)
            except Exception as e:
                st.error(f"連線異常：{str(e)}")
else:
    if pwd: st.error("密碼錯誤。")
