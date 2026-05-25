"""
Streamlit page for knowledge-file upload.
"""
import requests
import streamlit as st

st.title("知识库文档入库")
st.caption("上传 TXT/PDF 文档后，发送到后端并写入向量库。")

BACKEND_UPLOAD_URL = "http://127.0.0.1:8000/api/knowledge/upload"

upload_file = st.file_uploader(
    "选择要入库的文档",
    type=["txt", "pdf"],
    accept_multiple_files=False,
)

overwrite = st.checkbox("同名文件覆盖", value=True)

if upload_file is not None:
    file_name = upload_file.name

    st.write(f"目标文件：`{file_name}`")
    st.write(f"文件大小：{upload_file.size / 1024:.2f} KB")

    if st.button("写入知识库", type="primary"):
        with st.spinner("正在上传并写入向量库..."):
            try:
                files = {"file": (file_name, upload_file.getvalue(), upload_file.type)}
                data = {"overwrite": str(overwrite).lower()}
                response = requests.post(
                    BACKEND_UPLOAD_URL,
                    files=files,
                    data=data,
                    timeout=180,
                )
                payload = response.json()

                if response.status_code == 200 and payload.get("code") == 200:
                    st.success("入库完成，可以返回聊天页面测试。")
                else:
                    st.error(f"后端处理失败：{payload.get('message', response.text)}")
            except Exception as e:
                st.error(f"无法连接后端服务，请确认 main.py 已启动。错误：{e}")
