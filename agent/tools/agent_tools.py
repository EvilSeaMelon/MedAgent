import asyncio
import os
import sys
import threading
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService

rag = RagSummarizeService()

external_data = {}

# 工具 1：知识库问答
@tool(description="当用户询问具体的疾病症状、用药禁忌等医学知识时，必须调用此工具检索本地权威医学知识库")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)

# 工具 2：患者既往病历查询 做成mcp了

# 工具 3：触发报告生成流程
@tool(description="当用户明确要求【生成健康报告】、【出具评估档案】时，必须调用此工具来开启报告生成流程")
def fill_context_for_report() -> str:
    """
    这个工具本身不做任何事，只作为一个信号弹。
    middleware 会拦截它的调用，并在 runtime 中设置 report=True。
    """
    return "fill_context_for_report已调用"


# 工具 4：MCP 远程微服务接入网关

# 开新线程
def _run_async_in_thread(coro):
    """
    专门为 FastAPI 写的异步隔离器。
    确保无论主线程的事件循环怎么跑，这里的 MCP 异步通信都不会产生死锁冲突。
    """
    result = []
    error = []

    def run():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result.append(loop.run_until_complete(coro))
        except Exception as e:
            error.append(e)
        finally:
            loop.close()

    t = threading.Thread(target=run)
    t.start()
    t.join()

    if error:
        raise error[0]
    return result[0]

@tool(description="从外部病历系统中获取指定患者（如 P1001）的病历档案与体征数据")
def fetch_patient_record(patient_id: str) -> str:
    """
    大模型调用这个工具时，它实际上是一个“空壳中转站”。
    它会通过 MCP 标准协议，跨进程唤醒远端的 mcp_service.py，并把结果拿回来。
    """
    print(f"\n[MCP 网关] 正在建立安全协议通道，呼叫远端微服务查询: {patient_id}...")

    # “加密对讲机的呼叫过程”
    async def _call_mcp_server():
        # 引入官方 MCP 客户端核心库
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        # 精准定位你的微服务脚本路径
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        mcp_script = os.path.join(current_dir, "mcp_service.py")

        # 配置 MCP 宿主连接：采用 stdio (标准输入输出) 模式
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[mcp_script],

            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )

        # 1. 建立 MCP 协议连接通道
        async with stdio_client(server_params) as (read, write):
            # 2. 开启通信会话
            async with ClientSession(read, write) as session:
                # 3. 初始化握手
                await session.initialize()

                # 4. 跨系统远程调用！执行远端暴露的 "fetch_patient_record"
                response = await session.call_tool(
                    "fetch_patient_record",
                    arguments={"patient_id": patient_id}
                )

                # 5. 解析并返回微服务传回来的数据
                return response.content[0].text

    # 启动隔离器，运行上面的异步调用
    try:
        return _run_async_in_thread(_call_mcp_server())
    except Exception as e:
        print(f"[MCP 网关] 远程调用失败: {e}")
        return ""