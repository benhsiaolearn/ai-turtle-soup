import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted  # 新增：引入特定的錯誤類型

# --- 1. 設定基本環境 ---
load_dotenv()
st.set_page_config(page_title="AI 海龜湯 v1.2", page_icon="🐢", layout="wide")

# 設定 AI 模型
# 使用 gemini-1.5-flash 以獲得更快的速度和更高的免費額度限制
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- 2. 初始化遊戲狀態 ---
if "puzzle" not in st.session_state:
    st.session_state.puzzle = ""
    st.session_state.truth = ""
    st.session_state.history = []
    st.session_state.hint_count = 0

# --- 3. 定義核心功能 ---
def start_new_game(difficulty):
    """向 AI 請求一個新題目，根據難度調整"""
    st.session_state.hint_count = 0 # 重置提示次數
    
    prompt = f"""
    請出一個『{difficulty}』程度的海龜湯題目。
    
    如果是『簡單』：故事線索要明顯，邏輯不要太跳躍。
    如果是『困難』：可以包含敘述性詭計或超現實元素。
    
    請嚴格依照以下格式回傳：
    題目：[這裡寫題目故事]
    ===
    真相：[這裡寫故事的真相]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        if "===" in text:
            parts = text.split("===")
            st.session_state.puzzle = parts[0].replace("題目：", "").strip()
            st.session_state.truth = parts[1].replace("真相：", "").strip()
            st.session_state.history = []
        else:
            st.error("AI 產生的格式有點問題，請再試一次。")
            
    except ResourceExhausted:
        st.error("🐢 系統繁忙（流量管制中），請等待 30 秒後再試一次！")
    except Exception as e:
        st.error(f"發生未知錯誤：{e}")

def ask_ai(question):
    """判斷玩家的問題"""
    judge_prompt = f"""
    你是海龜湯的裁判。
    【題目】：{st.session_state.puzzle}
    【真相】：{st.session_state.truth}
    【玩家問題】：{question}
    
    請只回答以下其中一個詞，不要解釋：
    - 是
    - 否
    - 與此無關
    - 恭喜猜對 (只有當玩家完全說中核心手法或動機時才用這個)
    """
    try:
        response = model.generate_content(judge_prompt)
        return response.text.strip()
    except ResourceExhausted:
        return "🐢 海龜累了，請休息 10 秒後再問！(流量管制)"
    except Exception as e:
        return f"發生錯誤：{str(e)}"

def get_hint():
    """請求 AI 給一個提示"""
    hint_prompt = f"""
    玩家目前卡關了。
    【題目】：{st.session_state.puzzle}
    【真相】：{st.session_state.truth}
    
    請給一個「微小的提示」，引導玩家思考正確的方向，但絕對不要直接說出答案關鍵字。
    提示請控制在 20 字以內。
    """
    try:
        response = model.generate_content(hint_prompt)
        return response.text.strip()
    except ResourceExhausted:
        return "🐢 提示系統冷卻中，請稍後再試。"
    except Exception as e:
        return f"發生錯誤：{str(e)}"

# --- 4. 側邊欄：控制區 ---
with st.sidebar:
    st.title("🐢 遊戲控制")
    
    # 難度選擇
    difficulty = st.selectbox("選擇難度", ["簡單 (適合新手)", "普通 (燒腦)", "困難 (變態)"])
    
    if st.button("🆕 開始新的一碗湯", use_container_width=True):
        with st.spinner("正在熬湯中..."):
            start_new_game(difficulty)
    
    st.divider()
    
    # 提示功能
    if st.session_state.puzzle:
        st.write(f"💡 已使用提示：{st.session_state.hint_count} 次")
        if st.button("🆘 給我一點提示", use_container_width=True):
            with st.spinner("裁判正在想提示..."):
                hint = get_hint()
                # 如果回傳的是錯誤訊息，就不計次數，也不加入歷史紀錄
                if "🐢" in hint or "錯誤" in hint:
                    st.warning(hint)
                else:
                    st.session_state.history.append(("(玩家請求提示)", f"💡 提示：{hint}"))
                    st.session_state.hint_count += 1
                    st.rerun() # 重新整理頁面以顯示提示

    st.divider()
    with st.expander("🕵️ 偷看湯底 (真相)"):
        if st.session_state.truth:
            st.write(st.session_state.truth)
        else:
            st.write("還沒開始遊戲喔！")

# --- 5. 主畫面：遊戲進行區 ---
st.title("🐢 AI 海龜湯")

if st.session_state.puzzle:
    # 顯示題目 (用不同顏色框起來)
    st.info(f"📜 **題目**：\n\n{st.session_state.puzzle}")

    # 顯示對話紀錄區域
    chat_container = st.container()
    with chat_container:
        for q, a in st.session_state.history:
            if "(玩家請求提示)" in q:
                st.warning(a) # 提示用黃色顯示
            else:
                with st.chat_message("user"):
                    st.write(q)
                with st.chat_message("assistant"):
                    if "恭喜" in a:
                        st.success(a)
                    elif "是" in a:
                        st.write(f"⭕ {a}")
                    elif "否" in a:
                        st.write(f"❌ {a}")
                    else:
                        st.write(a)

    # 玩家輸入區
    if prompt := st.chat_input("請輸入你的 Yes/No 問題..."):
        # 顯示並處理
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                answer = ask_ai(prompt)
                if "恭喜" in answer:
                    st.balloons()
                    st.success(answer)
                elif "是" in answer:
                    st.write(f"⭕ {answer}")
                elif "否" in answer:
                    st.write(f"❌ {answer}")
                else:
                    st.write(answer)
        
        st.session_state.history.append((prompt, answer))

else:
    st.write("👈 請在左側選擇難度，然後點擊「開始」！")



