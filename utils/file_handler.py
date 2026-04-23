import hashlib
import os

from langchain_core.documents import Document

from utils.logger_handler import logger
from langchain_community.document_loaders import PyPDFLoader, TextLoader

# 获取指定路径的文件的md5值
def get_file_md5(file_path: str):

    # 文件不存在
    if not os.path.exists(file_path):
        logger.error(f"[MD5计算]文件{file_path}不存在")
        return None

    # 路径不是文件
    if not os.path.isfile(file_path):
        logger.error(f"[MD5计算]路径{file_path}不是文件")
        return None

    md5_obj = hashlib.md5()

    chunk_size = 4096       #4KB分片
    # 遍历文件并不断更新md5_obj的data，最后再生成md5
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
            while chunk:
                md5_obj.update(chunk)
                chunk = f.read(chunk_size)

            md5 = md5_obj.hexdigest()
            return md5

    except Exception as e:
        logger.error(f"[MD5计算]计算文件{file_path}md5失败，{str(e)}")
        return None

# 返回文件夹中文件（允许的）绝对路径列表,
def listdir_with_allowed_type(path: str, allowed_types: tuple[str]):

    if not os.path.isdir(path):
        logger.error(f"[授权文件的列表]{path}不是文件夹路径")
        return ()

    files_path_list = []
    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files_path_list.append(os.path.join(path, f))

    return tuple(files_path_list)

#加载pdf,返回一个列表包着一个document：[Document(metadata={...}, page_content="...")]
def pdf_loader(filepath: str, password: str = None) -> list[Document]:
    return PyPDFLoader(filepath, password).load()

# 加载txt,返回一个列表包着一个document
def txt_loader(filepath: str) -> list[Document]:
    return TextLoader(filepath, encoding="utf-8").load()


if __name__ == '__main__':

    res = pdf_loader(r"D:\wqxproject\Agent_Project\data\扫地机器人100问.pdf")
    print(res)