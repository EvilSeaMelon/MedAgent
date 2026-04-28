
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 引入刚刚写好的数据契约
from schemas.payload import ChatRequest

# 1. 初始化 FastAPI 引擎
app = FastAPI(
    title="MedAgent 医疗健康助手",
    description="后端服务架构",
    version="1.0.0"
)

# 2. 挂载 CORS 中间件 (极其重要！)
# 因为未来你的 Streamlit 跑在 8501 端口，FastAPI 跑在 8000 端口，
# 端口不同属于“跨域”，不加这个配置，前端请求会被浏览器直接拦截。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有前端访问，上线后改成你前端的真实域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. 基础健康检查接口
@app.get("/health")
async def health_check():
    """用于服务器监控，检查服务是否存活"""
    return {"status": "ok", "service": "Aegis-Med Backend is running!"}


# 4. 核心对话接口的“骨架”（暂时不接大模型，先测试通路）
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """接收对话请求的入口"""
    print(f"接收到前端请求 -> Session: {request.session_id} | Query: {request.query}")

    # 这里是下一阶段我们要把 react_agent.py 塞进去的地方
    return {
        "code": 200,
        "message": "请求已成功被后端拦截器接收",
        "data": {"your_query": request.query}
    }


if __name__ == "__main__":
    # 使用 Uvicorn 启动异步服务器
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)