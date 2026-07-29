def fixed_length_chunk(
    text: str,
    chunk_size: int = 512,
    overlap: int = 128,
) -> list[str]:
    """
    固定长度分块 + 重叠。
    尽量在换行符处断开以保留语义完整性。
    """
    if not text:
        return [""]

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Try to break at a newline, but only if it's past the midpoint
        if end < text_len:
            break_pos = text.rfind("\n", start, end)
            if break_pos > start + chunk_size // 2:
                end = break_pos + 1

        chunks.append(text[start:end])
        start = end - overlap

        if start >= text_len or end == text_len:
            break

    return chunks if chunks else [text]
