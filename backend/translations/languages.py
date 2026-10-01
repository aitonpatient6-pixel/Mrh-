LANGUAGES = {
    "fr": "Français",
    "en": "English",
    "pt": "Português",
    "es": "Español",
    "de": "Deutsch",
    "it": "Italiano",
    "ar": "العربية",
    "ru": "Русский",
    "uk": "Українська",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "tr": "Türkçe",
    "ha": "Hausa",
    "yo": "Yorùbá",
    "ig": "Igbo",
    "sw": "Kiswahili",
    "fon": "Fon",
}

DEFAULT_LANGUAGE = "fr"


def is_supported_language(language: str) -> bool:
    return language in LANGUAGES
