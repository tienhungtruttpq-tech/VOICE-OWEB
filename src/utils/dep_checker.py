"""Kiem tra dependencies + device availability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DepStatus:
    name: str
    available: bool
    version: str = ''
    note: str = ''


def check_dependencies() -> list[DepStatus]:
    results: list[DepStatus] = []

    def _try(name: str, import_expr: str, version_attr: str = '__version__', note: str = ''):
        try:
            mod = __import__(import_expr)
            for part in import_expr.split('.')[1:]:
                mod = getattr(mod, part)
            ver = getattr(mod, version_attr, '')
            results.append(DepStatus(name, True, str(ver), note))
        except Exception as e:
            results.append(DepStatus(name, False, '', str(e)))

    _try('PyQt6', 'PyQt6.QtCore', 'PYQT_VERSION_STR')
    _try('numpy', 'numpy')
    _try('scipy', 'scipy')
    _try('soundfile', 'soundfile')
    _try('torch', 'torch')
    _try('transformers', 'transformers')
    _try('qwen_tts', 'qwen_tts', note='Qwen3-TTS engine')
    _try('flash_attn', 'flash_attn', note='Optional GPU speedup')
    _try('huggingface_hub', 'huggingface_hub')

    return results


def torch_device_info() -> dict:
    try:
        import torch
    except ImportError:
        return {'available': False}
    info = {
        'available': True,
        'cuda_available': torch.cuda.is_available(),
        'cuda_device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    if info['cuda_available']:
        info['cuda_device_name'] = torch.cuda.get_device_name(0)
    return info
