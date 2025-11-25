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

# --- API Configuration ---
def configure_api():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        if api_key == "YOUR_API_KEY_HERE":
            st.error("⚠️ 請設定您的 Google API Key")
            st.info("請開啟專案資料夾中的 `.streamlit/secrets.toml` 檔案，並將 `YOUR_API_KEY_HERE` 替換為您真實的 API Key。")
            st.code('GOOGLE_API_KEY = "您的_API_KEY"', language="toml")
            return False
        genai.configure(api_key=api_key)
        return True
    except FileNotFoundError:
        st.error("⚠️ 未找到設定檔")
        st.info("請確認 `.streamlit/secrets.toml` 檔案是否存在。")
        return False
    except KeyError:
        st.error("⚠️ 設定檔缺少金鑰")
        st.info("請在 `.streamlit/secrets.toml` 中設定 `GOOGLE_API_KEY`。")
        return False
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
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
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
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    response = model.generate_content([myfile, SYSTEM_PROMPT])
                    
                    # 5. Display Results
                    result_text = response.text
                    
                    # Display Results (Sequential)
                    # Simple heuristic split (can be improved)
                    part1_marker = "【寶寶照顧日誌：逐字稿】"
                    part2_marker = "【寶寶照顧日誌：會議記錄整理】"
                    
                    content_transcript = ""
                    content_minutes = ""

                    if part1_marker in result_text and part2_marker in result_text:
                        parts = result_text.split(part2_marker)
                        if len(parts) > 1:
                            # Part 1 is usually first based on prompt order
                            if result_text.index(part1_marker) < result_text.index(part2_marker):
                                content_transcript = parts[0]
                                content_minutes = part2_marker + parts[1]
                            else:
                                content_minutes = parts[0]
                                content_transcript = part1_marker + parts[1]
                    else:
                        # Fallback if markers are missing or different
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
