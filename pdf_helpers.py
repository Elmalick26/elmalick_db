"""Shared PDF utilities for Arabic/French bilingual document generation.

All FPDF-based modules in this project share the same font-discovery,
Arabic-detection, and text-reshaping logic.  Import from here instead of
duplicating across modules.

Usage in a PDF class::

    from pdf_helpers import (
        find_arabic_font_path,
        contains_arabic,
        prepare_pdf_text,
        setup_pdf_arabic_font,
        sanitize_latin,
        latin_fallback,
        ARABIC_SUPPORT,
    )
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Optional Arabic support (graceful degradation if libs not installed)
# ---------------------------------------------------------------------------
try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_get_display

    ARABIC_SUPPORT = True
except ModuleNotFoundError:
    ARABIC_SUPPORT = False


# ---------------------------------------------------------------------------
# Font discovery
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_ARABIC_FONT_CANDIDATES = [
    os.path.join(_BASE_DIR, "fonts", "Amiri-Regular.ttf"),
    os.path.join(_BASE_DIR, "fonts", "NotoNaskhArabic-Regular.ttf"),
    os.path.join(_BASE_DIR, "fonts", "Cairo-Regular.ttf"),
    os.path.join(_BASE_DIR, "Fonts", "Amiri", "Amiri-Regular.ttf"),
    os.path.join(_BASE_DIR, "Fonts", "Noto_Naskh_Arabic", "NotoNaskhArabic-Regular.ttf"),
    os.path.join(_BASE_DIR, "Fonts", "Cairo", "Cairo-Regular.ttf"),
]

_cached_font_path: str | None | bool = False  # False = not yet resolved


def find_arabic_font_path() -> str | None:
    """Return the first existing Arabic TTF font path, or None."""
    global _cached_font_path
    if _cached_font_path is False:
        _cached_font_path = next((p for p in _ARABIC_FONT_CANDIDATES if os.path.exists(p)), None)
    return _cached_font_path  # type: ignore[return-value]


def is_arabic_font_ready() -> bool:
    return find_arabic_font_path() is not None


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def contains_arabic(text: object) -> bool:
    """Return True if *text* contains any Arabic/extended-Arabic codepoints."""
    if text is None:
        return False
    s = str(text)
    # FIX 2: Added Arabic Presentation Forms-A (U+FB50–U+FDFF) and
    # Presentation Forms-B (U+FE70–U+FEFF).  Text copy-pasted from rendered
    # Arabic sources is often already in presentation form; without these
    # ranges it bypasses prepare_pdf_text() and arabic_reshaper is not called.
    return any(
        "؀" <= ch <= "ۿ"  # Arabic
        or "ݐ" <= ch <= "ݿ"  # Arabic Supplement
        or "ࢠ" <= ch <= "ࣿ"  # Arabic Extended-A
        or "ﭐ" <= ch <= "﷿"  # Arabic Presentation Forms-A
        or "ﹰ" <= ch <= "﻿"  # Arabic Presentation Forms-B
        for ch in s
    )


def prepare_pdf_text(text: object) -> str:
    """Reshape and apply BiDi algorithm to Arabic text for correct FPDF rendering.

    For non-Arabic text the original string is returned unchanged.
    """
    if text is None:
        return ""
    s = str(text)
    if not s or not contains_arabic(s) or not ARABIC_SUPPORT:
        return s
    try:
        reshaped = arabic_reshaper.reshape(s)
        return _bidi_get_display(reshaped)
    except Exception:
        return s


def sanitize_latin(text: object) -> str:
    """Encode text to latin-1, discarding any characters that cannot be encoded.

    Use only when FPDF is configured without a Unicode font (legacy mode).
    """
    # FIX 1a: Use `is None` instead of truthiness — `not 0` and `not False`
    # are True, so the old guard silently returned "" for those values.
    if text is None:
        return ""
    # FIX 1b: Replace try/except with encode("latin-1","ignore") directly.
    # The old fallback used encode("ascii","ignore") which stripped valid
    # latin-1 accented chars (é, à, ü …) whenever ANY non-latin-1 char was
    # present in the string.  "ignore" on latin-1 drops only the out-of-range
    # characters, so accented French names remain intact.
    return str(text).encode("latin-1", "ignore").decode("latin-1")


def latin_fallback(text: object) -> str:
    """Return a latin-safe version of *text*, or '-' if blank."""
    if text is None:
        return "-"
    s = str(text)
    cleaned = s.encode("latin-1", "ignore").decode("latin-1").strip()
    return cleaned or "-"


# ---------------------------------------------------------------------------
# FPDF font setup
# ---------------------------------------------------------------------------


def setup_pdf_arabic_font(pdf, font_name: str = "ArabicFont") -> bool:
    """Add the Arabic TTF font to *pdf* (an FPDF instance).

    Returns True if the font was successfully registered, False otherwise.

    All four style variants (regular, bold, italic, bold-italic) are registered
    using the same TTF file.  Without this, any call to
    ``set_font(font_name, 'B', ...)`` raises
    ``"Undefined font: arabicfontB"`` because fpdf2 builds the internal font
    key as ``font_name.lower() + style``.
    """
    font_path = find_arabic_font_path()
    if not font_path:
        return False
    try:
        for style in ("", "B", "I", "BI"):
            pdf.add_font(font_name, style, font_path, uni=True)
        return True
    except Exception:
        return False


def get_pdf_font_name(font_name: str = "ArabicFont") -> str:
    """Return the font name to use: *font_name* if Arabic font is ready, else 'Arial'."""
    return font_name if is_arabic_font_ready() else "Arial"
