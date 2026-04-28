
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """前端向后端发送聊天请求的数据结构"""
    query: str = Field(..., description="用户输入的医疗问题", examples=["患者P1001的诊断结果是什么？"])
    session_id: str = Field(default="default.json", description="用于隔离不同用户记忆的标识")

class ChatResponse(BaseModel):
    """标准的非流式返回结构（备用）"""
    code: int = 200
    message: str = "success"
    data: dict = {}