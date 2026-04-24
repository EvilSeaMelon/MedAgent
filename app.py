import time

import streamlit as st
from agent.react_agent import ReactAgent

# 标题
st.title("MedAgent 医疗健康助手")
st.divider()

# 👇 新增：在左侧边栏放置清空按钮
with st.sidebar:
    st.header("⚙️ 助手控制台")
    if st.button("🗑️ 清空历史对话", use_container_width=True):
        # 1. 擦除数据库里的长时记忆
        if "agent" in st.session_state:
            st.session_state["agent"].clear_memory()

        # 2. 擦除网页 UI 的显示记忆，并恢复默认的欢迎语
        st.session_state["message"] = [
            {"role": "assistant", "content": "记忆已成功清空！"}]

        # 3. 强制刷新页面，让清空效果立刻生效
        st.rerun()


if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

if "message" not in st.session_state:
    st.session_state["message"] = [{"role": "assistant", "content": "干嘛？"}]

for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

# 用户输入提示词
prompt = st.chat_input()

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    response_messages = []
    with st.spinner("智能客服思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)

        def capture(generator, cache_list):

            for chunk in generator:
                cache_list.append(chunk)

                for char in chunk:
                    time.sleep(0.01)
                    yield char

        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))
        assistant_text = "".join(response_messages)
        st.session_state["message"].append({"role": "assistant", "content": assistant_text})
        st.rerun()
