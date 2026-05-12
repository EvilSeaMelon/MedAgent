
import csv
import os

import pymysql
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("AegisMedicalDB")

# ---------------------------------------------------------
# 数据库配置
# ---------------------------------------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "medagent_db",
    "charset": "utf8mb4",
    # 返回字典格式，方便按字段名取数据
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True
}

def get_db_connection():
    """获取数据库连接的辅助函数"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"[微服务致命错误] 无法连接到外部病历数据库: {e}")
        return None


# 使用 @mcp.tool 暴露给大模型
@mcp.tool()
def fetch_patient_record(patient_id: str) -> str:
    """
    从外部病历系统中获取指定患者（如 P1001）的病历档案与体征数据，
    以字符串形式返回，如果未检索到返回空字符串。
    """
    # 模拟网络请求日志
    print(f"\nMCP接收到查询请求 -> 目标患者: {patient_id}")

    conn = get_db_connection()
    if not conn:
        return ""  # 数据库连接失败时返回空，或者返回具体的错误提示给大模型

    try:
        with conn.cursor() as cursor:
            # 使用参数化查询防止 SQL 注入
            sql = "SELECT * FROM gastric_patients WHERE patient_id = %s"
            cursor.execute(sql, (patient_id,))
            record = cursor.fetchone()

            if record:
                # 将数据库里查出的字典格式化为大模型易读的字符串
                # 处理可能为 None 的字段
                formatted_result = (
                    f"患者姓名: {record.get('name', '未知')}\n"
                    f"年龄: {record.get('age', '未知')}\n"
                    f"性别: {record.get('gender', '未知')}\n"
                    f"既往病史: {record.get('medical_history', '未知')}\n"
                    f"过敏史: {record.get('allergies', '未知')}\n"
                    f"近期症状(主诉): {record.get('symptoms', '未知')}\n"
                    f"近期体征: {record.get('signs', '未知')}"
                )
                print(f"[MCP 微服务] 数据库命中 -> 成功获取 {patient_id} 的数据。")
                return formatted_result
            else:
                print(f"[MCP 微服务] 数据库未命中 -> 无 {patient_id} 的数据。")
                return ""

    except Exception as e:
        print(f"[微服务查询异常] {e}")
        return ""
    finally:
        # 用完关闭连接，防止连接池泄漏
        conn.close()


if __name__ == "__main__":
    # 启动 MCP 服务
    mcp.run()