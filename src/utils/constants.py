"""Constants cho ung dung Qwen3-TTS Studio."""

APP_NAME = 'Qwen3-TTS Studio'
APP_VERSION = '1.0.0'

# ============================================================================
# Qwen3-TTS supported languages (ten tieng Anh, engine nhan dang)
# ============================================================================
LANGUAGES = {
    'auto': 'Auto-detect',
    'zh':   'Chinese (中文)',
    'en':   'English',
    'ja':   'Japanese (日本語)',
    'ko':   'Korean (한국어)',
    'de':   'German (Deutsch)',
    'fr':   'French (Français)',
    'ru':   'Russian (Русский)',
    'pt':   'Portuguese (Português)',
    'es':   'Spanish (Español)',
    'it':   'Italian (Italiano)',
}

DEFAULT_LANGUAGE = 'en'

# ============================================================================
# Qwen3-TTS CustomVoice — 9 giong premium
# ============================================================================
QWEN3_CUSTOM_SPEAKERS = {
    'Vivian':    {'gender': 'female', 'native': 'zh',       'desc': 'Bright, slightly edgy young female voice.'},
    'Serena':    {'gender': 'female', 'native': 'zh',       'desc': 'Warm, gentle young female voice.'},
    'Uncle_Fu':  {'gender': 'male',   'native': 'zh',       'desc': 'Seasoned male voice with low, mellow timbre.'},
    'Dylan':     {'gender': 'male',   'native': 'zh-BJ',    'desc': 'Youthful Beijing male with clear, natural timbre.'},
    'Eric':      {'gender': 'male',   'native': 'zh-SC',    'desc': 'Lively Chengdu male, slightly husky brightness.'},
    'Ryan':      {'gender': 'male',   'native': 'en',       'desc': 'Dynamic male voice with strong rhythmic drive.'},
    'Aiden':     {'gender': 'male',   'native': 'en',       'desc': 'Sunny American male, clear midrange.'},
    'Ono_Anna':  {'gender': 'female', 'native': 'ja',       'desc': 'Playful Japanese female, light nimble timbre.'},
    'Sohee':     {'gender': 'female', 'native': 'ko',       'desc': 'Warm Korean female, rich emotion.'},
}


def get_speakers_for_language(lang_code):
    """Tra ve danh sach speakers phu hop voi ngon ngu."""
    natives = [s for s, info in QWEN3_CUSTOM_SPEAKERS.items()
               if info['native'].startswith(lang_code)]
    return natives if natives else list(QWEN3_CUSTOM_SPEAKERS.keys())


VOICES_FALLBACK = {
    lang: {
        'female': [s for s, i in QWEN3_CUSTOM_SPEAKERS.items()
                   if i['gender'] == 'female' and (i['native'].startswith(lang) or lang == 'auto')],
        'male':   [s for s, i in QWEN3_CUSTOM_SPEAKERS.items()
                   if i['gender'] == 'male'   and (i['native'].startswith(lang) or lang == 'auto')],
    }
    for lang in LANGUAGES
}

# ============================================================================
# TTS mode
# ============================================================================
TTS_MODES = {
    'custom': 'Custom Voice (9 preset speakers + instruct)',
    'design': 'Voice Design (mo ta giong bang text)',
    'clone':  'Voice Clone (clone tu reference audio)',
}
DEFAULT_MODE = 'custom'

# ============================================================================
# Model size
# ============================================================================
MODEL_SIZES = {
    '0.6b': '0.6B (nhanh, VRAM ~4GB)',
    '1.7b': '1.7B (chat luong cao, VRAM ~8GB, khuyen dung)',
}
DEFAULT_MODEL_SIZE = '1.7b'

# ============================================================================
# Device choices
# ============================================================================
DEVICES = {
    'auto': 'Auto-detect',
    'cuda': 'NVIDIA GPU (CUDA)',
    'cpu':  'CPU',
}
DEFAULT_DEVICE = 'auto'

# ============================================================================
# Instruct presets
# ============================================================================
INSTRUCT_PRESETS = {
    'None':          '',
    'Happy':         'Speak in a cheerful, upbeat tone with clear enthusiasm.',
    'Sad':           'Speak softly with a melancholic, gentle tone.',
    'Angry':         'Speak with a firm, intense, and forceful tone.',
    'Calm':          'Speak in a calm, steady, and reassuring tone.',
    'Whisper':       'Whisper softly as if sharing a secret.',
    'Excited':       'Speak rapidly with high energy and excitement.',
    'Serious':       'Speak in a serious, authoritative, news-anchor tone.',
    'Storytelling':  'Narrate with warmth and expressive pacing, like a storyteller.',
}

# ============================================================================
# Audio defaults (Qwen3-TTS output 24kHz)
# ============================================================================
DEFAULT_SAMPLE_RATE = 24000
SUPPORTED_SAMPLE_RATES = [16000, 22050, 24000, 44100, 48000]
DEFAULT_OUTPUT_FORMAT = 'wav'
SUPPORTED_OUTPUT_FORMATS = ['wav', 'mp3', 'flac', 'ogg']

# Speed range
MIN_SPEED = 0.5
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0

# ============================================================================
# HuggingFace repo IDs
# ============================================================================
QWEN3_REPO_IDS = {
    'tokenizer':         'Qwen/Qwen3-TTS-Tokenizer-12Hz',
    'custom_voice_1.7b': 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
    'custom_voice_0.6b': 'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',
    'voice_design_1.7b': 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign',
    'voice_clone_1.7b':  'Qwen/Qwen3-TTS-12Hz-1.7B-Base',
    'voice_clone_0.6b':  'Qwen/Qwen3-TTS-12Hz-0.6B-Base',
}

# ============================================================================
# UI defaults
# ============================================================================
MAX_TEXT_CHARS_PER_SEGMENT = 500
SILENCE_BETWEEN_JOIN_MS = 250
UI_REFRESH_INTERVAL_MS = 500
UI_ROWS_PER_TICK = 30

# ============================================================================
# Helpers
# ============================================================================


def fetch_speakers_from_model(model):
    """Lay danh sach speakers tu model.get_supported_speakers() (khi model da load)."""
    try:
        return list(model.get_supported_speakers())
    except Exception:
        return list(QWEN3_CUSTOM_SPEAKERS.keys())


def fetch_languages_from_model(model):
    """Lay danh sach languages tu model.get_supported_languages()."""
    try:
        return list(model.get_supported_languages())
    except Exception:
        return [v for k, v in LANGUAGES.items() if k != 'auto']
