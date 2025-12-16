import streamlit as st
import google.generativeai as genai
import os
import tempfile
import time

# Configure page settings
st.set_page_config(
    page_title="寶貝照顧日誌 AI 助理",
    page_icon="👶",
    layout="wide"
)

# --- 黃金標準：雙重保險讀取法 ---
def get_api_key():
    # 1. 第一順位：優先檢查 Streamlit Cloud 的 Secrets (雲端部署用)
    #    或是你專案資料夾裡 .streamlit/secrets.toml 有沒有寫
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    
    # 2. 第二順位：如果上面沒有，就檢查電腦的環境變數 (本機開發用)
    #    這樣你就不用每個專案都貼 secrets.toml 了！
    env_key = os.getenv("GOOGLE_API_KEY")
    if env_key:
        return env_key
        
    return None

# --- API Configuration ---
def configure_api():
    try:
        api_key = get_api_key()

        if not api_key:
            st.error("🚨 找不到 API Key！請檢查 secrets.toml 或 系統環境變數。")
            st.info("請確認是否已設定 `GOOGLE_API_KEY`。")
            return False

        if api_key == "YOUR_API_KEY_HERE":
            st.error("⚠️ 請設定您的 Google API Key")
            st.info("請開啟專案資料夾中的 `.streamlit/secrets.toml` 檔案，並將 `YOUR_API_KEY_HERE` 替換為您真實的 API Key。")
            return False
            
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"API 設定錯誤: {str(e)}")
        return False

# --- System Prompt ---
SYSTEM_PROMPT = """
角色設定：你是一位結合「工程師邏輯」與「幼保專業」的超級奶爸助理，負責整理育兒日誌。
任務目標：請分析錄音檔，分辨「爸爸」與「媽媽」的發言，產出兩部分內容。

第一部分：【寶寶照顧日誌：逐字稿】
請務必遵守以下格式規則，嚴禁將多句話合併：
1. 必須將對話「逐句拆解」，每一句發言都要有獨立的一行。
2. 嚴格使用 Markdown 表格格式輸出，欄位包含：`| 時間 | 講者 | 內容 |`。
3. 時間格式必須為 `[MM:SS]` (例如 [04:33])。
4. 講者請自動判斷是「爸爸」或「媽媽」。
5. 內容需為繁體中文，保留語氣但過濾無意義贅字。
範例格式： | 時間 | 講者 | 內容 | |---|---|---| | [04:33] | 爸爸 | 喝完之後就今天一整天都沒有大便... | | [04:52] | 爸爸 | 因為沒辦法大便，所以就帶上來睡覺... | | [05:26] | 媽媽 | 小虎牙要補充的嗎? |

第二部分：【寶寶照顧日誌：會議記錄整理】
* 標題格式：寶寶照顧日誌：會議記錄整理 (YYYY/MM/DD，寶寶出生第XXX天)
* 紀錄者：爸爸
* 內容規則：請**直接**輸出以下五大項標題與內容，**嚴禁**在標題上方或下方重複撰寫額外的摘要或總結段落。
本日事件紀錄

關鍵照顧細節：(體重、餵食量、排泄狀況、睡眠時間 - 請列點)

關鍵互動事件：(發展里程碑、情緒反應 - 請列點)

突發狀況：(生病、受傷等 - 若無則寫「無」)

個人反思與工程師視角

情緒：(焦慮、挫折、喜悅等)

SOP 檢核：(嘗試了什麼方法？成功或失敗？原因？)

幼保學習：(結合幼保理論的觀察與體悟)

伴侶互動與性別協商

分工：(誰做了什麼)

協商：(意見不合或討論過程)

支持：(具體的支持行為)

外部互動與社會眼光

親友互動

社會觀感

影像筆記備註

(若無則填寫「本日無特別影像紀錄」)
"""

# --- Main App Logic ---
def main():
    st.title("👶 寶貝照顧日誌 AI 助理")
    st.markdown("上傳錄音檔，自動生成逐字稿與專業育兒日誌分析。")

    if not configure_api():
        st.stop()

    uploaded_file = st.file_uploader("請上傳錄音檔 (支援 mp3, wav, m4a, ogg, aac)", type=["mp3", "wav", "m4a", "ogg", "aac"])

    if uploaded_file is not None:
        st.audio(uploaded_file, format="audio/mp3")
        
        if st.button("開始分析", type="primary"):
            with st.spinner("正在處理錄音檔... (上傳 -> 分析 -> 生成報告)"):
                try:
                    # 1. Save uploaded file to temp
                    file_ext = os.path.splitext(uploaded_file.name)[1]
                    if not file_ext:
                        file_ext = ".mp3" # Default fallback
                        
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name

                    # 2. Upload to Gemini
                    st.text("正在上傳至 Gemini...")
                    myfile = genai.upload_file(tmp_file_path)
                    
                    # 3. Wait for processing
                    while myfile.state.name == "PROCESSING":
                        time.sleep(2)
                        myfile = genai.get_file(myfile.name)
                    
                    if myfile.state.name == "FAILED":
                        st.error("Gemini 檔案處理失敗。")
                        return

                    # 4. Generate Content
                    st.text("正在進行 AI 分析...")
                    
                    # Candidate models in user-preferred order
                    # Note: 2.0-flash-exp added as invisible safety net if user's exact names fail
                    CANDIDATE_MODELS = [
                        'gemini-2.5-flash',
                        'gemini-2.0-flash',
                        'gemini-flash-latest',
                        'gemini-2.0-flash-exp' # Fallback for safety
                    ]
                    
                    # Configure safety settings to avoid PROHIBITED_CONTENT blocks on harmless data
                    safety_settings = [
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_NONE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_NONE"
                        },
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "threshold": "BLOCK_NONE"
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "threshold": "BLOCK_NONE"
                        },
                    ]
                    
                    response = None
                    
                    for model_name in CANDIDATE_MODELS:
                        st.text(f"正在嘗試模型：{model_name}...")
                        model = genai.GenerativeModel(model_name)
                        
                        retry_count = 0
                        max_retries = 3
                        success = False
                        
                        while retry_count < max_retries:
                            try:
                                # Add safety_settings
                                response = model.generate_content(
                                    [myfile, SYSTEM_PROMPT],
                                    safety_settings=safety_settings
                                )
                                
                                # Validate response has content immediately
                                if not response.parts:
                                     raise ValueError(f"AI 回傳內容為空 (可能被安全機制阻擋)，原因: {response.prompt_feedback}")
                                     
                                # Try accessing text to ensure it's valid
                                _ = response.text 
                                
                                success = True
                                break # Success inner loop
                            except Exception as e:
                                err_str = str(e)
                                if "429" in err_str or "Quota exceeded" in err_str:
                                    retry_count += 1
                                    wait_time = 2 ** retry_count + 3
                                    st.warning(f"模型 {model_name} 用量達上限 (429)，{wait_time}秒後重試 ({retry_count}/{max_retries})...")
                                    time.sleep(wait_time)
                                elif "404" in err_str or "not found" in err_str.lower():
                                    st.warning(f"模型 {model_name} 未找到或無權限，嘗試下一個...")
                                    break # Break inner retry loop, go to next model
                                else:
                                    st.error(f"模型 {model_name} 發生錯誤: {err_str}")
                                    # If it's a safety block (ValueError we raised or API error), maybe try next model?
                                    break # Break inner loop, try next model
                        
                        if success:
                            st.success(f"成功使用模型：{model_name}")
                            break # Break outer model loop
                    
                    if response is None or not success:
                        st.error("錯誤：所有模型嘗試皆失敗，請稍後再試或檢查 API Key 權限與檔案內容。")
                        return
                    
                    # 5. Display Results
                    result_text = response.text
                    
                    # Display Results (Sequential)
                    part1_marker = "【寶寶照顧日誌：逐字稿】"
                    part2_marker = "【寶寶照顧日誌：會議記錄整理】"
                    
                    content_transcript = ""
                    content_minutes = ""

                    # Improved splitting logic
                    if part1_marker in result_text and part2_marker in result_text:
                        p1_index = result_text.find(part1_marker)
                        p2_index = result_text.find(part2_marker)
                        
                        if p1_index < p2_index:
                            # Part 1 then Part 2
                            # Part 1 content is from p1 until p2 (excluding p2 header)
                            content_transcript = result_text[p1_index:p2_index].strip()
                            # Part 2 content is from p2 to end
                            content_minutes = result_text[p2_index:].strip()
                        else:
                            # Part 2 then Part 1
                            content_minutes = result_text[p2_index:p1_index].strip()
                            content_transcript = result_text[p1_index:].strip()
                    elif part1_marker in result_text:
                         content_transcript = result_text
                         content_minutes = "⚠️ 未能生成會議記錄部分"
                    elif part2_marker in result_text:
                         content_minutes = result_text
                         content_transcript = "⚠️ 未能生成逐字稿部分"
                    else:
                        # Fallback
                        content_minutes = result_text
                        content_transcript = result_text

                    st.subheader("📝 會議記錄分析")
                    st.markdown(content_minutes)
                    
                    st.divider()
                    
                    st.subheader("🗣️ 詳細逐字稿")
                    st.markdown(content_transcript)

                    # 6. Download Button
                    original_filename = os.path.splitext(uploaded_file.name)[0]
                    download_filename = f"{original_filename}-逐字稿.txt"
                    
                    st.download_button(
                        label="下載完整分析報告 (.txt)",
                        data=result_text,
                        file_name=download_filename,
                        mime="text/plain"
                    )

                    # 7. Cleanup
                    genai.delete_file(myfile.name)
                    os.unlink(tmp_file_path)

                except Exception as e:
                    st.error(f"發生錯誤: {str(e)}")
                    # Cleanup temp file if it exists
                    if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)

if __name__ == "__main__":
    main()
