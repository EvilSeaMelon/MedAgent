# 弃用

from langchain_community.chat_message_histories import SQLChatMessageHistory

# 你的 MySQL 连接字符串
# 格式: mysql+驱动名://用户名:密码@主机地址:端口/数据库名
MYSQL_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/medagent_db"


def get_history(session_id: str):
    """
    根据 session_id 从 MySQL 数据库提取历史对话。
    如果表不存在，SQLChatMessageHistory 会自动帮你建表！
    """
    chat_message_history = SQLChatMessageHistory(
        session_id=session_id,
        connection_string=MYSQL_URL,
        table_name="chat_history"  # 这是将在 MySQL 中自动创建的表名
    )

    return chat_message_history