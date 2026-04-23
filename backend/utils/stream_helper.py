from backend.schema.chat_schema import StreamEvent

def to_sse(event: StreamEvent) -> str:
    """
    将流式事件对象转换为 SSE　格式字符串。

    SSE (Server-Sent Events) 要求每条消息以 `data:` 开头，
    并以两个换行符结尾，用于前端持续接收流式事件。
    """
    return f"data: {event.model_dump_json()}\n\n"