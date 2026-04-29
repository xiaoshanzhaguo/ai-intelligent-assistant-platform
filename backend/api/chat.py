from fastapi import APIRouter, HTTPException

from backend.llm.client import get_client
from backend.rag.chunker import split_text_into_chunks
from backend.rag.store import save_document_chunks
from backend.schema.chat_schema import (
    ChatRequest,
    IndexDocumentRequest,
    IndexDocumentResponse
)
from backend.services.chat_service import chat_with_ai
from backend.services.workflow_engine import run_workflow_stream

# 路由注册器
router = APIRouter()


@router.post("/chat_stream")
def chat_stream(request: ChatRequest):
    """
    聊天流式接口。

    接收前端聊天请求，初始化模型客户端，
    并调用聊天服务返回 SSE 事件流响应。
    """
    client = get_client()
    return chat_with_ai(request, client)


@router.post("/workflow_stream")
def workflow_stream(request: ChatRequest):
    """
    工作流流式接口。

    接收前端工作流请求，初始化模型客户端，
    并调用工作流服务返回 SSE 事件流响应。
    """
    client = get_client()
    return run_workflow_stream(request, client)


@router.post("/index_document", response_model=IndexDocumentResponse)
def index_document(request: IndexDocumentRequest):
    """
    文档索引接口。

    作用：
    1. 接收前端上传并提取后的完整文本
    2. 做文本切块
    3. 存入当前 session 对应的内存存储
    """
    cleaned_text = request.document_text.strip()
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="文档内容不能为空。")

    chunks = split_text_into_chunks(cleaned_text)
    if not chunks:
        raise HTTPException(status_code=400, detail="文档切块后为空，请检查输入内容。")

    save_document_chunks(
        session_id=request.session_id,
        file_name=request.file_name,
        chunks=chunks
    )

    return IndexDocumentResponse(
        session_id=request.session_id,
        file_name=request.file_name,
        chunk_count=len(chunks)
    )