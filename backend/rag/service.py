from backend.rag.retriever import retrieve_top_chunks
from backend.rag.store import get_document_chunks

def build_rag_context(session_id: str | None, query: str, top_k: int = 3) -> str:
    """
    根据 session_id 和 query, 构造可直接拼接进 prompt 的检索上下文。
    """
    if not session_id:
        return ""

    chunks = get_document_chunks(session_id)
    if not chunks:
        return ""

    matched_chunks = retrieve_top_chunks(query=query, chunks=chunks, top_k=top_k)
    if not matched_chunks:
        return ""

    return "\n\n".join(
        [
            f"[参考片段 {index + 1}]\n{item['text']}"
            for index, item in enumerate(matched_chunks)
        ]
    )
