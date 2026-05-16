import sys
import psycopg2
import os
from datetime import datetime
from database_setup import DatabaseManager
from app_logger import AppLogger
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QHeaderView, QGroupBox, QDateEdit, QTimeEdit,
                             QTabWidget, QGridLayout, QLineEdit,
                             QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style
from print_export_service import output_pdf, get_report_output_mode
from repositories.staff_repo import StaffRepository
from pdf_report_style import apply_table_header_style, apply_table_body_style, set_zebra_row_fill

THEME_AVAILABLE = True
STAFF_ATTENDANCE_REPORT_OUTPUT_MODE = get_report_output_mode("staff_attendance_mode", "save")

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

# --- فئة تقارير PDF للحضور ---


class StaffAttendancePDF(FPDF):
    def __init__(self, school_info=None, orientation='P', unit='mm', format='A4'):
        super().__init__(orientation, unit, format)
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
            except Exception:
                pass

        self.set_xy(right_x, left_y + 22)
        self.set_y(self.get_y() + 2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

        title_style = '' if self.arabic_font_ready else 'B'
        self.set_font(self.font_name, title_style, 12)
        self.set_text_color(44, 62, 80)
        self.cell(0, 8, "RAPPORT DE PRESENCE DU PERSONNEL", 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, 'I', 8)
        self.set_text_color(127, 140, 141)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        self.cell(0, 10, datetime.now().strftime('%d/%m/%Y'), 0, 0, 'R')


class StaffAttendanceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion de Présence / إدارة حضور الموظفين")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر باستخدام ThemeManager
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
        self.load_staff_combo()
        self.load_attendance_list()
        self.load_report_records()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        bg_header = colors.BG_HEADER
        header_text = colors.HEADER_TEXT
        sub_text = colors.TEXT_SECONDARY

        header_frame.setStyleSheet(f"QFrame {{ background-color: {bg_header}; border-radius: 10px; }}")
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
        header_lbl = QLabel("POINTAGE PERSONNEL")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {header_text}; background: transparent;")

        sub_lbl = QLabel("تسجيل الحضور والانصراف للموظفين")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {sub_text}; background: transparent;")

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

        self.setup_daily_tab()
        self.setup_reports_tab()

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
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_date(self):
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setMinimumHeight(38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        de.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        return de

    def styled_combo(self):
        combo = QComboBox()
        combo.setMinimumHeight(38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())
        else:
            colors = Colors()
            table.setStyleSheet(f"""
                QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
            """)

    # ---------------------------------------------------------
    # TAB 1: Daily Entry
    # ---------------------------------------------------------
    def setup_daily_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        control_card = self.create_card()
        h_layout = QHBoxLayout(control_card)
        h_layout.setContentsMargins(15, 15, 15, 15)
        h_layout.setSpacing(15)

        self.date_picker = self.styled_date()
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.load_attendance_list)

        self.combo_role_filter = self.styled_combo()
        self.combo_role_filter.addItems(["Tous / الكل", "Professeur", "Administration", "Comptabilité", "Agent", "Sécurité", "Autre"])
        self.combo_role_filter.currentIndexChanged.connect(self.load_attendance_list)

        btn_refresh = QPushButton("Actualiser / تحديث")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_refresh.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 8px 15px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_refresh.clicked.connect(self.load_attendance_list)

        h_layout.addWidget(QLabel("Date:"))
        h_layout.addWidget(self.date_picker)
        h_layout.addWidget(QLabel("Rôle:"))
        h_layout.addWidget(self.combo_role_filter)
        h_layout.addWidget(btn_refresh)
        h_layout.addStretch()

        layout.addWidget(control_card)

        # Table
        self.table_attendance = QTableWidget()
        self.style_table(self.table_attendance)
        self.table_attendance.setColumnCount(7)
        self.table_attendance.setHorizontalHeaderLabels([
            "ID", "Nom & Prénom", "Rôle", "Statut", "Entrée (الدخول)", "Sortie (الخروج)", "Note"
        ])
        self.table_attendance.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_attendance.setColumnWidth(0, 50)
        self.table_attendance.verticalHeader().setDefaultSectionSize(40)

        layout.addWidget(self.table_attendance)

        # Save Button
        btn_save = QPushButton("💾 ENREGISTRER LE POINTAGE / حفظ السجل")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; padding: 12px; font-weight: bold; font-size: 14px; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_save.clicked.connect(self.save_all_attendance)
        layout.addWidget(btn_save)

        self.tabs.addTab(tab, "  📝 Pointage Journalier / تسجيل يومي  ")

    # ---------------------------------------------------------
    # TAB 2: Reports
    # ---------------------------------------------------------
    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        filter_card = self.create_card()
        glay = QGridLayout(filter_card)
        glay.setContentsMargins(15, 15, 15, 15)
        glay.setSpacing(15)

        card_title = QLabel("Rapport Mensuel / تقرير شهري")
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        card_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        glay.addWidget(card_title, 0, 0, 1, 4)

        self.combo_staff_report = self.styled_combo()
        self.combo_staff_report.currentIndexChanged.connect(self.load_report_records)

        self.date_report_month = self.styled_date()
        self.date_report_month.setDisplayFormat("MM/yyyy")
        self.date_report_month.setDate(QDate.currentDate())
        self.date_report_month.dateChanged.connect(self.load_report_records)

        btn_gen_report = QPushButton("🖨️ Générer PDF")
        btn_gen_report.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen_report.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.WARNING}; }}
        """)
        btn_gen_report.clicked.connect(self.generate_monthly_report)

        glay.addWidget(QLabel("Employé:"), 1, 0)
        glay.addWidget(self.combo_staff_report, 1, 1)
        glay.addWidget(QLabel("Mois:"), 1, 2)
        glay.addWidget(self.date_report_month, 1, 3)
        glay.addWidget(btn_gen_report, 1, 4)

        layout.addWidget(filter_card)

        self.table_report = QTableWidget(0, 6)
        self.style_table(self.table_report)
        self.table_report.setHorizontalHeaderLabels([
            "Employé", "Date", "Statut", "Entrée", "Sortie", "Note"
        ])
        self.table_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_report.setColumnWidth(1, 90)
        layout.addWidget(self.table_report)

        layout.addStretch()
        self.tabs.addTab(tab, "  📊 Rapports / التقارير  ")

    # ---------------------------------------------------------
    # Logic
    # ---------------------------------------------------------
    def load_staff_combo(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = StaffRepository(conn).list_active_staff_fullname()

            self.combo_staff_report.clear()
            self.combo_staff_report.addItem("Tous / الكل", None)
            for row in rows:
                self.combo_staff_report.addItem(row[1] or "-", row[0])
        except Exception as e:
            AppLogger.error("StaffAttendance", f"Error loading staff combo: {e}")

    def load_attendance_list(self):
        self.table_attendance.setRowCount(0)
        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        role_filter = self.combo_role_filter.currentText()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                role_arg = None if "Tous" in role_filter else role_filter
                staff_members = repo.list_active_staff_by_role(role_arg)

                for staff in staff_members:
                    row_idx = self.table_attendance.rowCount()
                    self.table_attendance.insertRow(row_idx)

                    id_item = QTableWidgetItem(str(staff[0]))
                    id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_attendance.setItem(row_idx, 0, id_item)

                    name_item = QTableWidgetItem(staff[1] or "-")
                    name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_attendance.setItem(row_idx, 1, name_item)

                    role_item = QTableWidgetItem(staff[2] or "-")
                    role_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_attendance.setItem(row_idx, 2, role_item)

                    status_combo = QComboBox()
                    status_combo.addItems(["Présent", "Absent", "Retard", "Congé", "Mission"])
                    status_combo.setStyleSheet("QComboBox { border: none; background: transparent; }")
                    self.table_attendance.setCellWidget(row_idx, 3, status_combo)

                    time_in = QTimeEdit()
                    time_in.setDisplayFormat("HH:mm")
                    time_in.setTime(QTime(8, 0))
                    time_in.setStyleSheet("QTimeEdit { border: none; background: transparent; }")
                    self.table_attendance.setCellWidget(row_idx, 4, time_in)

                    time_out = QTimeEdit()
                    time_out.setDisplayFormat("HH:mm")
                    time_out.setTime(QTime(16, 0))
                    time_out.setStyleSheet("QTimeEdit { border: none; background: transparent; }")
                    self.table_attendance.setCellWidget(row_idx, 5, time_out)

                    note_item = QLineEdit()
                    note_item.setStyleSheet("QLineEdit { border: none; background: transparent; }")
                    self.table_attendance.setCellWidget(row_idx, 6, note_item)

                    existing = repo.get_staff_attendance_for_date(staff[0], selected_date)

                    if existing:
                        status_combo.setCurrentText(existing[0])
                        if existing[1]: time_in.setTime(QTime.fromString(existing[1], "HH:mm"))
                        if existing[2]: time_out.setTime(QTime.fromString(existing[2], "HH:mm"))
                        if existing[3]: note_item.setText(existing[3])

                        if existing[0] == "Absent":
                            colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                            status_combo.setStyleSheet(f"QComboBox {{ color: {colors.DANGER}; font-weight: bold; }}")
        except Exception as e:
            AppLogger.error("StaffAttendance", f"Error loading attendance list: {e}")

    def load_report_records(self):
        if not hasattr(self, 'table_report'):
            return

        self.table_report.setRowCount(0)
        staff_id = self.combo_staff_report.currentData()
        month = self.date_report_month.date().toString("yyyy-MM")
        start_date, end_date = self._month_bounds(month)
        if not start_date:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = StaffRepository(conn).get_attendance_report_for_display(
                    start_date, end_date, staff_id
                )

            for row in rows:
                idx = self.table_report.rowCount()
                self.table_report.insertRow(idx)
                for col, value in enumerate(row):
                    text = value or "-"
                    self.table_report.setItem(idx, col, QTableWidgetItem(str(text)))
        except Exception as e:
            AppLogger.error("StaffAttendance", f"Error loading report records: {e}")

    def _month_bounds(self, month_str):
        try:
            start = datetime.strptime(f"{month_str}-01", "%Y-%m-%d")
        except ValueError:
            return None, None
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1)
        else:
            end = datetime(start.year, start.month + 1, 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def save_all_attendance(self):
        selected_date = self.date_picker.date().toString("yyyy-MM-dd")

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                for row in range(self.table_attendance.rowCount()):
                    staff_id = int(self.table_attendance.item(row, 0).text())
                    status = self.table_attendance.cellWidget(row, 3).currentText()
                    check_in = self.table_attendance.cellWidget(row, 4).time().toString("HH:mm")
                    check_out = self.table_attendance.cellWidget(row, 5).time().toString("HH:mm")
                    note = self.table_attendance.cellWidget(row, 6).text()
                    repo.upsert_staff_attendance(
                        staff_id, selected_date, check_in, check_out, status, note
                    )
                conn.commit()
            QMessageBox.information(self, "Succès", "Pointage enregistré avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de sauvegarde: {str(e)}")

    def sanitize_filename(self, text):
        if not text: return ""
        cleaned = str(text).strip().replace(" ", "_").replace("/", "-")
        return "".join(ch for ch in cleaned if ch.isalnum() or ch in "-_")

    def generate_monthly_report(self):
        staff_id = self.combo_staff_report.currentData()
        staff_name = self.combo_staff_report.currentText()
        month = self.date_report_month.date().toString("yyyy-MM")
        start_date, end_date = self._month_bounds(month)

        if not start_date: return

        default_name = f"Pointage_{self.sanitize_filename(staff_name)}_{month}.pdf"

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                school_info = repo.get_school_info()
                records = repo.get_attendance_report(
                    start_date, end_date, staff_id or None
                )
                is_all = staff_id is None

            pdf = StaffAttendancePDF(school_info)
            pdf.add_page()

            pdf.set_font(pdf.font_name, 'B', 10)
            pdf.cell(40, 8, "Employé(e):", 0, 0)
            pdf.set_font(pdf.font_name, '', 10)
            pdf.cell(60, 8, pdf.sanitize(staff_name), 0, 0)

            pdf.set_font(pdf.font_name, 'B', 10)
            pdf.cell(40, 8, "Mois:", 0, 0)
            pdf.set_font(pdf.font_name, '', 10)
            pdf.cell(60, 8, month, 0, 1)

            pdf.ln(5)

            apply_table_header_style(pdf, pdf.font_name, 9)

            if is_all:
                col_widths = [45, 25, 25, 20, 20, 55]
                headers = ["Employé", "Date", "Statut", "Entrée", "Sortie", "Note"]
            else:
                col_widths = [30, 30, 30, 30, 70]
                headers = ["Date", "Statut", "Entrée", "Sortie", "Note"]

            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 7, pdf.sanitize(header), 1, 0, 'C', True)
            pdf.ln(7)

            apply_table_body_style(pdf, pdf.font_name, 9)

            total_days = len(records)
            present_cnt = 0

            for i, record in enumerate(records):
                set_zebra_row_fill(pdf, i)

                if is_all:
                    emp_name = record[0]
                    date_val = record[1]
                    status = record[2]
                    t_in = record[3]
                    t_out = record[4]
                    note = record[5]
                else:
                    emp_name = None
                    date_val = record[0]
                    status = record[1]
                    t_in = record[2]
                    t_out = record[3]
                    note = record[4]

                date_fmt = datetime.strptime(date_val, '%Y-%m-%d').strftime('%d/%m/%Y') if date_val else ""
                if status == "Présent": present_cnt += 1

                if status == "Absent": pdf.set_text_color(200, 0, 0)
                elif status == "Retard": pdf.set_text_color(200, 150, 0)
                else: pdf.set_text_color(0, 0, 0)

                if is_all:
                    pdf.cell(col_widths[0], 6, pdf.sanitize(emp_name), 1, 0, 'L', True)
                    pdf.cell(col_widths[1], 6, date_fmt, 1, 0, 'C', True)
                    pdf.cell(col_widths[2], 6, pdf.sanitize(status), 1, 0, 'C', True)
                    pdf.set_text_color(51, 65, 85)
                    pdf.cell(col_widths[3], 6, t_in or "-", 1, 0, 'C', True)
                    pdf.cell(col_widths[4], 6, t_out or "-", 1, 0, 'C', True)
                    pdf.cell(col_widths[5], 6, pdf.sanitize(note or ""), 1, 1, 'L', True)
                else:
                    pdf.cell(col_widths[0], 6, date_fmt, 1, 0, 'C', True)
                    pdf.cell(col_widths[1], 6, pdf.sanitize(status), 1, 0, 'C', True)
                    pdf.set_text_color(51, 65, 85)
                    pdf.cell(col_widths[2], 6, t_in or "-", 1, 0, 'C', True)
                    pdf.cell(col_widths[3], 6, t_out or "-", 1, 0, 'C', True)
                    pdf.cell(col_widths[4], 6, pdf.sanitize(note or ""), 1, 1, 'L', True)

            pdf.ln(5)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(pdf.font_name, 'B', 10)
            if not is_all:
                pdf.cell(0, 8, f"Total Jours: {total_days} | Présence: {present_cnt}", 0, 1)
            else:
                pdf.cell(0, 8, f"Total Enregistrements: {total_days}", 0, 1)

            output_pdf(
                pdf,
                self,
                default_name,
                mode=STAFF_ATTENDANCE_REPORT_OUTPUT_MODE,
                dialog_title="Sauvegarder PDF",
                success_save_message="Rapport généré avec succès.",
                success_print_message="Rapport envoyé à l'imprimante.",
            )

        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Échec de la génération: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StaffAttendanceWindow()
    window.show()
    sys.exit(app.exec())
