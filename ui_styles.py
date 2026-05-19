"""
ملف الأنماط الموحدة للواجهة - الإصدار الاحترافي (Enhanced)
Unified UI Styles for the School Management System
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
)

from db_path import configure_qt_font_environment

configure_qt_font_environment()

# ========== COLORS (لوحة الألوان) ==========


class Colors:
    """مجموعة الألوان الموحدة - Deep Slate Theme (Light Mode)"""

    PRIMARY = "#3B82F6"  # Blue 500
    PRIMARY_HOVER = "#2563EB"  # Blue 600
    PRIMARY_DARK = "#1E40AF"  # Blue 700

    SECONDARY = "#8B5CF6"  # Violet 500

    SUCCESS = "#10B981"  # Emerald 500
    SUCCESS_HOVER = "#059669"  # Emerald 600
    WARNING = "#F59E0B"  # Amber 500
    DANGER = "#EF4444"  # Red 500
    DANGER_HOVER = "#DC2626"  # Red 600

    # خلفيات
    BG_MAIN = "#F1F5F9"  # Slate 100 (Application Background)
    BG_CARD = "#FFFFFF"  # White (Card Background)
    BG_HEADER = "#1E293B"  # Slate 800 (Header Background)

    # نصوص وحدود
    TEXT_PRIMARY = "#334155"  # Slate 700
    TEXT_SECONDARY = "#64748B"  # Slate 500
    HEADER_TEXT = "#FFFFFF"
    BORDER = "#E2E8F0"  # Slate 200
    BORDER_FOCUS = "#3B82F6"  # Primary Color
    INPUT_BG = "#EEF2F7"  # Slate 100
    INPUT_BG_FOCUS = "#FFFFFF"  # White
    INPUT_BORDER = "#94A3B8"  # Slate 400
    TAB_BG = "#E2E8F0"  # Slate 200
    TAB_HOVER_BG = "#CBD5E1"  # Slate 300

    # عناصر إضافية
    SCROLL_BG = "#F1F5F9"
    SCROLL_HANDLE = "#CBD5E1"


class DarkColors:
    """مجموعة الألوان للوضع الداكن - Dark Theme"""

    PRIMARY = "#60A5FA"  # Blue 400 (Lighter for dark mode)
    PRIMARY_HOVER = "#3B82F6"
    PRIMARY_DARK = "#2563EB"

    SECONDARY = "#A78BFA"

    SUCCESS = "#34D399"
    SUCCESS_HOVER = "#10B981"
    WARNING = "#FBBF24"
    DANGER = "#F87171"
    DANGER_HOVER = "#EF4444"

    # خلفيات
    BG_MAIN = "#0F172A"  # Slate 900
    BG_CARD = "#1E293B"  # Slate 800
    BG_HEADER = "#020617"  # Slate 950

    # نصوص وحدود
    TEXT_PRIMARY = "#F8FAFC"  # Slate 50
    TEXT_SECONDARY = "#94A3B8"  # Slate 400
    HEADER_TEXT = "#E2E8F0"
    BORDER = "#334155"  # Slate 700
    BORDER_FOCUS = "#60A5FA"
    INPUT_BG = "#111827"  # Gray 900
    INPUT_BG_FOCUS = "#1F2937"  # Gray 800
    INPUT_BORDER = "#64748B"  # Slate 500
    TAB_BG = "#0F172A"  # Slate 900
    TAB_HOVER_BG = "#1F2937"  # Gray 800

    # عناصر إضافية
    SCROLL_BG = "#0F172A"
    SCROLL_HANDLE = "#334155"


# ========== BASE STYLES (القوالب الأساسية) ==========
class StyleTemplates:

    @staticmethod
    def get_common_styles(colors):
        """توليد الأنماط المشتركة بناءً على الألوان الممررة"""
        return f"""
            /* --- Global Widget Settings --- */
            QWidget {{
                font-family: 'Segoe UI', 'Cairo', sans-serif;
                color: {colors.TEXT_PRIMARY};
            }}

            QLabel {{
                color: {colors.TEXT_PRIMARY};
            }}

            /* --- Main Window --- */
            QMainWindow {{
                background-color: {colors.BG_MAIN};
            }}

            /* --- GroupBox --- */
            QGroupBox {{
                border: 1px solid {colors.BORDER};
                border-radius: 8px;
                margin-top: 20px;
                background-color: {colors.BG_CARD};
                font-weight: bold;
                padding-top: 20px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
                color: {colors.TEXT_SECONDARY};
            }}

            /* --- Inputs (LineEdit, SpinBox, DateEdit) --- */
            QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox {{
                padding: 8px 10px;
                border: 1px solid {colors.BORDER};
                border-radius: 6px;
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
                selection-background-color: {colors.PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {colors.TEXT_SECONDARY};
            }}
            QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {colors.BORDER_FOCUS};
                background-color: {colors.INPUT_BG_FOCUS};
            }}
            QLineEdit:disabled, QDateEdit:disabled {{
                background-color: {colors.BG_MAIN};
                color: {colors.TEXT_SECONDARY};
            }}

            /* --- ComboBox --- */
            QComboBox {{
                padding: 8px 10px;
                border: 1px solid {colors.BORDER};
                border-radius: 6px;
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none; /* يمكن استبدالها بصورة */
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {colors.TEXT_SECONDARY};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {colors.BORDER};
                background-color: {colors.BG_CARD};
                color: {colors.TEXT_PRIMARY};
                selection-background-color: {colors.PRIMARY};
                selection-color: white;
                outline: none;
                padding: 5px;
            }}
            QComboBox:focus {{
                border: 2px solid {colors.BORDER_FOCUS};
                background-color: {colors.INPUT_BG_FOCUS};
            }}

            /* --- TextEdit --- */
            QTextEdit {{
                padding: 10px;
                border: 1px solid {colors.BORDER};
                border-radius: 6px;
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
            }}
            QTextEdit:focus {{
                border: 2px solid {colors.BORDER_FOCUS};
                background-color: {colors.INPUT_BG_FOCUS};
            }}

            /* --- Tables --- */
            QTableWidget {{
                background-color: {colors.BG_CARD};
                border: 1px solid {colors.BORDER};
                border-radius: 8px;
                gridline-color: {colors.BORDER};
                selection-background-color: {colors.PRIMARY}30; /* Semi-transparent primary */
                selection-color: {colors.TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {colors.BG_MAIN};
                color: {colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {colors.BG_HEADER};
                color: {colors.HEADER_TEXT};
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 13px;
                text-transform: uppercase;
            }}
            QTableCornerButton::section {{
                background-color: {colors.BG_HEADER};
                border: none;
            }}

            /* --- TabWidget (Modern Pills) --- */
            QTabWidget::pane {{
                border: 1px solid {colors.BORDER};
                border-radius: 8px;
                background: {colors.BG_CARD};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {colors.TAB_BG};
                color: {colors.TEXT_SECONDARY};
                padding: 10px 25px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {colors.BG_CARD};
                color: {colors.PRIMARY};
                border-bottom: 2px solid {colors.PRIMARY};
            }}
            QTabBar::tab:hover {{
                background: {colors.TAB_HOVER_BG};
            }}

            /* --- Menus --- */
            QMenu {{
                background-color: {colors.BG_CARD};
                color: {colors.TEXT_PRIMARY};
                border: 1px solid {colors.BORDER};
            }}
            QMenu::item:selected {{
                background-color: {colors.PRIMARY};
                color: white;
            }}
            QMenuBar {{
                background-color: {colors.BG_HEADER};
                color: {colors.HEADER_TEXT};
            }}
            QMenuBar::item:selected {{
                background-color: {colors.PRIMARY};
                color: white;
            }}

            /* --- Check/Radio --- */
            QCheckBox, QRadioButton {{
                color: {colors.TEXT_PRIMARY};
            }}

            /* --- Scrollbars (Modern & Slim) --- */
            QScrollBar:vertical {{
                border: none;
                background: {colors.SCROLL_BG};
                width: 10px;
                margin: 0px;
                border-radius: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors.SCROLL_HANDLE};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            /* --- Tooltips --- */
            QToolTip {{
                color: {colors.HEADER_TEXT};
                background-color: {colors.BG_HEADER};
                border: 1px solid {colors.BORDER};
                padding: 5px;
                border-radius: 4px;
                opacity: 230;
            }}

            /* --- MessageBox --- */
            QMessageBox {{
                background-color: {colors.BG_CARD};
            }}
            QMessageBox QLabel {{
                color: {colors.TEXT_PRIMARY};
            }}
        """

    @staticmethod
    def get_button_styles(colors):
        return f"""
            /* Primary Button */
            QPushButton {{
                background-color: {colors.PRIMARY};
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {colors.PRIMARY_DARK}; }}

            /* Specific Classes (Assign these manually in code if needed) */
            QPushButton[class="danger"] {{ background-color: {colors.DANGER}; }}
            QPushButton[class="danger"]:hover {{ background-color: {colors.DANGER_HOVER}; }}

            QPushButton[class="success"] {{ background-color: {colors.SUCCESS}; }}
            QPushButton[class="success"]:hover {{ background-color: {colors.SUCCESS_HOVER}; }}

            QPushButton[class="outline"] {{
                background-color: transparent;
                border: 2px solid {colors.PRIMARY};
                color: {colors.PRIMARY};
            }}
            QPushButton[class="outline"]:hover {{
                background-color: {colors.PRIMARY}10;
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


def get_card_style():
    """نمط البطاقة البيضاء"""
    colors = ThemeManager.get_colors()
    return f"""
        QFrame {{
            background-color: {colors.BG_CARD};
            border-radius: 12px;
            border: 1px solid {colors.BORDER};
        }}
    """


def get_table_style():
    """نمط موحد للجداول"""
    colors = ThemeManager.get_colors()
    return f"""
        QTableWidget {{
            background-color: {colors.BG_CARD};
            border: 1px solid {colors.BORDER};
            border-radius: 8px;
            gridline-color: {colors.BORDER};
            font-size: 13px;
            color: {colors.TEXT_PRIMARY};
        }}
        QTableWidget::item {{
            padding: 6px;
            border-bottom: 1px solid {colors.BG_MAIN};
            color: {colors.TEXT_PRIMARY};
        }}
        QTableWidget::item:alternate {{
            background-color: {colors.BG_MAIN};
        }}
        QTableWidget::item:selected {{
            background-color: {colors.PRIMARY};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {colors.BG_HEADER};
            color: {colors.HEADER_TEXT};
            padding: 10px;
            border: none;
            font-weight: bold;
        }}
    """


def get_tabs_style():
    """نمط موحد للتبويبات"""
    colors = ThemeManager.get_colors()
    return f"""
        QTabWidget::pane {{
            border: 1px solid {colors.BORDER};
            background: {colors.BG_CARD};
            border-radius: 12px;
            margin-top: 15px;
        }}
        QTabBar::tab {{
            background: {colors.BG_MAIN};
            color: {colors.TEXT_SECONDARY};
            padding: 12px 30px;
            margin-right: 6px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: bold;
            font-family: 'Segoe UI', 'Cairo';
        }}
        QTabBar::tab:selected {{
            background: {colors.BG_CARD};
            color: {colors.PRIMARY};
            border-bottom: 2px solid {colors.PRIMARY};
        }}
        QTabBar::tab:hover {{
            background: {colors.BORDER};
        }}
    """


# ========== LOADING OVERLAY ==========

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QVBoxLayout, QWidget  # noqa: E402 (imports at module level preferred)


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
    },
    "Pédagogique": {
        "academic_settings": {"can_write": False, "can_delete": False},
        "student_management": {"can_write": False, "can_delete": False},
        "student_attendance": {"can_write": True, "can_delete": False},
        "student_discipline": {"can_write": True, "can_delete": False},
        "student_grades": {"can_write": True, "can_delete": False},
        "bulletin_generation": {"can_write": True, "can_delete": False},
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
