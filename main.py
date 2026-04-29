import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
# 引入流式响应组件
from fastapi.responses import StreamingResponse

# 引入数据契约
from schemas.payload import ChatRequest
# 引入智能体大脑
from agent.react_agent import ReactAgent

# 1. 初始化 FastAPI 引擎
app = FastAPI(
    title="MedAgent 医疗健康助手",
    description="后端服务架构",
    version="1.0.0"
)

# 2. 挂载 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🌟 全局单例模式 (回归最稳的原生写法)
# ==========================================
# 在服务器启动时，只实例化一次大脑，常驻内存
print("⏳ 正在初始化核心大模型引擎...")
global_agent = ReactAgent()
print("✅ 引擎加载完毕！")

def get_shared_agent():
    """依赖注入函数：确保每个请求都共用上面那个全局大脑"""
    return global_agent


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Aegis-Med Backend is running!"}


@app.post("/api/chat")
async def chat_endpoint(
        request: ChatRequest,
        agent: ReactAgent = Depends(get_shared_agent)
):
    """接收对话请求，等待思考完毕后返回完整 JSON"""
    print(f"📥 接收到普通请求 -> Session: {request.session_id} | Query: {request.query}")

    # 调用刚才改好的 execute 同步方法
    answer = agent.execute(query=request.query, session_id=request.session_id)

    # 将完整的答案打包成标准 JSON 返回
    return {
        "code": 200,
        "message": "success",
        "data": {
            "answer": answer
        }
    }


# 5. 清理记忆接口
@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    agent: ReactAgent = Depends(get_shared_agent)
):
    try:
        agent.clear_memory(session_id=session_id)
        return {"code": 200, "message": "记忆清除成功"}
    except Exception as e:
        return {"code": 500, "message": f"记忆清除失败: {str(e)}"}


if __name__ == "__main__":
    # 使用 reload=True 方便你在修改代码后自动重启
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)