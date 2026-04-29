import re
from collections import Counter
from typing import Any


# 根据用户问题，从文本块里找最相关的几块
def tokenize(text: str) -> list[str]:
    """
    轻量分词：
    - 英文 / 数字按单词切
    - 中文按单字切
    第一阶段先不用复杂分词库，保证实现简单、可解释。
    """
    text = text.lower()
    return re.findall(r"[\u4e00-\u9fff]|[a-z0-9_]+", text)


def retrieve_top_chunks(query: str, chunks: list[dict[str, Any]], top_k: int = 3) -> list[dict[str, Any]]:
    """
    根据用户 query，从文本块里检索最相关的 top_k 个片段。

    第一阶段采用“关键词重叠评分”的轻量方案：
    - 不依赖向量数据库
    - 不依赖 embedding
    - 便于快速落地和讲解
    """
    if not chunks:
        return []

    query_tokens = Counter(tokenize(query))

    # 如果 query 太短或没切出有效 token，就直接返回前几个 chunk
    if not query_tokens:
        return chunks[:top_k]

    scored_chunks = []

    for chunk in chunks:
        chunk_text = chunk["text"]
        chunk_tokens = Counter(tokenize(chunk_text))

        # 计算 query token 和 chunk token 的重叠程度
        overlap_score = sum(
            min(query_tokens[token], chunk_tokens[token])
            for token in query_tokens
        )

        # 如果 query 整句出现在 chunk 里，额外加一点分
        phrase_bonus = 2 if query.strip() and query.lower() in chunk_text.lower() else 0

        total_score = overlap_score + phrase_bonus

        if total_score > 0:
            scored_chunks.append({
                **chunk,
                "score": total_score
            })

    if not scored_chunks:
        return chunks[:top_k]

    # 分数高的优先；如果分数相同，则 chunk_id 小的优先
    scored_chunks.sort(key=lambda item: (-item["score"], item["chunk_id"]))

    return scored_chunks[:top_k]