import sys
import os
from database_setup import DatabaseManager
from app_logger import AppLogger
from repositories.grades_repo import GradesRepository
from repositories.student_repo import StudentRepository
from repositories.finance_repo import FinanceRepository
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QHeaderView, QFrame, QGroupBox, QDoubleSpinBox,
                             QGridLayout, QTabWidget, QLineEdit,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_table_header_style, apply_table_body_style, set_zebra_row_fill

THEME_AVAILABLE = True
GRADES_SHEET_OUTPUT_MODE = get_report_output_mode("grades_sheet_mode", "print")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ModuleNotFoundError:
    ARABIC_SUPPORT = False


def _get_arabic_font_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    families = [
        {
            "regular": os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Regular.ttf"),
            "bold": os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Bold.ttf"),
            "italic": os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Italic.ttf"),
            "bold_italic": os.path.join(base_dir, "Fonts", "Amiri", "Amiri-BoldItalic.ttf"),
        },
        {
            "regular": os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "static", "NotoNaskhArabic-Regular.ttf"),
            "bold": os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "static", "NotoNaskhArabic-Bold.ttf"),
            "italic": os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "static", "NotoNaskhArabic-Regular.ttf"),
            "bold_italic": os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "static", "NotoNaskhArabic-Bold.ttf"),
        },
        {
            "regular": os.path.join(base_dir, "Fonts", "Cairo", "static", "Cairo-Regular.ttf"),
            "bold": os.path.join(base_dir, "Fonts", "Cairo", "static", "Cairo-Bold.ttf"),
            "italic": os.path.join(base_dir, "Fonts", "Cairo", "static", "Cairo-Regular.ttf"),
            "bold_italic": os.path.join(base_dir, "Fonts", "Cairo", "static", "Cairo-Bold.ttf"),
        },
        {
            "regular": os.path.join(base_dir, "fonts", "Amiri-Regular.ttf"),
            "bold": os.path.join(base_dir, "fonts", "Amiri-Bold.ttf"),
            "italic": os.path.join(base_dir, "fonts", "Amiri-Italic.ttf"),
            "bold_italic": os.path.join(base_dir, "fonts", "Amiri-BoldItalic.ttf"),
        },
        {
            "regular": os.path.join(base_dir, "fonts", "NotoNaskhArabic-Regular.ttf"),
            "bold": os.path.join(base_dir, "fonts", "NotoNaskhArabic-Bold.ttf"),
            "italic": os.path.join(base_dir, "fonts", "NotoNaskhArabic-Regular.ttf"),
            "bold_italic": os.path.join(base_dir, "fonts", "NotoNaskhArabic-Bold.ttf"),
        },
        {
            "regular": os.path.join(base_dir, "fonts", "Cairo-Regular.ttf"),
            "bold": os.path.join(base_dir, "fonts", "Cairo-Bold.ttf"),
            "italic": os.path.join(base_dir, "fonts", "Cairo-Regular.ttf"),
            "bold_italic": os.path.join(base_dir, "fonts", "Cairo-Bold.ttf"),
        },
    ]

    for family in families:
        if os.path.exists(family["regular"]):
            return {
                "regular": family["regular"],
                "bold": family["bold"] if os.path.exists(family["bold"]) else family["regular"],
                "italic": family["italic"] if os.path.exists(family["italic"]) else family["regular"],
                "bold_italic": family["bold_italic"] if os.path.exists(family["bold_italic"]) else family["bold"] if os.path.exists(family["bold"]) else family["regular"],
            }
    return None


def _contains_arabic(text):
    if text is None:
        return False
    if not isinstance(text, str):
        text = str(text)
    return any(
        "\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" or "\u08A0" <= ch <= "\u08FF"
        for ch in text
    )


def _prepare_pdf_text(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if _contains_arabic(text) and ARABIC_SUPPORT:
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
    return text


def _sanitize_latin(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.encode('latin-1', 'ignore').decode('latin-1')


def _register_arabic_font(pdf):
    font_files = _get_arabic_font_files()
    if not font_files:
        return False
    try:
        pdf.add_font("ArabicFont", style="", fname=font_files["regular"])
        pdf.add_font("ArabicFont", style="B", fname=font_files["bold"])
        pdf.add_font("ArabicFont", style="I", fname=font_files["italic"])
        pdf.add_font("ArabicFont", style="BI", fname=font_files["bold_italic"])
        return True
    except Exception:
        return False

# --- فئة تقارير PDF الرسمية ---


class GradesSheetPDF(FPDF):
    def __init__(self, title_doc="FEUILLE DE NOTES"):
        super().__init__()
        self.title_doc = title_doc
        self.school_info = None
        self.font_name = "Helvetica"
        self.arabic_font_ready = False
        if _register_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def set_school_info(self, info):
        self.school_info = info

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def header(self):
        left_x, left_y = 10, 5
        self.set_xy(left_x, left_y)
        self.set_font(self.font_name, '', 8)
        if self.school_info:
            republic = self.sanitize(self.school_info[1])
            self.cell(80, 3, republic, 0, 1, 'L')
            ia_text = self.sanitize(self.school_info[2])
            self.cell(80, 3, ia_text, 0, 1, 'L')
            ief_text = self.sanitize(self.school_info[3])
            self.cell(80, 3, ief_text, 0, 1, 'L')
            school_name = self.sanitize(self.school_info[4])
            self.cell(80, 3, school_name, 0, 1, 'L')
            auth_text = self.sanitize(self.school_info[5])
            self.cell(80, 3, f"Auto N: {auth_text}", 0, 1, 'L')
            addr_text = self.sanitize(self.school_info[6])
            self.cell(80, 3, f"Lieu: {addr_text}", 0, 1, 'L')
            phone_text = self.sanitize(self.school_info[7])
            self.cell(80, 3, f"Tel: {phone_text}", 0, 1, 'L')

        right_x = 175
        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=20, h=22)
            except Exception:
                pass

        self.set_xy(right_x, left_y + 22)
        self.set_y(self.get_y() + 2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

        title_style = '' if self.arabic_font_ready else 'B'
        self.set_font(self.font_name, title_style, 12)
        self.set_text_color(44, 62, 80)
        self.cell(0, 8, self.title_doc, 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


class StudentGradesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Notes / إدارة العلامات")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER}; border-radius: 8px; margin-top: 10px;
                    background-color: {colors.BG_CARD}; font-weight: bold; color: {colors.TEXT_SECONDARY};
                }}
            """)

        self.init_ui()
        self.load_classes(self.combo_class)
        self.load_classes(self.combo_view_class)
        self.on_view_class_changed()

    # ===== إضافة دالة جلب السنة النشطة =====
    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return StudentRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        header_frame.setStyleSheet(f"""
            QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 10px; }}
        """)
        header_frame.setMaximumHeight(80)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)

        icon_lbl = QLabel("📝")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DES NOTES")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("إدارة العلامات والاختبارات")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")

        title_layout.addWidget(header_lbl)
        title_layout.addWidget(sub_lbl)

        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_layout)
        hl.addStretch()

        self.main_layout.addWidget(header_frame)

        # 2. Tabs
        self.tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.tabs.setStyleSheet(get_tabs_style())
        else:
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 12px; margin-top: 15px; }}
                QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 12px 30px; margin-right: 6px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-family: 'Segoe UI', 'Cairo'; }}
                QTabBar::tab:selected {{ background: {colors.BG_CARD}; color: {colors.PRIMARY}; border-bottom: 2px solid {colors.PRIMARY}; }}
                QTabBar::tab:hover {{ background: {colors.BORDER}; }}
            """)

        self.setup_entry_tab()
        self.setup_view_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20); shadow.setColor(QColor(15, 23, 42, 15)); shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def sanitize_filename(self, text):
        if not text: return ""
        cleaned = str(text).strip().replace(" ", "_")
        return "".join(ch for ch in cleaned if ch.isalnum() or ch in "-_")

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        combo.setMinimumHeight(40)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())
        else:
            colors = Colors()
            table.setStyleSheet(f"""
                QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item:alternate {{ background-color: {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 8px; border: none; font-weight: bold; }}
            """)

    # ---------------------------------------------------------
    # TAB 1: Saisie (الإدخال)
    # ---------------------------------------------------------
    def setup_entry_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        filter_card = self.create_card()
        filter_layout = QGridLayout(filter_card)
        filter_layout.setContentsMargins(20, 20, 20, 20)
        filter_layout.setSpacing(15)

        self.combo_class = self.styled_combo()
        self.combo_class.currentIndexChanged.connect(self.on_class_changed_entry)

        self.combo_subject = self.styled_combo()
        self.combo_period = self.styled_combo()
        self.combo_period.currentIndexChanged.connect(self.load_assessments_entry)

        self.combo_assessment = self.styled_combo()

        btn_load = QPushButton("📥 Charger / تحميل")
        btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_load.setStyleSheet(f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_load.clicked.connect(self.load_grading_sheet)

        filter_layout.addWidget(QLabel("Classe:"), 0, 0)
        filter_layout.addWidget(self.combo_class, 0, 1)
        filter_layout.addWidget(QLabel("Matiere:"), 0, 2)
        filter_layout.addWidget(self.combo_subject, 0, 3)
        filter_layout.addWidget(QLabel("Periode:"), 1, 0)
        filter_layout.addWidget(self.combo_period, 1, 1)
        filter_layout.addWidget(QLabel("Evaluation:"), 1, 2)
        filter_layout.addWidget(self.combo_assessment, 1, 3)
        filter_layout.addWidget(btn_load, 1, 4)

        layout.addWidget(filter_card)

        self.table_grades = QTableWidget()
        self.style_table(self.table_grades)
        self.table_grades.setColumnCount(5)
        self.table_grades.setHorizontalHeaderLabels(["ID", "Nom (FR)", "Nom (AR)", "Note", "Obs"])
        self.table_grades.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_grades.verticalHeader().setDefaultSectionSize(44)
        layout.addWidget(self.table_grades)

        btn_print_blank = QPushButton("🖨️ Feuille Vierge / ورقة فارغة")
        btn_print_blank.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_blank.setStyleSheet(f"QPushButton {{ background-color: {colors.SECONDARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_print_blank.clicked.connect(self.print_sheet)

        btn_save = QPushButton("💾 Enregistrer / حفظ")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}")
        btn_save.clicked.connect(self.save_grades)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        action_layout.addWidget(btn_print_blank)
        action_layout.addWidget(btn_save)
        layout.addLayout(action_layout)

        self.tabs.addTab(tab, "  📝 Saisie / الإدخال  ")

    def setup_view_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        search_card = self.create_card()
        slayout = QHBoxLayout(search_card)
        slayout.setContentsMargins(20, 20, 20, 20)
        slayout.setSpacing(15)

        self.combo_view_class = self.styled_combo()
        self.combo_view_class.addItem("Toutes les classes", None)
        self.combo_view_class.currentIndexChanged.connect(self.on_view_class_changed)

        self.combo_view_period = self.styled_combo()
        self.combo_view_period.addItem("Toutes les périodes", None)
        self.combo_view_period.currentIndexChanged.connect(self.search_grades)

        self.txt_search_student = QLineEdit()
        self.txt_search_student.setPlaceholderText("Nom de l'etudiant...")
        self.txt_search_student.setMinimumHeight(38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        self.txt_search_student.setStyleSheet(f"QLineEdit {{ padding: 6px 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")

        btn_search = QPushButton("🔍 Rechercher")
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setStyleSheet(f"QPushButton {{ background-color: {colors.SECONDARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_search.clicked.connect(self.search_grades)

        slayout.addWidget(self.combo_view_class, 1)
        slayout.addWidget(self.combo_view_period, 1)
        slayout.addWidget(self.txt_search_student, 2)
        slayout.addWidget(btn_search)

        layout.addWidget(search_card)

        self.table_view = QTableWidget()
        self.style_table(self.table_view)
        self.table_view.setColumnCount(7)
        self.table_view.setHorizontalHeaderLabels(["Date", "Classe", "Eleve", "Matiere", "Eval", "Note", "Obs"])
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_view.verticalHeader().setDefaultSectionSize(32)
        layout.addWidget(self.table_view)

        self.tabs.addTab(tab, "  👁️ Consultation & Historique / الأرشيف  ")

    # ---------------------------------------------------------
    # Logic methods
    # ---------------------------------------------------------
    def load_classes(self, combo):
        combo.clear()
        combo.addItem("- Choisir -", None)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                for c in GradesRepository(conn).list_classes():
                    combo.addItem(c[1], c[0])
        except Exception as e:
            AppLogger.error("StudentGrades", f"Error loading classes: {e}")

    def load_periods(self, combo):
        try:
            active_year = self.get_active_year_id()
            if active_year == -1:
                return
            db = DatabaseManager()
            with db.get_connection() as conn:
                seen = set()
                for p in GradesRepository(conn).list_periods_for_year(active_year):
                    if p[1] not in seen:
                        combo.addItem(p[1], p[0])
                        seen.add(p[1])
        except Exception as e:
            pass

    def on_view_class_changed(self):
        class_id = self.combo_view_class.currentData()
        self.combo_view_period.blockSignals(True)
        self.combo_view_period.clear()
        self.combo_view_period.addItem("Toutes les périodes", None)

        try:
            active_year = self.get_active_year_id()
            if active_year == -1:
                return
            db = DatabaseManager()
            with db.get_connection() as conn:
                periods = GradesRepository(conn).list_periods_for_class_year(
                    class_id, active_year
                ) if class_id else GradesRepository(conn).list_periods_for_year(active_year)
            for period_id, period_name in periods:
                self.combo_view_period.addItem(period_name, period_id)
        except Exception:
            pass
        finally:
            self.combo_view_period.blockSignals(False)

    def on_class_changed_entry(self):
        class_id = self.combo_class.currentData()
        self.combo_subject.clear()
        self.combo_period.clear()
        if not class_id: return

        active_year = self.get_active_year_id()
        if active_year == -1:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                subjects = repo.get_class_subjects(class_id)
                if not subjects: return

                for s in subjects:
                    self.combo_subject.addItem(f"{s[1]} (Coef: {s[3]})", s[0])

                self.combo_period.addItem("- Période -", None)
                for p in repo.list_periods_for_class_year(class_id, active_year):
                    self.combo_period.addItem(p[1], p[0])
        except Exception as e:
            AppLogger.error("StudentGrades", f"Error class changed: {e}")

    def load_assessments_entry(self):
        period_id = self.combo_period.currentData()
        self.combo_assessment.clear()
        if not period_id: return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                for a in GradesRepository(conn).list_assessments_for_period(period_id):
                    self.combo_assessment.addItem(a[1], a[0])
        except Exception: pass
    # ===== جلب الطلاب باستخدام جدول التسجيل SCN =====

    def load_grading_sheet(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()

        if not all([class_id, subject_id, assess_id]):
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner la classe, la matière et l'évaluation.")
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            QMessageBox.warning(self, "Attention", "Aucune année scolaire active n'a été trouvée.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                max_score = repo.get_max_score_for_class(class_id)
                self.table_grades.horizontalHeaderItem(3).setText(f"Note /{int(max_score)}")
                rows = repo.load_grading_sheet(class_id, subject_id, assess_id, active_year)

                self.table_grades.setRowCount(0)
                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

                for r in rows:
                    idx = self.table_grades.rowCount()
                    self.table_grades.insertRow(idx)

                    id_item = QTableWidgetItem(str(r[0]))
                    id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 0, id_item)

                    item_fr = QTableWidgetItem(r[1])
                    item_fr.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 1, item_fr)

                    item_ar = QTableWidgetItem(r[2])
                    item_ar.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 2, item_ar)

                    spin = QDoubleSpinBox()
                    spin.setRange(0, max_score)
                    spin.setSingleStep(0.25)
                    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    spin.setStyleSheet(f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};")
                    if r[3] is not None: spin.setValue(r[3])
                    self.table_grades.setCellWidget(idx, 3, spin)

                    self.table_grades.setItem(idx, 4, QTableWidgetItem(r[4] or ""))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement : {e}")

    def save_grades(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()

        if not all([class_id, subject_id, assess_id]): return

        active_year = self.get_active_year_id()
        if active_year == -1: return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                today = QDate.currentDate().toString("yyyy-MM-dd")
                for row in range(self.table_grades.rowCount()):
                    sid = int(self.table_grades.item(row, 0).text())
                    score_widget = self.table_grades.cellWidget(row, 3)
                    score = score_widget.value() if score_widget else 0.0
                    obs = self.table_grades.item(row, 4).text()
                    repo.upsert_grade(sid, subject_id, assess_id, active_year, score, obs, today)
                conn.commit()
            QMessageBox.information(self, "Info", "Notes enregistrées avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement : {e}")

    def search_grades(self):
        class_id = self.combo_view_class.currentData()
        period_id = self.combo_view_period.currentData()
        student_name = self.txt_search_student.text().strip()
        active_year = self.get_active_year_id()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = GradesRepository(conn).search_grades(
                    active_year,
                    class_id=class_id,
                    period_id=period_id,
                    student_name=student_name or None,
                )

                self.table_view.setRowCount(0)
                for r in rows:
                    idx = self.table_view.rowCount()
                    self.table_view.insertRow(idx)
                    for c, val in enumerate(r):
                        self.table_view.setItem(idx, c, QTableWidgetItem(str(val if val is not None else "-")))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de recherche : {e}")

    def print_sheet(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()
        active_year = self.get_active_year_id()

        if not all([class_id, subject_id, assess_id]):
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner la classe, la matière et l'évaluation.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                try:
                    school_info = FinanceRepository(conn).get_school_info()
                except Exception:
                    school_info = None
                cls_txt = repo.get_class_label(class_id)
                sub_txt = repo.get_subject_label(subject_id)
                eval_txt = repo.get_assessment_label(assess_id)
                max_score = repo.get_max_score_for_class(class_id)
                rows = repo.get_students_for_class_year(class_id, active_year)

            file_stub = f"Feuille_Notes_{self.sanitize_filename(cls_txt)}_{self.sanitize_filename(sub_txt)}_{self.sanitize_filename(eval_txt)}"

            if self.table_grades.rowCount() == 0:
                self.table_grades.horizontalHeaderItem(3).setText(f"Note /{int(max_score)}")
                self.table_grades.setRowCount(0)
                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

                for r in rows:
                    idx = self.table_grades.rowCount()
                    self.table_grades.insertRow(idx)

                    id_item = QTableWidgetItem(str(r[0]))
                    id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 0, id_item)

                    item_fr = QTableWidgetItem(r[1])
                    item_fr.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 1, item_fr)

                    item_ar = QTableWidgetItem(r[2])
                    item_ar.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 2, item_ar)

                    spin = QDoubleSpinBox()
                    spin.setRange(0, max_score)
                    spin.setSingleStep(0.25)
                    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    spin.setStyleSheet(f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};")
                    self.table_grades.setCellWidget(idx, 3, spin)

                    self.table_grades.setItem(idx, 4, QTableWidgetItem(""))

            pdf = GradesSheetPDF()
            pdf.set_school_info(school_info)
            pdf.add_page()

            pdf.set_font(pdf.font_name, '', 11)
            cls_txt_pdf = pdf.sanitize(self.combo_class.currentText())
            sub_txt_pdf = pdf.sanitize(self.combo_subject.currentText())
            eval_txt_pdf = pdf.sanitize(self.combo_assessment.currentText())

            pdf.cell(0, 7, f"Classe: {cls_txt_pdf}", 0, 1)
            pdf.cell(0, 7, f"Matiere: {sub_txt_pdf}", 0, 1)
            pdf.cell(0, 7, f"Evaluation: {eval_txt_pdf}", 0, 1)
            pdf.ln(5)

            apply_table_header_style(pdf, pdf.font_name, 10)
            pdf.cell(15, 8, "ID", 1, 0, 'C', True)
            pdf.cell(80, 8, "Nom et Prenom", 1, 0, 'C', True)
            pdf.cell(30, 8, "Note", 1, 0, 'C', True)
            pdf.cell(65, 8, "Observation", 1, 1, 'C', True)

            apply_table_body_style(pdf, pdf.font_name, 10)
            for row in range(self.table_grades.rowCount()):
                sid = self.table_grades.item(row, 0).text()
                name = self.table_grades.item(row, 1).text()
                safe_name = pdf.sanitize(name)
                set_zebra_row_fill(pdf, row)

                pdf.cell(15, 8, sid, 1, 0, 'C', True)
                pdf.cell(80, 8, safe_name, 1, 0, 'L', True)
                pdf.cell(30, 8, "", 1, 0, 'C', True)
                pdf.cell(65, 8, "", 1, 1, 'L', True)

            output_pdf(
                pdf,
                self,
                f"{file_stub}.pdf",
                mode=GRADES_SHEET_OUTPUT_MODE,
                dialog_title="Save PDF",
                success_save_message="PDF généré.",
                success_print_message="Feuille envoyée à l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentGradesWindow()
    window.show()
    sys.exit(app.exec())
