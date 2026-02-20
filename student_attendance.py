import sys
import sqlite3
import os
from datetime import datetime
from database_setup import DatabaseManager
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QFrame, QDateEdit,
                             QTabWidget, QGraphicsDropShadowEffect, QGridLayout, 
                             QCheckBox, QFileDialog, QGroupBox)
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

# --- فئة تقارير PDF الرسمية (كما هي مع تحسينات طفيفة) ---
class AttendancePDF(FPDF):
    def __init__(self, school_info):
        super().__init__(orientation='P')
        self.school_info = school_info
        self.font_name = "Helvetica"
        self.arabic_font_ready = False
        if _register_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def header(self):
        left_x, left_y = 10, 10
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
        self.cell(0, 8, "RAPPORT D'ASSIDUITE", 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | {datetime.now().strftime("%Y-%m-%d")}', 0, 0, 'C')

class StudentAttendanceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion de l'Assiduité / إدارة الحضور والغياب")
        self.setMinimumSize(1100, 750)
        
        # تطبيق المظهر باستخدام ThemeManager
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            self.setStyleSheet(f"background-color: {Colors().BG_MAIN};")
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
            """)
        
        # self.init_db() - moved to database_setup.py
        self.init_ui()
        self.load_classes()

    # init_db logic moved to database_setup.py

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header (Deep Slate Style)
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
        
        icon_lbl = QLabel("📅")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("SUIVI DE L'ASSIDUITÉ")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {Colors().HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("متابعة الغياب والحضور اليومي")
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

        self.setup_daily_entry_tab()
        self.setup_reports_tab()

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

    def styled_date(self):
        de = QDateEdit()
        de.setCalendarPopup(True)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            de.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        else:
            colors = Colors()
            de.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        de.setMinimumHeight(38)
        return de

    def setup_daily_entry_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        filter_card = self.create_card()
        grid = QGridLayout(filter_card)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)

        self.combo_class_entry = self.styled_combo()
        self.combo_class_entry.addItem("Choisir une Classe...", None)
        self.combo_class_entry.currentIndexChanged.connect(self.load_students_for_entry)

        self.date_entry = self.styled_date()
        self.date_entry.setDate(QDate.currentDate())
        self.date_entry.dateChanged.connect(self.load_students_for_entry)

        btn_load = QPushButton("📥 Charger / تحميل")
        btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_load.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; padding: 10px; border-radius: 6px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_load.clicked.connect(self.load_students_for_entry)

        grid.addWidget(QLabel("Classe:"), 0, 0)
        grid.addWidget(self.combo_class_entry, 0, 1)
        grid.addWidget(QLabel("Date:"), 0, 2)
        grid.addWidget(self.date_entry, 0, 3)
        grid.addWidget(btn_load, 0, 4)

        layout.addWidget(filter_card)

        self.table_entry = QTableWidget()
        self.style_table(self.table_entry)
        self.table_entry.setColumnCount(7)
        self.table_entry.setHorizontalHeaderLabels(["ID", "Élève", "Statut", "Justifié", "Motif", "Notes", "Action"])
        self.table_entry.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_entry)

        btn_save_all = QPushButton("💾 Enregistrer / حفظ")
        btn_save_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_all.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {colors.SUCCESS};
                color: white; 
                padding: 12px; 
                font-weight: bold; 
                font-size: 14px; 
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_save_all.clicked.connect(self.save_daily_attendance)
        layout.addWidget(btn_save_all)

        self.tabs.addTab(tab, "  📝 Pointage Journalier / تسجيل يومي  ")

    # ---------------------------------------------------------
    # TAB 2: Reports
    # ---------------------------------------------------------
    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # فلاتر التقرير
        filter_card = self.create_card()
        grid = QGridLayout(filter_card)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)

        self.combo_class_report = self.styled_combo()
        self.combo_class_report.addItem("Toutes les classes", None)
        self.combo_class_report.currentIndexChanged.connect(self.load_students_for_report_combo)

        self.combo_student_report = self.styled_combo()
        self.combo_student_report.addItem("Tous les élèves", None)

        self.date_from = self.styled_date()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))

        self.date_to = self.styled_date()
        self.date_to.setDate(QDate.currentDate())

        grid.addWidget(QLabel("Classe:"), 0, 0)
        grid.addWidget(self.combo_class_report, 0, 1)
        grid.addWidget(QLabel("Élève:"), 0, 2)
        grid.addWidget(self.combo_student_report, 0, 3)
        grid.addWidget(QLabel("Du (من):"), 1, 0)
        grid.addWidget(self.date_from, 1, 1)
        grid.addWidget(QLabel("Au (إلى):"), 1, 2)
        grid.addWidget(self.date_to, 1, 3)

        # أزرار التقارير
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_style = """
            QPushButton { color: white; font-weight: bold; border-radius: 6px; padding: 10px; border: none; }
        """
        
        btn_daily_pdf = QPushButton("📄 Journalier (Journal)")
        btn_daily_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_daily_pdf.setStyleSheet(btn_style + f"QPushButton {{ background-color: {colors.WARNING}; }} QPushButton:hover {{ background-color: {colors.WARNING}; }}")
        btn_daily_pdf.clicked.connect(lambda: self.generate_pdf_report("daily"))

        btn_indiv_pdf = QPushButton("👤 Individuel (Historique)")
        btn_indiv_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_indiv_pdf.setStyleSheet(btn_style + f"QPushButton {{ background-color: {colors.PRIMARY}; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_indiv_pdf.clicked.connect(lambda: self.generate_pdf_report("individual"))

        btn_global_pdf = QPushButton("📊 Statistiques (Stats)")
        btn_global_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_global_pdf.setStyleSheet(btn_style + f"QPushButton {{ background-color: {colors.SECONDARY}; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_global_pdf.clicked.connect(lambda: self.generate_pdf_report("stats"))

        btn_layout.addWidget(btn_daily_pdf)
        btn_layout.addWidget(btn_indiv_pdf)
        btn_layout.addWidget(btn_global_pdf)
        
        grid.addLayout(btn_layout, 2, 0, 1, 4)
        layout.addWidget(filter_card)

        # معاينة النتائج
        layout.addWidget(QLabel("Aperçu Rapide / معاينة سريعة:"))
        self.table_report = QTableWidget()
        self.style_table(self.table_report)
        self.table_report.setColumnCount(5)
        self.table_report.setHorizontalHeaderLabels(["Date", "Élève", "Classe", "Statut", "Motif"])
        self.table_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_report)

        btn_preview = QPushButton("🔍 Rechercher / بحث")
        btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_preview.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.TEXT_SECONDARY}; color: white; padding: 8px; border-radius: 6px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: {colors.TEXT_PRIMARY}; }}
        """)
        btn_preview.clicked.connect(self.preview_report_data)
        layout.addWidget(btn_preview)

        self.tabs.addTab(tab, "  📈 Rapports & Statistiques / التقارير  ")

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(44)
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
    # Logic: Data Loading
    # ---------------------------------------------------------
    def load_classes(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, class_name_fr FROM Classes")
                classes = cursor.fetchall()
            
            self.combo_class_entry.clear()
            self.combo_class_entry.addItem("Choisir une Classe...", None)
            
            self.combo_class_report.clear()
            self.combo_class_report.addItem("Toutes les classes", None)
            
            for c in classes:
                self.combo_class_entry.addItem(c[1], c[0])
                self.combo_class_report.addItem(c[1], c[0])
        except:
            pass

    def load_students_for_entry(self):
        class_id = self.combo_class_entry.currentData()
        date_sel = self.date_entry.date().toString("yyyy-MM-dd")
        self.table_entry.setRowCount(0)
        
        if not class_id: return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr, 
                    A.status, A.justifie, A.reason, A.notes
                FROM Students S
                LEFT JOIN StudentAttendance A ON S.id = A.student_id AND A.date = ?
                WHERE S.class_id = ? AND S.status = 'Active'
            """
            cursor.execute(query, (date_sel, class_id))
            rows = cursor.fetchall()
        
        for r in rows:
            idx = self.table_entry.rowCount()
            self.table_entry.insertRow(idx)
            
            # ID & Name
            id_item = QTableWidgetItem(str(r[0]))
            id_item.setFlags(id_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table_entry.setItem(idx, 0, id_item)
            
            name_item = QTableWidgetItem(r[1])
            name_item.setFlags(name_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table_entry.setItem(idx, 1, name_item)
            
            # Status Combo
            cmb_status = QComboBox()
            cmb_status.addItems(["Présent", "Absent", "Retard", "Exclu"])
            if r[2]: cmb_status.setCurrentText(r[2])
            # تنسيق الكومبو داخل الجدول
            cmb_status.setStyleSheet("QComboBox { border: none; background: transparent; }")
            self.table_entry.setCellWidget(idx, 2, cmb_status)
            
            # Justified Checkbox
            chk_widget = QWidget()
            chk_box = QCheckBox()
            if r[3] == 1: chk_box.setChecked(True)
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk_box)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0,0,0,0)
            self.table_entry.setCellWidget(idx, 3, chk_widget)
            
            # Reason & Notes
            self.table_entry.setItem(idx, 4, QTableWidgetItem(r[4] if r[4] else ""))
            self.table_entry.setItem(idx, 5, QTableWidgetItem(r[5] if r[5] else ""))
            
            # Action
            btn_reset = QPushButton("↺")
            btn_reset.setToolTip("Réinitialiser")
            colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
            btn_reset.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.TEXT_SECONDARY}; color: white; border-radius: 4px; font-weight: bold; border: none; }}
                QPushButton:hover {{ background-color: {colors.TEXT_PRIMARY}; }}
            """)
            btn_reset.clicked.connect(lambda ch, row=idx: self.reset_row(row))
            self.table_entry.setCellWidget(idx, 6, btn_reset)

        # conn.close()

    def reset_row(self, row):
        self.table_entry.cellWidget(row, 2).setCurrentIndex(0) # Présent
        self.table_entry.cellWidget(row, 3).findChild(QCheckBox).setChecked(False)
        self.table_entry.item(row, 4).setText("")
        self.table_entry.item(row, 5).setText("")

    def save_daily_attendance(self):
        class_id = self.combo_class_entry.currentData()
        date_sel = self.date_entry.date().toString("yyyy-MM-dd")
        
        if not class_id: return

        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Fetch active year once
                cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
                active_year = cursor.fetchone()
                year_id = active_year[0] if active_year else None
            
                for row in range(self.table_entry.rowCount()):
                    sid = int(self.table_entry.item(row, 0).text())
                    
                    status = self.table_entry.cellWidget(row, 2).currentText()
                    is_justified = 1 if self.table_entry.cellWidget(row, 3).findChild(QCheckBox).isChecked() else 0
                    reason = self.table_entry.item(row, 4).text()
                    notes = self.table_entry.item(row, 5).text()
                    
                    cursor.execute("SELECT id FROM StudentAttendance WHERE student_id = ? AND date = ?", (sid, date_sel))
                    exists = cursor.fetchone()

                    if exists:
                        cursor.execute("""
                            UPDATE StudentAttendance 
                            SET status=?, justifie=?, reason=?, notes=?, year_id=?
                            WHERE id=?
                        """, (status, is_justified, reason, notes, year_id, exists[0]))
                    else:
                        cursor.execute("""
                            INSERT INTO StudentAttendance (student_id, date, status, justifie, reason, notes, year_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (sid, date_sel, status, is_justified, reason, notes, year_id))
            
                conn.commit()
                QMessageBox.information(self, "Succès", "Données enregistrées avec succès!")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # ---------------------------------------------------------
    # Logic: Reports
    # ---------------------------------------------------------
    def load_students_for_report_combo(self):
        class_id = self.combo_class_report.currentData()
        self.combo_student_report.clear()
        self.combo_student_report.addItem("Tous les élèves", None)
        
        if not class_id: return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, first_name_fr || ' ' || last_name_fr FROM Students WHERE class_id=?", (class_id,))
            for r in cursor.fetchall():
                self.combo_student_report.addItem(r[1], r[0])

    def preview_report_data(self):
        data = self.fetch_report_data()
        self.table_report.setRowCount(0)
        for r in data:
            idx = self.table_report.rowCount()
            self.table_report.insertRow(idx)
            self.table_report.setItem(idx, 0, QTableWidgetItem(r['date']))
            self.table_report.setItem(idx, 1, QTableWidgetItem(r['name']))
            self.table_report.setItem(idx, 2, QTableWidgetItem(r['class']))
            self.table_report.setItem(idx, 3, QTableWidgetItem(r['status']))
            motif = r['reason']
            if r['justifie']: motif += " (Justifié)"
            self.table_report.setItem(idx, 4, QTableWidgetItem(motif))

    def fetch_report_data(self):
        cid = self.combo_class_report.currentData()
        sid = self.combo_student_report.currentData()
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to = self.date_to.date().toString("yyyy-MM-dd")

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT A.date, S.first_name_fr || ' ' || S.last_name_fr, C.class_name_fr, 
                    A.status, A.justifie, A.reason
                FROM StudentAttendance A
                JOIN Students S ON A.student_id = S.id
                JOIN Classes C ON S.class_id = C.id
                WHERE A.date BETWEEN ? AND ?
            """
            params = [d_from, d_to]
            
            if cid:
                query += " AND S.class_id = ?"
                params.append(cid)
            if sid:
                query += " AND A.student_id = ?"
                params.append(sid)
                
            query += " ORDER BY A.date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append({
                'date': r[0], 'name': r[1], 'class': r[2],
                'status': r[3], 'justifie': r[4], 'reason': r[5]
            })
        return results

    def sanitize_text(self, text):
        if not text:
            return ""
        if _contains_arabic(text) and ARABIC_SUPPORT and _get_arabic_font_path():
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def sanitize_filename(self, text):
        if not text:
            return ""
        cleaned = str(text).strip().replace(" ", "_")
        return "".join(ch for ch in cleaned if ch.isalnum() or ch in "-_")

    def generate_pdf_report(self, report_type):
        data = self.fetch_report_data()
        if not data:
            QMessageBox.warning(self, "Vide", "Aucune donnée à imprimer.")
            return

        date_str = self.date_to.date().toString('yyyy-MM-dd')
        student_name = self.combo_student_report.currentText() if hasattr(self, 'combo_student_report') else ""
        student_slug = self.sanitize_filename(student_name)

        if report_type == "daily":
            default_name = f"Rapport_Journalier_{date_str}.pdf"
        elif report_type == "individual":
            default_name = f"Rapport_Individuel_{student_slug}.pdf" if student_slug else "Rapport_Individuel.pdf"
        elif report_type == "stats":
            default_name = "Rapport_Statistique.pdf"
        else:
            default_name = "Rapport.pdf"

        file_path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder PDF", default_name, "PDF Files (*.pdf)")
        if not file_path: return

        school_info = None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
                school_info = cursor.fetchone()
        except:
            pass

        try:
            pdf = AttendancePDF(school_info)
            pdf.add_page()
            pdf.set_font(pdf.font_name, '', 10)

            title = ""
            if report_type == "daily": title = f"RAPPORT JOURNALIER ({self.date_to.date().toString('yyyy-MM-dd')})"
            elif report_type == "individual": title = "HISTORIQUE INDIVIDUEL D'ASSIDUITE"
            elif report_type == "stats": title = "RAPPORT STATISTIQUE"
            
            pdf.set_font(pdf.font_name, 'B', 12)
            pdf.cell(0, 10, pdf.sanitize(title), 0, 1, 'C')
            pdf.set_font(pdf.font_name, '', 10)
            pdf.cell(0, 10, pdf.sanitize(f"Periode: {self.date_from.text()} - {self.date_to.text()}"), 0, 1, 'C')
            pdf.ln(5)

            pdf.set_fill_color(220, 220, 220)
            if report_type == "stats":
                pdf.cell(80, 10, "Eleve", 1, 0, 'C', True)
                pdf.cell(30, 10, "Absences", 1, 0, 'C', True)
                pdf.cell(30, 10, "Retards", 1, 0, 'C', True)
                pdf.cell(50, 10, "Taux Presence", 1, 1, 'C', True)
                
                stats = {}
                for row in data:
                    name = row['name']
                    if name not in stats: stats[name] = {'abs': 0, 'late': 0, 'total': 0}
                    stats[name]['total'] += 1
                    if row['status'] == 'Absent': stats[name]['abs'] += 1
                    if row['status'] == 'Retard': stats[name]['late'] += 1
                
                for name, val in stats.items():
                    rate = 100 - ((val['abs'] / val['total']) * 100) if val['total'] > 0 else 100
                    pdf.cell(80, 10, self.sanitize_text(name), 1)
                    pdf.cell(30, 10, str(val['abs']), 1, 0, 'C')
                    pdf.cell(30, 10, str(val['late']), 1, 0, 'C')
                    pdf.cell(50, 10, f"{rate:.1f}%", 1, 1, 'C')

            else:
                pdf.cell(30, 10, "Date", 1, 0, 'C', True)
                pdf.cell(60, 10, "Eleve", 1, 0, 'C', True)
                pdf.cell(30, 10, "Statut", 1, 0, 'C', True)
                pdf.cell(70, 10, "Motif / Remarque", 1, 1, 'C', True)

                for row in data:
                    pdf.cell(30, 10, str(row['date']), 1)
                    pdf.cell(60, 10, self.sanitize_text(row['name']), 1)
                    
                    status_txt = self.sanitize_text(row['status'])
                    if row['justifie']: status_txt += " (J)"
                    
                    pdf.cell(30, 10, status_txt, 1, 0, 'C')
                    
                    motif = self.sanitize_text(row['reason']) if row['reason'] else "-"
                    pdf.cell(70, 10, motif, 1, 1)

            pdf.output(file_path)
            QMessageBox.information(self, "Terminé", "Le fichier PDF a été généré.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur PDF: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentAttendanceWindow()
    window.show()
    sys.exit(app.exec())