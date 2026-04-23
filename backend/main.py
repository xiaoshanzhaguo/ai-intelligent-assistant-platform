from fastapi import FastAPI

from backend.api.chat import router as chat_router


# 应用入口: 只负责创建应用并注册路由
app = FastAPI(
    title="AI 内容分析与创作助手",
    version="0.1.0"
)

# 注册聊天与工作流相关接口
app.include_router(chat_router)