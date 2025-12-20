import streamlit as st
import google.generativeai as genai

st.title("🔍 系統連線診斷工具")

# 1. 檢查 Secrets 讀取狀況
st.subheader("1. 檢查 Secrets")
if "gemini_api_key" in st.secrets:
    key = st.secrets["gemini_api_key"]
    st.success(f"✅ 已偵測到變數 `gemini_api_key`")
    st.write(f"🔑 金鑰開頭為: `{key[:8]}...` (請檢查是否為 AIza 開頭)")
else:
    st.error("❌ 找不到 `gemini_api_key`！請檢查 Secrets 命名。")

# 2. 嘗試與 Google 連線
st.subheader("2. 嘗試連線測試")
if "gemini_api_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        # 強制進行一次微小通訊測試
        test_response = model.generate_content("Hi", generation_config={"max_output_tokens": 1})
        st.success("🎉 連線成功！AI 引擎運作正常。")
        st.balloons()
        st.info("既然診斷成功，您可以換回剛才那份『最終版』程式碼了。")
    except Exception as e:
        st.error("❌ 連線測試失敗")
        st.warning(f"Google 回報的具體錯誤訊息：\n`{str(e)}`")
        
        # 針對常見錯誤給建議
        if "API_KEY_INVALID" in str(e):
            st.info("💡 建議：金鑰無效。請確認您是從 Google AI Studio 複製的，且沒有多複製到空格。")
        elif "404" in str(e):
            st.info("💡 建議：找不到模型。這通常發生在金鑰權限尚未生效，請等 2 分鐘再試。")
