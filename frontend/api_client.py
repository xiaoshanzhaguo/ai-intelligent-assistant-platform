import json

import requests


BACKEND_BASE_URL = "http://127.0.0.1:8000"


def index_uploaded_document(session_id: str, file_name: str, document_text: str) -> tuple[bool, str]:
    """
    调用后端 /index_document 接口，为当前会话建立临时文档索引。
    """
    response = requests.post(
        "http://127.0.0.1:8000/index_document",
        json={
            "session_id": session_id,
            "file_name": file_name,
            "document_text": document_text
        },
        timeout=60 # 请求最多等60秒
    )

    if response.status_code != 200:
        return False, f"文档索引失败: {response.text}"

    result = response.json()
    return True, f"文档索引完成，共切分 {result['chunk_count']} 个文本块。"


def clear_indexed_document(session_id: str) -> None:
    """
    调用后端清理接口，删除某个 session 对应的临时文档索引。

    说明：
    - 该函数不阻断主流程
    - 即使清理失败，也不影响前端继续新建会话
    """
    try:
        requests.delete(
            f"http://127.0.0.1:8000/clear_document/{session_id}",
            timeout=10
        )
    except Exception:
        # 第一阶段先做静默失败，避免清理动作影响主流程
        pass


def post_stream_request(payload: dict, is_workflow: bool):
    """
    根据任务类型发送流式请求。
    """
    endpoint = "/workflow_stream" if is_workflow else "/chat_stream"
    return requests.post(
        f"{BACKEND_BASE_URL}{endpoint}",
        json=payload,
        stream=True,
        timeout=120
    )


def iter_sse_events(response):
    """
    逐行解析 SSE 响应，产出事件字典。
    """
    # 逐行解析 SSE 事件流。chunk_size=1 可以避免小块 SSE 被 requests 缓冲太久。
    for raw_line in response.iter_lines(chunk_size=1, decode_unicode=True):
        # 如果这一行是空的，就不处理。SSE 里经常会有空行，用来分隔事件。
        if not raw_line:
            # 跳过当前这一轮循环，直接进入下一轮
            continue

        raw_text = raw_line.strip()

        # SSE 标准格式：data: {...}
        if not raw_text.startswith("data: "):
            continue

        # 把前面的 "data: " 去掉
        json_text = raw_text[6:]

        try:
            # 把字符串形式的 JSON 变成 Python 可操作的数据结构
            event = json.loads(json_text)
        except json.JSONDecodeError:
            continue
