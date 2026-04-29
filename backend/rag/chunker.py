import re

# 切块模块
# - 先不做复杂的切块策略，目前只做段落优先、固定长度、少量重叠
def normalize_text(text: str) -> str:
    """
    规范化文本：
    - 统一换行
    - 压缩过多空行
    - 去除首尾空白
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text_into_chunks(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """
    将长文本切分成多个文本块，供后续检索使用。

    设计原则：
    - 优先按段落切
    - 每个 chunk 控制在 chunk_size 左右
    - 相邻 chunk 保留少量重叠，减少语义断裂
    """
    text = normalize_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        if not current_chunk:
            current_chunk = paragraph
            continue

        candidate = f"{current_chunk}\n\n{paragraph}"

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            chunks.append(current_chunk)

            # 保留尾部少量重叠，降低切块导致的信息断裂
            overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
            current_chunk = f"{overlap_text}\n\n{paragraph}".strip()

    if current_chunk:
        chunks.append(current_chunk)

    return chunks