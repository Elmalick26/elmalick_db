"""
ملف الأنماط الموحدة للواجهة - الإصدار الاحترافي (Enhanced)
Unified UI Styles for the School Management System
"""

import math

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db_path import configure_qt_font_environment

configure_qt_font_environment()

# ========== COLORS (لوحة الألوان) ==========


class Colors:
    """مجموعة الألوان الموحدة 2026 — Indigo/Slate Light Mode"""

    # ── Primary (Indigo spectrum) ───────────────────────────────────────
    PRIMARY = "#4F46E5"  # Indigo 600
    PRIMARY_HOVER = "#4338CA"  # Indigo 700
    PRIMARY_DARK = "#3730A3"  # Indigo 800
    PRIMARY_LIGHT = "#EEF2FF"  # Indigo 50  (tint for backgrounds)

    # ── Accent / Secondary (Violet) ─────────────────────────────────────
    SECONDARY = "#7C3AED"  # Violet 600

    # ── Semantic ────────────────────────────────────────────────────────
    SUCCESS = "#059669"  # Emerald 600
    SUCCESS_HOVER = "#047857"  # Emerald 700
    SUCCESS_LIGHT = "#ECFDF5"  # Emerald 50
    WARNING = "#D97706"  # Amber 600
    WARNING_LIGHT = "#FFFBEB"  # Amber 50
    DANGER = "#DC2626"  # Red 600
    DANGER_HOVER = "#B91C1C"  # Red 700
    DANGER_LIGHT = "#FEF2F2"  # Red 50
    INFO = "#0284C7"  # Sky 600
    INFO_LIGHT = "#F0F9FF"  # Sky 50

    # ── Application Backgrounds ─────────────────────────────────────────
    BG_MAIN = "#F8FAFC"  # Slate 50  — page canvas
    BG_CARD = "#FFFFFF"  # White     — card surface
    BG_HEADER = "#1E293B"  # Slate 800 — module header / topbar

    # ── Sidebar ─────────────────────────────────────────────────────────
    SIDEBAR_BG = "#0F1629"  # Deep navy sidebar
    SIDEBAR_ITEM_HOVER = "#1E2D45"  # Nav item hover
    SIDEBAR_ITEM_ACTIVE = "#1E40AF"  # Nav item active (indigo tint)
    SIDEBAR_ACCENT = "#4F46E5"  # Active item left border
    SIDEBAR_TEXT = "#CBD5E1"  # Nav item label
    SIDEBAR_TEXT_MUTED = "#475569"  # Category headers
    SIDEBAR_ICON = "#94A3B8"  # Icon color at rest

    # ── Text ────────────────────────────────────────────────────────────
    TEXT_PRIMARY = "#1E293B"  # Slate 800
    TEXT_SECONDARY = "#64748B"  # Slate 500
    HEADER_TEXT = "#F8FAFC"  # Near-white on dark headers

    # ── Borders & Inputs ────────────────────────────────────────────────
    BORDER = "#E2E8F0"  # Slate 200
    BORDER_FOCUS = "#4F46E5"  # Indigo on focus
    INPUT_BG = "#F1F5F9"  # Slate 100
    INPUT_BG_FOCUS = "#FFFFFF"
    INPUT_BORDER = "#CBD5E1"  # Slate 300

    # ── Tabs ────────────────────────────────────────────────────────────
    TAB_BG = "#F1F5F9"
    TAB_HOVER_BG = "#E2E8F0"

    # ── Scrollbars ──────────────────────────────────────────────────────
    SCROLL_BG = "#F8FAFC"
    SCROLL_HANDLE = "#CBD5E1"


class DarkColors:
    """مجموعة الألوان للوضع الداكن 2026 — Indigo/Slate Dark Mode"""

    # ── Primary ─────────────────────────────────────────────────────────
    PRIMARY = "#818CF8"  # Indigo 400 (lighter on dark)
    PRIMARY_HOVER = "#6366F1"  # Indigo 500
    PRIMARY_DARK = "#4F46E5"  # Indigo 600
    PRIMARY_LIGHT = "#1E1B4B"  # Indigo 950 tint

    # ── Accent ──────────────────────────────────────────────────────────
    SECONDARY = "#A78BFA"  # Violet 400

    # ── Semantic ────────────────────────────────────────────────────────
    SUCCESS = "#34D399"  # Emerald 400
    SUCCESS_HOVER = "#10B981"
    SUCCESS_LIGHT = "#022C22"
    WARNING = "#FBBF24"  # Amber 400
    WARNING_LIGHT = "#1C1400"
    DANGER = "#F87171"  # Red 400
    DANGER_HOVER = "#EF4444"
    DANGER_LIGHT = "#1F0A0A"
    INFO = "#38BDF8"  # Sky 400
    INFO_LIGHT = "#082F49"

    # ── Application Backgrounds ─────────────────────────────────────────
    BG_MAIN = "#0D1117"  # Very dark canvas
    BG_CARD = "#161B2E"  # Card surface
    BG_HEADER = "#0A0F1E"  # Module header

    # ── Sidebar ─────────────────────────────────────────────────────────
    SIDEBAR_BG = "#080D1A"  # Darker than card
    SIDEBAR_ITEM_HOVER = "#151E35"
    SIDEBAR_ITEM_ACTIVE = "#1E1B4B"
    SIDEBAR_ACCENT = "#818CF8"
    SIDEBAR_TEXT = "#94A3B8"
    SIDEBAR_TEXT_MUTED = "#334155"
    SIDEBAR_ICON = "#64748B"

    # ── Text ────────────────────────────────────────────────────────────
    TEXT_PRIMARY = "#E2E8F0"  # Slate 200
    TEXT_SECONDARY = "#94A3B8"  # Slate 400
    HEADER_TEXT = "#F8FAFC"

    # ── Borders & Inputs ────────────────────────────────────────────────
    BORDER = "#1E293B"  # Slate 800
    BORDER_FOCUS = "#818CF8"
    INPUT_BG = "#0F172A"
    INPUT_BG_FOCUS = "#1E293B"
    INPUT_BORDER = "#334155"

    # ── Tabs ────────────────────────────────────────────────────────────
    TAB_BG = "#0F172A"
    TAB_HOVER_BG = "#1E293B"

    # ── Scrollbars ──────────────────────────────────────────────────────
    SCROLL_BG = "#0D1117"
    SCROLL_HANDLE = "#1E293B"


# ========== BASE STYLES (القوالب الأساسية) ==========
class StyleTemplates:

    @staticmethod
    def get_common_styles(colors):
        """توليد الأنماط المشتركة بناءً على الألوان الممررة"""
        return f"""
            /* ═══════════════════════════════════════════════════
               Global Reset
            ═══════════════════════════════════════════════════ */
            QWidget {{
                font-family: 'Segoe UI', 'Cairo', 'Noto Sans Arabic', sans-serif;
                font-size: 13px;
                color: {colors.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {colors.TEXT_PRIMARY};
                background: transparent;
            }}
            QMainWindow {{
                background-color: {colors.BG_MAIN};
            }}

            /* ═══════════════════════════════════════════════════
               GroupBox
            ═══════════════════════════════════════════════════ */
            QGroupBox {{
                border: 1px solid {colors.BORDER};
                border-radius: 10px;
                margin-top: 22px;
                background-color: {colors.BG_CARD};
                font-weight: 600;
                padding-top: 18px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 8px;
                left: 12px;
                color: {colors.TEXT_SECONDARY};
                font-size: 11px;
                letter-spacing: 0.5px;
            }}

            /* ═══════════════════════════════════════════════════
               Inputs — Line / Spin / Date
            ═══════════════════════════════════════════════════ */
            QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox {{
                padding: 9px 12px;
                border: 1.5px solid {colors.INPUT_BORDER};
                border-radius: 8px;
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
                selection-background-color: {colors.PRIMARY};
                selection-color: #ffffff;
                min-height: 36px;
            }}
            QLineEdit::placeholder {{
                color: {colors.TEXT_SECONDARY};
                font-style: italic;
            }}
            QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus,
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {colors.BORDER_FOCUS};
                background-color: {colors.INPUT_BG_FOCUS};
                outline: none;
            }}
            QLineEdit:disabled, QDateEdit:disabled, QSpinBox:disabled {{
                background-color: {colors.BG_MAIN};
                color: {colors.TEXT_SECONDARY};
                border-color: {colors.BORDER};
            }}

            /* ═══════════════════════════════════════════════════
               ComboBox
            ═══════════════════════════════════════════════════ */
            QComboBox {{
                padding: 9px 12px;
                border: 1.5px solid {colors.INPUT_BORDER};
                border-radius: 8px;
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
                min-height: 36px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 12px;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {colors.TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {colors.BORDER};
                border-radius: 8px;
                background-color: {colors.BG_CARD};
                color: {colors.TEXT_PRIMARY};
                selection-background-color: {colors.PRIMARY};
                selection-color: white;
                outline: none;
                padding: 4px;
            }}
            QComboBox:focus {{
                border: 2px solid {colors.BORDER_FOCUS};
                background-color: {colors.INPUT_BG_FOCUS};
            }}

            /* ═══════════════════════════════════════════════════
               TextEdit
            ═══════════════════════════════════════════════════ */
            QTextEdit {{
                padding: 10px 12px;
                border: 1.5px solid {colors.INPUT_BORDER};
                border-radius: 8px;
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border: 2px solid {colors.BORDER_FOCUS};
                background-color: {colors.INPUT_BG_FOCUS};
            }}

            /* ═══════════════════════════════════════════════════
               Tables — Clean with subtle row stripe & hover
            ═══════════════════════════════════════════════════ */
            QTableWidget {{
                background-color: {colors.BG_CARD};
                border: 1px solid {colors.BORDER};
                border-radius: 10px;
                gridline-color: transparent;
                alternate-background-color: {colors.BG_MAIN};
                selection-background-color: {colors.PRIMARY}22;
                selection-color: {colors.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 10px 12px;
                border-bottom: 1px solid {colors.BORDER};
                color: {colors.TEXT_PRIMARY};
            }}
            QTableWidget::item:hover {{
                background-color: {colors.PRIMARY}14;
            }}
            QTableWidget::item:selected {{
                background-color: {colors.PRIMARY}2A;
                color: {colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {colors.BG_HEADER};
                color: {colors.HEADER_TEXT};
                padding: 11px 12px;
                border: none;
                border-right: 1px solid {colors.BORDER};
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 0.4px;
                text-transform: uppercase;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 10px;
            }}
            QHeaderView::section:last {{
                border-right: none;
                border-top-right-radius: 10px;
            }}
            QTableCornerButton::section {{
                background-color: {colors.BG_HEADER};
                border: none;
                border-top-left-radius: 10px;
            }}

            /* ═══════════════════════════════════════════════════
               TabWidget — Pill-style
            ═══════════════════════════════════════════════════ */
            QTabWidget::pane {{
                border: 1px solid {colors.BORDER};
                border-radius: 10px;
                background: {colors.BG_CARD};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {colors.TAB_BG};
                color: {colors.TEXT_SECONDARY};
                padding: 9px 22px;
                margin-right: 4px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                font-weight: 600;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background: {colors.BG_CARD};
                color: {colors.PRIMARY};
                border-bottom: 2px solid {colors.PRIMARY};
                font-weight: 700;
            }}
            QTabBar::tab:hover:!selected {{
                background: {colors.TAB_HOVER_BG};
                color: {colors.TEXT_PRIMARY};
            }}

            /* ═══════════════════════════════════════════════════
               Menus
            ═══════════════════════════════════════════════════ */
            QMenu {{
                background-color: {colors.BG_CARD};
                color: {colors.TEXT_PRIMARY};
                border: 1px solid {colors.BORDER};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background-color: {colors.PRIMARY}18;
                color: {colors.PRIMARY};
            }}
            QMenu::separator {{
                height: 1px;
                background: {colors.BORDER};
                margin: 4px 8px;
            }}
            QMenuBar {{
                background-color: {colors.BG_HEADER};
                color: {colors.HEADER_TEXT};
                padding: 2px;
            }}
            QMenuBar::item {{
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QMenuBar::item:selected {{
                background-color: {colors.PRIMARY};
                color: white;
            }}

            /* ═══════════════════════════════════════════════════
               CheckBox / RadioButton
            ═══════════════════════════════════════════════════ */
            QCheckBox, QRadioButton {{
                color: {colors.TEXT_PRIMARY};
                spacing: 8px;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 17px;
                height: 17px;
                border: 2px solid {colors.INPUT_BORDER};
                border-radius: 4px;
                background: {colors.INPUT_BG};
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors.PRIMARY};
                border-color: {colors.PRIMARY};
            }}

            /* ═══════════════════════════════════════════════════
               Scrollbars — Slim & modern
            ═══════════════════════════════════════════════════ */
            QScrollBar:vertical {{
                border: none;
                background: {colors.SCROLL_BG};
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {colors.SCROLL_HANDLE};
                min-height: 30px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: {colors.SCROLL_BG};
                height: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {colors.SCROLL_HANDLE};
                min-width: 30px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}

            /* ═══════════════════════════════════════════════════
               Tooltips
            ═══════════════════════════════════════════════════ */
            QToolTip {{
                color: {colors.HEADER_TEXT};
                background-color: {colors.BG_HEADER};
                border: 1px solid {colors.BORDER};
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 12px;
                opacity: 240;
            }}

            /* ═══════════════════════════════════════════════════
               MessageBox
            ═══════════════════════════════════════════════════ */
            QMessageBox {{
                background-color: {colors.BG_CARD};
                border-radius: 10px;
            }}
            QMessageBox QLabel {{
                color: {colors.TEXT_PRIMARY};
                font-size: 14px;
                padding: 4px;
            }}

            /* ═══════════════════════════════════════════════════
               Frame / Cards
            ═══════════════════════════════════════════════════ */
            QFrame[class="card"] {{
                background-color: {colors.BG_CARD};
                border: 1px solid {colors.BORDER};
                border-radius: 12px;
            }}

            /* ═══════════════════════════════════════════════════
               Splitter
            ═══════════════════════════════════════════════════ */
            QSplitter::handle {{
                background: {colors.BORDER};
                width: 1px;
                height: 1px;
            }}
        """

    @staticmethod
    def get_button_styles(colors):
        return f"""
            /* ─── Default / Primary ───────────────────────────── */
            QPushButton {{
                background-color: {colors.PRIMARY};
                color: #ffffff;
                font-weight: 700;
                padding: 9px 20px;
                border-radius: 8px;
                border: none;
                font-size: 13px;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover  {{ background-color: {colors.PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {colors.PRIMARY_DARK}; }}
            QPushButton:disabled {{
                background-color: {colors.BORDER};
                color: {colors.TEXT_SECONDARY};
            }}

            /* ─── Danger ──────────────────────────────────────── */
            QPushButton[class="danger"] {{
                background-color: {colors.DANGER};
                color: white;
            }}
            QPushButton[class="danger"]:hover  {{ background-color: {colors.DANGER_HOVER}; }}

            /* ─── Success ─────────────────────────────────────── */
            QPushButton[class="success"] {{
                background-color: {colors.SUCCESS};
                color: white;
            }}
            QPushButton[class="success"]:hover {{ background-color: {colors.SUCCESS_HOVER}; }}

            /* ─── Outline (Ghost) ─────────────────────────────── */
            QPushButton[class="outline"] {{
                background-color: transparent;
                border: 2px solid {colors.PRIMARY};
                color: {colors.PRIMARY};
            }}
            QPushButton[class="outline"]:hover {{
                background-color: {colors.PRIMARY_LIGHT};
            }}

            /* ─── Secondary / Subtle ──────────────────────────── */
            QPushButton[class="secondary"] {{
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
                border: 1px solid {colors.BORDER};
            }}
            QPushButton[class="secondary"]:hover {{
                background-color: {colors.BORDER};
            }}

            /* ─── Icon-only round ─────────────────────────────── */
            QPushButton[class="icon"] {{
                background-color: transparent;
                border: none;
                border-radius: 20px;
                padding: 4px;
            }}
            QPushButton[class="icon"]:hover {{
                background-color: {colors.INPUT_BG};
            }}
        """


# ========== THEME MANAGER ==========
class ThemeManager:
    """يدير تطبيق الأنماط على التطبيق بالكامل"""

    _current_theme = "light"

    @staticmethod
    def is_dark_mode():
        return ThemeManager._current_theme == "dark"

    @staticmethod
    def set_theme(theme):
        ThemeManager._current_theme = theme

    @staticmethod
    def apply_theme(app_or_window, theme=None):
        """
        يطبق الثيم على التطبيق بالكامل أو نافذة محددة.
        الأفضل تمرير QApplication لضمان تلوين الـ Dialogs والقوائم.
        """
        if theme is None:
            theme = ThemeManager._current_theme
        else:
            ThemeManager._current_theme = theme

        colors = DarkColors if theme == "dark" else Colors

        # دمج الأنماط العامة وأنماط الأزرار
        full_stylesheet = StyleTemplates.get_common_styles(colors) + StyleTemplates.get_button_styles(colors)

        app_or_window.setStyleSheet(full_stylesheet)

    @staticmethod
    def get_colors():
        return DarkColors if ThemeManager._current_theme == "dark" else Colors


# ========== HELPER FUNCTIONS (للاستخدام داخل الملفات) ==========


def create_shadow_effect(blur=15, offset=4, opacity=40):
    """تأثير ظل موحد"""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(offset)
    shadow.setColor(QColor(0, 0, 0, opacity))
    return shadow


def apply_shadow_to_widget(widget):
    """تطبيق الظل مباشرة على الويدجت"""
    widget.setGraphicsEffect(create_shadow_effect())


def rgba(color, alpha):
    """Return rgba() string from a hex color and alpha (0-255)."""
    qcolor = color if isinstance(color, QColor) else QColor(color)
    return f"rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {alpha})"


def get_card_style(elevated: bool = False):
    """نمط البطاقة البيضاء"""
    colors = ThemeManager.get_colors()
    if elevated:
        return f"""
            QFrame {{
                background-color: {colors.BG_CARD};
                border-radius: 14px;
                border: 1px solid {colors.BORDER_FOCUS}66;
            }}
        """
    return f"""
        QFrame {{
            background-color: {colors.BG_CARD};
            border-radius: 14px;
            border: 1px solid {colors.BORDER};
        }}
        QFrame:hover {{
            border-color: {colors.BORDER_FOCUS}66;
        }}
    """


def get_table_style():
    """نمط موحد للجداول"""
    colors = ThemeManager.get_colors()
    return f"""
        QTableWidget {{
            background-color: {colors.BG_CARD};
            border: 1px solid {colors.BORDER};
            border-radius: 10px;
            gridline-color: transparent;
            alternate-background-color: {colors.BG_MAIN};
            font-size: 13px;
            color: {colors.TEXT_PRIMARY};
            selection-background-color: {colors.PRIMARY}22;
            selection-color: {colors.TEXT_PRIMARY};
        }}
        QTableWidget::item {{
            padding: 10px 12px;
            border-bottom: 1px solid {colors.BORDER};
            color: {colors.TEXT_PRIMARY};
        }}
        QTableWidget::item:hover {{
            background-color: {colors.PRIMARY}14;
        }}
        QTableWidget::item:selected {{
            background-color: {colors.PRIMARY}2A;
            color: {colors.TEXT_PRIMARY};
        }}
        QHeaderView::section {{
            background-color: {colors.BG_HEADER};
            color: {colors.HEADER_TEXT};
            padding: 11px 12px;
            border: none;
            border-right: 1px solid {colors.BORDER};
            font-weight: 700;
            font-size: 12px;
            letter-spacing: 0.4px;
        }}
        QHeaderView::section:first {{
            border-top-left-radius: 10px;
        }}
        QHeaderView::section:last {{
            border-right: none;
            border-top-right-radius: 10px;
        }}
        QTableCornerButton::section {{
            background-color: {colors.BG_HEADER};
            border: none;
            border-top-left-radius: 10px;
        }}
    """


def get_tabs_style():
    """نمط موحد للتبويبات"""
    colors = ThemeManager.get_colors()
    return f"""
        QTabWidget::pane {{
            border: 1px solid {colors.BORDER};
            background: {colors.BG_CARD};
            border-radius: 10px;
            top: -1px;
        }}
        QTabBar::tab {{
            background: {colors.TAB_BG};
            color: {colors.TEXT_SECONDARY};
            padding: 9px 24px;
            margin-right: 4px;
            border-top-left-radius: 7px;
            border-top-right-radius: 7px;
            font-weight: 600;
            font-size: 13px;
            font-family: 'Segoe UI', 'Cairo', sans-serif;
        }}
        QTabBar::tab:selected {{
            background: {colors.BG_CARD};
            color: {colors.PRIMARY};
            border-bottom: 2px solid {colors.PRIMARY};
            font-weight: 700;
        }}
        QTabBar::tab:hover:!selected {{
            background: {colors.TAB_HOVER_BG};
            color: {colors.TEXT_PRIMARY};
        }}
    """


# ========== STAT CHIP (for ModuleHeaderWidget inline stats) ==========


class _StatChip(QFrame):
    """
    Chip de statistique compact intégré dans ModuleHeaderWidget.
    Affiche une icône, une valeur en gras colorée et un libellé court.
    """

    def __init__(self, icon: str, label: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedWidth(108)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(1)

        # Top row: icon + value
        top_w = QWidget()
        top_w.setStyleSheet("background: transparent; border: none;")
        top = QHBoxLayout(top_w)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(5)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setFont(QFont("Segoe UI", 15))
        self._icon_lbl.setStyleSheet("background: transparent;")

        self._value_lbl = QLabel(value)
        self._value_lbl.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        self._value_lbl.setStyleSheet(f"color: {color}; background: transparent;")

        top.addWidget(self._icon_lbl)
        top.addWidget(self._value_lbl)
        top.addStretch()

        # Label row
        self._label_lbl = QLabel(label)
        self._label_lbl.setFont(QFont("Segoe UI", 8))

        layout.addWidget(top_w)
        layout.addWidget(self._label_lbl)

        self._apply_styles()

    def _apply_styles(self):
        # Keep header stat chips visually aligned with dark module headers
        # regardless of global theme mode.
        dark_bg = "#1E293B"
        dark_border = "#334155"
        label_color = "#94A3B8"
        icon_color = "#E2E8F0"
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {dark_bg};
                border-radius: 7px;
                border: 1px solid {dark_border};
                border-left: 3px solid {self._color};
            }}
        """
        )
        self._icon_lbl.setStyleSheet(f"color: {icon_color}; background: transparent;")
        self._label_lbl.setStyleSheet(f"color: {label_color}; background: transparent;")

    def set_value(self, value: str):
        """Mettre à jour la valeur affichée."""
        self._value_lbl.setText(value)

    def refresh_theme(self):
        self._apply_styles()


# ========== MODULE HEADER WIDGET ==========


class ModuleHeaderWidget(QFrame):
    """
    En-tête unifié pour tous les modules. Contient titre + sous-titre à gauche
    et des chips de statistiques compacts à droite (via add_stat).

    Usage::
        header = ModuleHeaderWidget(icon="📊", title="TITRE", subtitle="Sous-titre")
        layout.addWidget(header)
        stat = header.add_stat("👥", "Total", "—", "#3B82F6")
        # Plus tard :
        stat.set_value("42")
    """

    def __init__(self, icon: str = "📋", title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self._icon = icon
        self._title = title
        self._subtitle = subtitle
        self._stat_chips: list = []
        self.setFixedHeight(82)
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(20, 10, 16, 10)
        self._main_layout.setSpacing(14)

        self._icon_lbl = QLabel(self._icon)
        self._icon_lbl.setFont(QFont("Segoe UI", 26))
        self._icon_lbl.setFixedWidth(42)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)

        self._title_lbl = QLabel(self._title)
        self._title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        self._sub_lbl = QLabel(self._subtitle)
        self._sub_lbl.setFont(QFont("Cairo", 10))

        text_box.addWidget(self._title_lbl)
        text_box.addWidget(self._sub_lbl)

        self._main_layout.addWidget(self._icon_lbl)
        self._main_layout.addLayout(text_box)
        self._main_layout.addStretch()

        # Zone des chips de statistiques (droite)
        self._stats_layout = QHBoxLayout()
        self._stats_layout.setSpacing(7)
        self._stats_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addLayout(self._stats_layout)

    def add_stat(self, icon: str, label: str, value: str = "—", color: str = "#3B82F6") -> _StatChip:
        """
        Ajoute un chip de statistique à droite du header.
        Retourne le chip pour pouvoir mettre à jour la valeur via set_value().
        """
        chip = _StatChip(icon, label, value, color)
        self._stats_layout.addWidget(chip)
        self._stat_chips.append(chip)
        return chip

    def _apply_styles(self):
        colors = ThemeManager.get_colors()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {colors.BG_HEADER};
                border-radius: 10px;
                border-bottom: 1px solid {colors.BORDER};
            }}
        """
        )
        self._icon_lbl.setStyleSheet("background: transparent;")
        self._title_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        self._sub_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")

    def refresh_theme(self):
        """Appelé après un changement de thème."""
        self._apply_styles()
        for chip in self._stat_chips:
            chip.refresh_theme()

    def set_subtitle(self, text: str):
        """Mise à jour dynamique du sous-titre."""
        self._subtitle = text
        self._sub_lbl.setText(text)


# ========== KPI CARD ==========


class KpiCard(QFrame):
    """
    بطاقة مؤشر أداء (KPI) قابلة لإعادة الاستخدام في جميع الوحدات.
    تستجيب للثيم الفاتح والداكن.

    Usage::
        card = KpiCard(icon="👥", label="Total Élèves", value="320", color="#3B82F6")
        layout.addWidget(card)
        # لاحقاً:
        card.set_value("345")
    """

    def __init__(
        self,
        icon: str = "📊",
        label: str = "",
        value: str = "—",
        color: str = "#3B82F6",
        parent=None,
        theme_mode: str = "dark",
    ):
        super().__init__(parent)
        self._color = color
        self._theme_mode = theme_mode
        self.setMinimumSize(160, 100)
        self.setMaximumHeight(130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        top_row_widget = QFrame()
        top_row_widget.setStyleSheet("background: transparent; border: none;")
        top_row = QHBoxLayout(top_row_widget)
        top_row.setContentsMargins(0, 0, 0, 0)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setFont(QFont("Segoe UI", 20))
        self._icon_lbl.setStyleSheet("background: transparent;")

        self._label_lbl = QLabel(label)
        self._label_lbl.setFont(QFont("Segoe UI", 11))

        top_row.addWidget(self._icon_lbl)
        top_row.addStretch()
        top_row.addWidget(self._label_lbl)

        self._value_lbl = QLabel(value)
        self._value_lbl.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self._value_lbl.setStyleSheet(f"color: {color}; background: transparent;")

        layout.addWidget(top_row_widget)
        layout.addWidget(self._value_lbl)

        self._apply_styles()

    def _apply_styles(self):
        if self._theme_mode == "default":
            colors = ThemeManager.get_colors()
            bg_color = colors.BG_CARD
            border_color = colors.BORDER
            label_color = colors.TEXT_SECONDARY
            icon_color = colors.TEXT_PRIMARY
        else:
            # KPI cards are intentionally kept dark for visual consistency
            # with module headers in both light and dark app modes.
            bg_color = "#1E293B"
            border_color = "#334155"
            label_color = "#94A3B8"
            icon_color = "#E2E8F0"
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 10px;
                border: 1px solid {border_color};
                border-left: 4px solid {self._color};
            }}
        """
        )
        self._icon_lbl.setStyleSheet(f"color: {icon_color}; background: transparent;")
        self._label_lbl.setStyleSheet(f"color: {label_color}; background: transparent;")

    def set_value(self, value: str):
        """تحديث القيمة ديناميكياً."""
        self._value_lbl.setText(value)

    def refresh_theme(self):
        """اُستدعى بعد تغيير الثيم."""
        self._apply_styles()


# ========== TOAST NOTIFICATION ==========


class ToastNotification(QFrame):
    """
    إشعار غير مُعيق (Snackbar) يظهر أسفل يمين النافذة الأم
    ثم يختفي تلقائياً بعد *duration* مللي ثانية.

    Usage::
        ToastNotification.show_toast(parent_window, "تم الحفظ بنجاح ✔", kind="success")
        ToastNotification.show_toast(parent_window, "حدث خطأ", kind="error")
    """

    _COLORS = {
        "success": ("#10B981", "#FFFFFF"),
        "error": ("#EF4444", "#FFFFFF"),
        "info": ("#3B82F6", "#FFFFFF"),
        "warning": ("#F59E0B", "#FFFFFF"),
    }

    def __init__(self, parent: QWidget, message: str, kind: str = "success", duration: int = 3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        bg_color, fg_color = self._COLORS.get(kind, self._COLORS["info"])
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
            }}
        """
        )

        icon_map = {"success": "✔", "error": "✖", "info": "ℹ", "warning": "⚠"}
        icon_lbl = QLabel(icon_map.get(kind, "ℹ") + "  " + message)
        icon_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        icon_lbl.setStyleSheet(f"color: {fg_color}; background: transparent;")
        layout.addWidget(icon_lbl)

        self.adjustSize()
        self._position_self()

        QTimer.singleShot(duration, self.close)
        self.show()
        self.raise_()

    def _position_self(self):
        if self.parent():
            p = self.parent()
            pw, ph = p.width(), p.height()  # type: ignore[union-attr]
            self.setFixedWidth(min(420, pw - 40))
            x = pw - self.width() - 20
            y = ph - self.height() - 20
            self.move(x, y)

    @staticmethod
    def show_toast(parent: QWidget, message: str, kind: str = "success", duration: int = 3000):
        """طريقة مختصرة لعرض الإشعار."""
        ToastNotification(parent, message, kind, duration)


# ========== LOADING OVERLAY ==========


class LoadingOverlay(QWidget):
    """
    Superpose un voile semi-transparent + spinner texte sur un widget parent
    pendant les opérations longues (requêtes DB, génération PDF…).

    Utilisation :
        overlay = LoadingOverlay(parent_widget)
        overlay.show_loading("Chargement en cours…")
        # … travail en arrière-plan …
        overlay.hide_loading()
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("⏳  جارٍ التحميل…")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(self._label)

        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    # ------------------------------------------------------------------ #
    def show_loading(self, message: str = "Chargement…") -> None:
        """Affiche le voile avec *message* et démarre l'animation."""
        self._base_msg = message
        self._label.setText(f"⏳  {message}")
        colors = ThemeManager.get_colors()
        self.setStyleSheet("background-color: rgba(0,0,0,0.45); border-radius: 8px;")
        self._label.setStyleSheet(
            f"color: white; background: transparent; padding: 20px 40px;"
            f"border-radius: 12px; background-color: {colors.BG_HEADER};"
        )
        # Ajuster la taille sur le parent
        if self.parent():
            self.setGeometry(self.parent().rect())  # type: ignore[union-attr]
        self.raise_()
        self.show()
        self._dots = 0
        self._timer.start(400)

    def hide_loading(self) -> None:
        """Masque le voile et arrête l'animation."""
        self._timer.stop()
        self.hide()

    def _animate(self) -> None:
        self._dots = (self._dots + 1) % 4
        dots = "." * self._dots
        self._label.setText(f"⏳  {self._base_msg}{dots}")

    # Redimensionnement automatique quand le parent change de taille
    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())  # type: ignore[union-attr]


# ========== FRIENDLY DB ERROR MESSAGES ==========


def friendly_db_error(exc: Exception) -> str:
    """
    Traduit une exception psycopg2 / générale en message lisible
    pour l'utilisateur final (arabe + français).

    Usage :
        except Exception as e:
            QMessageBox.warning(self, "Erreur", friendly_db_error(e))
    """
    msg = str(exc).lower()

    # Contrainte de clé étrangère
    if "foreign key" in msg or "violates foreign key" in msg or "fk" in msg:
        return (
            "Impossible de supprimer cet enregistrement : il est lié à d'autres données.\n"
            "لا يمكن حذف هذا السجل لأنه مرتبط ببيانات أخرى."
        )
    # Valeur unique dupliquée
    if "unique" in msg or "duplicate" in msg:
        return (
            "Cette valeur existe déjà. Veuillez en choisir une autre.\n"
            "هذه القيمة موجودة بالفعل. يرجى اختيار قيمة مختلفة."
        )
    # Colonne / table introuvable (erreur de schéma)
    if "column" in msg and ("does not exist" in msg or "n'existe pas" in msg):
        return (
            "Erreur de structure de la base de données. Contactez l'administrateur.\n"
            "خطأ في هيكل قاعدة البيانات. تواصل مع المسؤول."
        )
    # Connexion perdue
    if "connection" in msg or "connexion" in msg or "timeout" in msg:
        return (
            "Connexion à la base de données interrompue. Vérifiez le serveur.\n"
            "انقطع الاتصال بقاعدة البيانات. تحقق من الخادم."
        )
    # Données trop longues
    if "too long" in msg or "value too long" in msg or "character varying" in msg:
        return "La valeur saisie est trop longue pour ce champ.\n" "القيمة المُدخلة أطول مما يسمح به الحقل."
    # Champ obligatoire NULL
    if "null value" in msg or "not-null" in msg or "violates not-null" in msg:
        return (
            "Un champ obligatoire est vide. Vérifiez les données saisies.\n"
            "حقل إلزامي فارغ. يرجى التحقق من البيانات المُدخلة."
        )
    # Message générique
    return (
        "Une erreur inattendue s'est produite. Consultez les journaux pour plus de détails.\n"
        "حدث خطأ غير متوقع. راجع سجلات النظام للمزيد من التفاصيل."
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RBAC — صلاحيات كل دور لكل وحدة (can_write / can_delete)
# ─────────────────────────────────────────────────────────────────────────────

#: القيمة الافتراضية حين لا يُوجد سجل في القاموس
_DEFAULT_CAPS: dict = {"can_write": False, "can_delete": False}

#: يُعرِّف صلاحية الكتابة (إضافة/تعديل) والحذف لكل دور في كل وحدة.
#: الـ Admin يملك wildcard "*" تغني عن ذكر كل وحدة.
ROLE_CAPABILITIES: dict = {
    "Admin": {
        "*": {"can_write": True, "can_delete": True},
    },
    "Comptable": {
        "finance_dashboard": {"can_write": False, "can_delete": False},
        "finance_payments": {"can_write": True, "can_delete": False},
        "fees_setup": {"can_write": True, "can_delete": False},
        "student_dues": {"can_write": True, "can_delete": False},
        "expenses_payroll": {"can_write": True, "can_delete": False},
        "inventory": {"can_write": True, "can_delete": False},
    },
    "Secretaire": {
        "student_management": {"can_write": True, "can_delete": False},
        "staff_management": {"can_write": False, "can_delete": False},
        "staff_attendance": {"can_write": True, "can_delete": False},
        "staff_leaves": {"can_write": True, "can_delete": False},
        "student_attendance": {"can_write": True, "can_delete": False},
        "admin_docs": {"can_write": True, "can_delete": False},
        "communication": {"can_write": True, "can_delete": False},
        "timetable_manager": {"can_write": False, "can_delete": False},
    },
    "Pédagogique": {
        "academic_settings": {"can_write": False, "can_delete": False},
        "student_management": {"can_write": False, "can_delete": False},
        "student_attendance": {"can_write": True, "can_delete": False},
        "student_discipline": {"can_write": True, "can_delete": False},
        "student_grades": {"can_write": True, "can_delete": False},
        "bulletin_generation": {"can_write": True, "can_delete": False},
        "timetable_manager": {"can_write": True, "can_delete": True},
        "advanced_reports": {"can_write": False, "can_delete": False},
    },
    "Prof": {
        "student_attendance": {"can_write": True, "can_delete": False},
        "student_discipline": {"can_write": True, "can_delete": False},
        "student_grades": {"can_write": True, "can_delete": False},
    },
}


def get_module_caps(role: str, module_id: str) -> dict:
    """
    Retourne {'can_write': bool, 'can_delete': bool} pour le rôle et le module donnés.

    يُعيد قاموس الصلاحيات للدور والوحدة المحددين.
    - Admin يملك wildcard '*' → صلاحية كاملة على الجميع.
    - أي دور/وحدة غير مُعرَّف → {'can_write': False, 'can_delete': False}.
    """
    role_caps = ROLE_CAPABILITIES.get(role, {})
    if "*" in role_caps:
        return role_caps["*"]
    return role_caps.get(module_id, _DEFAULT_CAPS)


# ─────────────────────────────────────────────────────────────────────────────
#  PaginationWidget — شريط تنقل بين صفحات الجدول
# ─────────────────────────────────────────────────────────────────────────────


class PaginationWidget(QWidget):
    """
    شريط ترقيم الصفحات لجداول البيانات الكبيرة.

    Émet ``page_changed(page_index)`` (0-based) à chaque changement de page.

    Usage::
        self.pagination = PaginationWidget(page_size=50)
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination)
        # بعد استرداد البيانات:
        self.pagination.set_total(total_count)
    """

    page_changed = pyqtSignal(int)  # page index (0-based)

    def __init__(self, page_size: int = 50, parent=None):
        super().__init__(parent)
        self.page_size = page_size
        self._current_page = 0
        self._total = 0

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(8)

        colors = ThemeManager.get_colors()

        btn_style = (
            f"QPushButton {{ background: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY}; "
            f"border: 1px solid {colors.BORDER}; border-radius: 6px; "
            f"padding: 4px 14px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY}; color: white; }}"
            f"QPushButton:disabled {{ color: {colors.TEXT_SECONDARY}; }}"
        )

        self.btn_first = QPushButton("⏮")
        self.btn_prev = QPushButton("◀")
        self.lbl_info = QLabel("Page 1 / 1  (0 résultats)")
        self.btn_next = QPushButton("▶")
        self.btn_last = QPushButton("⏭")

        for btn in (self.btn_first, self.btn_prev, self.btn_next, self.btn_last):
            btn.setFixedHeight(32)
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.lbl_info.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 12px; padding: 0 10px;")

        lay.addStretch()
        lay.addWidget(self.btn_first)
        lay.addWidget(self.btn_prev)
        lay.addWidget(self.lbl_info)
        lay.addWidget(self.btn_next)
        lay.addWidget(self.btn_last)
        lay.addStretch()

        self.btn_first.clicked.connect(lambda: self._go_to(0))
        self.btn_prev.clicked.connect(lambda: self._go_to(self._current_page - 1))
        self.btn_next.clicked.connect(lambda: self._go_to(self._current_page + 1))
        self.btn_last.clicked.connect(lambda: self._go_to(self._total_pages() - 1))

        self._refresh_ui()

    # ------------------------------------------------------------------ #
    def set_total(self, total: int) -> None:
        """Met à jour le nombre total de résultats sans réinitialiser la page."""
        self._total = max(0, total)
        # Clamp current page in case total shrank
        if self._current_page >= self._total_pages():
            self._current_page = max(0, self._total_pages() - 1)
        self._refresh_ui()

    def reset(self) -> None:
        """Réinitialise à la page 0 (à appeler lors d'un changement de filtre)."""
        self._current_page = 0
        self._refresh_ui()

    def current_offset(self) -> int:
        """Offset SQL à passer à la requête (page × page_size)."""
        return self._current_page * self.page_size

    def _total_pages(self) -> int:
        if self._total == 0:
            return 1
        return math.ceil(self._total / self.page_size)

    def _go_to(self, page: int) -> None:
        page = max(0, min(page, self._total_pages() - 1))
        if page == self._current_page:
            return
        self._current_page = page
        self._refresh_ui()
        self.page_changed.emit(self._current_page)

    def _refresh_ui(self) -> None:
        total_pages = self._total_pages()
        self.lbl_info.setText(f"Page {self._current_page + 1} / {total_pages}  ({self._total} résultats)")
        self.btn_first.setEnabled(self._current_page > 0)
        self.btn_prev.setEnabled(self._current_page > 0)
        self.btn_next.setEnabled(self._current_page < total_pages - 1)
        self.btn_last.setEnabled(self._current_page < total_pages - 1)
        # Cacher le widget entier si tout tient sur 1 page
        self.setVisible(self._total > self.page_size)


# ─────────────────────────────────────────────────────────────────────────────
#  EmptyStateWidget — رسالة حالة فارغة للجداول
# ─────────────────────────────────────────────────────────────────────────────


class EmptyStateWidget(QWidget):
    """
    Widget affiché à la place d'un tableau vide.

    Affiche une icône, un message principal et un sous-message
    bilingues (arabe + français).

    Usage::
        self.empty_state = EmptyStateWidget(
            icon="🎓",
            title="Aucun élève trouvé / لا يوجد طلاب",
            subtitle="Ajoutez un élève ou modifiez les filtres.",
        )
        layout.addWidget(self.empty_state)
        self.empty_state.setVisible(len(rows) == 0)
        my_table.setVisible(len(rows) > 0)
    """

    def __init__(self, icon: str = "📭", title: str = "Aucun résultat", subtitle: str = "", parent=None):
        super().__init__(parent)
        colors = ThemeManager.get_colors()

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)
        lay.setContentsMargins(40, 40, 40, 40)

        lbl_icon = QLabel(icon)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 48px; background: transparent; border: none;")

        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(
            f"color: {colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold; background: transparent; border: none;"
        )

        lay.addWidget(lbl_icon)
        lay.addWidget(lbl_title)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet(
                f"color: {colors.TEXT_SECONDARY}; font-size: 13px; background: transparent; border: none;"
            )
            lay.addWidget(lbl_sub)
