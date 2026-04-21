from fastapi import APIRouter
from starlette.responses import StreamingResponse

from backend.schema.chat_schema import ChatRequest
from backend.services.chat_service import chat_with_ai
from backend.services.workflow_engine import run_workflow_stream
from backend.llm.client import get_client

router = APIRouter()

# 接口层，接收请求+调用service
@router.post("/chat_stream")
def chat_stream(request: ChatRequest):
    client = get_client()
    return chat_with_ai(request, client)


# 工作流接口
@router.post("/workflow_stream")
def workflow_stream(request: ChatRequest):
    client = get_client() # 在接口层获取

    def generator():
        for chunk in run_workflow_stream(request.message, client):
            yield chunk

    return StreamingResponse(generator(), media_type="text/plain")