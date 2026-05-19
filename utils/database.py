# utils/database.py
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


# 1. 数据库 URL 配置
# 你的基础信息
DB_USER = "root"
DB_PASS = "123456"
DB_HOST = "127.0.0.1:3306"
DB_NAME = "medagent_db"

# 异步 URL (mysql_history)
ASYNC_DB_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"
# 同步 URL (mcp_service)
SYNC_DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

# ==========================================
# 2. 创建引擎与会话工厂
# ==========================================
# 异步引擎与 Session
async_engine = create_async_engine(ASYNC_DB_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)

# 同步引擎与 Session
sync_engine = create_engine(SYNC_DB_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine)

# ==========================================
# 3. 定义 ORM 数据模型 (Models)
# ==========================================
Base = declarative_base()


class ChatHistory(Base):
    """聊天记录表模型"""
    __tablename__ = 'chat_history'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(128), index=True, nullable=False)
    message_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class GastricPatient(Base):
    """患者病历表模型"""
    __tablename__ = 'gastric_patients'

    # 假设 patient_id 是主键，根据你实际表结构可调整
    patient_id = Column(String(50), primary_key=True)
    name = Column(String(50))
    age = Column(String(10))
    gender = Column(String(10))
    medical_history = Column(Text)
    allergies = Column(Text)
    symptoms = Column(Text)
    vitals = Column(Text)
    diagnosis = Column(Text)
    treatment_plan = Column(Text)