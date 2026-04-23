"""Load / save settings."""

from __future__ import annotations

import json
import os
from typing import Any


DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.qwen3_tts_studio.json')


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: dict[str, Any], path: str = DEFAULT_CONFIG_PATH) -> None:
    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
