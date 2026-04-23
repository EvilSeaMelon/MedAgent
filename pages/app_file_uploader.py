"""
基于 Streamlit 的知识库入库页面。
"""
import os
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from rag.vector_store import VectorStoreService
from utils.config_handler import chroma_conf
from utils.path_tool import get_abs_path

st.title("知识库文档入库")
st.caption("上传 TXT/PDF 文档后，将文件保存到 data 目录并写入向量库。")

if "service" not in st.session_state:
    st.session_state["service"] = VectorStoreService()

data_dir = get_abs_path(chroma_conf["data_path"])
os.makedirs(data_dir, exist_ok=True)

upload_file = st.file_uploader(
    "选择要入库的文档",
    type=chroma_conf["allow_knowledge_file_type"],
    accept_multiple_files=False,
)
overwrite = st.checkbox("同名文件覆盖", value=True)

if upload_file is not None:
    file_name = upload_file.name
    target_path = os.path.join(data_dir, file_name)

    st.write(f"目标路径：`{target_path}`")
    st.write(f"文件大小：{upload_file.size / 1024:.2f} KB")

    can_save = overwrite or (not os.path.exists(target_path))
    if not can_save:
        st.warning("同名文件已存在，请勾选“同名文件覆盖”后重试。")

    if st.button("写入知识库", type="primary", disabled=not can_save):
        with st.spinner("正在保存文件并写入向量库..."):
            with open(target_path, "wb") as f:
                f.write(upload_file.getbuffer())

            st.session_state["service"].load_document()

        st.success("入库完成。可返回聊天页面进行测试。")






