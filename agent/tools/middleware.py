from typing import Callable

from utils.path_tool import get_abs_path
from utils.prompt_loader import load_system_prompt, load_report_prompt
from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest, after_model
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from utils.logger_handler import logger
import os
from datetime import datetime


@wrap_tool_call
def monitor_tool(
        # 请求的数据封装
        request: ToolCallRequest,
        # 执行的函数本身
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:             # 工具执行的监控
    logger.info(f"[tool monitor]执行工具：{request.tool_call['name']}")
    logger.info(f"[tool monitor]传入参数：{request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")

        if request.tool_call['name'] == "fill_context_for_report":
            request.runtime.context["report"] = True

        return result
    except Exception as e:
        logger.error(f"工具{request.tool_call['name']}调用失败，原因：{str(e)}")
        raise e


@before_model
def log_before_model(
        state: AgentState,          # 整个Agent智能体中的状态记录
        runtime: Runtime,           # 记录了整个执行过程中的上下文信息
):         # 在模型执行前输出日志

    logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息。")

    logger.debug(f"[log_before_model]{type(state['messages'][-1]).__name__} | {state['messages'][-1].content.strip()}")

    return None


@dynamic_prompt                 # 每一次在生成提示词之前，调用此函数
def report_prompt_switch(request: ModelRequest):     # 动态切换提示词
    is_report = request.runtime.context.get("report", False)
    if is_report:               # 是报告生成场景，返回报告生成提示词内容
        return load_report_prompt()

    return load_system_prompt()


# ---------------------------------------------------------
# 新增中间件 1：医疗报告自动落盘拦截器
# ---------------------------------------------------------
@after_model
def report_generator_middleware(
        state: AgentState,
        runtime: Runtime,
):
    """
    专门监听模型输出。如果你原先的 `report_prompt_switch` 成功让大模型生成了报告，
    这个中间件就会在它输出后立刻拦截，将文本写进服务器硬盘。
    """
    # 检查当前是否处于报告生成模式
    if runtime.context.get("report"):
        last_message = state['messages'][-1]

        # 确保最后一条是 AI 生成的实质性回复，且不是在调用工具
        if last_message.type == "ai" and last_message.content and not last_message.tool_calls:
            try:
                # 1. 创建保存报告的本地目录
                report_dir = get_abs_path("data/reports")
                os.makedirs(report_dir, exist_ok=True)

                # 2. 生成带时间戳的唯一文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(report_dir, f"Health_Report_{timestamp}.md")

                # 3. 拦截内容，执行真实的物理落盘！
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(last_message.content)

                logger.info(f"[Report Middleware] 报告已成功落盘至: {file_path}")

                # 4. 在发给用户的前端消息末尾，悄悄加上一句系统提示
                last_message.content += f"\n\n---\n*(✅ 系统提示：您的健康评估报告已自动归档并保存在医院系统：`{file_path}`)*"

                # 5. 可选：报告生成完毕后重置标志位，防止后续普通聊天也写文件
                # runtime.context["report"] = False

            except Exception as e:
                logger.error(f"[Report Middleware] 报告落盘失败: {str(e)}")


# ---------------------------------------------------------
# 新增中间件 2：医疗免责声明强制注入器
# ---------------------------------------------------------
@after_model
def medical_disclaimer_middleware(
        state: AgentState,
        runtime: Runtime,
):
    """
    拦截大模型的每一次最终回复，强制注入医疗免责声明。
    这在医疗 AI 中是极其重要的合规性（Compliance）设计！
    """
    last_message = state['messages'][-1]

    # 只有在 AI 最终给出文字回复时（而不是在默默调用工具时）才追加声明
    if last_message.type == "ai" and last_message.content and not last_message.tool_calls:

        # 使用红色或加粗突出显示（支持 Markdown 的前端可以直接渲染）
        disclaimer = "\n\n⚠️ 本系统的分析与建议仅供参考，不具有临床医学诊断效力。如有身体不适，请及时前往正规医疗机构就诊。"

        # 防止因为重试机制导致免责声明被重复添加
        if "免责声明" not in last_message.content:
            last_message.content += disclaimer
            logger.debug("[Disclaimer Middleware] 已成功为本次回复注入医疗免责声明。")


"""
触发：用户说“帮我生成报告” -> 大模型调用 fill_context_for_report 工具。

打标：原有的 monitor_tool 拦截到该工具，设置 runtime.context["report"] = True。

换脑：原有的 report_prompt_switch 发现标志位，立刻把提示词换成专业的“医学报告模板”。

生成：大模型根据极其严谨的医学模板，写出一份高质量的 Markdown 报告。

落盘：我们刚写的 report_generator_middleware 拦截到这份报告，瞬间将其存入硬盘 data/reports/ 目录下！

免责：紧接着，medical_disclaimer_middleware 在这篇报告末尾狠狠敲上一个红色的免责钢印！
"""
