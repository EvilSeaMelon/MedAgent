import os
from langchain_chroma import Chroma
from langchain_classic.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from model.factory import embed_model
from utils.config_handler import chroma_conf
from utils.file_handler import txt_loader, pdf_loader, listdir_with_allowed_type, get_file_md5
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
"""
核心知识检索引擎 (VectorStoreService)
职责：负责企业级医疗知识文档的预处理、防重缓存、语义切分以及高精度检索。

【核心组件配置】
4个核心属性：
    1. vector_store (Chroma)  : 持久化稠密向量库（负责语义泛化海选）。
    2. spliter                : 智能语义切分器（基于 Embedding 相似度断崖，替代传统机械切分）。
    3. bm25_retriever         : 内存级稀疏向量索引（负责关键词精准字面匹配）。
    4. cross_encoder/compressor: HuggingFace BGE 交叉编码器（负责终极精排降噪）。

【数据摄入流水线 (存)】
核心入口：load_document()
内部微服务：check_md5(), save_md5(), get_file_content()
执行逻辑：
    1. 扫描 -> 获取 data 目录下所有合规文件的绝对路径。
    2. 校验 -> 计算文件 MD5 并比对底层缓存，命中则极速跳过防穿透。
    3. 解析 -> 读取文档并触发 Semantic Chunker 进行智能语义分块。
    4. 落库 -> 将格式化的 [Document(...)] 存入 Chroma 数据库并固化 MD5。
    5. 重载 -> 若有新数据入库，触发 reload_memory() 刷新 BM25 内存索引。

【混合检索流水线 (取)】
核心入口：get_retriever()
执行逻辑：
    1. 海选 -> EnsembleRetriever 并发调度 BM25 与 Chroma，进行双路联合召回。
    2. 精排 -> 将海选结果送入 ContextualCompressionRetriever，由 BGE 模型进行严苛打分并截取 Top-K 核心片段。
"""

class VectorStoreService:

    def __init__(self):
        # 1. 持久化向量库 (Chroma)
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=get_abs_path(chroma_conf["persist_directory"]),
        )

        # 2. 【核心增强：语义切分器】按语义断崖分块，保证上下文完整
        self.spliter = SemanticChunker(embed_model, breakpoint_threshold_type="percentile")

        # 3. 【核心增强：BM25内存索引】
        self.bm25_retriever = self._init_bm25()

        # 4. 【核心增强：BGE重排法官】
        # 将 1.2GB 模型缓存在本地 hf_cache，避免重启重复下载
        os.environ["HF_HOME"] = get_abs_path("hf_cache")
        # 【新增代码】：设置 HuggingFace 为全局离线模式，跳过网络连接检查
        os.environ["HF_HUB_OFFLINE"] = "1"
        self.cross_encoder = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.cross_encoder, top_n=chroma_conf.get("k", 3))

    def _init_bm25(self):
        """从 Chroma 提取所有已有文档，构建 BM25 稀疏索引"""
        try:
            docs = self.vector_store.get()
            if not docs or not docs.get('documents'):
                return None

            documents = [Document(page_content=text, metadata=meta) for text, meta in
                         zip(docs['documents'], docs['metadatas'])]
            bm25 = BM25Retriever.from_documents(documents)
            bm25.k = chroma_conf.get("k", 3)
            return bm25
        except Exception as e:
            logger.error(f"[BM25初始化] 失败，可能库为空: {e}")
            return None

    def reload_memory(self):
        """热重载机制：新数据入库后刷新 BM25"""
        self.bm25_retriever = self._init_bm25()
        logger.info("[VectorStore] 混合检索 BM25 内存索引已完成热重载")


    # 检索器：检索向量库返回对应知识文档,返回[Document, Document,...]
    def get_retriever(self):
        """返回组装好的【双路召回 + BGE交叉重排】终极检索器"""
        vector_retriever = self.vector_store.as_retriever(search_kwargs={"k": chroma_conf.get("k", 3)})

        # 如果库里什么都没有，或者 BM25 没初始化成功，兜底使用单路向量+重排
        if not self.bm25_retriever:
            return ContextualCompressionRetriever(base_compressor=self.compressor, base_retriever=vector_retriever)

        # 构建双路海选 (字面匹配 50% + 语义泛化 50%)
        ensemble_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )

        # 套上 BGE 终极重排外壳
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=ensemble_retriever
        )
        return compression_retriever

    # 存数据到向量库
    def load_document(self):
        """
        从data文件夹内读取数据文件，转为向量存入向量库
        要计算文件的MD5做去重
        :return: None
        """

        def check_md5(md5: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                # if进入表示文件不存在，创建md5.txt
                open(get_abs_path(chroma_conf["md5_hex_store"]), 'w', encoding='utf-8').close()
                return False
            else:
                for line in open(get_abs_path(chroma_conf["md5_hex_store"]), 'r', encoding='utf-8').readlines():
                    line = line.strip()  # 处理字符串前后的空格和回车
                    if line == md5:
                        return True  # 已处理过

                return False

        def save_md5(md5):
            """将传入的md5字符串，记录到文件内保存"""
            with open(get_abs_path(chroma_conf["md5_hex_store"]), 'a', encoding="utf-8") as f:
                f.write(md5 + '\n')

        # 读取文件内容 -> [Document(metadata={...}, page_content="...")]
        def get_file_content(read_path: str) -> list[Document]:
            if read_path.endswith("txt"):
                return txt_loader(read_path)

            if read_path.endswith("pdf"):
                return pdf_loader(read_path)

            return []


        """函数main"""

        # 获取所有允许类型文件的绝对路径列表
        allowed_files_path = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        need_reload = False  # 标记是否需要热重载

        for path in allowed_files_path:
            md5 = get_file_md5(path)
            if check_md5(md5):
                logger.info(f"[加载知识库] {path} 已经存在知识库内，跳过")
                continue

            try:
                documents: list[Document] = get_file_content(path)
                if not documents:
                    continue

                # 使用语义切分器切分
                split_document: list[Document] = self.spliter.split_documents(documents)
                if not split_document:
                    continue

                self.vector_store.add_documents(split_document)

                save_md5(md5)

                logger.info(f"[加载知识库] {path} 内容加载成功")
                need_reload = True
            except Exception as e:
                logger.error(f"[加载知识库] {path}加载失败：{str(e)}", exc_info=True)
                continue

        # 如果有新文档入库，触发一次热重载，同步更新 BM25 内存索引
        if need_reload:
            self.reload_memory()




if __name__ == '__main__':
    vs = VectorStoreService()
    vs.load_document()
    retriever = vs.get_retriever()

    res = retriever.invoke("高血压")
    for r in res:
        print(r.page_content)
        print("-" * 20)



