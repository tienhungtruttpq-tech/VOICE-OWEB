"""SRT / TXT parser + SRT exporter cho Qwen3-TTS Studio."""

from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from typing import Iterable


TIMESTAMP_RE = re.compile(
    r'(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})'
)
HTML_TAG_RE = re.compile(r'<[^>]+>')


@dataclass
class Segment:
    index: int
    start_ms: int
    end_ms: int
    text: str
    source_file: str = ''
    status: str = 'pending'
    audio_path: str = ''
    extras: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


def _t2ms(h: int, m: int, s: int, ms: int) -> int:
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def _ms2ts(ms: int) -> str:
    if ms < 0:
        ms = 0
    h = ms // 3_600_000
    m = (ms // 60_000) % 60
    s = (ms // 1000) % 60
    ms_part = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_part:03d}"


def _strip(text: str) -> str:
    return HTML_TAG_RE.sub('', text).strip()


def parse_srt(path: str) -> list[Segment]:
    """Parse SRT file → list Segment. Ho tro BOM, multi-line, HTML tags."""
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        content = f.read()

    segments: list[Segment] = []
    blocks = re.split(r'\r?\n\r?\n+', content.strip())
    source = os.path.basename(path)

    idx_counter = 0
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        ts_line_idx = 0
        if lines[0].strip().isdigit() and len(lines) > 1:
            ts_line_idx = 1
        if ts_line_idx >= len(lines):
            continue
        m = TIMESTAMP_RE.search(lines[ts_line_idx])
        if not m:
            continue
        start_ms = _t2ms(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        end_ms = _t2ms(int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8)))
        text = _strip(' '.join(lines[ts_line_idx + 1:]))
        if not text:
            continue
        idx_counter += 1
        segments.append(Segment(
            index=idx_counter,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            source_file=source,
        ))
    return segments


def parse_txt(path: str) -> list[Segment]:
    """Parse TXT → moi dong 1 Segment (timestamps se duoc tao sau tu audio thuc te)."""
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        raw_lines = [ln.strip() for ln in f.readlines()]
    lines = [ln for ln in raw_lines if ln]
    source = os.path.basename(path)
    return [
        Segment(
            index=i + 1,
            start_ms=0,
            end_ms=0,
            text=ln,
            source_file=source,
        )
        for i, ln in enumerate(lines)
    ]


def parse_file(path: str) -> list[Segment]:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.srt':
        return parse_srt(path)
    if ext in ('.txt', '.text'):
        return parse_txt(path)
    raise ValueError(f"Unsupported file extension: {ext}")


def export_srt(segments: Iterable[Segment], output_path: str) -> None:
    """Export list Segment → file SRT."""
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_ms2ts(seg.start_ms)} --> {_ms2ts(seg.end_ms)}")
        lines.append(seg.text)
        lines.append('')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines).rstrip() + '\n')


def build_srt_from_durations(
    texts: list[str],
    durations_ms: list[int],
    gap_ms: int = 200,
) -> list[Segment]:
    """Tao SRT tu text + duration thuc te cua tung audio."""
    segs: list[Segment] = []
    cursor = 0
    for i, (text, dur) in enumerate(zip(texts, durations_ms), start=1):
        start = cursor
        end = start + max(0, int(dur))
        segs.append(Segment(index=i, start_ms=start, end_ms=end, text=text))
        cursor = end + gap_ms
    return segs


class SRTParser:
    """Lop wrapper tien dung — moi method tra ve list[Segment]."""

    @staticmethod
    def parse_file(path: str) -> list[Segment]:
        return parse_file(path)

    @staticmethod
    def parse_srt(path: str) -> list[Segment]:
        return parse_srt(path)

    @staticmethod
    def parse_txt(path: str) -> list[Segment]:
        return parse_txt(path)

    @staticmethod
    def export_srt(segments, output_path: str) -> None:
        return export_srt(segments, output_path)

    @staticmethod
    def build_from_durations(texts: list[str], durations_ms: list[int], gap_ms: int = 200) -> list[Segment]:
        return build_srt_from_durations(texts, durations_ms, gap_ms)
