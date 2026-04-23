"""Smart text chunking cho TTS — tranh cau qua dai."""

from __future__ import annotations

import re


SENTENCE_END_RE = re.compile(r'([.!?。！？]+[\'")\]]*\s+)')
CLAUSE_SPLIT_RE = re.compile(r'([,;，；、]\s+)')


def smart_chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Chia text thanh cac chunk ngan hon max_chars, uu tien cat tai dau cau."""
    text = (text or '').strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    # Tach theo cau truoc
    parts = SENTENCE_END_RE.split(text)
    sentences: list[str] = []
    buf = ''
    for p in parts:
        if not p:
            continue
        if SENTENCE_END_RE.match(p):
            buf += p
            sentences.append(buf.strip())
            buf = ''
        else:
            buf = p
    if buf.strip():
        sentences.append(buf.strip())

    chunks: list[str] = []
    current = ''
    for s in sentences:
        if len(s) > max_chars:
            # Chunk theo dau phay
            sub_parts = CLAUSE_SPLIT_RE.split(s)
            sub_buf = ''
            for sp in sub_parts:
                if not sp:
                    continue
                if len(sub_buf) + len(sp) > max_chars and sub_buf:
                    chunks.append(sub_buf.strip())
                    sub_buf = sp
                else:
                    sub_buf += sp
            if sub_buf.strip():
                chunks.append(sub_buf.strip())
            continue
        if len(current) + len(s) + 1 <= max_chars:
            current = (current + ' ' + s).strip() if current else s
        else:
            if current:
                chunks.append(current.strip())
            current = s
    if current.strip():
        chunks.append(current.strip())

    # Fallback hard split neu con chunk qua dai
    result: list[str] = []
    for c in chunks:
        while len(c) > max_chars:
            result.append(c[:max_chars])
            c = c[max_chars:]
        if c:
            result.append(c)
    return result
