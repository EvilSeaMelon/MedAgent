import json
import threading

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from model.factory import chat_model
from utils.profile_manager import get_patient_profile, update_patient_profile_task, clear_patient_profile
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

    def execute(self, query: str, session_id: str = "default.json"):
        history = get_history(session_id)
        input_messages = list(history.messages)

        # ==========================================
        # 1：静默注入长时记忆（患者画像）
        # ==========================================
        profile = get_patient_profile(session_id)
        if profile:
            profile_str = json.dumps(profile, ensure_ascii=False)
            # 在历史记录之后、本次问题之前，插入一条极其关键的系统提示
            # 这样大模型就能“回想”起这个人的特征，且这条消息不会被存入 MySQL！
            memory_injection = SystemMessage(content=f"【系统后台提示】当前患者的长期特征画像如下，请在回答时结合这些背景：\n{profile_str}")
            input_messages.append(memory_injection)

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
                context={"report": False}
            )

            final_ai_message = response["messages"][-1].content

            # 存入 MySQL 记忆 (注意：这里只存了用户的原问题和 AI 的回答，上面的 memory_injection 被完美过滤掉了)
            history.add_messages([
                HumanMessage(content=query),
                AIMessage(content=final_ai_message),
            ])
            print("\n✅ [AI 引擎] 思考完毕，准备返回完整结果")

            # ==========================================
            # 2：开启后台线程，更新长时记忆
            # ==========================================
            # 不让用户等，直接开个线程去背后慢慢提取
            threading.Thread(
                target=update_patient_profile_task,
                args=(session_id, query, final_ai_message)
            ).start()

            return final_ai_message

        except Exception as e:
            error_msg = f"🚨 引擎底层报错: {str(e)}"
            print(error_msg)
            return error_msg

    def clear_memory(self, session_id: str = "default.json"):
        """调用底层的 clear() 方法，一键清空 MySQL 中对应 session_id 的所有记录，同时清空画像"""
        history = get_history(session_id)
        history.clear()
        # 🌟 同步清空长时记忆 JSON
        clear_patient_profile(session_id)