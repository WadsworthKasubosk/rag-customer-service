from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def split_text(text: str) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    step = max(CHUNK_SIZE - CHUNK_OVERLAP, 1)

    while start < len(cleaned):
        end = min(start + CHUNK_SIZE, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start += step

    return chunks
