"""Voice library — quan ly custom voices + reference audio cho voice clone."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class VoiceProfile:
    id: str                # unique key
    name: str              # display name
    mode: str              # 'custom' | 'design' | 'clone'
    speaker: str = ''      # Qwen3 speaker (mode=custom)
    language: str = 'en'
    instruct: str = ''     # natural-language instruction
    ref_audio: str = ''    # path file .wav (mode=clone)
    ref_text: str = ''     # transcript (mode=clone)
    notes: str = ''
    extras: dict = field(default_factory=dict)


class VoiceLibrary:
    def __init__(self, data_path: str, voices_dir: str) -> None:
        self.data_path = data_path
        self.voices_dir = voices_dir
        os.makedirs(self.voices_dir, exist_ok=True)
        self.profiles: dict[str, VoiceProfile] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.data_path):
            self.profiles = {}
            return
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception:
            self.profiles = {}
            return
        self.profiles = {
            vid: VoiceProfile(**{**{'id': vid}, **data})
            for vid, data in (raw.get('voices') or {}).items()
        }

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.data_path) or '.', exist_ok=True)
        payload = {'voices': {vid: asdict(p) for vid, p in self.profiles.items()}}
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def add(self, profile: VoiceProfile, copy_ref_audio: bool = True) -> VoiceProfile:
        if copy_ref_audio and profile.ref_audio and os.path.exists(profile.ref_audio):
            dst = os.path.join(self.voices_dir, f"{profile.id}.wav")
            if os.path.abspath(profile.ref_audio) != os.path.abspath(dst):
                shutil.copy2(profile.ref_audio, dst)
            profile.ref_audio = dst
        self.profiles[profile.id] = profile
        self.save()
        return profile

    def remove(self, voice_id: str) -> None:
        p = self.profiles.pop(voice_id, None)
        if p and p.ref_audio and p.ref_audio.startswith(self.voices_dir):
            try:
                os.remove(p.ref_audio)
            except OSError:
                pass
        self.save()

    def get(self, voice_id: str) -> Optional[VoiceProfile]:
        return self.profiles.get(voice_id)

    def list(self) -> list[VoiceProfile]:
        return list(self.profiles.values())

    def filter_by_mode(self, mode: str) -> list[VoiceProfile]:
        return [p for p in self.profiles.values() if p.mode == mode]
