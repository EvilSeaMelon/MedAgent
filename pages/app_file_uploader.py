"""
基于 Streamlit 的知识库入库页面
"""
import streamlit as st
import requests

st.title("知识库文档入库")
st.caption("上传 TXT/PDF 文档后，将文件传输到后端服务器并写入向量库。")

# 注意：这里彻底删除了 VectorStoreService 和 config 的导入

BACKEND_UPLOAD_URL = "http://127.0.0.1:8000/api/knowledge/upload"

# 替代原来的 chroma_conf["allow_knowledge_file_type"]
upload_file = st.file_uploader(
    "选择要入库的文档",
    type=["txt", "pdf", "md", "csv"],
    accept_multiple_files=False,
)

# 前端不再控制同名覆盖逻辑，仅保留 UI
overwrite = st.checkbox("同名文件覆盖", value=True)

if upload_file is not None:
    file_name = upload_file.name

    st.write(f"目标文件：`{file_name}`")
    st.write(f"文件大小：{upload_file.size / 1024:.2f} KB")

    if st.button("写入知识库", type="primary"):
        with st.spinner("正在将文件上传至后端并写入向量库..."):
            try:
                # 利用 requests 发送 multipart/form-data 格式的文件
                files = {"file": (file_name, upload_file.getvalue(), upload_file.type)}
                response = requests.post(BACKEND_UPLOAD_URL, files=files)

                if response.status_code == 200:
                    st.success("入库完成。可返回聊天页面进行测试。")
                else:
                    st.error(f"后端处理失败，状态码：{response.status_code}")
            except Exception as e:
                st.error(f"无法连接到后端服务器，请确认 main.py 已启动。报错详情：{e}")