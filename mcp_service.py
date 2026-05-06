
import csv
import os
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("AegisMedicalDB")

# 存放外部数据的内存字典
external_data = {}

def get_external_data():
    """读取本地 CSV 模拟外部数据库"""
    global external_data
    if not external_data:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "data", "external", "gastric_patients.csv")
        
        if not os.path.exists(csv_path):
            print(f"[微服务警告] 未找到外部数据文件：{csv_path}")
            return

        # 准备多种常见的编码格式
        encodings_to_try = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin1']

        for encod in encodings_to_try:
            try:
                # errors="replace" 会把无法识别的生僻乱码强行替换为 ""，不让程序崩溃
                with open(csv_path, "r", encoding=encod, errors="replace") as f:
                    reader = csv.reader(f)
                    next(reader)  # 跳过表头

                    for arr in reader:
                        # 防止空行或列数不够导致的数组越界报错
                        if len(arr) >= 8:
                            patient_id = arr[0].strip()
                            if patient_id not in external_data:
                                external_data[patient_id] = {
                                    "姓名": arr[1],
                                    "年龄": arr[2],
                                    "性别": arr[3],
                                    "既往病史": arr[4],
                                    "过敏史": arr[5],
                                    "近期症状(主诉)": arr[6],
                                    "近期体征": arr[7],
                                }
                # 没有抛出编码异常则说明读取成功，跳出循环
                break
            except UnicodeDecodeError:
                # 如果当前编码报错，就默默继续尝试下一种编码
                continue

# 使用 @mcp.tool 暴露给大模型
@mcp.tool()
def fetch_patient_record(patient_id: str) -> str:
    """
    从外部病历系统中获取指定患者（如 P1001）的病历档案与体征数据，
    以字符串形式返回，如果未检索到返回空字符串。
    """
    # 模拟网络请求日志
    print(f"\n[MCP 微服务] 接收到查询请求 -> 目标患者: {patient_id}")
    
    get_external_data()
    try:
        result = str(external_data[patient_id])
        print(f"[MCP 微服务] 查询成功，已返回数据。")
        return result
    except KeyError:
        print(f"[MCP 微服务] 未能检索到患者 {patient_id} 的数据。")
        return ""

if __name__ == "__main__":
    mcp.run(transport="stdio")