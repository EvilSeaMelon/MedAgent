
from sqlalchemy import select, delete
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from utils.database import AsyncSessionLocal, ChatHistory


async def load_chat_history(session_id: str) -> list[BaseMessage]:
    """从 MySQL 加载历史聊天记录"""
    messages = []

    async with AsyncSessionLocal() as session:
        # SELECT * FROM chat_history WHERE session_id = ? ORDER BY id ASC
        stmt = select(ChatHistory).where(ChatHistory.session_id == session_id).order_by(ChatHistory.id.asc())
        result = await session.execute(stmt)
        rows = result.scalars().all()  # 解析为对象列表

        for row in rows:
            if row.message_type == 'human':
                messages.append(HumanMessage(content=row.content))
            elif row.message_type == 'ai':
                messages.append(AIMessage(content=row.content))
            elif row.message_type == 'system':
                messages.append(SystemMessage(content=row.content))

    return messages


async def save_chat_message(session_id: str, message_type: str, content: str):
    """将单条消息持久化到 chat_history 表中"""
    async with AsyncSessionLocal() as session:
        # 直接实例化对象并添加
        new_msg = ChatHistory(
            session_id=session_id,
            message_type=message_type,
            content=content
        )
        session.add(new_msg)
        await session.commit()


async def clear_chat_history_db(session_id: str):
    """清除 MySQL 中指定 session_id 的所有聊天记录"""
    async with AsyncSessionLocal() as session:
        # DELETE FROM chat_history WHERE session_id = ?
        stmt = delete(ChatHistory).where(ChatHistory.session_id == session_id)
        await session.execute(stmt)
        await session.commit()