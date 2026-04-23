"""Utility helpers."""

from __future__ import annotations

import os
import re


SAFE_NAME_RE = re.compile(r'[^A-Za-z0-9._-]+')


def safe_filename(name: str, fallback: str = 'output') -> str:
    stem = SAFE_NAME_RE.sub('_', name).strip('_')
    return stem or fallback


def ensure_dir(path: str) -> str:
    if path:
        os.makedirs(path, exist_ok=True)
    return path


def format_duration_ms(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def export_project(path: str, payload: dict) -> None:
    import json
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def import_project(path: str) -> dict:
    import json
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
