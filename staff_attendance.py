import os
import sys
from datetime import date, datetime

# FIX 5: Removed `import psycopg2` — never referenced in this file.
from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt, QTime
from PyQt6.QtWidgets import (  # FIX 5: Removed QDateEdit, QFrame, QGridLayout, QGroupBox — none directly instantiated.
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from pdf_report_style import apply_table_body_style, apply_table_header_style, set_zebra_row_fill
from print_export_service import get_report_output_mode, output_pdf
from repositories.staff_repo import StaffRepository
from ui_styles import (  # FIX 5: Removed Colors, apply_shadow_to_widget, get_card_style, get_table_style — unused.
    ModuleHeaderWidget,
    ThemeManager,
    get_module_caps,
    get_tabs_style,
)

STAFF_ATTENDANCE_REPORT_OUTPUT_MODE = get_report_output_mode("staff_attendance_mode", "save")

from pdf_helpers import (
    prepare_pdf_text as _prepare_pdf_text,  # FIX 1: Renamed alias sanitize_latin as sanitize → _sanitize_latin so the; instance method StaffAttendancePDF.sanitize() can call _sanitize_latin(text); without NameError.  The old alias `sanitize` conflicted with the method name; and was shadowed inside the class, so _sanitize_latin(text) was never resolvable.; FIX 5: Removed 6 unused imports: ARABIC_SUPPORT, contains_arabic,; find_arabic_font_path, get_pdf_font_name, is_arabic_font_ready, latin_fallback.
)
from pdf_helpers import sanitize_latin as _sanitize_latin
from pdf_helpers import setup_pdf_arabic_font
from ui_components import card_frame, style_table, styled_combo, styled_date_edit

# FIX 6: Removed _register_arabic_font() pass-through wrapper — setup_pdf_arabic_font
# is called directly below; the wrapper added no value.

# --- فئة تقارير PDF للحضور ---


class StaffAttendancePDF(FPDF):
    def __init__(self, school_info=None, orientation='P', unit='mm', format='A4'):
        super().__init__(orientation, unit, format)
        self.school_info = school_info
        self.font_name = "Helvetica"
        self.arabic_font_ready = False
        if setup_pdf_arabic_font(self):
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

        # FIX 4: Added len > 7 guard — same pattern as pdf_report_style.py Screen 18.
        # school_info[7] raises IndexError if the tuple has fewer than 8 elements.
        if self.school_info and len(self.school_info) > 7:
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
        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_staff_combo()
        self.load_attendance_list()
        self.load_report_records()
        self._load_kpi_stats()

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "staff_attendance")
        self.btn_save.setEnabled(caps["can_write"])
        self.btn_save.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. En-tête unifié
        header = ModuleHeaderWidget(
            icon="📅",
            title="POINTAGE PERSONNEL",
            subtitle="تسجيل الحضور والانصراف للموظفين",
        )
        self.main_layout.addWidget(header)
        self._stat_present = header.add_stat("✅", "Présents Aujourd'hui", "—", "#22C55E")
        self._stat_absent = header.add_stat("❌", "Absents", "—", "#EF4444")
        self._stat_late = header.add_stat("⏰", "Retards", "—", "#F59E0B")
        self._stat_total_staff = header.add_stat("👥", "Total Personnel", "—", "#3B82F6")

        # 2. KPI Cards

        # 3. Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_daily_tab()
        self.setup_reports_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        return card_frame()

    def styled_date(self):
        return styled_date_edit(min_height=32)

    def styled_combo(self):
        return styled_combo(min_height=32)

    def style_table(self, table):
        style_table(table)

    def _load_kpi_stats(self):
        """Charge les KPI du pointage du jour."""
        try:
            today = date.today().isoformat()
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Total personnel
                cursor.execute("SELECT COUNT(*) FROM Staff WHERE is_active = TRUE")
                total_staff = cursor.fetchone()[0] or 0
                # Présents aujourd'hui
                cursor.execute(
                    "SELECT COUNT(*) FROM StaffAttendance WHERE attendance_date = %s AND status = 'present'", (today,)
                )
                present = cursor.fetchone()[0] or 0
                # Absents aujourd'hui
                cursor.execute(
                    "SELECT COUNT(*) FROM StaffAttendance WHERE attendance_date = %s AND status = 'absent'", (today,)
                )
                absent = cursor.fetchone()[0] or 0
                # Retards aujourd'hui
                cursor.execute(
                    "SELECT COUNT(*) FROM StaffAttendance WHERE attendance_date = %s AND status = 'late'", (today,)
                )
                late = cursor.fetchone()[0] or 0

            self._stat_present.set_value(str(present))
            self._stat_absent.set_value(str(absent))
            self._stat_late.set_value(str(late))
            self._stat_total_staff.set_value(str(total_staff))
        except Exception as e:
            AppLogger.error("StaffAttendanceWindow", f"Erreur KPI stats: {e}")

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
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(10)

        self.date_picker = self.styled_date()
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.load_attendance_list)

        self.combo_role_filter = self.styled_combo()
        self.combo_role_filter.addItems(
            ["Tous / الكل", "Professeur", "Administration", "Comptabilité", "Agent", "Sécurité", "Autre"]
        )
        self.combo_role_filter.currentIndexChanged.connect(self.load_attendance_list)

        btn_refresh = QPushButton("Actualiser / تحديث")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedHeight(32)
        colors = ThemeManager.get_colors()
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            # FIX 2: Added missing comma between stop:0 and stop:1.
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER}); color:white;"
            f" font-weight:bold; font-size:11px; padding:4px 12px; border-radius:7px; border:none; }}"
            f"QPushButton:hover {{ background:{colors.PRIMARY_DARK}; }}"
        )
        btn_refresh.clicked.connect(self.load_attendance_list)

        h_layout.addWidget(QLabel("Date:"))
        h_layout.addWidget(self.date_picker)
        h_layout.addWidget(QLabel("Rôle:"))
        h_layout.addWidget(self.combo_role_filter)
        h_layout.addStretch()
        h_layout.addWidget(btn_refresh)

        layout.addWidget(control_card)

        # Table
        self.table_attendance = QTableWidget()
        self.style_table(self.table_attendance)
        self.table_attendance.setColumnCount(7)
        self.table_attendance.setHorizontalHeaderLabels(
            ["ID", "Nom & Prénom", "Rôle", "Statut", "Entrée (الدخول)", "Sortie (الخروج)", "Note"]
        )
        self.table_attendance.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_attendance.setColumnWidth(0, 50)
        self.table_attendance.verticalHeader().setDefaultSectionSize(40)

        layout.addWidget(self.table_attendance)

        # Save Button
        self.btn_save = QPushButton("💾 ENREGISTRER LE POINTAGE / حفظ السجل")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setMinimumHeight(46)
        self.btn_save.setStyleSheet(
            f"""
            QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS}, stop:1 #16A34A); color: white; padding: 12px; font-weight: bold; font-size: 14px; border-radius: 10px; border: none; }}
            QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}
        """
        )
        self.btn_save.clicked.connect(self.save_all_attendance)
        layout.addWidget(self.btn_save)

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
        h_fil = QHBoxLayout(filter_card)
        h_fil.setContentsMargins(10, 8, 10, 8)
        h_fil.setSpacing(10)
        colors = ThemeManager.get_colors()

        self.combo_staff_report = self.styled_combo()
        self.combo_staff_report.setMinimumWidth(180)
        self.combo_staff_report.currentIndexChanged.connect(self.load_report_records)

        self.date_report_month = self.styled_date()
        self.date_report_month.setDisplayFormat("MM/yyyy")
        self.date_report_month.setDate(QDate.currentDate())
        self.date_report_month.setMaximumWidth(130)
        self.date_report_month.dateChanged.connect(self.load_report_records)

        btn_gen_report = QPushButton("🖨️ Générer PDF")
        btn_gen_report.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen_report.setFixedHeight(32)
        btn_gen_report.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.WARNING} stop:1 #D97706); color:white; font-weight:bold;"
            f" font-size:11px; padding:4px 12px; border-radius:7px; border:none; }}"
            f"QPushButton:hover {{ background:#B45309; }}"
        )
        btn_gen_report.clicked.connect(self.generate_monthly_report)

        h_fil.addWidget(QLabel("Employé:"))
        h_fil.addWidget(self.combo_staff_report)
        h_fil.addWidget(QLabel("Mois:"))
        h_fil.addWidget(self.date_report_month)
        h_fil.addStretch()
        h_fil.addWidget(btn_gen_report)

        layout.addWidget(filter_card)

        self.table_report = QTableWidget(0, 6)
        self.style_table(self.table_report)
        self.table_report.setHorizontalHeaderLabels(["Employé", "Date", "Statut", "Entrée", "Sortie", "Note"])
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
                        # FIX 3: psycopg2 returns TIME columns as datetime.time objects,
                        # not strings — QTime.fromString() raises TypeError on them.
                        if existing[1]:
                            t = existing[1]
                            time_in.setTime(
                                QTime(t.hour, t.minute) if hasattr(t, 'hour') else QTime.fromString(str(t), "HH:mm")
                            )
                        if existing[2]:
                            t = existing[2]
                            time_out.setTime(
                                QTime(t.hour, t.minute) if hasattr(t, 'hour') else QTime.fromString(str(t), "HH:mm")
                            )
                        if existing[3]:
                            note_item.setText(existing[3])

                        if existing[0] == "Absent":
                            colors = ThemeManager.get_colors()
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
                rows = StaffRepository(conn).get_attendance_report_for_display(start_date, end_date, staff_id)

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
                    repo.upsert_staff_attendance(staff_id, selected_date, check_in, check_out, status, note)
                conn.commit()
            QMessageBox.information(self, "Succès", "Pointage enregistré avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de sauvegarde: {str(e)}")

    def sanitize_filename(self, text):
        if not text:
            return ""
        cleaned = str(text).strip().replace(" ", "_").replace("/", "-")
        return "".join(ch for ch in cleaned if ch.isalnum() or ch in "-_")

    def generate_monthly_report(self):
        staff_id = self.combo_staff_report.currentData()
        staff_name = self.combo_staff_report.currentText()
        month = self.date_report_month.date().toString("yyyy-MM")
        start_date, end_date = self._month_bounds(month)

        if not start_date:
            return

        default_name = f"Pointage_{self.sanitize_filename(staff_name)}_{month}.pdf"

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                school_info = repo.get_school_info()
                records = repo.get_attendance_report(start_date, end_date, staff_id or None)
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

                # FIX 3: psycopg2 returns DATE columns as datetime.date objects —
                # datetime.strptime() raises TypeError on non-string input.
                if date_val:
                    date_fmt = (
                        date_val.strftime('%d/%m/%Y')
                        if hasattr(date_val, 'strftime')
                        else datetime.strptime(str(date_val), '%Y-%m-%d').strftime('%d/%m/%Y')
                    )
                else:
                    date_fmt = ""
                if status == "Présent":
                    present_cnt += 1

                if status == "Absent":
                    pdf.set_text_color(200, 0, 0)
                elif status == "Retard":
                    pdf.set_text_color(200, 150, 0)
                else:
                    pdf.set_text_color(0, 0, 0)

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
