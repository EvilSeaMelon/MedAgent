# 🏥 MedAgent 医疗健康智能体系统 (Medical Intelligence Agent)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)
![LangChain](https://img.shields.io/badge/LangChain-Integration-green.svg)
![MCP](https://img.shields.io/badge/Protocol-MCP-orange.svg)
![Architecture](https://img.shields.io/badge/Architecture-ReAct-blueviolet.svg)

## 📖 项目简介

本项目是基于 FastAPI 与 LangChain 框架构建的严肃医疗智能体 Agent 系统。基于 ReAct (Reasoning and Acting) 架构实现自主病理推理与工具调度，底层深度整合高精度混合检索 RAG。

针对大模型落地医疗场景的核心痛点，系统**采用多线程沙盒与异步路由结合的混合调度基座**，重点攻克了专业幻觉、长上下文记忆管理瓶颈、以及复杂多框架嵌套（全异步 FastAPI 嵌套同步阻塞 LangChain）下的死锁难题。

## ✨ 核心特性与架构亮点

* **🧠 ReAct 智能体大脑**：基于 LangChain 搭建“思考-行动-观察”循环，能够自主拆解复杂医疗问诊，动态调度后台诊断工具。
* **🛠️ MCP 微服务解耦**：前沿落地 Model Context Protocol (MCP) 协议，将高敏医疗工具链、结构化外部数据流（如 `gastric_patients.csv`）与主干大模型进行进程级物理隔离与安全解耦。
* **⚡ 同异步混合调度网关**：为彻底解决 FastAPI 异步事件循环与 Agent 同步推理流冲突导致的死锁问题，创新设计“AOP 中间件 + 多线程沙盒隔离”网关，实现外层高并发接入与内层同步推理的完美兼顾。
* **🔍 高精度混合检索 (Hybrid RAG)**：重构基础 RAG 链路，采用“双路召回 (BM25 + ChromaDB) + BAAI/BGE 交叉编码器深度精排”，辅以 `SemanticChunker` 动态语义切分，消除医疗长尾词汇与专有名词的检索幻觉。
* **💾 持久化长时记忆引擎**：基于 MySQL 实现会话级与用户级 (Patient Profile) 双轨持久化。引入“基于 Token 触发的动态滑动窗口截断策略 (`tiktoken` 反向累加)”，精准控制 API 成本并赋予极度流畅的多轮问诊体验。

## 📂 核心目录结构

\`\`\`text
Agent_Project/
├── agent/                  # Agent 核心逻辑
│   ├── react_agent.py      # ReAct Agent 组装与调度执行主干
│   └── tools/              # Agent 工具库与拦截器
│       ├── agent_tools.py  # 医疗诊断/检索等具体工具定义
│       └── middleware.py   # AOP 切面拦截、状态流转记录
├── config/                 # 配置文件中心 (agent, chroma, prompts, rag)
├── data/                   # 本地知识库与数据资产
│   ├── profiles/           # 用户/患者结构化 JSON 画像 (如 P1001.json)
│   ├── external/           # 外部导入数据 (CSV/Excel)
│   └── *.txt / *.pdf       # 病理分类、用药方案等医疗长文本库
├── logs/                   # 日志归档目录
├── model/                  # 大模型工厂
│   └── factory.py          # LLM 实例初始化 (集成百炼/GPT等)
├── pages/                  # Streamlit 多页应用前端
│   └── app_file_uploader.py# 知识库文档上传与管理页面
├── prompts/                # 提示词工程管理
│   ├── main_prompt.txt     # 核心系统人设与 ReAct 模板
│   └── report_prompt.txt   # 诊断报告生成模板
├── rag/                    # RAG 检索微服务
│   ├── rag_service.py      # 混合检索调用流水线
│   └── vector_store.py     # 向量数据库操作封装
├── schemas/                # 数据交互模型
│   └── payload.py          # 基于 Pydantic 的 API 输入输出验证
├── utils/                  # 基础设施与工具类
│   ├── file_history_store.py # Token 动态截断与会话本地化存储
│   └── config_handler.py   # YAML 配置解析
├── app.py                  # Streamlit 前端交互主入口
├── main.py                 # FastAPI 后端微服务主入口
└── mcp_service.py          # MCP 协议服务端入口
\`\`\`

## 🛠️ 技术栈 (Tech Stack)

* **后端开发**：Python 3.10+, FastAPI, Pydantic, Uvicorn
* **前端交互**：Streamlit
* **AI 与 Agent 架构**：LangChain, Model Context Protocol (MCP), ReAct Paradigm
* **RAG 与算法**：ChromaDB, BM25 (Rank-BM25), BGE-Reranker, SemanticChunker, `tiktoken`
* **并发与存储**：Asyncio, ThreadPoolExecutor, MySQL, 本地 JSON 持久化

## 🚀 快速启动

### 1. 环境准备
确保已安装 Python 3.10+ 环境。克隆项目后安装核心依赖：

\`\`\`bash
pip install fastapi uvicorn streamlit langchain langchain-openai chromadb rank_bm25 tiktoken

### 2. 配置环境变量
在项目根目录创建 `.env` 文件，或在 `config/` 下的 yaml 文件中填入相应的 API Keys (如阿里云百炼 API_KEY, 数据库连接等)。

### 3. 启动后端微服务 (FastAPI)
启动支持同异步解耦的底层服务：
\`\`\`bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
\`\`\`

### 4. 启动 MCP 服务 (可选)
如果需要独立运行 MCP 工具挂载服务：
\`\`\`bash
python mcp_service.py
\`\`\`

### 5. 启动交互式前端 (Streamlit)
新开一个终端窗口，启动可视化医疗问诊台：
\`\`\`bash
streamlit run app.py
\`\`\`

## 📝 研发纪要与避坑指南
* **开发规约**：为防止 Event Loop 死锁，在 FastAPI 路由中调用 LangChain `.invoke()` 时，**必须**使用标准的同步 `def` 路由，依托 FastAPI 底层线程池接管阻塞任务。
* **Context 控制**：严禁直接加载全量 history，必须调用 `file_history_store.py` 中的 `truncate_by_token()` 进行反向截断。

---
*Powered by RAG & MCP Architecture*
