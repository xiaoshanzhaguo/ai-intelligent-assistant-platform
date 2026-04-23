from fastapi import APIRouter

from backend.llm.client import get_client
from backend.schema.chat_schema import ChatRequest
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