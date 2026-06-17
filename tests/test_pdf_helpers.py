"""Tests for pdf_helpers — pure-Python utilities, no Qt, no real FPDF required."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Isolation helpers
# ---------------------------------------------------------------------------


def _fresh_module():
    """Import pdf_helpers fresh (bypass module-level cache side-effects)."""
    # Ensure the project root is on sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import importlib

    import pdf_helpers

    importlib.reload(pdf_helpers)
    return pdf_helpers


# ---------------------------------------------------------------------------
# contains_arabic
# ---------------------------------------------------------------------------


class TestContainsArabic:

    def setup_method(self):
        from pdf_helpers import contains_arabic

        self.fn = contains_arabic

    def test_arabic_text_detected(self):
        assert self.fn("مرحبا") is True

    def test_latin_text_not_arabic(self):
        assert self.fn("Bonjour") is False

    def test_mixed_text_detected(self):
        assert self.fn("Classe 6ème — السادس") is True

    def test_numbers_not_arabic(self):
        assert self.fn("12345") is False

    def test_empty_string(self):
        assert self.fn("") is False

    def test_none_input(self):
        assert self.fn(None) is False

    def test_integer_input_not_arabic(self):
        assert self.fn(42) is False

    def test_arabic_numeral_unicode_detected(self):
        # U+0660 ARABIC-INDIC DIGIT ZERO falls in 0x0600–0x06FF range
        assert self.fn("٠") is True

    def test_whitespace_only(self):
        assert self.fn("   \t\n") is False


# ---------------------------------------------------------------------------
# sanitize_latin
# ---------------------------------------------------------------------------


class TestSanitizeLatin:

    def setup_method(self):
        from pdf_helpers import sanitize_latin

        self.fn = sanitize_latin

    def test_pure_latin_unchanged(self):
        assert self.fn("Résultat") == "Résultat"

    def test_arabic_stripped(self):
        result = self.fn("مرحبا")
        # Arabic codepoints can't be latin-1 encoded → stripped to empty string
        assert result == ""

    def test_empty_string(self):
        assert self.fn("") == ""

    def test_none_returns_empty(self):
        assert self.fn(None) == ""

    def test_mixed_keeps_latin_part(self):
        result = self.fn("Nom: محمد")
        # Arabic characters dropped, latin part kept
        assert "Nom:" in result

    def test_accented_chars_kept(self):
        result = self.fn("élève Ü ñ")
        assert "élève" in result


# ---------------------------------------------------------------------------
# latin_fallback
# ---------------------------------------------------------------------------


class TestLatinFallback:

    def setup_method(self):
        from pdf_helpers import latin_fallback

        self.fn = latin_fallback

    def test_latin_text_returned(self):
        assert self.fn("Dupont") == "Dupont"

    def test_none_returns_dash(self):
        assert self.fn(None) == "-"

    def test_empty_string_returns_dash(self):
        assert self.fn("") == "-"

    def test_whitespace_only_returns_dash(self):
        assert self.fn("   ") == "-"

    def test_arabic_only_returns_dash(self):
        result = self.fn("مرحبا")
        assert result == "-"

    def test_integer_converted(self):
        result = self.fn(99)
        assert result == "99"


# ---------------------------------------------------------------------------
# prepare_pdf_text — with Arabic support available
# ---------------------------------------------------------------------------


class TestPreparePdfText:

    def test_latin_text_passes_through(self):
        from pdf_helpers import prepare_pdf_text

        result = prepare_pdf_text("Bonjour le monde")
        assert result == "Bonjour le monde"

    def test_none_returns_empty(self):
        from pdf_helpers import prepare_pdf_text

        assert prepare_pdf_text(None) == ""

    def test_empty_string(self):
        from pdf_helpers import prepare_pdf_text

        assert prepare_pdf_text("") == ""

    def test_arabic_text_returned_as_string(self):
        """When ARABIC_SUPPORT is True reshaping happens; result is still a string."""
        from pdf_helpers import ARABIC_SUPPORT, prepare_pdf_text

        result = prepare_pdf_text("مرحبا")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("pdf_helpers.ARABIC_SUPPORT", False)
    def test_arabic_text_unchanged_when_no_support(self):
        """Without Arabic support the original string is returned as-is."""
        from pdf_helpers import prepare_pdf_text

        text = "مرحبا"
        # Reload to pick up patched ARABIC_SUPPORT
        result = prepare_pdf_text(text)
        assert result == text

    def test_reshaper_exception_returns_original(self):
        """If arabic_reshaper raises, the fallback returns the original text."""
        from pdf_helpers import prepare_pdf_text

        arabic_text = "طالب"
        with patch("pdf_helpers.arabic_reshaper") as mock_reshaper:
            mock_reshaper.reshape.side_effect = RuntimeError("test error")
            result = prepare_pdf_text(arabic_text)
        # Fallback: original string returned
        assert result == arabic_text


# ---------------------------------------------------------------------------
# find_arabic_font_path — filesystem interactions mocked
# ---------------------------------------------------------------------------


class TestFindArabicFontPath:

    def test_returns_none_when_no_font_exists(self):
        import pdf_helpers as ph

        # Reset the cache
        original_cache = ph._cached_font_path
        ph._cached_font_path = False
        try:
            with patch("os.path.exists", return_value=False):
                result = ph.find_arabic_font_path()
            assert result is None
        finally:
            ph._cached_font_path = original_cache

    def test_returns_first_existing_font(self):
        import pdf_helpers as ph

        original_cache = ph._cached_font_path
        ph._cached_font_path = False
        try:
            # Only the first candidate exists
            def exists_mock(path):
                return "Amiri-Regular.ttf" in path and "Fonts" not in path

            with patch("os.path.exists", side_effect=exists_mock):
                result = ph.find_arabic_font_path()
            assert result is not None
            assert "Amiri-Regular.ttf" in result
        finally:
            ph._cached_font_path = original_cache

    def test_result_is_cached_after_first_call(self):
        import pdf_helpers as ph

        original_cache = ph._cached_font_path
        ph._cached_font_path = False
        try:
            with patch("os.path.exists", return_value=False) as mock_exists:
                ph.find_arabic_font_path()
                ph.find_arabic_font_path()  # second call must not re-scan
            # os.path.exists should only have been called for the candidates, not doubled
            first_call_count = len(ph._ARABIC_FONT_CANDIDATES)
            assert mock_exists.call_count == first_call_count
        finally:
            ph._cached_font_path = original_cache


# ---------------------------------------------------------------------------
# setup_pdf_arabic_font — FPDF integration (FPDF mocked)
# ---------------------------------------------------------------------------


class TestSetupPdfArabicFont:

    def test_returns_false_when_no_font_found(self):
        from pdf_helpers import setup_pdf_arabic_font

        pdf = MagicMock()
        with patch("pdf_helpers.find_arabic_font_path", return_value=None):
            result = setup_pdf_arabic_font(pdf)
        assert result is False
        pdf.add_font.assert_not_called()

    def test_returns_true_and_calls_add_font_when_font_exists(self):
        from pdf_helpers import setup_pdf_arabic_font

        pdf = MagicMock()
        fake_path = "/fake/path/Amiri-Regular.ttf"
        with patch("pdf_helpers.find_arabic_font_path", return_value=fake_path):
            result = setup_pdf_arabic_font(pdf)
        assert result is True
        # The font is registered for all 4 styles ("", "B", "I", "BI") to support bold/italic.
        assert pdf.add_font.call_count == 4
        pdf.add_font.assert_any_call("ArabicFont", "", fake_path, uni=True)
        pdf.add_font.assert_any_call("ArabicFont", "B", fake_path, uni=True)

    def test_returns_false_when_add_font_raises(self):
        from pdf_helpers import setup_pdf_arabic_font

        pdf = MagicMock()
        pdf.add_font.side_effect = Exception("font error")
        fake_path = "/fake/Amiri.ttf"
        with patch("pdf_helpers.find_arabic_font_path", return_value=fake_path):
            result = setup_pdf_arabic_font(pdf)
        assert result is False

    def test_custom_font_name_passed_to_add_font(self):
        from pdf_helpers import setup_pdf_arabic_font

        pdf = MagicMock()
        fake_path = "/fonts/Cairo.ttf"
        with patch("pdf_helpers.find_arabic_font_path", return_value=fake_path):
            setup_pdf_arabic_font(pdf, font_name="CairoFont")
        # Registered for all 4 styles; verify the custom font_name is used.
        assert pdf.add_font.call_count == 4
        pdf.add_font.assert_any_call("CairoFont", "", fake_path, uni=True)


# ---------------------------------------------------------------------------
# get_pdf_font_name
# ---------------------------------------------------------------------------


class TestGetPdfFontName:

    def test_returns_arabic_font_when_font_ready(self):
        from pdf_helpers import get_pdf_font_name

        with patch("pdf_helpers.is_arabic_font_ready", return_value=True):
            assert get_pdf_font_name() == "ArabicFont"

    def test_returns_arial_when_font_not_ready(self):
        from pdf_helpers import get_pdf_font_name

        with patch("pdf_helpers.is_arabic_font_ready", return_value=False):
            assert get_pdf_font_name() == "Arial"

    def test_custom_font_name_used_when_ready(self):
        from pdf_helpers import get_pdf_font_name

        with patch("pdf_helpers.is_arabic_font_ready", return_value=True):
            assert get_pdf_font_name("MyFont") == "MyFont"
