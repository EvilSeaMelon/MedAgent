
import json
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from model.factory import chat_model
from agent.tools.agent_tools import rag_summarize, fetch_patient_record, fill_context_for_report
from utils.prompt_loader import load_system_prompt, load_report_prompt
from utils.profile_manager import get_patient_profile, async_update_patient_profile


# ==========================================
# 1. 定义图的State
# ==========================================
class MedAgentState(TypedDict):
    # add_messages 自动把新产生的消息 append 到列表中，而不是覆盖
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    report_mode: bool  # 抛弃 middleware，用这个管理状态机


# ==========================================
# 2. 定义图的Nodes
# ==========================================
# 工具节点 (LangGraph 自带了极其稳定的 ToolNode，直接封装)
tools = [rag_summarize, fetch_patient_record, fill_context_for_report]
tool_node = ToolNode(tools)

# 将工具绑定给大模型
model_with_tools = chat_model.bind_tools(tools)


# 核心大脑推理节点
def reasoner_node(state: MedAgentState):
    print("\n[LangGraph 引擎] 进入核心推理节点...")
    messages = state["messages"]

    # 动态注入系统 Prompt 和长时记忆 (患者画像)
    sys_prompt = load_system_prompt()
    profile = get_patient_profile(state["session_id"])
    if profile:
        sys_prompt += f"\n\n【系统后台提示】该患者目前的长期画像特征为：{json.dumps(profile, ensure_ascii=False)}"

    # 组装上下文（System + 历史记录）
    invoke_messages = [SystemMessage(content=sys_prompt)] + messages

    # 调用大模型
    response = model_with_tools.invoke(invoke_messages)

    # 返回的内容会自动通过 add_messages 追加到 state["messages"] 中
    return {"messages": [response]}


# 【新增】节点：独立的报告生成器（取代 report_generator_middleware）
def report_node(state: MedAgentState):
    print("\n[LangGraph] 信号触发！进入独立【报告生成】车间...")
    sys_prompt = load_report_prompt()  # 专门的写报告人设

    # 强制大模型不去调工具，而是基于现有对话历史生成报告
    invoke_messages = [SystemMessage(content=sys_prompt)] + state["messages"]
    response = chat_model.invoke(invoke_messages)

    return {"messages": [response]}


# 【新增】节点：合规质检/免责声明（取代 medical_disclaimer_middleware）
def disclaimer_node(state: MedAgentState):
    print("\n[LangGraph] 离站质检：追加免责声明...")
    last_message = state["messages"][-1]

    # 只处理大模型的最终文本回复
    if isinstance(last_message, AIMessage) and not last_message.tool_calls:
        disclaimer_text = "\n\n*(注：以上内容仅供参考，不作为最终诊断依据，请遵医嘱。)*"
        updated_content = last_message.content + disclaimer_text

        # 传入与原来完全相同的 ID
        # add_messages 看到 ID 相同，就会执行覆盖而不是追加
        updated_message = AIMessage(content=updated_content, id=last_message.id)
        return {"messages": [updated_message]}

    return {}  # 如果不是文本回复，什么都不做


# ==========================================
# 【新增】节点：旁路画像更新节点 (异步并行)
# ==========================================
async def profile_updater_node(state: MedAgentState):
    session_id = state["session_id"]
    messages = state["messages"]

    # 1. 状态解析：逆序寻找最近的一次有效医患对话
    user_query = ""
    ai_response = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not ai_response and msg.content:
            ai_response = msg.content
        elif isinstance(msg, HumanMessage) and not user_query and msg.content:
            user_query = msg.content

        if user_query and ai_response:
            break

    # 如果没找到有效对话，不执行任何操作
    if not user_query or not ai_response:
        return {}

    # 2. 直接抛给专门的管理类去处理，必须 await！
    await async_update_patient_profile(
        session_id=session_id,
        query=user_query,
        ai_response=ai_response
    )

    # 3. 返回空字典，不污染主对话流
    return {}

# ==========================================
# 3. 定义图的Edges
# ==========================================
def route_after_reasoning(state: MedAgentState):
    """大模型思考完后，由这个路由器决定数据流向哪里"""
    last_message = state["messages"][-1]

    # 如果大模型返回了 tool_calls，说明它想用工具，扳道岔导向 tool_node
    if last_message.tool_calls:
        print(f"[LangGraph 路由] 发现工具调用请求: {last_message.tool_calls[0]['name']} -> 导向 ToolNode")
        return ["tools"]

    # 2. Fan-out并行广播
    # 如果大模型决定回答用户，同时把数据包发往两个节点
    # 它们将在底层完全并行执行
    print("[LangGraph 路由] 触发并行分支：一路去加免责声明，一路去后台写画像")
    return ["disclaimer", "profile_updater"]


# 工具执行完后去哪儿？（核心状态机切换点）
def route_after_tools(state: MedAgentState):
    last_message = state["messages"][-1]
    # 检查刚刚执行完的工具，是不是大模型发出的“写报告”信号？
    if last_message.type == "tool" and last_message.name == "fill_context_for_report":
        print("[LangGraph 路由] 检测到生成报告信号，切换至【报告车间】")
        return "report"

    # 普通工具查完数据，乖乖回大脑继续思考
    return "reasoner"


# ==========================================
# 4. 组装装配线 (Build the Graph)
# ==========================================
workflow = StateGraph(MedAgentState)

# 注册所有node
workflow.add_node("reasoner", reasoner_node)
workflow.add_node("tools", tool_node)
workflow.add_node("report", report_node)           # 注册报告站
workflow.add_node("disclaimer", disclaimer_node)   # 注册质检站
workflow.add_node("profile_updater", profile_updater_node)

# 连线编排
workflow.add_edge(START, "reasoner")
# 大脑出来后，走向分叉口 1
workflow.add_conditional_edges(
    "reasoner",
    route_after_reasoning,
    {
     "tools": "tools",
     "disclaimer": "disclaimer",
     "profile_updater": "profile_updater"
     }
)
#  工具出来后，走向分叉口 2
workflow.add_conditional_edges(
    "tools",
    route_after_tools,
    {"report": "report", "reasoner": "reasoner"}
)
# 报告生成完毕后，也要去加免责声明！
workflow.add_edge("report", "disclaimer")
# 质检合格，正式离站给用户！
workflow.add_edge("disclaimer", END)
workflow.add_edge("profile_updater", END)

# 实例化一个内存检查点
memory = MemorySaver()

# 编译成最终可执行的 Agent 图，并挂载记忆引擎！
med_agent_graph = workflow.compile(checkpointer=memory)