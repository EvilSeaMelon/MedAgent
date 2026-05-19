
import pymysql
from mcp.server.fastmcp import FastMCP

from utils.database import SyncSessionLocal, GastricPatient

# 初始化 MCP 服务器
mcp = FastMCP("AegisMedicalDB")

# 使用 @mcp.tool 暴露给大模型
@mcp.tool()
def fetch_patient_record(patient_id: str) -> str:
    """
    从外部病历系统中获取指定患者（如 P1001）的病历档案与体征数据。
    """
    print(f"\n[MCP 工具] 接收到查询请求 -> 目标患者: {patient_id}")

    try:
        # 使用 SQLAlchemy 同步会话
        with SyncSessionLocal() as session:
            # SELECT * WHERE patient_id = x
            patient = session.get(GastricPatient, patient_id)

            if patient:
                # 查出来的是一个 Python 对象，直接用 .属性 访问
                formatted_result = (
                    f"患者姓名: {patient.name or '未知'}\n"
                    f"年龄: {patient.age or '未知'}\n"
                    f"性别: {patient.gender or '未知'}\n"
                    f"既往病史: {patient.medical_history or '无'}\n"
                    f"过敏史: {patient.allergies or '无'}\n"
                    f"近期症状(主诉): {patient.symptoms or '无'}\n"
                    f"近期体征: {patient.vitals or '未知'}\n"
                    f"当前诊断: {patient.diagnosis or '未知'}\n"
                    f"治疗方案: {patient.treatment_plan or '未知'}"
                )
                print("[MCP 工具] 成功从数据库获取并格式化病历。")
                return formatted_result
            else:
                print(f"[MCP 工具] 未找到患者 {patient_id} 的病历。")
                return ""

    except Exception as e:
        print(f"[MCP 致命错误] 数据库查询失败: {e}")
        return ""


if __name__ == "__main__":
    # 启动 MCP 服务
    mcp.run()