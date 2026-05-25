from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

from agent.graph_agent import med_agent_graph
from rag.vector_store import VectorStoreService
from schemas.payload import ChatRequest
from utils.config_handler import chroma_conf
from utils.mysql_history import (
    clear_chat_history_db,
    load_chat_history,
    save_chat_message,
)
from utils.path_tool import get_abs_path
from utils.profile_manager import clear_patient_profile

app = FastAPI(
    title="MedAgent Backend",
    description="FastAPI service for chat and knowledge ingestion",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_vector_store_service: Optional[VectorStoreService] = None


def _api_response(code: int, message: str, data: Optional[dict] = None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data or {},
    }


def _get_vector_store_service() -> VectorStoreService:
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service


def _allowed_extensions() -> set[str]:
    configured = chroma_conf.get("allow_knowledge_file_type", [])
    return {str(ext).lower().lstrip(".") for ext in configured}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Aegis-Med Backend is running!"}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"\n[API] Chat request received -> session_id={request.session_id}")

    try:
        history_messages = await load_chat_history(request.session_id)

        current_user_msg = HumanMessage(content=request.query)
        history_messages.append(current_user_msg)

        initial_state = {
            "messages": history_messages,
            "session_id": request.session_id,
        }

        final_state = await med_agent_graph.ainvoke(initial_state)
        ai_answer = final_state["messages"][-1].content

        await save_chat_message(request.session_id, "human", request.query)
        await save_chat_message(request.session_id, "ai", ai_answer)

        return _api_response(
            code=200,
            message="success",
            data={"answer": ai_answer},
        )
    except Exception as e:
        print(f"[API] Chat error: {e}")
        return _api_response(code=500, message=f"server_error: {str(e)}")


@app.post("/api/knowledge/upload")
async def upload_knowledge_file(
    file: UploadFile = File(..., description="Knowledge file (txt/pdf)"),
    overwrite: bool = Form(True, description="Overwrite if same filename exists"),
):
    """
    上传知识文件并触发向量库导入

    Request:
      - file: 二进制文件
      - overwrite: 布尔值（可选）

    Response (uniform format):
    - code/message/data
    """
    if not file.filename:
        return _api_response(code=400, message="bad_request: empty filename")

    safe_filename = Path(file.filename).name.strip()
    if not safe_filename:
        return _api_response(code=400, message="bad_request: invalid filename")

    ext = Path(safe_filename).suffix.lower().lstrip(".")
    allowed_exts = _allowed_extensions()
    if ext not in allowed_exts:
        return _api_response(
            code=400,
            message="bad_request: unsupported file type",
            data={"allowed_types": sorted(allowed_exts)},
        )

    file_bytes = await file.read()
    if not file_bytes:
        return _api_response(code=400, message="bad_request: file is empty")

    data_dir = Path(get_abs_path(chroma_conf["data_path"]))
    data_dir.mkdir(parents=True, exist_ok=True)
    target_path = data_dir / safe_filename

    exists_before = target_path.exists()
    if exists_before and not overwrite:
        return _api_response(
            code=409,
            message="conflict: file already exists, set overwrite=true to replace",
            data={"filename": safe_filename},
        )

    with open(target_path, "wb") as f:
        f.write(file_bytes)

    try:
        vector_store_service = await run_in_threadpool(_get_vector_store_service)
        await run_in_threadpool(vector_store_service.load_document)
    except Exception as e:
        return _api_response(code=500, message=f"ingest_failed: {str(e)}")
    finally:
        await file.close()

    return _api_response(
        code=200,
        message="success",
        data={
            "filename": safe_filename,
            "saved_path": str(target_path),
            "size_bytes": len(file_bytes),
            "content_type": file.content_type or "application/octet-stream",
            "overwrite": overwrite,
            "indexed": True,
        },
    )


@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    print(f"\n[API] Clear history request -> session_id={session_id}")
    try:
        await clear_chat_history_db(session_id)
        await clear_patient_profile(session_id)
        return _api_response(code=200, message="session data cleared")
    except Exception as e:
        return _api_response(code=500, message=f"clear_failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
