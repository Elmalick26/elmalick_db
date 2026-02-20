import sys
import os
from database_setup import DatabaseManager
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QComboBox, QMessageBox, 
                             QHeaderView, QFrame, QGroupBox, QDoubleSpinBox, 
                             QFileDialog, QGridLayout, QTabWidget, QLineEdit,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style

THEME_AVAILABLE = True

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ModuleNotFoundError:
    ARABIC_SUPPORT = False

def _get_arabic_font_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "fonts", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "fonts", "NotoNaskhArabic-Regular.ttf"),
        os.path.join(base_dir, "fonts", "Cairo-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "NotoNaskhArabic-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Cairo", "Cairo-Regular.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
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
    font_path = _get_arabic_font_path()
    if not font_path:
        return False
    try:
        pdf.add_font("ArabicFont", "", font_path, uni=True)
        pdf.add_font("ArabicFont", "B", font_path, uni=True)
        pdf.add_font("ArabicFont", "I", font_path, uni=True)
        pdf.add_font("ArabicFont", "BI", font_path, uni=True)
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
            except:
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
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            # تطبيق نمط Deep Slate
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors.BG_MAIN};
                }}
                QLabel {{
                    font-family: 'Segoe UI', 'Cairo', sans-serif;
                    color: {colors.TEXT_PRIMARY};
                }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    margin-top: 10px;
                    background-color: {colors.BG_CARD};
                    font-weight: bold;
                    color: {colors.TEXT_SECONDARY};
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                    left: 10px;
                }}
            """)
        
        self.init_ui()
        self.load_classes(self.combo_class)
        self.load_classes(self.combo_view_class)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header
        header_frame = QFrame()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_HEADER};
                    border-radius: 10px;
                }}
            """)
        else:
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors().BG_HEADER};
                    border-radius: 10px;
                }}
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
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {Colors().HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("إدارة العلامات والاختبارات")
        sub_lbl.setFont(QFont("Cairo", 11))
        if THEME_AVAILABLE:
            sub_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        else:
            sub_lbl.setStyleSheet(f"color: {Colors().TEXT_SECONDARY}; background: transparent;")
        
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
            colors = ThemeManager.get_colors()
            self.tabs.setStyleSheet(f"""
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
            """)
        else:
            colors = Colors()
            self.tabs.setStyleSheet(f"""
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
                    background: {colors.BG_HEADER}; 
                    color: {colors.HEADER_TEXT}; 
                }}
                QTabBar::tab:hover {{
                    background: {colors.BORDER}; 
                }}
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
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_CARD}; 
                    border-radius: 12px; 
                    border: 1px solid {colors.BORDER};
                }}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def sanitize_filename(self, text):
        if not text:
            return ""
        cleaned = str(text).strip().replace(" ", "_")
        return "".join(ch for ch in cleaned if ch.isalnum() or ch in "-_")

    def styled_combo(self):
        combo = QComboBox()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            combo.setStyleSheet(f"""
                QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            combo.setStyleSheet(f"""
                QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        combo.setMinimumHeight(38)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            table.setStyleSheet(f"""
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
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                }}
            """)
        else:
            colors = Colors()
            table.setStyleSheet(f"""
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
                }}
                QTableWidget::item:alternate {{
                    background-color: {colors.BG_MAIN};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors.PRIMARY};
                    color: {colors.HEADER_TEXT};
                }}
                QHeaderView::section {{
                    background-color: {colors.BG_HEADER};
                    color: {colors.HEADER_TEXT};
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                }}
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
        btn_load.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
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

        btn_save = QPushButton("💾 Enregistrer / حفظ")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_save.clicked.connect(self.save_grades)
        layout.addWidget(btn_save)

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

        self.combo_view_period = self.styled_combo()
        self.combo_view_period.addItem("Toutes les périodes", None)
        self.load_periods(self.combo_view_period)

        self.txt_search_student = QLineEdit()
        self.txt_search_student.setPlaceholderText("Nom de l'etudiant...")
        self.txt_search_student.setMinimumHeight(38)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.txt_search_student.setStyleSheet(f"""
                QLineEdit {{ padding: 6px 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            self.txt_search_student.setStyleSheet(f"""
                QLineEdit {{ padding: 6px 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)

        btn_search = QPushButton("🔍 Rechercher")
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SECONDARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
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
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, class_name_fr FROM Classes")
            for c in cursor.fetchall():
                combo.addItem(c[1], c[0])

    def load_periods(self, combo):
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, period_name_fr FROM AcademicPeriods")
            seen = set()
            for p in cursor.fetchall():
                if p[1] not in seen:
                    combo.addItem(p[1], p[0])
                    seen.add(p[1])

    def get_class_subjects(self, cursor, class_id):
        """إرجاع المواد الفعلية للفصل: من جدول الحصص أولاً، ثم مواد المرحلة."""
        cursor.execute("""
            SELECT DISTINCT S.id, S.subject_name_fr, S.subject_name_ar, S.coefficient
            FROM Timetable T
            JOIN Subjects S ON T.subject_id = S.id
            WHERE T.class_id = ?
            ORDER BY S.id
        """, (class_id,))
        subjects = cursor.fetchall()
        if subjects:
            return subjects

        cursor.execute("SELECT cycle_id FROM Classes WHERE id=?", (class_id,))
        res = cursor.fetchone()
        if not res:
            return []
        cycle_id = res[0]
        cursor.execute("SELECT id, subject_name_fr, subject_name_ar, coefficient FROM Subjects WHERE cycle_id=? ORDER BY id", (cycle_id,))
        return cursor.fetchall()

    def on_class_changed_entry(self):
        class_id = self.combo_class.currentData()
        self.combo_subject.clear()
        self.combo_period.clear()
        if not class_id: return
        
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            subjects = self.get_class_subjects(cursor, class_id)
            if not subjects:
                return

            for s in subjects:
                self.combo_subject.addItem(f"{s[1]} (Coef: {s[3]})", s[0])

            cursor.execute("SELECT cycle_id FROM Classes WHERE id=?", (class_id,))
            res = cursor.fetchone()
            if not res:
                return
            cycle_id = res[0]
                
            self.combo_period.addItem("- Période -", None)
            cursor.execute("SELECT id, period_name_fr FROM AcademicPeriods WHERE cycle_id=? ORDER BY sort_order", (cycle_id,))
            for p in cursor.fetchall():
                self.combo_period.addItem(p[1], p[0])

    def load_assessments_entry(self):
        period_id = self.combo_period.currentData()
        self.combo_assessment.clear()
        if not period_id: return
        
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name_fr FROM AssessmentTypes WHERE period_id=?", (period_id,))
            for a in cursor.fetchall():
                self.combo_assessment.addItem(a[1], a[0])

    def load_grading_sheet(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()
        
        if not all([class_id, subject_id, assess_id]):
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner tous les champs.")
            return

        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT CY.name_fr FROM Classes CL JOIN Cycles CY ON CL.cycle_id = CY.id WHERE CL.id = ?", (class_id,))
            cname = cursor.fetchone()[0].lower()
            max_score = 10.0 if ("elem" in cname or "prim" in cname) else 20.0
            self.table_grades.horizontalHeaderItem(3).setText(f"Note /{int(max_score)}")

            query = """
                SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr, 
                       S.first_name_ar || ' ' || S.last_name_ar,
                       G.score, G.observation
                FROM Students S
                LEFT JOIN Grades G ON S.id = G.student_id 
                                   AND G.subject_id = ? 
                                   AND G.assessment_id = ?
                WHERE S.class_id = ? AND S.status = 'Active'
                ORDER BY S.last_name_fr
            """
            cursor.execute(query, (subject_id, assess_id, class_id))
            rows = cursor.fetchall()
            
            self.table_grades.setRowCount(0)
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
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    spin.setStyleSheet(
                        f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};"
                    )
                else:
                    colors = Colors()
                    spin.setStyleSheet(f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};")
                if r[3] is not None: spin.setValue(r[3])
                self.table_grades.setCellWidget(idx, 3, spin)
                
                self.table_grades.setItem(idx, 4, QTableWidgetItem(r[4] if r[4] else ""))

    def save_grades(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()
        
        if not all([class_id, subject_id, assess_id]): return

        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            today = QDate.currentDate().toString("yyyy-MM-dd")
            
            # الحصول على السنة الدراسية النشطة
            cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
            active_year = cursor.fetchone()
            year_id = active_year[0] if active_year else None
            
            for row in range(self.table_grades.rowCount()):
                sid = int(self.table_grades.item(row, 0).text())
                score_widget = self.table_grades.cellWidget(row, 3)
                score = score_widget.value() if score_widget else 0.0
                obs = self.table_grades.item(row, 4).text()
                
                cursor.execute("SELECT id FROM Grades WHERE student_id=? AND subject_id=? AND assessment_id=? AND year_id=?", (sid, subject_id, assess_id, year_id))
                exists = cursor.fetchone()
                if exists:
                    cursor.execute("UPDATE Grades SET score=?, observation=?, date_recorded=? WHERE id=?", (score, obs, today, exists[0]))
                else:
                    cursor.execute("INSERT INTO Grades (student_id, subject_id, assessment_id, score, observation, date_recorded, year_id) VALUES (?,?,?,?,?,?,?)", 
                                   (sid, subject_id, assess_id, score, obs, today, year_id))
            
            conn.commit()
        QMessageBox.information(self, "Info", "Notes enregistrées avec succès.")

    def search_grades(self):
        class_id = self.combo_view_class.currentData()
        student_name = self.txt_search_student.text().strip()

        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT G.date_recorded, C.class_name_fr, 
                       S.first_name_fr || ' ' || S.last_name_fr,
                       Sub.subject_name_fr, A.name_fr, G.score, G.observation
                FROM Grades G
                JOIN Students S ON G.student_id = S.id
                JOIN Classes C ON S.class_id = C.id
                JOIN Subjects Sub ON G.subject_id = Sub.id
                JOIN AssessmentTypes A ON G.assessment_id = A.id
                WHERE 1=1
            """
            params = []
            if class_id:
                query += " AND S.class_id = ?"
                params.append(class_id)
            if student_name:
                query += " AND (S.first_name_fr LIKE ? OR S.last_name_fr LIKE ?)"
                params.extend([f"%{student_name}%", f"%{student_name}%"])
                
            query += " ORDER BY G.date_recorded DESC LIMIT 100"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            self.table_view.setRowCount(0)
            for r in rows:
                idx = self.table_view.rowCount()
                self.table_view.insertRow(idx)
                for c, val in enumerate(r):
                    self.table_view.setItem(idx, c, QTableWidgetItem(str(val)))

    def print_sheet(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()
        if not all([class_id, subject_id, assess_id]):
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner la classe, la matière et l'évaluation.")
            return

        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            # محاولة جلب بيانات المدرسة إن وجدت
            try:
                cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
                school_info = cursor.fetchone()
            except:
                school_info = None
            
            cursor.execute("SELECT class_name_fr FROM Classes WHERE id=?", (class_id,))
            cls_row = cursor.fetchone()
            cls_txt = cls_row[0] if cls_row else "Classe"

            cursor.execute("SELECT subject_name_fr FROM Subjects WHERE id=?", (subject_id,))
            sub_row = cursor.fetchone()
            sub_txt = sub_row[0] if sub_row else "Matiere"

            cursor.execute("SELECT name_fr FROM AssessmentTypes WHERE id=?", (assess_id,))
            eval_row = cursor.fetchone()
            eval_txt = eval_row[0] if eval_row else "Evaluation"
            
            # Fetch grades data for the empty check logic later
            cursor.execute("SELECT CY.name_fr FROM Classes CL JOIN Cycles CY ON CL.cycle_id = CY.id WHERE CL.id = ?", (class_id,))
            cname = cursor.fetchone()[0].lower()
            max_score = 10.0 if ("elem" in cname or "prim" in cname) else 20.0
            
            cursor.execute("""
                SELECT id, first_name_fr || ' ' || last_name_fr,
                       first_name_ar || ' ' || last_name_ar
                FROM Students
                WHERE class_id = ? AND status = 'Active'
                ORDER BY last_name_fr
            """, (class_id,))
            rows = cursor.fetchall()

        file_stub = f"Feuille_Notes_{self.sanitize_filename(cls_txt)}_{self.sanitize_filename(sub_txt)}_{self.sanitize_filename(eval_txt)}"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{file_stub}.pdf", "PDF Files (*.pdf)")
        if not file_path: return

        if self.table_grades.rowCount() == 0:
            self.table_grades.horizontalHeaderItem(3).setText(f"Note /{int(max_score)}")

            self.table_grades.setRowCount(0)
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
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    spin.setStyleSheet(
                        f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};"
                    )
                else:
                    colors = Colors()
                    spin.setStyleSheet(f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};")
                self.table_grades.setCellWidget(idx, 3, spin)

                self.table_grades.setItem(idx, 4, QTableWidgetItem(""))

        try:
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
            
            pdf.set_fill_color(225, 225, 225)
            pdf.set_font(pdf.font_name, 'B', 10)
            pdf.cell(15, 8, "ID", 1, 0, 'C', True)
            pdf.cell(80, 8, "Nom et Prenom", 1, 0, 'C', True)
            pdf.cell(30, 8, "Note", 1, 0, 'C', True)
            pdf.cell(65, 8, "Observation", 1, 1, 'C', True)
            
            pdf.set_font(pdf.font_name, '', 10)
            for row in range(self.table_grades.rowCount()):
                sid = self.table_grades.item(row, 0).text()
                name = self.table_grades.item(row, 1).text()
                safe_name = pdf.sanitize(name)

                pdf.cell(15, 8, sid, 1)
                pdf.cell(80, 8, safe_name, 1)
                pdf.cell(30, 8, "", 1, 0, 'C')
                pdf.cell(65, 8, "", 1, 1)

            pdf.output(file_path)
            QMessageBox.information(self, "Terminé", "PDF généré.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentGradesWindow()
    window.show()
    sys.exit(app.exec())