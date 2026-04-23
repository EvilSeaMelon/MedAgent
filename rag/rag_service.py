
"""
总结服务类：用用户提问向向量库检索参考资料，将提问和参考资料生成prompt提交给模型，让模型总结回复

逻辑：用提问向知识库检索数据 -> 将数据转成str -> 传给chain让llm模型总结并返回结果
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompt


class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    # chain：提示词模板 -> 模型 -> 输出
    def _init_chain(self):
        chain = self.prompt_template | self.model | StrOutputParser()
        return chain

    # 输入提问，返回检索的文档数据[Document, Document,...]
    def retriever_docs(self, query: str):
        return self.retriever.invoke(query)

    def rag_summarize(self, query: str) -> str:
        """
        主要获取检索数据，遍历生成str，传给chain
        """

        context_docs = self.retriever_docs(query)

        context = ""
        counter = 0
        for doc in context_docs:
            counter += 1
            context += f"【参考资料{counter}】: 参考资料：{doc.page_content} | 参考元数据：{doc.metadata}\n"

        # 将提问和检索到的资料传入chain并返回结果
        return self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )

if __name__ == '__main__':
    rag = RagSummarizeService()
    res = rag.rag_summarize("胃溃疡患者在饮食上需要注意什么？")
    print(res)