from typing import Any


# 内存级文档存储
# 第一阶段只做“单会话 + 临时索引”，不做数据库持久化
RAG_STORE: dict[str, dict[str, Any]] = {}


def save_document_chunks(session_id: str, file_name: str | None, chunks: list[str]) -> None:
    """
    将切分后的文本块存入当前 session 对应的内存存储。
    如果同一个 session 再次上传文档，则直接覆盖旧内容。
    """
    RAG_STORE[session_id] = {
        "file_name": file_name,
        "chunks": [
            {
                "chunk_id": index + 1,
                "text": chunk
            }
            for index, chunk in enumerate(chunks)
        ]
    }


def get_document_chunks(session_id: str) -> list[dict[str, Any]]:
    """
    获取某个 session 当前已索引的文本块列表。
    """
    return RAG_STORE.get(session_id, {}).get("chunks", [])


def clear_document_chunks(session_id: str) -> None:
    """
    清理某个 session 已索引的文档。
    """
    RAG_STORE.pop(session_id, None)