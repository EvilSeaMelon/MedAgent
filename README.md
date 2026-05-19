# 🏥 MedAgent 2.0 - 基于 LangGraph 的高可用医疗智能体

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Framework](https://img.shields.io/badge/Framework-LangGraph%20%7C%20FastAPI-green.svg)
![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20SQLAlchemy-orange.svg)

**MedAgent 2.0** 是一个企业级的全异步医疗 AI 助手后端架构。它摒弃了传统的单例 AgentExecutor 和黑盒拦截器，全面拥抱 **LangGraph 显式状态机**，实现了问诊对话与医疗报告生成的无缝切换。通过彻底解耦无状态网关与底层并发任务，系统具备了极高的响应速度与横向扩展能力。

---

## ✨ 核心特性 (Key Features)

### 1. 🚄 纯异步状态机架构 (LangGraph)
* 废弃传统的 Agent 中间件拦截器，利用 LangGraph 的 **Conditional Edges (条件边)** 显式控制数据流。
* **双轨模式**：大模型可自主触发信号弹，在“多轮闲聊问诊”与“严肃医疗报告生成”两种截然不同的 Prompt 状态间无缝切换，彻底消除上下文串线。

### 2. ⚡ 高并发旁路任务 (Fan-out)
* 引入图并发节点机制。当系统决定回复用户时，数据流瞬间分为两路：
  * **主路**：毫秒级生成最终回复（带免责声明）并返回给网关。
  * **旁路**：在后台静默调用大模型，提取并持久化用户的“长时特征画像 (JSON)”。主线程 0 阻塞，极致提升用户体验。

### 3. 🗄️ SQLAlchemy 双引擎数据基座
* **异步引擎 (AsyncEngine)**：支撑 FastAPI 与 LangGraph 的全速流转，管理用户会话历史，保证高并发下的数据库连接池稳定。
* **同步引擎 (SyncEngine)**：支撑跨进程的 MCP (Model Context Protocol) 服务，优雅查询外部真实的医疗病历系统。

### 4. 🛠️ 统一工具车间 (Unified ToolNode)
* 摒弃臃肿的定制节点，将 `RAG 向量检索` 与 `MCP 微服务调用` 统一封装于 `ToolNode`。
* 利用大模型原生的 Function Calling 自动分发，图拓扑结构极其精简，新增工具“零”架构修改成本。

---

## 🏗️ 系统架构图 (Architecture)

```text
[用户请求] -> FastAPI 网关 (无状态)
                 ↓
                 (捞取 MySQL 历史)
                 ↓
[ START ] ---> 【Reasoner (大模型思考)】 <=======> 【ToolNode (RAG / MCP 查病历)】
                 ↓                                         (条件路由：打回继续思考)
        (触发报告模式变道?) 
          ↙              ↘
    【报告生成器】      【返回给用户】 (Fan-out 并发分叉)
          ↓              ↙           ↘
          ↓   【免责声明 (主线程)】   【后台长时画像抽取 (异步线程)】
          ↘              ↓                   ↓
                [ 返回前端界面 ]        [ 写入本地 JSON / 数据库 ]
                 ↓
                 (请求结束，双向落盘 MySQL)
```

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
确保你的系统已安装 Python 3.10+ 和 MySQL 8.0+。

```bash
# 克隆仓库
git clone https://github.com/yourusername/MedAgent.git
cd MedAgent

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置
1. 在 MySQL 中创建一个名为 `medagent_db` 的数据库。
2. 确保 `utils/database.py` 中的数据库配置（用户名、密码）与你的本地环境一致。
3. 系统会在首次启动时，利用 FastAPI 的生命周期钩子（Lifespan）自动创建所需的表结构 (`chat_history` 等)。

### 3. 环境变量与密钥
在项目根目录（或 `config/` 目录）配置你的 LLM API 密钥。例如：
```bash
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxx"
```

### 4. 启动服务

**启动主干服务 (FastAPI + LangGraph)：**
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**启动独立的 MCP 微服务 (可选，用于查病历)：**
```bash
# 在新终端窗口中启动
mcp dev mcp_service.py
```

---

## 📂 目录结构 (Project Structure)

```text
MedAgent/
├── agent/
│   ├── graph_agent.py      # 【核心】LangGraph 状态机编排与节点定义
│   └── tools/              # 业务工具 (RAG 触发器、报告触发器等)
├── data/
│   ├── external/           # 模拟的外部病历 CSV
│   └── profiles/           # 用户长时画像持久化 JSON 目录
├── model/
│   └── factory.py          # 大模型统一工厂类实例化
├── rag/
│   └── ...                 # ChromaDB 向量检索库初始化与封装
├── schemas/
│   └── payload.py          # Pydantic 接口请求体定义
├── utils/
│   ├── database.py         # 【核心】SQLAlchemy 双引擎连接池与 ORM 模型
│   ├── mysql_history.py    # 基于 ORM 的异步短时对话记忆读写
│   ├── profile_manager.py  # 异步长时画像特征抽取与管理
│   └── prompt_loader.py    # 提示词加载器
├── config/                 # YAML 配置文件目录
├── main.py                 # FastAPI 入口：无状态网关与会话生命周期管理
├── mcp_service.py          # 基于 FastMCP 的独立外部系统接口
└── requirements.txt        # 项目依赖
```

---

## 💡 核心 API 接口说明

| Method | Endpoint                     | Description                                   |
| ------ | ---------------------------- | --------------------------------------------- |
| `GET`  | `/health`                    | 检查服务运行状态                              |
| `POST` | `/api/chat`                  | 主力问诊对话接口。传入 `session_id` 与 `query`|
| `DEL`  | `/api/chat/history/{id}`     | 彻底重置指定用户的历史对话与长期画像数据      |

**`/api/chat` 请求示例:**
```json
{
  "session_id": "P1001",
  "query": "我最近吃海鲜总是胃痛，请帮我查一下我的病历，看看怎么回事。"
}
```

---

## 🛠️ 下一步开发计划 (Roadmap)
- [ ] **PostgreSQL 迁移**：利用 LangGraph 官方 `AsyncPostgresSaver` 进一步增强 Checkpointer 能力。
- [ ] **LangSmith 监控接入**：实现图节点运行耗时与 Token 消耗的可视化追踪。

