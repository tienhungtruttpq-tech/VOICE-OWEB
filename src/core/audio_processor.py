"""Audio xu ly: join, normalize, resample, convert format."""

from __future__ import annotations

import os
from typing import Iterable

import numpy as np


def save_wav(path: str, audio: np.ndarray, sample_rate: int = 24000) -> None:
    import soundfile as sf
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    sf.write(path, audio.astype(np.float32), sample_rate, subtype='PCM_16')


def load_wav(path: str) -> tuple[np.ndarray, int]:
    import soundfile as sf
    audio, sr = sf.read(path, dtype='float32', always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float32), int(sr)


def duration_ms(audio: np.ndarray, sample_rate: int = 24000) -> int:
    if audio is None or len(audio) == 0:
        return 0
    return int(round(len(audio) / sample_rate * 1000))


def normalize_audio(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Chuan hoa peak ve target_peak (tranh clipping)."""
    if audio is None or len(audio) == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-6:
        return audio
    gain = target_peak / peak
    if gain >= 1.0:
        return audio  # already quieter than target
    return (audio * gain).astype(np.float32)


def resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio.astype(np.float32)
    try:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(int(orig_sr), int(target_sr))
        return resample_poly(audio, target_sr // g, orig_sr // g).astype(np.float32)
    except ImportError:
        ratio = target_sr / orig_sr
        new_len = int(len(audio) * ratio)
        idx = np.linspace(0, len(audio) - 1, new_len).astype(np.int64)
        return audio[idx].astype(np.float32)


def resample_file(input_path: str, output_path: str, target_sr: int) -> None:
    audio, sr = load_wav(input_path)
    audio = resample(audio, sr, target_sr)
    save_wav(output_path, audio, target_sr)


def join_audio_files(
    files: Iterable[str],
    output_path: str,
    silence_ms: int = 250,
    sample_rate: int = 24000,
) -> int:
    """Ghep nhieu file WAV voi khoang im lang giua. Tra ve tong duration_ms."""
    chunks: list[np.ndarray] = []
    silence = np.zeros(int(sample_rate * silence_ms / 1000), dtype=np.float32)
    total_ms = 0
    for i, path in enumerate(files):
        if not os.path.exists(path):
            continue
        audio, sr = load_wav(path)
        if sr != sample_rate:
            audio = resample(audio, sr, sample_rate)
        chunks.append(audio)
        total_ms += duration_ms(audio, sample_rate)
        if silence_ms > 0 and i < len(list(files)) - 1:
            chunks.append(silence)
            total_ms += silence_ms
    if not chunks:
        return 0
    merged = np.concatenate(chunks)
    save_wav(output_path, merged, sample_rate)
    return total_ms


def join_audio_arrays(
    arrays: list[np.ndarray],
    output_path: str | None = None,
    silence_ms: int = 250,
    sample_rate: int = 24000,
) -> tuple[np.ndarray, list[int]]:
    """Ghep list numpy arrays → 1 array. Tra ve (merged, durations_ms[])."""
    silence = np.zeros(int(sample_rate * silence_ms / 1000), dtype=np.float32)
    chunks: list[np.ndarray] = []
    durations: list[int] = []
    for i, audio in enumerate(arrays):
        if audio is None or len(audio) == 0:
            durations.append(0)
            continue
        chunks.append(audio)
        durations.append(duration_ms(audio, sample_rate))
        if silence_ms > 0 and i < len(arrays) - 1:
            chunks.append(silence)
    merged = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    if output_path:
        save_wav(output_path, merged, sample_rate)
    return merged, durations


def convert_format(input_path: str, output_path: str) -> None:
    """Convert wav → mp3/ogg/flac (dung pydub + ffmpeg)."""
    ext = os.path.splitext(output_path)[1].lower().lstrip('.')
    if ext == 'wav':
        audio, sr = load_wav(input_path)
        save_wav(output_path, audio, sr)
        return
    try:
        from pydub import AudioSegment
    except ImportError as e:
        raise RuntimeError("Can pydub + ffmpeg de convert format khong phai wav") from e
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format=ext)
