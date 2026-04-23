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
            middleware=[monitor_tool, log_before_model, report_prompt_switch, report_generator_middleware, medical_disclaimer_middleware],
        )

    def execute_stream(self, query: str, session_id: str = "default.json"):
        history = get_history(session_id)
        input_messages = list(history.messages)
        input_messages.append(HumanMessage(content=query))
        input_dict = {
            "messages": input_messages
        }

        latest_ai_content = ""
        # 第三个参数context就是上下文runtime中的信息，就是我们做提示词切换的标记
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                if latest_message.__class__.__name__ == "AIMessage":
                    latest_ai_content = latest_message.content.strip()
                yield latest_message.content.strip() + "\n"

        if latest_ai_content:
            history.add_messages([
                HumanMessage(content=query),
                AIMessage(content=latest_ai_content),
            ])


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)
