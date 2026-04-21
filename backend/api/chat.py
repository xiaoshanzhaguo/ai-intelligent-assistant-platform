from fastapi import APIRouter
from backend.schema.chat_schema import ChatRequest
from backend.service.chat_service import chat_with_ai

router = APIRouter()

# 接口层，接收请求+调用service
@router.post("/chat_stream")
def chat_stream(request: ChatRequest):
    return chat_with_ai(request)