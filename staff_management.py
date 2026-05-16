import sys
import psycopg2
import os
import shutil
import base64
from datetime import datetime
from database_setup import DatabaseManager, log_audit
from app_logger import AppLogger
from repositories.staff_repo import StaffRepository
from repositories.finance_repo import FinanceRepository
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QLineEdit, QComboBox,
                             QMessageBox, QHeaderView, QGroupBox, QDateEdit,
                             QTabWidget, QGraphicsDropShadowEffect, QFrame,
                             QFileDialog, QDoubleSpinBox, QScrollArea, QGridLayout)
from PyQt6.QtCore import Qt, QDate, QSize, QBuffer, QByteArray
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from fpdf import FPDF

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_grades_sheet_header, apply_table_header_style, apply_table_body_style, set_zebra_row_fill, get_school_info_row

THEME_AVAILABLE = True
STAFF_LIST_OUTPUT_MODE = get_report_output_mode("staff_list_mode", "save")
TIMETABLE_OUTPUT_MODE = get_report_output_mode("timetable_mode", "save")

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


class StaffReportPDF(FPDF):
    def __init__(self, school_info, report_title, orientation='L'):
        super().__init__(orientation=orientation, unit='mm', format='A4')
        self.school_info = school_info
        self.report_title = report_title
        self.set_auto_page_break(True, margin=12)
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
        left_x, left_y = 10, 5
        page_w = self.w
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

        right_x = page_w - 30
        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=20, h=22)
            except Exception:
                pass

        body_bottom_y = self.get_y()
        line_y = max(body_bottom_y + 2, left_y + 24)
        self.line(10, line_y, page_w - 10, line_y)
        self.set_y(line_y + 4)

        title_style = '' if self.arabic_font_ready else 'B'
        self.set_font(self.font_name, title_style, 12)
        self.set_text_color(44, 62, 80)
        self.cell(0, 8, self.sanitize(self.report_title), 0, 1, 'C')
        self.set_font(self.font_name, '', 9)
        self.set_text_color(100, 116, 139)
        if "LISTE DU PERSONNEL" in self.report_title:
            self.cell(0, 5, self.sanitize("Gestion des ressources humaines"), 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font(self.font_name, 'I', 7)
        date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        page_w = self.w - self.l_margin - self.r_margin
        self.cell(page_w / 2, 4, f"Imprimé le {date_str}", 0, 0, 'L')
        self.cell(page_w / 2, 4, f"Page {self.page_no()}", 0, 0, 'R')


class ModernStaffManagement(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des RH / إدارة الموارد البشرية")
        self.setMinimumSize(1100, 700)

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
                QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }}
                QScrollArea {{ border: none; background: transparent; }}
            """)

        self.current_photo_path = None
        self.selected_staff_id = None

        self.init_ui()
        self.load_staff_list()
        self.load_classes_into_combo()
        self.load_subjects_into_combo()
        self.load_timetable()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        header_frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 10px; }}")
        header_frame.setMaximumHeight(80)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15); shadow.setColor(QColor(15, 23, 42, 40)); shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)

        icon_lbl = QLabel("👥")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_layout = QVBoxLayout()
        header_lbl = QLabel("RESSOURCES HUMAINES")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("إدارة الموظفين، الرواتب، والجدول الزمني")
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
                QTabBar::tab:selected {{ background: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; }}
                QTabBar::tab:hover {{ background: {colors.BORDER}; }}
            """)

        self.setup_staff_tab()
        self.setup_timetable_tab()

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

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        le.setMinimumHeight(38)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            le.setStyleSheet(f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        return le

    def sanitize(self, text):
        if not text:
            return ""
        return str(text).encode('latin-1', 'ignore').decode('latin-1')

    def styled_combo(self):
        combo = QComboBox()
        combo.setMinimumHeight(38)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
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
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
            """)

    def setup_staff_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # --- العمود الأيمن: نموذج الإدخال (مع Scroll) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(420)

        form_container = QFrame()
        form_container.setStyleSheet(f"background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER};")

        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)

        lbl_new = QLabel("📝 Nouveau Profil / ملف جديد")
        lbl_new.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_new.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; font-weight: bold; font-size: 14px; padding: 10px; border-radius: 6px; border: 1px dashed {colors.BORDER};")
        form_layout.addWidget(lbl_new)

        # الصورة الشخصية
        photo_layout = QHBoxLayout()
        self.lbl_photo = QLabel()
        self.lbl_photo.setFixedSize(110, 110)
        self.lbl_photo.setStyleSheet(f"background-color: {colors.BG_MAIN}; border-radius: 55px; border: 3px solid {colors.BORDER}; color: {colors.TEXT_SECONDARY};")
        self.lbl_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo.setText("Photo")

        btn_upload = QPushButton("📷")
        btn_upload.setFixedSize(36, 36)
        btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload.setStyleSheet(f"background-color: {colors.PRIMARY_DARK}; color: white; border-radius: 18px; border: 2px solid {colors.BG_CARD};")
        btn_upload.clicked.connect(self.upload_photo)

        photo_wrapper = QWidget()
        photo_wrapper.setStyleSheet("background: transparent;")
        pw_layout = QVBoxLayout(photo_wrapper)
        pw_layout.addWidget(self.lbl_photo)

        photo_layout.addStretch()
        photo_layout.addWidget(photo_wrapper)
        photo_layout.addWidget(btn_upload, 0, Qt.AlignmentFlag.AlignBottom)
        photo_layout.addStretch()
        form_layout.addLayout(photo_layout)

        # الحقول الأساسية
        lbl_info = QLabel("👤 Infos Personnelles / البيانات الشخصية")
        lbl_info.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; border-bottom: 2px solid {colors.BORDER}; padding-bottom: 5px;")
        form_layout.addWidget(lbl_info)

        self.txt_fname = self.styled_input("Prénom / الاسم")
        self.txt_lname = self.styled_input("Nom / اللقب")

        self.combo_role = self.styled_combo()
        self.combo_role.addItems(["Professeur", "Administration", "Comptabilité", "Agent", "Sécurité"])

        form_layout.addWidget(self.txt_fname)
        form_layout.addWidget(self.txt_lname)
        form_layout.addWidget(self.combo_role)

        self.txt_spec = self.styled_input("Spécialité (Ex: Math)")
        self.txt_phone = self.styled_input("Téléphone / الهاتف")
        self.txt_email = self.styled_input("Email / البريد الإلكتروني")
        self.txt_address = self.styled_input("Adresse / العنوان")

        self.combo_status = self.styled_combo()
        self.combo_status.addItems(["Actif / نشط", "Congé / إجازة", "Suspendu / موقوف", "Démission / استقالة", "Licencié / مفصول", "Retraité / متقاعد"])

        form_layout.addWidget(self.txt_spec)
        form_layout.addWidget(self.txt_phone)
        form_layout.addWidget(self.txt_email)
        form_layout.addWidget(self.txt_address)
        form_layout.addWidget(QLabel("Statut / الحالة:"))
        form_layout.addWidget(self.combo_status)

        # إعدادات العقد والراتب
        lbl_contract = QLabel("💼 Contrat & Salaire / العقد والراتب")
        lbl_contract.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; margin-top: 10px; border-bottom: 2px solid {colors.BORDER}; padding-bottom: 5px;")
        form_layout.addWidget(lbl_contract)

        self.date_hire = QDateEdit()
        self.date_hire.setCalendarPopup(True)
        self.date_hire.setDate(QDate.currentDate())
        self.date_hire.setStyleSheet(f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        self.date_hire.setMinimumHeight(38)

        form_layout.addWidget(QLabel("Date d'embauche:"))
        form_layout.addWidget(self.date_hire)

        self.combo_contract = self.styled_combo()
        self.combo_contract.addItems(["Salaire Mensuel (راتب شهري)", "Vacataire/Horaire (بالساعة)"])
        self.combo_contract.currentIndexChanged.connect(self.toggle_salary_fields)
        form_layout.addWidget(self.combo_contract)

        # Salary Inputs
        self.spin_salary = QDoubleSpinBox()
        self.spin_salary.setRange(0, 5000000)
        self.spin_salary.setPrefix("FCFA ")
        self.spin_salary.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_salary.setStyleSheet(f"QDoubleSpinBox {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        self.spin_salary.setMinimumHeight(38)
        self.lbl_salary = QLabel("Salaire de Base:")

        self.spin_hourly = QDoubleSpinBox()
        self.spin_hourly.setRange(0, 100000)
        self.spin_hourly.setPrefix("FCFA ")
        self.spin_hourly.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_hourly.setStyleSheet(f"QDoubleSpinBox {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        self.spin_hourly.setMinimumHeight(38)
        self.lbl_hourly = QLabel("Taux Horaire:")

        form_layout.addWidget(self.lbl_salary)
        form_layout.addWidget(self.spin_salary)
        form_layout.addWidget(self.lbl_hourly)
        form_layout.addWidget(self.spin_hourly)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 Enregistrer")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setMinimumHeight(45)
        self.btn_save.setStyleSheet(f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; border-radius: 8px; font-weight: bold; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}")
        self.btn_save.clicked.connect(self.save_staff)

        btn_clear = QPushButton("🔄")
        btn_clear.setMinimumHeight(45)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(f"QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_SECONDARY}; border-radius: 8px; font-weight: bold; border: 1px solid {colors.BORDER}; }} QPushButton:hover {{ background-color: {colors.BG_MAIN}; }}")
        btn_clear.clicked.connect(self.clear_form)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(btn_clear)
        form_layout.addLayout(btn_layout)

        form_layout.addStretch()
        scroll.setWidget(form_container)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        layout.addWidget(scroll)

        # --- العمود الأيسر: الجدول والبحث ---
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setSpacing(15)
        list_layout.setContentsMargins(0, 0, 0, 0)

        # Search Bar
        search_card = self.create_card()
        slayout = QHBoxLayout(search_card)
        slayout.setContentsMargins(10, 10, 10, 10)

        self.txt_search = self.styled_input("🔍 Rechercher un employé...")
        self.txt_search.textChanged.connect(self.load_staff_list)

        btn_print = QPushButton("🖨️ Liste")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setStyleSheet(f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; padding: 8px 15px; border-radius: 6px; font-weight: bold; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_print.clicked.connect(self.print_staff_list)

        slayout.addWidget(self.txt_search)
        slayout.addWidget(btn_print)
        list_layout.addWidget(search_card)

        # Table
        self.table_staff = QTableWidget()
        self.style_table(self.table_staff)
        self.table_staff.setColumnCount(9)
        self.table_staff.setHorizontalHeaderLabels(["ID", "Nom & Prénom", "Fonction", "Spécialité", "Tél", "Contrat", "Montant", "Statut", "Actions"])
        self.table_staff.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_staff.setColumnWidth(0, 50)
        self.table_staff.setColumnWidth(7, 80)
        self.table_staff.setColumnWidth(8, 120)
        self.table_staff.setIconSize(QSize(32, 32))
        self.table_staff.itemSelectionChanged.connect(self.on_staff_selected)

        list_layout.addWidget(self.table_staff)
        layout.addWidget(list_container)

        self.toggle_salary_fields()
        self.tabs.addTab(tab, "  👨‍💼 Personnel / الموظفون  ")

    def setup_timetable_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Control Card
        control_card = self.create_card()
        clayout = QVBoxLayout(control_card)
        clayout.setContentsMargins(15, 15, 15, 15)
        clayout.setSpacing(8)

        row_top = QHBoxLayout()
        row_top.setSpacing(10)
        row_bottom = QHBoxLayout()
        row_bottom.setSpacing(10)

        self.combo_prof_tt = self.styled_combo()
        self.combo_class_tt = self.styled_combo()
        self.combo_subject_tt = self.styled_combo()
        self.combo_day_tt = self.styled_combo()
        self.combo_day_tt.addItems(["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"])

        self.txt_time_start = self.styled_input("Début (08:00)")
        self.txt_time_start.setMaximumWidth(100)
        self.txt_time_end = self.styled_input("Fin (10:00)")
        self.txt_time_end.setMaximumWidth(100)

        btn_add_tt = QPushButton("➕ Ajouter")
        btn_add_tt.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_add_tt.setStyleSheet(f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; padding: 10px 20px; font-weight: bold; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}")
        btn_add_tt.clicked.connect(self.add_to_timetable)

        # زر جديد لطباعة جدول الفصل
        btn_print_class_tt = QPushButton("🖨️ Imprimer Classe")
        btn_print_class_tt.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_class_tt.setStyleSheet(f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; padding: 10px 15px; font-weight: bold; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_print_class_tt.clicked.connect(self.print_class_timetable)

        row_top.addWidget(QLabel("Prof:"))
        row_top.addWidget(self.combo_prof_tt, 2)
        row_top.addWidget(QLabel("Classe:"))
        row_top.addWidget(self.combo_class_tt, 1)
        row_top.addWidget(btn_print_class_tt)
        row_top.addStretch()

        row_bottom.addWidget(QLabel("Matière:"))
        row_bottom.addWidget(self.combo_subject_tt, 2)
        row_bottom.addWidget(self.combo_day_tt, 1)
        row_bottom.addWidget(self.txt_time_start)
        row_bottom.addWidget(self.txt_time_end)
        row_bottom.addWidget(btn_add_tt)

        clayout.addLayout(row_top)
        clayout.addLayout(row_bottom)

        layout.addWidget(control_card)

        # Table
        self.table_tt = QTableWidget()
        self.style_table(self.table_tt)
        self.table_tt.setColumnCount(7)
        self.table_tt.setHorizontalHeaderLabels(["ID", "Professeur", "Classe", "Matière", "Jour", "Horaire", "Action"])
        self.table_tt.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_tt.setColumnWidth(0, 50)
        self.table_tt.setColumnWidth(6, 60)

        layout.addWidget(self.table_tt)
        self.tabs.addTab(tab, "  🗓️ Emploi du Temps / الجدول  ")

    # --- Logic Methods ---
    def toggle_salary_fields(self):
        idx = self.combo_contract.currentIndex()
        if idx == 0:  # Monthly
            self.lbl_salary.setVisible(True)
            self.spin_salary.setVisible(True)
            self.lbl_hourly.setVisible(False)
            self.spin_hourly.setVisible(False)
        else:  # Hourly
            self.lbl_salary.setVisible(False)
            self.spin_salary.setVisible(False)
            self.lbl_hourly.setVisible(True)
            self.spin_hourly.setVisible(True)

    def upload_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir une photo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.current_photo_path = file_path
            pixmap = QPixmap(file_path)
            self.lbl_photo.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            self.lbl_photo.setText("")

    def load_staff_list(self):
        self.table_staff.setRowCount(0)
        self.combo_prof_tt.clear()
        search_txt = self.txt_search.text()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                rows = repo.list_staff(search_txt)

            for row in rows:
                r_idx = self.table_staff.rowCount()
                self.table_staff.insertRow(r_idx)

                self.table_staff.setItem(r_idx, 0, QTableWidgetItem(str(row[0])))

                name_item = QTableWidgetItem(row[1] or "")
                if row[8] and os.path.exists(row[8]):
                    icon = QIcon(row[8])
                    name_item.setIcon(icon)
                self.table_staff.setItem(r_idx, 1, name_item)

                self.table_staff.setItem(r_idx, 2, QTableWidgetItem(row[2] or ""))
                self.table_staff.setItem(r_idx, 3, QTableWidgetItem(row[3] or ""))
                self.table_staff.setItem(r_idx, 4, QTableWidgetItem(row[4] or ""))

                ctype = "Mensuel" if row[5] == "Monthly" else "Horaire"
                amount = f"{row[6]:,.0f}" if row[5] == "Monthly" else f"{row[7]:,.0f}/h"

                self.table_staff.setItem(r_idx, 5, QTableWidgetItem(ctype))
                self.table_staff.setItem(r_idx, 6, QTableWidgetItem(amount))

                status = row[9] or "Actif"
                status_item = QTableWidgetItem(status)
                if status == "Actif":
                    status_item.setForeground(QColor(16, 185, 129))
                elif status in ["Congé", "Suspendu"]:
                    status_item.setForeground(QColor(245, 158, 11))
                else:
                    status_item.setForeground(QColor(239, 68, 68))
                self.table_staff.setItem(r_idx, 7, status_item)

                role_value = row[2] or ""
                if ("Prof" in role_value or "Ens" in role_value) and status == "Actif":
                    self.combo_prof_tt.addItem(row[1], row[0])

                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(5)

                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                btn_edit = QPushButton("✎")
                btn_edit.setFixedSize(28, 28)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet(f"background-color: {colors.WARNING}; color: white; border-radius: 4px; border: none;")
                btn_edit.clicked.connect(lambda ch, pid=row[0]: self.load_staff_details(pid))

                btn_del = QPushButton("✕")
                btn_del.setFixedSize(28, 28)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 4px; border: none;")
                btn_del.clicked.connect(lambda ch, pid=row[0]: self.delete_staff_from_table(pid))

                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_del)
                self.table_staff.setCellWidget(r_idx, 8, btn_widget)
        except Exception as e:
            AppLogger.error("StaffManagement", f"Error loading staff list: {e}")

    def save_staff(self):
        fname = self.txt_fname.text().strip()
        lname = self.txt_lname.text().strip()
        role = self.combo_role.currentText()
        spec = self.txt_spec.text().strip()
        phone = self.txt_phone.text().strip()
        email = self.txt_email.text().strip()
        address = self.txt_address.text().strip()
        hire_d = self.date_hire.date().toString("yyyy-MM-dd")

        is_monthly = (self.combo_contract.currentIndex() == 0)
        contract = "Monthly" if is_monthly else "Hourly"
        base_sal = self.spin_salary.value() if is_monthly else 0.0
        hr_rate = 0.0 if is_monthly else self.spin_hourly.value()

        status_text = self.combo_status.currentText()
        status = status_text.split(" / ")[0]

        if not fname or not lname:
            QMessageBox.warning(self, "Erreur", "Nom et Prénom obligatoires.")
            return

        saved_photo_path = ""

        try:
            db = DatabaseManager()
            if self.current_photo_path:
                save_dir = "staff_photos"
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                ext = os.path.splitext(self.current_photo_path)[1]
                filename = f"staff_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                saved_photo_path = os.path.join(save_dir, filename)
                try: shutil.copy(self.current_photo_path, saved_photo_path)
                except Exception as e: print(f"Failed to copy photo: {e}")
            elif self.selected_staff_id:
                with db.get_connection() as conn:
                    repo = StaffRepository(conn)
                    saved_photo_path = repo.get_photo_path(self.selected_staff_id) or ""

            staff_data = {
                "first_name": fname, "last_name": lname, "role": role,
                "specialty": spec, "phone": phone, "hire_date": hire_d,
                "contract_type": contract, "salary_base": base_sal,
                "hourly_rate": hr_rate, "photo_path": saved_photo_path,
                "email": email, "address": address, "status": status,
            }

            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                if self.selected_staff_id:
                    repo.update_staff(self.selected_staff_id, staff_data)
                    log_audit(conn, getattr(self, "current_user", "system"),
                              "EDIT_STAFF", f"{fname} {lname} (id={self.selected_staff_id})")
                    QMessageBox.information(self, "Succès", "Mise à jour réussie.")
                else:
                    repo.add_staff(staff_data)
                    log_audit(conn, getattr(self, "current_user", "system"),
                              "ADD_STAFF", f"{fname} {lname}")
                    QMessageBox.information(self, "Succès", "Employé ajouté avec succès.")
                conn.commit()

            self.load_staff_list()
            self.clear_form()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur s'est produite lors de l'enregistrement: {str(e)}")

    def clear_form(self):
        self.txt_fname.clear()
        self.txt_lname.clear()
        self.txt_spec.clear()
        self.txt_phone.clear()
        self.txt_email.clear()
        self.txt_address.clear()
        self.spin_salary.setValue(0)
        self.spin_hourly.setValue(0)
        self.lbl_photo.clear()
        self.lbl_photo.setText("Photo")
        self.current_photo_path = None
        self.selected_staff_id = None
        self.combo_status.setCurrentIndex(0)
        self.btn_save.setText("💾 Enregistrer")
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        self.btn_save.setStyleSheet(f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; border-radius: 8px; font-weight: bold; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}")

    def on_staff_selected(self):
        selected_rows = self.table_staff.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            staff_id = int(self.table_staff.item(row, 0).text())
            self.load_staff_details(staff_id)

    def load_staff_details(self, staff_id):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                data = repo.get_staff_details(staff_id)

            if data:
                self.selected_staff_id = staff_id
                self.txt_fname.setText(data[0] or "")
                self.txt_lname.setText(data[1] or "")
                self.combo_role.setCurrentText(data[2] or "")
                self.txt_spec.setText(data[3] or "")
                self.txt_phone.setText(data[4] or "")
                self.txt_email.setText(data[5] or "")
                self.txt_address.setText(data[6] or "")

                try:
                    if data[7]: self.date_hire.setDate(QDate.fromString(data[7], "yyyy-MM-dd"))
                except Exception: pass
                idx = 0 if data[8] == "Monthly" else 1
                self.combo_contract.setCurrentIndex(idx)
                self.spin_salary.setValue(data[9] or 0)
                self.spin_hourly.setValue(data[10] or 0)

                if data[11] and os.path.exists(data[11]):
                    self.current_photo_path = data[11]
                    pixmap = QPixmap(data[11])
                    self.lbl_photo.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                else:
                    self.lbl_photo.clear()
                    self.lbl_photo.setText("Photo")
                    self.current_photo_path = None

                staff_status = data[12] or "Actif"
                status_map = {
                    "Actif": 0, "Congé": 1, "Suspendu": 2,
                    "Démission": 3, "Licencié": 4, "Retraité": 5
                }
                self.combo_status.setCurrentIndex(status_map.get(staff_status, 0))

                self.btn_save.setText("✏️ Modifier")
                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                self.btn_save.setStyleSheet(f"QPushButton {{ background-color: {colors.WARNING}; color: white; border-radius: 8px; font-weight: bold; border: none; }}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les détails: {str(e)}")

    def delete_staff_from_table(self, pid):
        reply = QMessageBox.question(self, 'Confirmation', "Voulez-vous archiver cet employé ?\n(Cela masquera l'employé des listes actives)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    repo = StaffRepository(conn)
                    repo.archive_staff(pid)
                    log_audit(conn, getattr(self, "current_user", "system"), "ARCHIVE_STAFF", f"id={pid}")
                    conn.commit()
                self.load_staff_list()
                self.clear_form()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def print_staff_list(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                school_info = FinanceRepository(conn).get_school_info()
                rows = repo.list_staff_for_report()

            pdf = StaffReportPDF(school_info, "LISTE DU PERSONNEL")
            pdf.add_page()

            pdf.set_fill_color(30, 41, 59)
            pdf.set_text_color(255, 255, 255)
            font_to_use = "ArabicFont" if pdf.arabic_font_ready else "Helvetica"
            pdf.set_font(font_to_use, 'B', 8)

            col_widths = [10, 35, 25, 28, 32, 36, 36, 18, 15, 13, 13, 18]
            headers = [
                "ID", "Nom Complet", "Fonction", "Spécialité", "Téléphone",
                "Email", "Adresse", "Embauche", "Contrat", "Salaire",
                "Heure", "Statut"
            ]
            for i, header in enumerate(headers):
                ln_val = 1 if i == len(headers) - 1 else 0
                pdf.cell(col_widths[i], 7, pdf.sanitize(header), 1, ln_val, 'C', True)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font(font_to_use, '', 7)

            for i, row in enumerate(rows):
                fill = i % 2 == 0
                if fill:
                    pdf.set_fill_color(248, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.cell(col_widths[0], 6, str(row[0]), 1, 0, 'C', fill)
                pdf.cell(col_widths[1], 6, pdf.sanitize(row[1]), 1, 0, 'L', fill)
                pdf.cell(col_widths[2], 6, pdf.sanitize(row[2]), 1, 0, 'L', fill)
                pdf.cell(col_widths[3], 6, pdf.sanitize(row[3]), 1, 0, 'L', fill)
                pdf.cell(col_widths[4], 6, pdf.sanitize(row[4]), 1, 0, 'L', fill)
                pdf.cell(col_widths[5], 6, pdf.sanitize(row[5]), 1, 0, 'L', fill)
                pdf.cell(col_widths[6], 6, pdf.sanitize(row[6]), 1, 0, 'L', fill)
                pdf.cell(col_widths[7], 6, pdf.sanitize(row[7]), 1, 0, 'C', fill)
                pdf.cell(col_widths[8], 6, pdf.sanitize("Mensuel" if row[8] == "Monthly" else "Horaire"), 1, 0, 'L', fill)
                pdf.cell(col_widths[9], 6, pdf.sanitize(f"{row[9]:.0f}" if row[9] is not None else ""), 1, 0, 'R', fill)
                pdf.cell(col_widths[10], 6, pdf.sanitize(f"{row[10]:.0f}" if row[10] is not None else ""), 1, 0, 'R', fill)
                pdf.cell(col_widths[11], 6, pdf.sanitize(row[11]), 1, 1, 'C', fill)

            output_pdf(
                pdf,
                self,
                f"Liste_Personnel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mode=STAFF_LIST_OUTPUT_MODE,
                dialog_title="Sauvegarder PDF",
                success_save_message="Rapport généré en PDF.",
                success_print_message="Rapport envoyé à l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération du PDF: {str(e)}")

    # --- Timetable Logic ---
    def load_classes_into_combo(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                self.combo_class_tt.clear()
                for c in StaffRepository(conn).list_classes():
                    self.combo_class_tt.addItem(c[1], c[0])
        except Exception as e: print(f"Classes TT Load Error: {e}")

    def load_subjects_into_combo(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                self.combo_subject_tt.clear()
                for s in StaffRepository(conn).list_subjects():
                    self.combo_subject_tt.addItem(s[1], s[0])
        except Exception as e: print(f"Subjects TT Load Error: {e}")

    # ================== خوارزمية فحص التداخل (Conflict Detection) ==================
    def check_timetable_conflict(self, conn, teacher_id, class_id, day, start, end):
        """
        يفحص إذا كان هناك تداخل في الجدول الزمني
        يعود بـ (True, رسالة الخطأ) إذا كان هناك تداخل، و (False, "") إذا كان الوضع آمناً.
        """
        try:
            t_start = datetime.strptime(start, "%H:%M").time()
            t_end = datetime.strptime(end, "%H:%M").time()
        except ValueError:
            return True, "Format d'heure invalide. Utilisez HH:MM (ex: 08:00)"

        if t_start >= t_end:
            return True, "L'heure de fin doit être après l'heure de début."

        repo = StaffRepository(conn)

        # 1. فحص تداخل الأستاذ (هل يدرس في فصل آخر في نفس الوقت؟)
        for cname, existing_start, existing_end in repo.get_teacher_timetable_for_day(teacher_id, day):
            e_start = datetime.strptime(existing_start, "%H:%M").time()
            e_end = datetime.strptime(existing_end, "%H:%M").time()
            if (t_start < e_end) and (t_end > e_start):
                prof_name = self.combo_prof_tt.currentText()
                return True, f"Le professeur {prof_name} est déjà assigné à la classe {cname} le {day} de {existing_start} à {existing_end}."

        # 2. فحص تداخل الفصل (هل الفصل لديه حصة أخرى في نفس الوقت؟)
        for prof_name, sub_name, existing_start, existing_end in repo.get_class_timetable_for_day(class_id, day):
            e_start = datetime.strptime(existing_start, "%H:%M").time()
            e_end = datetime.strptime(existing_end, "%H:%M").time()
            if (t_start < e_end) and (t_end > e_start):
                cname = self.combo_class_tt.currentText()
                return True, f"La classe {cname} a déjà cours de {sub_name} avec {prof_name} le {day} de {existing_start} à {existing_end}."

        return False, ""

    def add_to_timetable(self):
        teacher_id = self.combo_prof_tt.currentData()
        class_id = self.combo_class_tt.currentData()
        sub_id = self.combo_subject_tt.currentData()
        day = self.combo_day_tt.currentText()
        start = self.txt_time_start.text().strip()
        end = self.txt_time_end.text().strip()

        if not teacher_id or not class_id or not sub_id or not start or not end:
            QMessageBox.warning(self, "Attention", "Veuillez remplir tous les champs du calendrier.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                # --- استخدام خوارزمية منع التداخل ---
                is_conflict, conflict_msg = self.check_timetable_conflict(conn, teacher_id, class_id, day, start, end)
                if is_conflict:
                    QMessageBox.critical(self, "Conflit d'Horaire / تداخل في الجدول", conflict_msg)
                    return

                StaffRepository(conn).insert_timetable_entry(teacher_id, class_id, sub_id, day, start, end)
                conn.commit()
            self.load_timetable()
            self.txt_time_start.clear()
            self.txt_time_end.clear()
            QMessageBox.information(self, "Succès", "Séance ajoutée avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {str(e)}")

    def load_timetable(self):
        self.table_tt.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = StaffRepository(conn).list_timetable()

            for row in rows:
                idx = self.table_tt.rowCount()
                self.table_tt.insertRow(idx)
                for c, val in enumerate(row):
                    self.table_tt.setItem(idx, c, QTableWidgetItem(str(val)))

                btn = QPushButton("✕")
                btn.setFixedSize(24, 24)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                btn.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 4px; border: none;")
                btn.clicked.connect(lambda ch, tid=row[0]: self.delete_tt(tid))

                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(btn)
                self.table_tt.setCellWidget(idx, 6, container)
        except Exception as e:
            AppLogger.error("StaffManagement", f"Error loading timetable: {e}")

    def delete_tt(self, tid):
        reply = QMessageBox.question(self, 'Confirmation', "Supprimer cet horaire ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    StaffRepository(conn).delete_timetable_entry(tid)
                    conn.commit()
                self.load_timetable()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    # ================== طباعة جدول الفصل (Print Class Timetable) ==================
    def print_class_timetable(self):
        class_id = self.combo_class_tt.currentData()
        class_name = self.combo_class_tt.currentText()
        if not class_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une classe d'abord.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                school_info = FinanceRepository(conn).get_school_info()
                timetable_data = StaffRepository(conn).get_timetable_for_class(class_id)

            if not timetable_data:
                QMessageBox.information(self, "Vide", f"Aucun emploi du temps trouvé pour la classe {class_name}.")
                return

            pdf = StaffReportPDF(school_info, f"EMPLOI DU TEMPS - {class_name.upper()}", orientation='P')
            pdf.add_page()

            # الألوان والخطوط للجدول المطبوع
            pdf.set_fill_color(30, 41, 59)  # Header color
            pdf.set_text_color(255, 255, 255)
            font_to_use = "ArabicFont" if pdf.arabic_font_ready else "Helvetica"
            pdf.set_font(font_to_use, 'B', 10)

            col_widths = [30, 40, 50, 70]  # Total 190 (A4 Portrait width minus margins)
            headers = ["Jour", "Horaire", "Matière", "Professeur"]

            for i, header in enumerate(headers):
                ln_val = 1 if i == len(headers) - 1 else 0
                pdf.cell(col_widths[i], 8, pdf.sanitize(header), 1, ln_val, 'C', True)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font(font_to_use, '', 9)

            current_day = ""
            for i, row in enumerate(timetable_data):
                day, start, end, subject, prof = row

                # تلوين تبادلي بناءً على الأيام لسهولة القراءة
                if day != current_day:
                    current_day = day
                    pdf.set_fill_color(226, 232, 240)  # لون رمادي فاتح لفاصل الأيام
                    pdf.set_font(font_to_use, 'B', 9)
                    pdf.cell(sum(col_widths), 6, pdf.sanitize(day.upper()), 1, 1, 'C', True)
                    pdf.set_font(font_to_use, '', 9)

                fill = i % 2 == 0
                if fill:
                    pdf.set_fill_color(248, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)

                time_str = f"{start} - {end}"
                pdf.cell(col_widths[0], 7, pdf.sanitize(day), 1, 0, 'C', fill)
                pdf.cell(col_widths[1], 7, pdf.sanitize(time_str), 1, 0, 'C', fill)
                pdf.cell(col_widths[2], 7, pdf.sanitize(subject), 1, 0, 'C', fill)
                pdf.cell(col_widths[3], 7, pdf.sanitize(prof), 1, 1, 'C', fill)

            output_pdf(
                pdf,
                self,
                f"Emploi_Du_Temps_{class_name.replace(' ', '_')}.pdf",
                mode=TIMETABLE_OUTPUT_MODE,
                dialog_title="Sauvegarder Emploi du Temps PDF",
                success_save_message="Emploi du temps généré en PDF.",
                success_print_message="Emploi du temps envoyé à l'imprimante.",
            )

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération du PDF: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernStaffManagement()
    window.show()
    sys.exit(app.exec())
