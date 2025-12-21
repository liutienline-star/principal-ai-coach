import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(page_title="雲端連線實驗室")

st.title("🧪 雲端試算表連線測試")

# 1. 顯示目前的連線資訊 (不顯示私鑰以保安全)
st.write("正在嘗試連線至試算表：`Education_Exam_Records`")

# 2. 核心連線函式
def test_connection():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 檢查 Secrets 是否存在
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets 中找不到 [gcp_service_account] 區塊")
            return
        
        # 嘗試讀取憑證
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        # 嘗試開啟試算表
        sheet = client.open("Education_Exam_Records").sheet1
        
        st.success("✅ 恭喜！連線成功！")
        
        # 試著讀取現有資料
        data = sheet.get_all_records()
        if data:
            st.write("目前雲端資料庫內容：")
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("連線成功，但目前試算表是空的。")
            
    except Exception as e:
        st.error(f"❌ 連線失敗。錯誤訊息如下：")
        st.code(str(e))
        
        # 針對常見錯誤給予白話建議
        error_msg = str(e)
        if "SpreadsheetNotFound" in error_msg:
            st.warning("💡 建議：請檢查試算表名稱是否完全符合 `Education_Exam_Records`，且已「共用」給服務帳號 Email。")
        elif "JSONDecodeError" in error_msg or "ValueError" in error_msg:
            st.warning("💡 建議：Secrets 的 TOML 格式可能有誤（例如引號、換行符號 \n 或使用了大括號）。")

if st.button("🚀 開始測試連線"):
    test_connection()
