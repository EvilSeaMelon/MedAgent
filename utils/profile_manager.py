""""读写 JSON 格式的患者画像，并调用大模型进行信息提取"""

import os
import json
from langchain_core.messages import HumanMessage, SystemMessage
from model.factory import chat_model  # 复用你现有的模型
from utils.path_tool import get_abs_path

# 设置存储画像的文件夹
PROFILE_DIR = get_abs_path("data/profiles")
os.makedirs(PROFILE_DIR, exist_ok=True)


def get_patient_profile(session_id: str) -> dict:
    """读取当前患者的画像，如果没有则返回空字典"""
    file_path = os.path.join(PROFILE_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def update_patient_profile_task(session_id: str, query: str, ai_response: str):
    """
    【后台任务】使用大模型提取本次对话中的医疗关键信息，并更新画像。
    """
    print(f"\n正在后台静默提取 {session_id} 的长时记忆...")
    old_profile = get_patient_profile(session_id)

    # 专门为“记忆提取”设计的 Prompt
    extract_prompt = f"""
    你是一个专业的医疗数据分析专家。
    请根据以下最新的【医患对话记录】，以及该患者【之前的画像】，提取或更新患者的长期特征。
    如果对话中没有提到新的医疗特征，请保持原有特征不变。

    【之前的画像】: {json.dumps(old_profile, ensure_ascii=False)}
    【最新患者提问】: {query}
    【最新医生回答】: {ai_response}

    请严格只输出一段合法的 JSON 格式数据，不要有任何 Markdown 标记或多余的解释。JSON 应该包含以下键（如果没有对应信息填 "未知"）：
    "age" (年龄), "gender" (性别), "chronic_disease" (慢性病史), "allergy" (过敏史), "current_symptoms" (近期症状), "psychological_status" (情绪/心理状态)
    """

    try:
        # 调用大模型进行总结
        response = chat_model.invoke([HumanMessage(content=extract_prompt)])
        new_profile_text = response.content.strip().replace("```json", "").replace("```", "")

        # 尝试解析为 JSON
        new_profile = json.loads(new_profile_text)

        # 保存到本地文件
        file_path = os.path.join(PROFILE_DIR, f"{session_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(new_profile, f, ensure_ascii=False, indent=4)

        print(f"{session_id} 画像已更新: {new_profile}")
    except Exception as e:
        print(f"提取记忆失败 (不影响主流程): {str(e)}")


def clear_patient_profile(session_id: str):
    """清空画像"""
    file_path = os.path.join(PROFILE_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)