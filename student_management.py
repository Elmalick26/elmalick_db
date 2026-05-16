import sys
import psycopg2
import os
import shutil
from datetime import datetime
from database_setup import DatabaseManager
from app_logger import AppLogger
from repositories.student_repo import StudentRepository
from repositories.finance_repo import FinanceRepository
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QLineEdit, QComboBox,
                             QMessageBox, QHeaderView, QFrame, QDateEdit,
                             QTabWidget, QGraphicsDropShadowEffect, QGridLayout, QFileDialog, QScrollArea)
from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap
from fpdf import FPDF

from ui_styles import ThemeManager, Colors, get_table_style, get_tabs_style
from print_export_service import output_pdf, get_report_output_mode

THEME_AVAILABLE = True
STUDENT_LIST_OUTPUT_MODE = get_report_output_mode("student_list_mode", "save")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ModuleNotFoundError:
    ARABIC_SUPPORT = False

# --- فئة توليد PDF (كما هي) ---


class StudentListPDF(FPDF):
    def __init__(self, school_info=None, title_doc="LISTE DES ETUDIANTS", orientation='P'):
        super().__init__(orientation=orientation, unit='mm', format='A4')
        self.school_info = school_info
        self.title_doc = title_doc

    def sanitize(self, text):
        if not text:
            return ""
        try:
            return str(text).encode('latin-1').decode('latin-1')
        except UnicodeEncodeError:
            return str(text).encode('ascii', 'ignore').decode('ascii')

    def header(self):
        left_x, left_y = 10, 5
        page_w = self.w
        right_x = page_w - 30
        self.set_xy(left_x, left_y)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(30, 41, 59)

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

        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=20, h=22)
            except Exception:
                pass

        # Keep divider/title position stable even when school info content varies.
        body_bottom_y = self.get_y()
        line_y = max(body_bottom_y + 2, left_y + 24)
        self.line(10, line_y, page_w - 10, line_y)
        self.set_y(line_y + 4)

        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(30, 41, 59)  # Slate 800
        self.set_text_color(248, 250, 252)  # Slate 50
        self.cell(0, 8, self.title_doc, 0, 1, 'C', True)
        self.set_text_color(44, 62, 80)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7)
        date_str = datetime.now().strftime('%Y-%m-%d')
        page_w = self.w - self.l_margin - self.r_margin
        self.cell(page_w / 2, 4, f"Imprimé le {date_str}", 0, 0, 'L')
        self.cell(page_w / 2, 4, f"Page {self.page_no()}", 0, 0, 'R')


class ModernStudentManagement(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Élèves / إدارة الطلاب")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
                QScrollArea {{ border: none; background: transparent; }}
            """)

        self.current_photo_path = None
        self.selected_student_id = None
        self.init_ui()
        self.load_cycles_filter()
        self.load_cycles_reg()
        self.refresh_student_list()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header (Deep Slate Style)
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

        icon_lbl = QLabel("👨‍🎓")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DES ÉLÈVES")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("إدارة ملفات الطلاب والتسجيل")
        sub_lbl.setFont(QFont("Cairo", 12))
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
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 12px; margin-top: 15px; }}
            QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 12px 30px; margin-right: 6px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-family: 'Segoe UI', 'Cairo'; font-size: 13px; }}
            QTabBar::tab:selected {{ background: {colors.BG_CARD}; color: {colors.PRIMARY}; border-bottom: 2px solid {colors.PRIMARY}; }}
            QTabBar::tab:hover {{ background: {colors.BORDER}; color: {colors.TEXT_PRIMARY}; }}
        """)

        self.setup_student_tab()
        self.setup_list_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(15, 23, 42, 15))
        shadow.setOffset(0, 4)
        frame.setGraphicsEffect(shadow)
        return frame

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        le.setMinimumHeight(40)
        return le

    def styled_combo(self):
        combo = QComboBox()
        combo.setMinimumHeight(40)
        return combo

    def styled_date(self):
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setMinimumHeight(40)
        return de

    def setup_student_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # ===== العمود الأيمن: نموذج الإدخال (Scrollable) =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(600)

        form_container = self.create_card()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)

        lbl_new = QLabel("📝 NOUVEAU PROFIL / ملف جديد")
        lbl_new.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_new.setStyleSheet(f"""
            background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; font-weight: bold;
            font-size: 14px; padding: 10px; border-radius: 6px; border: 1px dashed {colors.BORDER};
        """)
        form_layout.addWidget(lbl_new)

        photo_layout = QHBoxLayout()
        self.lbl_photo = QLabel()
        self.lbl_photo.setFixedSize(110, 110)
        self.lbl_photo.setStyleSheet(f"""
            QLabel {{ background-color: {colors.BG_MAIN}; border-radius: 55px; border: 3px solid {colors.BORDER}; color: {colors.TEXT_SECONDARY}; }}
        """)
        self.lbl_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo.setText("Photo\nصورة")

        btn_upload = QPushButton("📷")
        btn_upload.setFixedSize(36, 36)
        btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY_DARK}; color: white; border-radius: 18px; font-weight: bold; border: 2px solid {colors.BG_CARD}; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_upload.clicked.connect(self.upload_student_photo)

        photo_wrapper = QWidget()
        photo_wrapper.setStyleSheet("background: transparent; border: none;")
        pw_layout = QVBoxLayout(photo_wrapper)
        pw_layout.addWidget(self.lbl_photo)

        photo_layout.addStretch()
        photo_layout.addWidget(photo_wrapper)
        photo_layout.addWidget(btn_upload, 0, Qt.AlignmentFlag.AlignBottom)
        photo_layout.addStretch()
        form_layout.addLayout(photo_layout)

        def add_section_header(text, icon):
            lbl = QLabel(f"{icon} {text}")
            lbl.setStyleSheet(f"""
                color: {colors.TEXT_PRIMARY}; font-weight: bold; font-size: 13px; margin-top: 10px; border-bottom: 2px solid {colors.BORDER}; padding-bottom: 5px;
            """)
            form_layout.addWidget(lbl)

        # 1. البيانات الشخصية
        add_section_header("Informations Personnelles / بيانات الطالب", "👤")
        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Prénom (FR):"), 0, 0)
        self.txt_fname_fr = self.styled_input("Prénom")
        grid.addWidget(self.txt_fname_fr, 0, 1)

        grid.addWidget(QLabel("Nom (FR):"), 0, 2)
        self.txt_lname_fr = self.styled_input("Nom de famille")
        grid.addWidget(self.txt_lname_fr, 0, 3)

        grid.addWidget(QLabel("الاسم (AR):"), 1, 0)
        self.txt_fname_ar = self.styled_input("الاسم")
        grid.addWidget(self.txt_fname_ar, 1, 1)

        grid.addWidget(QLabel("اللقب (AR):"), 1, 2)
        self.txt_lname_ar = self.styled_input("اللقب")
        grid.addWidget(self.txt_lname_ar, 1, 3)

        grid.addWidget(QLabel("Naissance (Date):"), 2, 0)
        self.date_birth = self.styled_date()
        self.date_birth.setDate(QDate.currentDate().addYears(-6))
        grid.addWidget(self.date_birth, 2, 1)

        grid.addWidget(QLabel("Lieu (Lieu):"), 2, 2)
        self.txt_birth_place = self.styled_input("Lieu de naissance / مكان الولادة")
        grid.addWidget(self.txt_birth_place, 2, 3)

        grid.addWidget(QLabel("Sexe:"), 3, 0)
        self.combo_gender = self.styled_combo()
        self.combo_gender.addItems(["Masculin", "Féminin"])
        grid.addWidget(self.combo_gender, 3, 1)

        grid.addWidget(QLabel("Adresse:"), 3, 2)
        self.txt_address = self.styled_input("Adresse complète")
        grid.addWidget(self.txt_address, 3, 3)

        form_layout.addLayout(grid)

        # 2. التنسيب
        add_section_header("Affectation / التنسيب", "🎓")
        grid2 = QGridLayout()
        grid2.setSpacing(10)

        grid2.addWidget(QLabel("Cycle:"), 0, 0)
        self.combo_cycle_reg = self.styled_combo()
        self.combo_cycle_reg.currentIndexChanged.connect(self.load_classes_for_reg)
        grid2.addWidget(self.combo_cycle_reg, 0, 1)

        grid2.addWidget(QLabel("Classe:"), 0, 2)
        self.combo_class_reg = self.styled_combo()
        self.combo_class_reg.currentIndexChanged.connect(self.update_class_number_preview)
        grid2.addWidget(self.combo_class_reg, 0, 3)

        grid2.addWidget(QLabel("N° Classe:"), 0, 4)
        self.txt_class_number = self.styled_input("Auto")
        self.txt_class_number.setReadOnly(True)
        self.txt_class_number.setStyleSheet(f"""
            QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.BG_MAIN}; color: {colors.TEXT_PRIMARY}; font-weight: bold; }}
        """)
        grid2.addWidget(self.txt_class_number, 0, 5)
        form_layout.addLayout(grid2)

        # 3. الولي
        add_section_header("Tuteur / الولي", "👨‍👩‍👧")
        grid3 = QGridLayout()
        grid3.setSpacing(10)

        grid3.addWidget(QLabel("Nom:"), 0, 0)
        self.txt_parent_name = self.styled_input("Nom du tuteur")
        grid3.addWidget(self.txt_parent_name, 0, 1)

        grid3.addWidget(QLabel("Tél:"), 0, 2)
        self.txt_parent_phone = self.styled_input("Téléphone")
        grid3.addWidget(self.txt_parent_phone, 0, 3)

        grid3.addWidget(QLabel("Email:"), 1, 0)
        self.txt_parent_email = self.styled_input("Email Tuteur")
        grid3.addWidget(self.txt_parent_email, 1, 1)

        grid3.addWidget(QLabel("Adr Tuteur:"), 1, 2)
        self.txt_parent_addr = self.styled_input("Adresse du tuteur")
        grid3.addWidget(self.txt_parent_addr, 1, 3)
        form_layout.addLayout(grid3)

        # 4. الحالة
        add_section_header("Statut / الحالة", "📋")
        grid4 = QGridLayout()
        grid4.setSpacing(10)

        grid4.addWidget(QLabel("Date Inscr.:"), 0, 0)
        self.date_registration = self.styled_date()
        self.date_registration.setDate(QDate.currentDate())
        grid4.addWidget(self.date_registration, 0, 1)

        grid4.addWidget(QLabel("Statut:"), 0, 2)
        self.combo_status = self.styled_combo()
        self.combo_status.addItems(["Active", "Inactive", "Suspendu", "Diplômé"])
        grid4.addWidget(self.combo_status, 0, 3)
        form_layout.addLayout(grid4)

        form_layout.addSpacing(10)

        # أزرار العمل
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 Enregistrer / حفظ")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setMinimumHeight(45)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; border-radius: 8px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        self.btn_save.clicked.connect(self.save_student)

        self.btn_reset = QPushButton("🧹 Réinitialiser / مسح")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setMinimumHeight(45)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_SECONDARY}; border-radius: 8px; font-weight: bold; border: 1px solid {colors.BORDER}; }}
            QPushButton:hover {{ background-color: {colors.BG_MAIN}; }}
        """)
        self.btn_reset.clicked.connect(self.clear_student_form)

        btn_layout.addWidget(self.btn_save, 2)
        btn_layout.addWidget(self.btn_reset, 1)
        form_layout.addLayout(btn_layout)

        form_layout.addStretch()
        scroll.setWidget(form_container)
        layout.addWidget(scroll)

        # ===== العمود الأيسر: الجدول المختصر =====
        list_container = QWidget()
        list_container.setMaximumWidth(400)
        list_layout = QVBoxLayout(list_container)
        list_layout.setSpacing(15)
        list_layout.setContentsMargins(0, 0, 0, 0)

        toolbar = self.create_card()
        tlay = QVBoxLayout(toolbar)
        tlay.setContentsMargins(10, 10, 10, 10)
        tlay.setSpacing(8)

        self.combo_filter_class_reg = self.styled_combo()
        self.combo_filter_class_reg.addItem("Toutes les Classes", None)
        self.combo_filter_class_reg.currentIndexChanged.connect(self.refresh_student_list)

        self.combo_name_lang_reg = self.styled_combo()
        self.combo_name_lang_reg.addItem("Nom FR", "fr")
        self.combo_name_lang_reg.addItem("الاسم AR", "ar")
        self.combo_name_lang_reg.currentIndexChanged.connect(self.refresh_student_list)

        self.txt_search_reg = self.styled_input("🔍 Recherche...")
        self.txt_search_reg.textChanged.connect(self.refresh_student_list)

        btn_print_filtered = QPushButton("🖨️ Filtrée")
        btn_print_filtered.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_filtered.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY}; padding: 8px 14px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER}; }}
            QPushButton:hover {{ background-color: {colors.BG_MAIN}; }}
        """)
        btn_print_filtered.clicked.connect(self.print_filtered_list)

        btn_import_excel = QPushButton("📥 Importer Excel/CSV")
        btn_import_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import_excel.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; padding: 8px 14px; border-radius: 6px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_import_excel.clicked.connect(self._open_import_wizard)

        row_search = QHBoxLayout()
        row_search.addWidget(self.txt_search_reg, 1)

        row_filters = QHBoxLayout()
        row_filters.addWidget(self.combo_filter_class_reg)
        row_filters.addWidget(self.combo_name_lang_reg)
        row_filters.addWidget(btn_print_filtered)
        row_filters.addWidget(btn_import_excel)

        tlay.addLayout(row_search)
        tlay.addLayout(row_filters)
        list_layout.addWidget(toolbar)

        self.table_students_reg = QTableWidget()
        self.style_table(self.table_students_reg)
        self.table_students_reg.setColumnCount(4)
        self.table_students_reg.setHorizontalHeaderLabels(["ID", "N° Classe", "Nom & Prénom", "Actions"])
        self.table_students_reg.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_students_reg.setColumnWidth(0, 60)
        self.table_students_reg.setColumnWidth(1, 90)
        self.table_students_reg.setColumnWidth(3, 120)
        self.table_students_reg.itemSelectionChanged.connect(self.on_student_selected_reg)

        list_layout.addWidget(self.table_students_reg)
        layout.addWidget(list_container, 1)
        self.tabs.addTab(tab, "  Inscription & Gestion / التسجيل والإدارة  ")

    def setup_list_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        filter_frame = self.create_card()
        flay = QHBoxLayout(filter_frame)
        flay.setContentsMargins(15, 15, 15, 15)
        flay.setSpacing(15)

        self.combo_filter_cycle = self.styled_combo()
        self.combo_filter_cycle.addItem("Cycles (Tous)", None)
        self.combo_filter_cycle.currentIndexChanged.connect(self.load_classes_for_filter)
        self.combo_filter_cycle.setFixedWidth(120)

        self.combo_filter_class = self.styled_combo()
        self.combo_filter_class.addItem("Classes (Toutes)", None)
        self.combo_filter_class.currentIndexChanged.connect(self.refresh_student_list)
        self.combo_filter_class.setFixedWidth(130)

        self.date_filter_from = self.styled_date()
        self.date_filter_from.setDate(QDate(2025, 10, 1))
        self.date_filter_from.setFixedWidth(110)
        self.date_filter_from.dateChanged.connect(self.refresh_student_list)

        self.date_filter_to = self.styled_date()
        self.date_filter_to.setDate(QDate.currentDate())
        self.date_filter_to.setFixedWidth(110)
        self.date_filter_to.dateChanged.connect(self.refresh_student_list)

        self.txt_search = self.styled_input("🔍 Recherche globale...")
        self.txt_search.textChanged.connect(self.refresh_student_list)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_print = QPushButton("🖨️ Imprimer Liste")
        btn_print.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY}; padding: 10px 20px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER}; }}
            QPushButton:hover {{ background-color: {colors.BG_MAIN}; }}
        """)
        btn_print.clicked.connect(self.print_student_list)

        flay.addWidget(self.combo_filter_cycle)
        flay.addWidget(self.combo_filter_class)
        flay.addWidget(QLabel("Du"))
        flay.addWidget(self.date_filter_from)
        flay.addWidget(QLabel("Au"))
        flay.addWidget(self.date_filter_to)
        flay.addWidget(self.txt_search)
        flay.addWidget(btn_print)

        layout.addWidget(filter_frame)

        self.table_students = QTableWidget()
        self.style_table(self.table_students)
        self.table_students.setColumnCount(11)
        self.table_students.setHorizontalHeaderLabels([
            "ID", "Prénom & Nom (FR)", "الاسم واللقب (AR)", "Sexe", "Classe", "N° Classe", "Code Accès", "Tuteur", "Tél", "Date", "Actions"
        ])
        self.table_students.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_students.setColumnWidth(0, 50)
        self.table_students.setColumnWidth(3, 60)

        layout.addWidget(self.table_students)
        self.tabs.addTab(tab, "  Liste Complète / القائمة الشاملة  ")

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        table.setStyleSheet(f"""
            QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
            QTableWidget::item {{ padding: 5px; border-bottom: 1px solid {colors.BG_MAIN}; }}
            QTableWidget::item:alternate {{ background-color: {colors.BG_MAIN}; }}
            QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
            QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 8px; border: none; font-weight: bold; font-size: 13px; }}
        """)

    # ===== Logic Methods =====

    def upload_student_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.current_photo_path = file_path
            pixmap = QPixmap(file_path).scaledToWidth(110, Qt.TransformationMode.SmoothTransformation)
            self.lbl_photo.setPixmap(pixmap)
            self.lbl_photo.setText("")

    def clear_student_form(self):
        self.txt_lname_ar.clear()
        self.txt_fname_ar.clear()
        self.txt_lname_fr.clear()
        self.txt_fname_fr.clear()
        self.txt_address.clear()
        self.txt_birth_place.clear()
        self.txt_parent_name.clear()
        self.txt_parent_phone.clear()
        self.txt_parent_email.clear()
        self.txt_parent_addr.clear()
        self.date_birth.setDate(QDate.currentDate().addYears(-6))
        self.date_registration.setDate(QDate.currentDate())
        self.combo_gender.setCurrentIndex(0)
        self.combo_status.setCurrentIndex(0)
        self.lbl_photo.clear()
        self.lbl_photo.setText("Photo\nصورة")
        self.current_photo_path = None
        self.selected_student_id = None
        if hasattr(self, "txt_class_number"):
            self.txt_class_number.clear()
        self.btn_save.setText("💾 Enregistrer / حفظ")
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        self.btn_save.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; border-radius: 8px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return StudentRepository(conn).get_active_year_id() or None
        except Exception:
            return None

    def gender_to_db_value(self):
        return "M" if self.combo_gender.currentIndex() == 0 else "F"

    def gender_to_index(self, value):
        if value in (None, "", 0, "0", "M", "m", "Masculin", "Male", "Homme"):
            return 0
        if value in (1, "1", "F", "f", "Féminin", "Feminin", "Female", "Femme"):
            return 1
        try:
            return 0 if int(value) == 0 else 1
        except (TypeError, ValueError):
            return 0

    def gender_to_label(self, value):
        return "M" if self.gender_to_index(value) == 0 else "F"

    def get_next_class_number(self, class_id, year_id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            return StudentRepository(conn).get_next_class_number(class_id, year_id)

    def get_student_class_number(self, student_id, year_id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            return StudentRepository(conn).get_class_assignment(student_id, year_id)

    def assign_class_number(self, student_id, class_id):
        year_id = self.get_active_year_id()
        if not year_id or not class_id: return None

        existing = self.get_student_class_number(student_id, year_id)
        if existing and existing[0] == class_id: return existing[1]

        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = StudentRepository(conn)
            new_number = repo.get_next_class_number(class_id, year_id)
            repo.set_class_assignment(student_id, class_id, year_id, new_number)
            conn.commit()
            return new_number

    def update_class_number_preview(self):
        if not hasattr(self, "txt_class_number"): return
        class_id = self.combo_class_reg.currentData() if hasattr(self, "combo_class_reg") else None
        if not class_id:
            self.txt_class_number.clear()
            return
        year_id = self.get_active_year_id()
        if not year_id:
            self.txt_class_number.setText("-")
            return
        if self.selected_student_id:
            existing = self.get_student_class_number(self.selected_student_id, year_id)
            if existing and existing[0] == class_id:
                self.txt_class_number.setText(str(existing[1]))
                return
        next_num = self.get_next_class_number(class_id, year_id)
        self.txt_class_number.setText(str(next_num))

    # ================== التعديل الأهم هنا (RETURNING id) ==================
    def add_student(self):
        ln_ar = self.txt_lname_ar.text().strip()
        fn_ar = self.txt_fname_ar.text().strip()
        ln_fr = self.txt_lname_fr.text().strip()
        fn_fr = self.txt_fname_fr.text().strip()
        class_id = self.combo_class_reg.currentData()

        if not class_id:
            QMessageBox.warning(self, "Attention", "Veuillez inscrire l'élève dans une classe avant l'enregistrement.")
            return

        if not all([ln_fr, fn_fr]):
            QMessageBox.warning(self, "Attention", "Les champs obligatoires sont: Prénom et Nom (FR).")
            return

        gender = self.gender_to_db_value()
        birth_d = self.date_birth.date().toString("yyyy-MM-dd")
        birth_p = self.txt_birth_place.text()
        reg_d = self.date_registration.date().toString("yyyy-MM-dd")
        status = self.combo_status.currentText()
        p_email = self.txt_parent_email.text()

        try:
            photo_path = None
            if self.current_photo_path:
                os.makedirs("school_data/photos", exist_ok=True)
                filename = f"student_{datetime.now().timestamp()}.jpg"
                photo_path = f"school_data/photos/{filename}"
                shutil.copy(self.current_photo_path, photo_path)

            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StudentRepository(conn)
                student_id = repo.add_student({
                    "first_name_fr": fn_fr, "last_name_fr": ln_fr,
                    "first_name_ar": fn_ar, "last_name_ar": ln_ar,
                    "birth_date": birth_d, "birth_place": birth_p,
                    "gender": gender, "address": self.txt_address.text(),
                    "parent_name": self.txt_parent_name.text(),
                    "parent_phone": self.txt_parent_phone.text(),
                    "parent_email": p_email,
                    "parent_address": self.txt_parent_addr.text(),
                    "registration_date": reg_d, "status": status,
                    "photo_path": photo_path,
                })

                from database_setup import log_audit
                log_audit(conn, getattr(self, "current_user", "system"), "ADD_STUDENT", f"{fn_fr} {ln_fr}")
                conn.commit()

            class_number = self.assign_class_number(student_id, class_id)
            if class_number is None:
                QMessageBox.warning(self, "Attention", "Aucune année scolaire active pour attribuer رقم الفصل.")
            else:
                self.txt_class_number.setText(str(class_number))

            QMessageBox.information(self, "Succès", "Étudiant ajouté avec succès.")
            self.clear_student_form()
            self.refresh_student_list()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def save_student(self):
        if self.selected_student_id: self.update_student()
        else: self.add_student()

    def update_student(self):
        if not self.selected_student_id: return

        fn_fr = self.txt_fname_fr.text().strip()
        ln_fr = self.txt_lname_fr.text().strip()
        class_id = self.combo_class_reg.currentData()
        if not class_id:
            QMessageBox.warning(self, "Attention", "Veuillez inscrire l'élève dans une classe avant l'enregistrement.")
            return

        if not fn_fr or not ln_fr:
            QMessageBox.warning(self, "Attention", "Les champs obligatoires sont: Prénom et Nom (FR).")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                photo_path = None
                if self.current_photo_path and "school_data" not in self.current_photo_path:
                    os.makedirs("school_data/photos", exist_ok=True)
                    filename = f"student_{self.selected_student_id}_{datetime.now().timestamp()}.jpg"
                    photo_path = f"school_data/photos/{filename}"
                    shutil.copy(self.current_photo_path, photo_path)

                repo = StudentRepository(conn)
                repo.update_student(self.selected_student_id, {
                    "first_name_fr": self.txt_fname_fr.text(),
                    "last_name_fr": self.txt_lname_fr.text(),
                    "first_name_ar": self.txt_fname_ar.text(),
                    "last_name_ar": self.txt_lname_ar.text(),
                    "birth_date": self.date_birth.date().toString("yyyy-MM-dd"),
                    "birth_place": self.txt_birth_place.text(),
                    "gender": self.gender_to_db_value(),
                    "address": self.txt_address.text(),
                    "parent_name": self.txt_parent_name.text(),
                    "parent_phone": self.txt_parent_phone.text(),
                    "parent_email": self.txt_parent_email.text(),
                    "parent_address": self.txt_parent_addr.text(),
                    "registration_date": self.date_registration.date().toString("yyyy-MM-dd"),
                    "status": self.combo_status.currentText(),
                    "photo_path": photo_path,
                })

                from database_setup import log_audit
                fn_fr_val = self.txt_fname_fr.text().strip()
                ln_fr_val = self.txt_lname_fr.text().strip()
                log_audit(conn, getattr(self, "current_user", "system"), "EDIT_STUDENT", f"{fn_fr_val} {ln_fr_val} (id={self.selected_student_id})")
                conn.commit()

            class_number = self.assign_class_number(self.selected_student_id, class_id)
            if class_number is None:
                QMessageBox.warning(self, "Attention", "Aucune année scolaire active pour attribuer رقم الفصل.")
            else:
                self.txt_class_number.setText(str(class_number))

            QMessageBox.information(self, "Succès", "Mise à jour réussie.")
            self.clear_student_form()
            self.refresh_student_list()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_student(self, student_id):
        reply = QMessageBox.question(self, "Confirmation", "Supprimer cet étudiant ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    repo = StudentRepository(conn)
                    repo.delete_student(student_id)
                    conn.commit()
                    from database_setup import log_audit
                    log_audit(conn, getattr(self, "current_user", "system"), "DELETE_STUDENT", f"id={student_id}")
                self.refresh_student_list()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def on_student_selected_reg(self):
        rows = self.table_students_reg.selectedItems()
        if rows:
            row = rows[0].row()
            student_id = int(self.table_students_reg.item(row, 0).text())
            self.load_student_for_edit(student_id)

    def load_student_for_edit(self, student_id):
        try:
            active_year = self.get_active_year_id()
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StudentRepository(conn)
                data = repo.get_student_for_edit(active_year, student_id)

            if data:
                self.selected_student_id = student_id
                self.txt_fname_fr.setText(data[0] or "")
                self.txt_lname_fr.setText(data[1] or "")
                self.txt_fname_ar.setText(data[2] or "")
                self.txt_lname_ar.setText(data[3] or "")
                if data[4]:
                    self.date_birth.setDate(QDate.fromString(str(data[4]), "yyyy-MM-dd"))
                self.txt_birth_place.setText(data[5] or "")
                self.combo_gender.setCurrentIndex(self.gender_to_index(data[6]))
                self.txt_address.setText(data[7] or "")
                self.txt_parent_name.setText(data[8] or "")
                self.txt_parent_phone.setText(data[9] or "")
                self.txt_parent_email.setText(data[10] or "")
                self.txt_parent_addr.setText(data[11] or "")

                # إعداد الـ Class
                class_id = data[15]  # Index 15 is class_id from JOIN
                if class_id:
                    idx = self.combo_class_reg.findData(class_id)
                    if idx >= 0: self.combo_class_reg.setCurrentIndex(idx)
                self.update_class_number_preview()

                if data[12]:
                    self.date_registration.setDate(QDate.fromString(str(data[12]), "yyyy-MM-dd"))
                self.combo_status.setCurrentText(data[13] or "Active")

                if data[14] and os.path.exists(data[14]):
                    self.current_photo_path = data[14]
                    pixmap = QPixmap(data[14]).scaledToWidth(110, Qt.TransformationMode.SmoothTransformation)
                    self.lbl_photo.setPixmap(pixmap)
                else:
                    self.lbl_photo.clear()
                    self.lbl_photo.setText("No Photo")

                self.btn_save.setText("✏️ Modifier / تعديل")
                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                self.btn_save.setStyleSheet(f"""
                    QPushButton {{ background-color: {colors.WARNING}; color: white; border-radius: 8px; font-weight: bold; border: none; }}
                    QPushButton:hover {{ background-color: {colors.WARNING}; }}
                """)
                self.tabs.setCurrentIndex(0)
        except Exception as e:
            AppLogger.error("StudentManagement", f"Error loading student: {e}")

    def load_cycles_reg(self):
        self._load_cycles_into(self.combo_cycle_reg, "Choisis Cycle...")
        try:
            self._load_classes_into(self.combo_filter_class_reg, None, "Toutes les Classes")
        except Exception: pass

    def load_cycles_filter(self):
        self._load_cycles_into(self.combo_filter_cycle, "Tous les cycles")

    def _load_cycles_into(self, combo, default_text):
        db = DatabaseManager()
        with db.get_connection() as conn:
            rows = StudentRepository(conn).list_cycles()
        combo.clear()
        combo.addItem(default_text, None)
        for r in rows: combo.addItem(r[1], r[0])

    def load_classes_for_reg(self):
        cid = self.combo_cycle_reg.currentData()
        self._load_classes_into(self.combo_class_reg, cid, "Choisis Classe...")
        self.update_class_number_preview()

    def load_classes_for_filter(self):
        cid = self.combo_filter_cycle.currentData()
        self._load_classes_into(self.combo_filter_class, cid, "Toutes les classes")

    def _load_classes_into(self, combo, cycle_id, default_text):
        db = DatabaseManager()
        with db.get_connection() as conn:
            rows = StudentRepository(conn).list_classes(cycle_id)
        combo.clear()
        combo.addItem(default_text, None)
        for r in rows: combo.addItem(r[1], r[0])

    def refresh_student_list(self):
        self.populate_table(self.table_students)
        self.populate_table(self.table_students_reg)

    def populate_table(self, table):
        table.setRowCount(0)
        if table == self.table_students:
            cycle_id = self.combo_filter_cycle.currentData()
            class_id = self.combo_filter_class.currentData()
            search = self.txt_search.text().strip()
            date_from = self.date_filter_from.date().toString("yyyy-MM-dd") if hasattr(self, "date_filter_from") else None
            date_to = self.date_filter_to.date().toString("yyyy-MM-dd") if hasattr(self, "date_filter_to") else None
        else:
            cycle_id = None
            class_id = self.combo_filter_class_reg.currentData()
            search = self.txt_search_reg.text().strip()
            date_from = None
            date_to = None

        active_year_id = self.get_active_year_id()
        year_param = active_year_id or -1

        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = StudentRepository(conn)
            rows = repo.list_students(
                year_param,
                cycle_id=cycle_id,
                class_id=class_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
            )

        for r in rows:
            row_idx = table.rowCount()
            table.insertRow(row_idx)
            full_name_fr = f"{r[1]} {r[2]}"
            full_name_ar = f"{r[3]} {r[4]}"
            gender_str = self.gender_to_label(r[5])
            class_no = str(r[10]) if r[10] else "-"

            if table == self.table_students_reg:
                name_lang = self.combo_name_lang_reg.currentData() if hasattr(self, "combo_name_lang_reg") else "fr"
                if name_lang == "ar":
                    self.table_students_reg.setHorizontalHeaderLabels(["ID", "رقم الفصل", "الاسم الكامل", "Actions"])
                    name_value = full_name_ar.strip()
                else:
                    self.table_students_reg.setHorizontalHeaderLabels(["ID", "N° Classe", "Prénom & Nom", "Actions"])
                    name_value = full_name_fr.strip()

                table.setItem(row_idx, 0, QTableWidgetItem(str(r[0])))
                table.setItem(row_idx, 1, QTableWidgetItem(class_no))
                name_item = QTableWidgetItem(name_value)
                if name_lang == "ar": name_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row_idx, 2, name_item)

                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(2, 2, 2, 2)
                layout.setSpacing(5)

                btn_edit = QPushButton("✎")
                btn_edit.setFixedSize(28, 28)
                btn_edit.setStyleSheet(f"background: {Colors().PRIMARY}; color: white; border-radius: 4px; border: none;")
                btn_edit.clicked.connect(lambda ch, sid=r[0]: self.load_student_for_edit(sid))

                btn_del = QPushButton("✕")
                btn_del.setFixedSize(28, 28)
                btn_del.setStyleSheet(f"background: {Colors().DANGER}; color: white; border-radius: 4px; border: none;")
                btn_del.clicked.connect(lambda ch, sid=r[0]: self.delete_student(sid))

                layout.addWidget(btn_edit)
                layout.addWidget(btn_del)
                layout.addStretch()
                table.setCellWidget(row_idx, 3, container)

            else:  # Full Table
                table.setItem(row_idx, 0, QTableWidgetItem(str(r[0])))
                full_fr = f"{r[1]} {r[2]}".strip()
                full_ar = f"{r[3]} {r[4]}".strip()
                table.setItem(row_idx, 1, QTableWidgetItem(full_fr))
                table.setItem(row_idx, 2, QTableWidgetItem(full_ar))
                table.setItem(row_idx, 3, QTableWidgetItem(gender_str))
                table.setItem(row_idx, 4, QTableWidgetItem(r[6] or "-"))
                table.setItem(row_idx, 5, QTableWidgetItem(class_no))
                table.setItem(row_idx, 6, QTableWidgetItem(r[11] or "-"))  # student_code
                table.setItem(row_idx, 7, QTableWidgetItem(r[7] or ""))
                table.setItem(row_idx, 8, QTableWidgetItem(r[8] or ""))
                table.setItem(row_idx, 9, QTableWidgetItem(str(r[9]) if r[9] else ""))

                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(2, 2, 2, 2)
                btn_del = QPushButton("✕")
                btn_del.setFixedSize(24, 24)
                btn_del.setStyleSheet(f"background: {Colors().DANGER}; color: white; border-radius: 4px; border: none;")
                btn_del.clicked.connect(lambda ch, sid=r[0]: self.delete_student(sid))
                layout.addWidget(btn_del)
                table.setCellWidget(row_idx, 10, container)

    def print_student_list(self):
        rows = self._fetch_full_list_rows()
        headers = [
            "ID", "Prénom (FR)", "Nom (FR)", "الاسم (AR)", "اللقب (AR)",
            "Naissance", "Lieu", "Sexe", "Adresse", "Classe", "N° Cls", "Code Accès",
            "Tuteur", "Tél", "Email", "Date", "Statut"
        ]
        filename = self._build_report_filename("Liste_Complete_Eleves", self.combo_filter_class.currentText())
        self._generate_pdf_rows(headers, rows, filename, orientation='L', title_doc="LISTE COMPLETE DES ELEVES INSCRITES DE: " +
                                (self.combo_filter_class.currentText() if self.combo_filter_class.currentData() else "Toutes les classes"))

    def _open_import_wizard(self):
        from import_wizard import ImportWizard
        actor = getattr(self, "current_user", "system")
        wiz = ImportWizard(parent=self, actor=actor)
        wiz.exec()
        self.refresh_student_list()

    def print_filtered_list(self):
        rows, headers = self._fetch_reg_list_rows()
        filename = self._build_report_filename("Liste_Eleves_Filtrees", self.combo_filter_class_reg.currentText())
        self._generate_pdf_rows(headers, rows, filename, orientation='P', title_doc="LISTE DES ELEVES DE: " +
                                (self.combo_filter_class_reg.currentText() if self.combo_filter_class_reg.currentData() else "Toutes les classes"))

    def _build_report_filename(self, prefix, class_label):
        class_text = class_label if class_label and "Toutes" not in class_label else "Toutes_Classes"
        class_slug = "".join(ch for ch in class_text.replace(" ", "_") if ch.isalnum() or ch in "-_") or "Classe"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{class_slug}_{timestamp}.pdf"

    def _get_school_info(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return FinanceRepository(conn).get_school_info()
        except Exception:
            return None

    def _fetch_full_list_rows(self):
        cycle_id = self.combo_filter_cycle.currentData()
        class_id = self.combo_filter_class.currentData()
        search = self.txt_search.text().strip()
        date_from = self.date_filter_from.date().toString("yyyy-MM-dd") if hasattr(self, "date_filter_from") else None
        date_to = self.date_filter_to.date().toString("yyyy-MM-dd") if hasattr(self, "date_filter_to") else None
        active_year_id = self.get_active_year_id()
        year_param = active_year_id or -1

        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = StudentRepository(conn)
            rows = repo.list_students_detailed(
                year_param,
                cycle_id=cycle_id,
                class_id=class_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
            )

        result = []
        for r in rows:
            gender_str = self.gender_to_label(r[7])
            class_no = str(r[10]) if r[10] else "-"
            result.append([
                str(r[0]), r[1] or "", r[2] or "", r[3] or "", r[4] or "",
                r[5] or "", r[6] or "", gender_str, r[8] or "", r[9] or "-",
                class_no, r[11] or "", r[12] or "", r[13] or "", r[14] or "", r[15] or "",
                r[16] or ""
            ])
        return result

    def _fetch_reg_list_rows(self):
        name_lang = self.combo_name_lang_reg.currentData() if hasattr(self, "combo_name_lang_reg") else "fr"
        headers = ["N° Classe", "Nom & Prénom"] if name_lang == "fr" else ["رقم الفصل", "الاسم الكامل"]
        rows = []
        for row in range(self.table_students_reg.rowCount()):
            class_item = self.table_students_reg.item(row, 1)
            name_item = self.table_students_reg.item(row, 2)
            class_val = class_item.text() if class_item else ""
            name_val = name_item.text() if name_item else ""
            rows.append([class_val, name_val])
        return rows, headers

    def _generate_pdf_rows(self, headers, rows, filename, orientation='P', title_doc="LISTE DES ELEVES INSCRITES"):
        pdf = StudentListPDF(self._get_school_info(), title_doc=title_doc, orientation=orientation)
        self._setup_pdf_fonts(pdf)
        pdf.add_page()
        pdf.set_font(self._get_pdf_font_name(), size=8 if orientation == 'L' else 10)

        col_count = len(headers)
        page_w = pdf.w - 20
        col_widths = None
        if orientation == 'L' and col_count == 16:
            col_widths = [10, 20, 15, 18, 13, 16, 17, 10, 24, 13, 12, 33, 16, 35, 15, 10]
        if orientation == 'L' and col_count == 17:
            col_widths = [9, 18, 14, 16, 12, 16, 14, 9, 22, 12, 12, 22, 15, 35, 20, 14, 12]
        w = page_w / max(1, col_count)

        pdf.set_draw_color(203, 213, 225)
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(248, 250, 252)
        for i, h in enumerate(headers):
            txt = self._prepare_pdf_text(h)
            cell_w = col_widths[i] if col_widths else w
            pdf.cell(cell_w, 9, txt, 1, 0, 'C', fill=True)
        pdf.ln()

        pdf.set_text_color(51, 65, 85)
        row_fill = False

        for row in rows:
            pdf.set_fill_color(241, 245, 249) if row_fill else pdf.set_fill_color(255, 255, 255)
            for col in range(col_count):
                txt = row[col] if col < len(row) else ""
                txt = self._prepare_pdf_text(txt)
                try: txt.encode('latin-1')
                except Exception:
                    if not self._is_arabic_font_ready(): txt = self._latin_fallback_text(txt)
                cell_w = col_widths[col] if col_widths else w
                pdf.cell(cell_w, 8, txt, 1, 0, fill=row_fill)
            pdf.ln()
            row_fill = not row_fill

        output_pdf(pdf, self, filename, mode=STUDENT_LIST_OUTPUT_MODE, dialog_title="Save PDF", success_save_message="PDF généré.", success_print_message="Liste envoyée à l'imprimante.")

    def _generate_pdf(self, table, filename):
        pdf = StudentListPDF()
        self._setup_pdf_fonts(pdf)
        pdf.add_page()
        pdf.set_font(self._get_pdf_font_name(), size=10)

        col_count = table.columnCount()
        w = 190 / max(1, col_count)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_text_color(51, 65, 85)
        row_fill = False

        for row in range(table.rowCount()):
            pdf.set_fill_color(241, 245, 249) if row_fill else pdf.set_fill_color(255, 255, 255)
            for col in range(col_count):
                item = table.item(row, col)
                txt = item.text() if item else ""
                txt = txt.replace("\n", " / ")
                txt = self._prepare_pdf_text(txt)
                try: txt.encode('latin-1')
                except Exception:
                    if not self._is_arabic_font_ready(): txt = self._latin_fallback_text(txt)
                pdf.cell(w, 10, txt, 1, 0, fill=row_fill)
            pdf.ln()
            row_fill = not row_fill

        output_pdf(pdf, self, filename, mode=STUDENT_LIST_OUTPUT_MODE, dialog_title="Save PDF", success_save_message="PDF généré.", success_print_message="Liste envoyée à l'imprimante.")

    def _get_pdf_font_name(self): return "ArabicFont" if self._is_arabic_font_ready() else "Arial"

    def _get_arabic_font_path(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "fonts", "Amiri-Regular.ttf"), os.path.join(base_dir, "fonts", "NotoNaskhArabic-Regular.ttf"),
            os.path.join(base_dir, "fonts", "Cairo-Regular.ttf"), os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Regular.ttf"),
            os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "NotoNaskhArabic-Regular.ttf"), os.path.join(base_dir, "Fonts", "Cairo", "Cairo-Regular.ttf"),
        ]
        for path in candidates:
            if os.path.exists(path): return path
        return None

    def _latin_fallback_text(self, text):
        if text is None: return "-"
        if not isinstance(text, str): text = str(text)
        cleaned = text.encode('latin-1', 'ignore').decode('latin-1').strip()
        return cleaned or "-"

    def _is_arabic_font_ready(self): return self._get_arabic_font_path() is not None

    def _setup_pdf_fonts(self, pdf):
        font_path = self._get_arabic_font_path()
        if font_path:
            try: pdf.add_font("ArabicFont", "", font_path, uni=True)
            except Exception: pass
        else:
            if ARABIC_SUPPORT:
                QMessageBox.information(self, "Police عربية مفقودة", "لتصدير PDF يدعم العربية، ضع ملف خط (TTF) في مجلد fonts داخل المشروع.")

    def _prepare_pdf_text(self, text):
        if text is None: return text
        if not isinstance(text, str): text = str(text)
        if not text: return text
        if not self._contains_arabic(text): return text
        if not ARABIC_SUPPORT: return text
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception: return text

    def _contains_arabic(self, text):
        if text is None: return False
        if not isinstance(text, str): text = str(text)
        return any("\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" or "\u08A0" <= ch <= "\u08FF" for ch in text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernStudentManagement()
    window.show()
    sys.exit(app.exec())
