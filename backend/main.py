from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from backend.api.chat import router as chat_router
from pydantic import BaseModel
from openai import OpenAI
from backend.prompt.prompt_templates import ROLE_PROMPTS

# 入口只做“注册路由”
app = FastAPI()
app.include_router(chat_router)

# 实现多模式功能
def build_system_prompt(mode):
    if mode == "聊天":
        return "你是一个温柔的AI助手，你的职责是陪伴用户进行聊天。"
    elif mode == "总结":
        return "你是一个具有总结能力的AI助手，你的职责是帮用户总结内容，提取重点。"
    elif mode == "翻译":
        return "你是一个专业的英语老师，你的职责是将用户输入翻译成英文。"
    elif mode == "改写":
        return "你是一个专业的语文老师，你的职责是优化用户输入，使表达更清晰。"
    return "你是一个通用AI助手"

# 非流式输出
# @app.post("/chat")
# def chat(req: ChatRequest):
#     system_prompt = build_system_prompt(req.role)
#
#     response = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": req.message}
#         ],
#         stream=False
#     )
#
#     return {
#         "response": response.choices[0].message.content
#     }

# 流式输出
# @app.post("/chat_stream")
# def chat_stream(req: ChatRequest):
#     system_prompt = build_system_prompt(req.role)
#
#     def generate():
#         response = client.chat.completions.create(
#             model="deepseek-chat",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": req.message}
#             ],
#             stream=True
#         )
#
#         for chunk in response:
#             if chunk.choices[0].delta.content:
#                 yield chunk.choices[0].delta.content # yield实现一点点吐
#
#     return StreamingResponse(generate(), media_type="text/plain") # StreamingResponse告诉前端这是流

