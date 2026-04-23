"""Qwen3-TTS Engine wrapper.

Cung cap mot interface thong nhat cho 3 che do cua Qwen3-TTS:
- CustomVoice: 9 giong preset + instruct control
- VoiceDesign: thiet ke giong tu mo ta text
- VoiceClone: clone giong tu reference audio (3+ giay)

Output: numpy float32 array, sample rate = 24000 Hz.
"""

from __future__ import annotations

import numpy as np


QWEN3_LANGUAGES = {
    'zh': 'Chinese',
    'en': 'English',
    'ja': 'Japanese',
    'ko': 'Korean',
    'de': 'German',
    'fr': 'French',
    'ru': 'Russian',
    'pt': 'Portuguese',
    'es': 'Spanish',
    'it': 'Italian',
    'auto': 'Auto',
}

QWEN3_SPEAKERS = [
    'Vivian',
    'Serena',
    'Uncle_Fu',
    'Dylan',
    'Eric',
    'Ryan',
    'Aiden',
    'Ono_Anna',
    'Sohee',
]

QWEN3_REPO_IDS = {
    'custom_voice_1.7b': 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
    'custom_voice_0.6b': 'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',
    'voice_design_1.7b': 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign',
    'voice_clone_1.7b':  'Qwen/Qwen3-TTS-12Hz-1.7B-Base',
    'voice_clone_0.6b':  'Qwen/Qwen3-TTS-12Hz-0.6B-Base',
}


class TTSEngine:
    """Qwen3-TTS Engine wrapper — interface chuan cho app."""

    OUTPUT_SAMPLE_RATE = 24000

    MODE_CUSTOM = 'custom'
    MODE_DESIGN = 'design'
    MODE_CLONE = 'clone'

    def __init__(
        self,
        lang_code: str = 'en',
        device: str | None = None,
        mode: str = 'custom',
        model_size: str = '1.7b',
    ) -> None:
        self.lang_code = lang_code
        self.device = device
        self.mode = mode
        self.model_size = model_size
        self.model = None
        self._current_voice = 'Ryan'
        self._speed = 1.0
        self._instruct = ''
        self._ref_audio = None
        self._ref_text = ''
        self._clone_prompt = None
        self._loaded = False
        self._loaded_repo_id = None

    def _resolve_repo_id(self) -> str:
        size = self.model_size.lower().replace('.', '_')
        if self.mode == self.MODE_CUSTOM:
            key = f'custom_voice_{size}'
        elif self.mode == self.MODE_DESIGN:
            key = 'voice_design_1.7b'
        elif self.mode == self.MODE_CLONE:
            key = f'voice_clone_{size}'
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
        if key not in QWEN3_REPO_IDS:
            key = key.replace('_0_6b', '_1_7b')
        return QWEN3_REPO_IDS[key]

    def load(self) -> None:
        import torch
        from qwen_tts import Qwen3TTSModel

        repo_id = self._resolve_repo_id()

        if self._loaded and self._loaded_repo_id == repo_id and self.model is not None:
            return

        torch.set_float32_matmul_precision('high')

        if self.device is None or self.device == 'auto':
            device_map = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        elif self.device == 'cuda':
            device_map = 'cuda:0'
        else:
            device_map = self.device

        dtype = torch.bfloat16 if 'cuda' in str(device_map) else torch.float32

        try:
            import flash_attn  # noqa: F401
            attn_impl = 'flash_attention_2' if 'cuda' in str(device_map) else 'eager'
        except ImportError:
            attn_impl = 'sdpa'

        self.model = Qwen3TTSModel.from_pretrained(
            repo_id,
            device_map=device_map,
            dtype=dtype,
            attn_implementation=attn_impl,
        )

        try:
            with torch.inference_mode():
                self._warm_up()
        except Exception:
            pass

        self._loaded = True
        self._loaded_repo_id = repo_id
        self._clone_prompt = None

    def _warm_up(self) -> None:
        if self.mode == self.MODE_CUSTOM:
            self.model.generate_custom_voice(
                text="Hello.",
                language=QWEN3_LANGUAGES.get(self.lang_code, 'English'),
                speaker=self._current_voice if self._current_voice in QWEN3_SPEAKERS else 'Ryan',
                max_new_tokens=32,
            )
        elif self.mode == self.MODE_DESIGN:
            self.model.generate_voice_design(
                text="Hello.",
                language=QWEN3_LANGUAGES.get(self.lang_code, 'English'),
                instruct="Natural tone.",
                max_new_tokens=32,
            )

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    def set_language(self, lang_code: str) -> None:
        self.lang_code = lang_code

    def set_device(self, device: str | None) -> None:
        if device == 'auto':
            device = None
        if device != self.device:
            self.device = device
            self._loaded = False
            self.model = None
            self._clone_prompt = None

    def set_voice(self, voice_name: str) -> None:
        self._current_voice = voice_name

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.5, min(2.0, float(speed)))

    def set_mode(self, mode: str) -> None:
        if mode not in (self.MODE_CUSTOM, self.MODE_DESIGN, self.MODE_CLONE):
            raise ValueError(f"Invalid mode: {mode}")
        if mode != self.mode:
            self.mode = mode
            self._loaded = False
            self.model = None
            self._clone_prompt = None

    def set_instruct(self, instruct: str) -> None:
        self._instruct = (instruct or '').strip()

    def set_reference(self, ref_audio, ref_text: str = '') -> None:
        self._ref_audio = ref_audio
        self._ref_text = ref_text or ''
        self._clone_prompt = None

    def create_clone_prompt(self, ref_audio=None, ref_text=None, x_vector_only: bool = False):
        if not self.is_loaded:
            self.load()
        if self.mode != self.MODE_CLONE:
            raise RuntimeError("create_clone_prompt chi dung khi mode='clone'")

        audio = ref_audio if ref_audio is not None else self._ref_audio
        text = ref_text if ref_text is not None else self._ref_text

        self._clone_prompt = self.model.create_voice_clone_prompt(
            ref_audio=audio,
            ref_text=text,
            x_vector_only_mode=x_vector_only,
        )
        return self._clone_prompt

    def generate(self, text: str, voice: str | None = None, speed: float | None = None, split_pattern=None):
        if not self.is_loaded:
            self.load()

        voice = voice or self._current_voice
        speed = speed if speed is not None else self._speed
        text = (text or '').strip()
        if not text:
            return np.zeros(2400, dtype=np.float32)

        lang = QWEN3_LANGUAGES.get(self.lang_code, 'Auto')

        import torch
        with torch.inference_mode():
            if self.mode == self.MODE_CUSTOM:
                speaker = voice if voice in QWEN3_SPEAKERS else 'Ryan'
                wavs, sr = self.model.generate_custom_voice(
                    text=text,
                    language=lang,
                    speaker=speaker,
                    instruct=self._instruct or None,
                )
            elif self.mode == self.MODE_DESIGN:
                wavs, sr = self.model.generate_voice_design(
                    text=text,
                    language=lang,
                    instruct=self._instruct or 'Natural, clear voice.',
                )
            elif self.mode == self.MODE_CLONE:
                if self._clone_prompt is not None:
                    wavs, sr = self.model.generate_voice_clone(
                        text=text,
                        language=lang,
                        voice_clone_prompt=self._clone_prompt,
                    )
                else:
                    if self._ref_audio is None:
                        raise RuntimeError(
                            "Mode clone yeu cau reference audio. "
                            "Goi set_reference() hoac create_clone_prompt() truoc."
                        )
                    wavs, sr = self.model.generate_voice_clone(
                        text=text,
                        language=lang,
                        ref_audio=self._ref_audio,
                        ref_text=self._ref_text,
                    )
            else:
                raise ValueError(f"Invalid mode: {self.mode}")

        audio = wavs[0] if isinstance(wavs, (list, tuple)) else wavs
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.squeeze()

        if sr != self.OUTPUT_SAMPLE_RATE:
            audio = self._resample(audio, sr, self.OUTPUT_SAMPLE_RATE)

        if abs(speed - 1.0) > 1e-3:
            audio = self._apply_speed(audio, speed)

        return audio.astype(np.float32)

    def generate_batch(self, texts: list[str], voice: str | None = None, speed: float | None = None):
        """Batch generation — tan dung throughput cua Qwen3-TTS."""
        if not self.is_loaded:
            self.load()
        if not texts:
            return []

        voice = voice or self._current_voice
        speed = speed if speed is not None else self._speed
        lang = QWEN3_LANGUAGES.get(self.lang_code, 'Auto')
        clean_texts = [(t or '').strip() for t in texts]
        valid_idx = [i for i, t in enumerate(clean_texts) if t]

        if not valid_idx:
            return [np.zeros(2400, dtype=np.float32) for _ in texts]

        import torch
        valid_texts = [clean_texts[i] for i in valid_idx]
        with torch.inference_mode():
            if self.mode == self.MODE_CUSTOM:
                speaker = voice if voice in QWEN3_SPEAKERS else 'Ryan'
                wavs, sr = self.model.generate_custom_voice(
                    text=valid_texts,
                    language=[lang] * len(valid_texts),
                    speaker=[speaker] * len(valid_texts),
                    instruct=self._instruct or None,
                )
            elif self.mode == self.MODE_DESIGN:
                wavs, sr = self.model.generate_voice_design(
                    text=valid_texts,
                    language=[lang] * len(valid_texts),
                    instruct=self._instruct or 'Natural, clear voice.',
                )
            elif self.mode == self.MODE_CLONE:
                if self._clone_prompt is None and self._ref_audio is None:
                    raise RuntimeError("Mode clone yeu cau reference audio.")
                if self._clone_prompt is None:
                    self.create_clone_prompt()
                wavs, sr = self.model.generate_voice_clone(
                    text=valid_texts,
                    language=[lang] * len(valid_texts),
                    voice_clone_prompt=self._clone_prompt,
                )
            else:
                raise ValueError(f"Invalid mode: {self.mode}")

        results: list[np.ndarray] = [np.zeros(2400, dtype=np.float32) for _ in texts]
        for out_i, orig_i in enumerate(valid_idx):
            audio = wavs[out_i]
            if isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()
            audio = np.asarray(audio, dtype=np.float32)
            if audio.ndim > 1:
                audio = audio.squeeze()
            if sr != self.OUTPUT_SAMPLE_RATE:
                audio = self._resample(audio, sr, self.OUTPUT_SAMPLE_RATE)
            if abs(speed - 1.0) > 1e-3:
                audio = self._apply_speed(audio, speed)
            results[orig_i] = audio.astype(np.float32)
        return results

    @staticmethod
    def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        if orig_sr == target_sr:
            return audio
        try:
            from scipy.signal import resample_poly
            from math import gcd
            g = gcd(int(orig_sr), int(target_sr))
            up = int(target_sr // g)
            down = int(orig_sr // g)
            return resample_poly(audio, up, down).astype(np.float32)
        except ImportError:
            ratio = target_sr / orig_sr
            new_len = int(len(audio) * ratio)
            idx = np.linspace(0, len(audio) - 1, new_len).astype(np.int64)
            return audio[idx].astype(np.float32)

    @staticmethod
    def _apply_speed(audio: np.ndarray, speed: float) -> np.ndarray:
        new_len = int(len(audio) / speed)
        if new_len < 1:
            return audio
        idx = np.linspace(0, len(audio) - 1, new_len).astype(np.int64)
        return audio[idx].astype(np.float32)

    def blend_voices(self, voice_a, voice_b, ratio: float = 0.5):
        raise NotImplementedError(
            "Qwen3-TTS khong ho tro voice blend tensor. "
            "Hay dung VoiceDesign mode voi instruct de thiet ke giong moi."
        )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, int(len((text or '').strip()) * 1.0))
