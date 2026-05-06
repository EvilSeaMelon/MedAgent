import streamlit as st
import requests
import time

st.set_page_config(page_title="MedAgent 医疗健康助手", page_icon="⚕️")
st.title("MedAgent 医疗健康助手")
st.caption("稳定版")
st.divider()

BACKEND_URL = "http://127.0.0.1:8000/api/chat"

with st.sidebar:
    st.header("助手控制台")
    if st.button("清空历史对话", use_container_width=True):
        delete_url = "http://127.0.0.1:8000/api/chat/history/P1001"
        try:
            res = requests.delete(delete_url)
            if res.status_code == 200:
                st.session_state["message"] = [{"role": "assistant", "content": "记忆已成功清空！"}]
                st.rerun()
        except requests.exceptions.ConnectionError:
            st.error("无法连接到后端服务器！")

if "message" not in st.session_state:
    st.session_state["message"] = [{"role": "assistant", "content": "干嘛"}]

for msg in st.session_state["message"]:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("请输入问题..."):
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("正在检索医学知识并深度思考..."):
            try:
                # 先一次性把完整答案拿过来
                response = requests.post(
                    BACKEND_URL,
                    json={"query": prompt, "session_id": "P1001"}
                )

                if response.status_code == 200:
                    data = response.json()
                    full_response = data["data"]["answer"]


                    # 前端生成器，制造打字机流式效果
                    def stream_data(text):
                        for char in text:
                            time.sleep(0.015)  # 调节这个数字可以改变打字速度 (0.015 秒一个字)
                            yield char


                    # 2. st.write_stream 会接收生成器
                    st.write_stream(stream_data(full_response))

                    # 3. 保存进记忆
                    st.session_state["message"].append({"role": "assistant", "content": full_response})
                else:
                    st.error(f"后端返回错误状态码: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("无法连接到后端服务器！请确保 FastAPI 后端正在运行！")