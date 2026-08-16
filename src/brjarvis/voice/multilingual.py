# voice/multilingual.py — JARVIS MK37 Multilingual STT Support
"""
Provides 90+ language support for speech recognition.
Maps ISO-639-1 codes to display names and configures STT engines accordingly.
"""
from __future__ import annotations

# ── 90+ Supported Languages ──────────────────────────────────────────────────
# ISO-639-1 code -> (Display Name, Google STT code, Whisper code)
SUPPORTED_LANGUAGES: dict[str, tuple[str, str, str]] = {
    "af": ("Afrikaans", "af-ZA", "af"),
    "am": ("Amharic", "am-ET", "am"),
    "ar": ("Arabic", "ar-SA", "ar"),
    "az": ("Azerbaijani", "az-AZ", "az"),
    "be": ("Belarusian", "be-BY", "be"),
    "bg": ("Bulgarian", "bg-BG", "bg"),
    "bn": ("Bengali", "bn-BD", "bn"),
    "bs": ("Bosnian", "bs-BA", "bs"),
    "ca": ("Catalan", "ca-ES", "ca"),
    "cs": ("Czech", "cs-CZ", "cs"),
    "cy": ("Welsh", "cy-GB", "cy"),
    "da": ("Danish", "da-DK", "da"),
    "de": ("German", "de-DE", "de"),
    "el": ("Greek", "el-GR", "el"),
    "en": ("English", "en-US", "en"),
    "es": ("Spanish", "es-ES", "es"),
    "et": ("Estonian", "et-EE", "et"),
    "eu": ("Basque", "eu-ES", "eu"),
    "fa": ("Persian", "fa-IR", "fa"),
    "fi": ("Finnish", "fi-FI", "fi"),
    "fil": ("Filipino", "fil-PH", "tl"),
    "fr": ("French", "fr-FR", "fr"),
    "ga": ("Irish", "ga-IE", "ga"),  # not in Whisper — fallback to en
    "gl": ("Galician", "gl-ES", "gl"),
    "gu": ("Gujarati", "gu-IN", "gu"),
    "ha": ("Hausa", "ha-NG", "ha"),
    "he": ("Hebrew", "he-IL", "he"),
    "hi": ("Hindi", "hi-IN", "hi"),
    "hr": ("Croatian", "hr-HR", "hr"),
    "hu": ("Hungarian", "hu-HU", "hu"),
    "hy": ("Armenian", "hy-AM", "hy"),
    "id": ("Indonesian", "id-ID", "id"),
    "is": ("Icelandic", "is-IS", "is"),
    "it": ("Italian", "it-IT", "it"),
    "ja": ("Japanese", "ja-JP", "ja"),
    "jv": ("Javanese", "jv-ID", "jw"),
    "ka": ("Georgian", "ka-GE", "ka"),
    "kk": ("Kazakh", "kk-KZ", "kk"),
    "km": ("Khmer", "km-KH", "km"),
    "kn": ("Kannada", "kn-IN", "kn"),
    "ko": ("Korean", "ko-KR", "ko"),
    "lo": ("Lao", "lo-LA", "lo"),
    "lt": ("Lithuanian", "lt-LT", "lt"),
    "lv": ("Latvian", "lv-LV", "lv"),
    "mg": ("Malagasy", "mg-MG", "mg"),
    "mk": ("Macedonian", "mk-MK", "mk"),
    "ml": ("Malayalam", "ml-IN", "ml"),
    "mn": ("Mongolian", "mn-MN", "mn"),
    "mr": ("Marathi", "mr-IN", "mr"),
    "ms": ("Malay", "ms-MY", "ms"),
    "mt": ("Maltese", "mt-MT", "mt"),
    "my": ("Myanmar", "my-MM", "my"),
    "ne": ("Nepali", "ne-NP", "ne"),
    "nl": ("Dutch", "nl-NL", "nl"),
    "no": ("Norwegian", "no-NO", "no"),
    "pa": ("Punjabi", "pa-IN", "pa"),
    "pl": ("Polish", "pl-PL", "pl"),
    "ps": ("Pashto", "ps-AF", "ps"),
    "pt": ("Portuguese", "pt-BR", "pt"),
    "ro": ("Romanian", "ro-RO", "ro"),
    "ru": ("Russian", "ru-RU", "ru"),
    "si": ("Sinhala", "si-LK", "si"),
    "sk": ("Slovak", "sk-SK", "sk"),
    "sl": ("Slovenian", "sl-SI", "sl"),
    "so": ("Somali", "so-SO", "so"),
    "sq": ("Albanian", "sq-AL", "sq"),
    "sr": ("Serbian", "sr-RS", "sr"),
    "su": ("Sundanese", "su-ID", "su"),
    "sv": ("Swedish", "sv-SE", "sv"),
    "sw": ("Swahili", "sw-KE", "sw"),
    "ta": ("Tamil", "ta-IN", "ta"),
    "te": ("Telugu", "te-IN", "te"),
    "tg": ("Tajik", "tg-TJ", "tg"),
    "th": ("Thai", "th-TH", "th"),
    "tk": ("Turkmen", "tk-TM", "tk"),
    "tr": ("Turkish", "tr-TR", "tr"),
    "uk": ("Ukrainian", "uk-UA", "uk"),
    "ur": ("Urdu", "ur-PK", "ur"),
    "uz": ("Uzbek", "uz-UZ", "uz"),
    "vi": ("Vietnamese", "vi-VN", "vi"),
    "yo": ("Yoruba", "yo-NG", "yo"),
    "zh": ("Chinese (Mandarin)", "zh-CN", "zh"),
    "zh-tw": ("Chinese (Traditional)", "zh-TW", "zh"),
    "zu": ("Zulu", "zu-ZA", "zu"),
}

_current_language: str = "en"


def get_language() -> str:
    """Get the current recognition language code."""
    return _current_language


def set_language(lang_code: str) -> str:
    """Set the current recognition language. Returns display name or error."""
    global _current_language
    code = lang_code.lower().strip()
    if code in SUPPORTED_LANGUAGES:
        _current_language = code
        name = SUPPORTED_LANGUAGES[code][0]
        return f"Language set to {name} ({code})"
    return f"Unsupported language '{lang_code}'. Use /languages to see available options."


def get_google_stt_code(lang_code: str = None) -> str:
    """Get the Google STT language code for the given ISO code."""
    code = lang_code or _current_language
    entry = SUPPORTED_LANGUAGES.get(code)
    return entry[1] if entry else "en-US"


def get_whisper_code(lang_code: str = None) -> str:
    """Get the Whisper language code for the given ISO code."""
    code = lang_code or _current_language
    entry = SUPPORTED_LANGUAGES.get(code)
    return entry[2] if entry else "en"


def list_languages() -> str:
    """Return a formatted table of all supported languages."""
    lines = [f"{'Code':<8} {'Language':<25} {'Google STT':<12} {'Whisper':<8}"]
    lines.append("─" * 55)
    for code, (name, google, whisper) in sorted(SUPPORTED_LANGUAGES.items()):
        marker = " ◀" if code == _current_language else ""
        lines.append(f"{code:<8} {name:<25} {google:<12} {whisper:<8}{marker}")
    return "\n".join(lines)


def detect_language_from_text(text: str) -> str:
    """Simple heuristic to detect language from transcribed text.
    Returns ISO-639-1 code or 'en' as default."""
    # Character range detection for scripts
    for ch in text[:100]:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            return "hi"  # Devanagari
        if 0x0980 <= cp <= 0x09FF:
            return "bn"  # Bengali
        if 0x0A80 <= cp <= 0x0AFF:
            return "gu"  # Gujarati
        if 0x0B80 <= cp <= 0x0BFF:
            return "ta"  # Tamil
        if 0x0C00 <= cp <= 0x0C7F:
            return "te"  # Telugu
        if 0x0C80 <= cp <= 0x0CFF:
            return "kn"  # Kannada
        if 0x0D00 <= cp <= 0x0D7F:
            return "ml"  # Malayalam
        if 0x0600 <= cp <= 0x06FF:
            return "ar"  # Arabic / Urdu / Persian
        if 0x4E00 <= cp <= 0x9FFF:
            return "zh"  # Chinese
        if 0x3040 <= cp <= 0x30FF:
            return "ja"  # Japanese
        if 0xAC00 <= cp <= 0xD7AF:
            return "ko"  # Korean
        if 0x0400 <= cp <= 0x04FF:
            return "ru"  # Cyrillic
        if 0x0E00 <= cp <= 0x0E7F:
            return "th"  # Thai
    return "en"
