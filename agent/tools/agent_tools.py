import csv
import os
from utils.logger_handler import logger
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
import random
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path

rag = RagSummarizeService()

external_data = {}

# ---------------------------------------------------------
# 工具 1：知识库问答 (保留你的 RAG)
# ---------------------------------------------------------
@tool(description="当用户询问具体的疾病症状、用药禁忌等医学知识时，必须调用此工具检索本地权威医学知识库")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)

# ---------------------------------------------------------
# 工具 2：患者既往病历查询
# ---------------------------------------------------------
def get_external_data():
    """
    {
        "P1001": {"姓名": xxx, "既往病史": xxx, "近期体征": xxx, ...},
        "P1002": {"姓名": xxx, "既往病史": xxx, "近期体征": xxx, ...},
        ...
    }
    """
    global external_data
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件{external_data_path}不存在")

        with open(external_data_path, "r", encoding="utf-8") as f:
            # 引入 csv.reader 防止带有逗号的句子被错误切分
            reader = csv.reader(f)
            next(reader)  # 跳过第一行表头

            for arr in reader:
                # 对应 csv 的 8 列数据
                patient_id: str = arr[0].strip()
                name: str = arr[1]
                age: str = arr[2]
                gender: str = arr[3]
                history: str = arr[4]
                allergy: str = arr[5]
                symptom: str = arr[6]
                signs: str = arr[7]

                # 赋值装载（直接挂载到 patient_id 下）
                if patient_id not in external_data:
                    external_data[patient_id] = {
                        "姓名": name,
                        "年龄": age,
                        "性别": gender,
                        "既往病史": history,
                        "过敏史": allergy,
                        "近期症状(主诉)": symptom,
                        "近期体征": signs,
                    }


@tool(description="从外部病历系统中获取指定患者（如 P1001）的病历档案与体征数据，以字符串形式返回，如果未检索到返回空字符串")
def fetch_patient_record(patient_id: str) -> str:
    get_external_data()

    try:
        # 字典装载得，直接用 str() 将字典转为字符串喂给大模型即可
        return str(external_data[patient_id])
    except KeyError:
        logger.warning(f"[外部数据]未能检索到患者：{patient_id} 的病历记录数据")
        return ""


# ---------------------------------------------------------
# 工具 3：触发报告生成流程
# ---------------------------------------------------------
@tool(description="当用户明确要求【生成健康报告】、【出具评估档案】时，必须调用此工具来开启报告生成流程")
def fill_context_for_report() -> str:
    """
    这个工具本身不做任何事，只作为一个信号弹。
    middleware 会拦截它的调用，并在 runtime 中设置 report=True。
    """
    return "fill_context_for_report已调用"