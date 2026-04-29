from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from model.factory import chat_model
from utils.prompt_loader import load_system_prompt
from utils.file_history_store import get_history
from agent.tools.agent_tools import (rag_summarize, fetch_patient_record, fill_context_for_report)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch, medical_disclaimer_middleware, \
    report_generator_middleware


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompt(),
            tools=[rag_summarize, fetch_patient_record, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch, report_generator_middleware,
                        medical_disclaimer_middleware],
        )

    # 🌟 删掉所有的 stream，换回最稳的 invoke
    def execute(self, query: str, session_id: str = "default.json"):
        history = get_history(session_id)
        input_messages = list(history.messages)
        input_messages.append(HumanMessage(content=query))
        input_dict = {
            "messages": input_messages
        }

        print(f"\n⏳ [AI 引擎] 收到请求：{query}，正在全面思考...")
        try:
            # 阻塞式调用，我们已知这个绝对不会卡！
            response = self.agent.invoke(
                input_dict,
                config={"configurable": {"thread_id": session_id}},
                context={"report": False}  # 之前修复过的中间件参数
            )

            final_ai_message = response["messages"][-1].content

            # 存入 MySQL 记忆
            history.add_messages([
                HumanMessage(content=query),
                AIMessage(content=final_ai_message),
            ])
            print("\n✅ [AI 引擎] 思考完毕，准备返回完整结果")
            return final_ai_message

        except Exception as e:
            error_msg = f"🚨 引擎底层报错: {str(e)}"
            print(error_msg)
            return error_msg

    # 👇 原有的清空记忆方法完美保留
    def clear_memory(self, session_id: str = "default.json"):
        """调用底层的 clear() 方法，一键清空 MySQL 中对应 session_id 的所有记录"""
        history = get_history(session_id)
        history.clear()