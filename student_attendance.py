import os
import sys
from datetime import date, datetime

from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt, QTime, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from pdf_report_style import apply_table_body_style, apply_table_header_style, set_zebra_row_fill
from print_export_service import get_report_output_mode, output_pdf
from repositories.attendance_repo import AttendanceRepository
from repositories.finance_repo import FinanceRepository
from repositories.student_repo import StudentRepository
from ui_styles import ModuleHeaderWidget, ThemeManager, friendly_db_error, get_module_caps, get_tabs_style

ATTENDANCE_REPORT_OUTPUT_MODE = get_report_output_mode("student_attendance_mode", "save")

from pdf_helpers import ARABIC_SUPPORT
from pdf_helpers import (
    contains_arabic as _contains_arabic,  # FIX 1: alias was `sanitize` but both AttendancePDF.sanitize() and; sanitize_text() called `_sanitize_latin(text)` — NameError on every; non-Arabic cell, aborting all three PDF report types.
)
from pdf_helpers import find_arabic_font_path as _get_arabic_font_path
from pdf_helpers import prepare_pdf_text as _prepare_pdf_text
from pdf_helpers import sanitize_latin as _sanitize_latin
from pdf_helpers import setup_pdf_arabic_font
from ui_components import card_frame, style_table, styled_combo, styled_date_edit, styled_time_edit

# --- فئة تقارير PDF الرسمية ---


class AttendancePDF(FPDF):
    def __init__(self, school_info):
        super().__init__(orientation='P')
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

        # FIX 3: Added len > 7 guard — indices 1–7 raised IndexError on partial tuples.
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
        self.cell(0, 8, "RAPPORT D'ASSIDUITE", 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')


class StudentAttendanceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion de l'Assiduité / إدارة الحضور والغياب")
        self.setMinimumSize(1100, 750)

        # تطبيق المظهر باستخدام ThemeManager
        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_classes()
        self._load_kpi_stats()

    def get_active_year_id(self):
        """جلب السنة الدراسية النشطة لضمان ربط الحضور بالسنة الصحيحة"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return StudentRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def get_periods_for_class(self, class_id, year_id):
        if not class_id or year_id == -1:
            return []
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return AttendanceRepository(conn).get_periods_for_class(class_id, year_id)
        except Exception:
            return []

    def resolve_period_id_for_class_date(self, class_id, date_str, year_id):
        if not class_id or not date_str or year_id == -1:
            return None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return AttendanceRepository(conn).resolve_period_id_for_class_date(class_id, date_str, year_id)
        except Exception:
            return None

    def get_entry_period_context(self, class_id, date_sel, year_id):
        if not class_id or not date_sel or year_id == -1:
            return None, None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AttendanceRepository(conn)
                period_id = repo.resolve_period_id_for_class_date(class_id, date_sel, year_id)
                if not period_id:
                    return None, None
                for current_period_id, period_name in repo.get_periods_for_class(class_id, year_id):
                    if current_period_id == period_id:
                        return period_id, period_name
                return period_id, None
        except Exception:
            return None, None

    def _format_slot_time_value(self, value):
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        text = str(value or "")
        return text[:5] if len(text) >= 5 else text

    def get_entry_slot_context(self, class_id, date_sel, time_sel):
        if not class_id or not date_sel or not time_sel:
            return None, None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AttendanceRepository(conn)
                slot = repo.resolve_timetable_slot_context_for_class_datetime(class_id, date_sel, time_sel)
                if not slot:
                    return None, None
                slot_id, start_time, end_time, subject_name = slot
                label = f"{subject_name or 'Séance planifiée'} ({self._format_slot_time_value(start_time)}-{self._format_slot_time_value(end_time)})"
                return slot_id, label
        except Exception:
            return None, None

    def refresh_entry_slot_options(self):
        class_id = self.combo_class_entry.currentData()
        date_sel = self.date_entry.date().toString("yyyy-MM-dd") if hasattr(self, "date_entry") else ""
        current_slot_id = self.combo_slot_entry.currentData() if hasattr(self, "combo_slot_entry") else None

        self.combo_slot_entry.blockSignals(True)
        self.combo_slot_entry.clear()
        self.combo_slot_entry.addItem("Séance automatique selon l'heure", None)

        if class_id and date_sel:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    slots = AttendanceRepository(conn).list_timetable_slots_for_class_date(class_id, date_sel)
                for slot_id, start_time, end_time, subject_name in slots:
                    start_txt = self._format_slot_time_value(start_time)
                    end_txt = self._format_slot_time_value(end_time)
                    slot_label = f"{start_txt}-{end_txt} | {subject_name or 'Séance'}"
                    self.combo_slot_entry.addItem(slot_label, slot_id)
            except Exception:
                pass

        if current_slot_id is not None:
            idx = self.combo_slot_entry.findData(current_slot_id)
            if idx >= 0:
                self.combo_slot_entry.setCurrentIndex(idx)
        self.combo_slot_entry.blockSignals(False)

    def on_entry_slot_changed(self):
        slot_id = self.combo_slot_entry.currentData()
        if not slot_id:
            self.load_students_for_entry()
            return

        slot_label = self.combo_slot_entry.currentText()
        time_range = slot_label.split("|", 1)[0].strip() if "|" in slot_label else ""
        start_txt = time_range.split("-", 1)[0].strip() if "-" in time_range else ""
        start_time = QTime.fromString(start_txt, "HH:mm")
        if start_time.isValid():
            self.time_entry.blockSignals(True)
            self.time_entry.setTime(start_time)
            self.time_entry.blockSignals(False)
        self.load_students_for_entry()

    def on_entry_time_changed(self):
        class_id = self.combo_class_entry.currentData()
        date_sel = self.date_entry.date().toString("yyyy-MM-dd") if hasattr(self, "date_entry") else ""
        time_sel = self.time_entry.time().toString("HH:mm") if hasattr(self, "time_entry") else ""

        slot_id, _ = self.get_entry_slot_context(class_id, date_sel, time_sel)
        self.combo_slot_entry.blockSignals(True)
        if slot_id:
            idx = self.combo_slot_entry.findData(slot_id)
            self.combo_slot_entry.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.combo_slot_entry.setCurrentIndex(0)
        self.combo_slot_entry.blockSignals(False)
        self.load_students_for_entry()

    def on_entry_class_changed(self):
        self.refresh_entry_slot_options()
        self.load_students_for_entry()

    def on_report_class_changed(self):
        class_id = self.combo_class_report.currentData()
        active_year = self.get_active_year_id()
        self.combo_period_report.clear()
        self.combo_period_report.addItem("Toutes les périodes", None)
        for period_id, period_name in self.get_periods_for_class(class_id, active_year):
            self.combo_period_report.addItem(period_name, period_id)
        self.load_subjects_for_report()
        self.load_slots_for_report()
        self.load_students_for_report_combo()

    def on_report_subject_changed(self):
        self.load_slots_for_report()

    def _format_report_slot_label(self, row):
        day_name = str(row[1] or "")
        start_txt = self._format_slot_time_value(row[2])
        end_txt = self._format_slot_time_value(row[3])
        subject_name = str(row[4] or "Séance")
        return f"{day_name} | {start_txt}-{end_txt} | {subject_name}"

    def load_subjects_for_report(self):
        class_id = self.combo_class_report.currentData()
        self.combo_subject_report.clear()
        self.combo_subject_report.addItem("Toutes les matières", None)

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = AttendanceRepository(conn).list_subjects_for_report(class_id)
            for subject_id, subject_name in rows:
                self.combo_subject_report.addItem(subject_name, subject_id)
        except Exception as e:
            AppLogger.error("StudentAttendance", f"Error loading report subjects: {e}")

    def load_slots_for_report(self):
        class_id = self.combo_class_report.currentData()
        subject_id = self.combo_subject_report.currentData() if hasattr(self, "combo_subject_report") else None
        self.combo_slot_report.clear()
        self.combo_slot_report.addItem("Toutes les séances", None)

        if not class_id:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = AttendanceRepository(conn).list_slots_for_report(class_id, subject_id)
            for row in rows:
                self.combo_slot_report.addItem(self._format_report_slot_label(row), row[0])
        except Exception as e:
            AppLogger.error("StudentAttendance", f"Error loading report slots: {e}")

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "student_attendance")
        self.btn_save_all.setEnabled(caps["can_write"])
        self.btn_save_all.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. Header
        header = ModuleHeaderWidget(
            icon="📅",
            title="SUIVI DE L'ASSIDUITÉ",
            subtitle="متابعة الغياب والحضور اليومي",
        )
        self.main_layout.addWidget(header)
        self._stat_present = header.add_stat("✅", "Présents", "—", "#22C55E")
        self._stat_absent = header.add_stat("❌", "Absents", "—", "#EF4444")
        self._stat_late = header.add_stat("⏰", "Retards", "—", "#F59E0B")
        self._stat_rate = header.add_stat("📊", "Taux Présence", "—", "#3B82F6")

        # 2. KPI Cards

        # 3. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_daily_entry_tab()
        self.setup_reports_tab()

        self.main_layout.addWidget(self.tabs)

    def setup_daily_entry_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        filter_card = card_frame(with_shadow=True)
        vlay_entry = QVBoxLayout(filter_card)
        vlay_entry.setContentsMargins(12, 10, 12, 10)
        vlay_entry.setSpacing(8)

        self.combo_class_entry = styled_combo(min_height=32)
        self.combo_class_entry.addItem("Choisir une Classe...", None)
        self.combo_class_entry.currentIndexChanged.connect(self.on_entry_class_changed)

        self.combo_slot_entry = styled_combo(min_height=32)
        self.combo_slot_entry.addItem("Séance automatique selon l'heure", None)
        self.combo_slot_entry.currentIndexChanged.connect(self.on_entry_slot_changed)

        self.lbl_period_entry_auto = QLabel("Détectée automatiquement selon la date / تُحدَّد تلقائياً حسب التاريخ")
        self.lbl_period_entry_auto.setStyleSheet("font-weight: 600;")
        self.lbl_slot_entry_auto = QLabel(
            "Séance détectée automatiquement selon l'heure / تُحدَّد الحصة تلقائياً حسب الوقت"
        )
        self.lbl_slot_entry_auto.setStyleSheet("font-weight: 600;")

        self.date_entry = styled_date_edit(min_height=32)
        self.date_entry.setDate(QDate.currentDate())
        self.date_entry.dateChanged.connect(self.refresh_entry_slot_options)
        self.date_entry.dateChanged.connect(self.load_students_for_entry)

        self.time_entry = styled_time_edit(min_height=32)
        self.time_entry.setTime(QTime.currentTime())
        self.time_entry.timeChanged.connect(self.on_entry_time_changed)

        colors = ThemeManager.get_colors()
        btn_load = QPushButton("📥 Charger / تحميل")
        btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_load.setFixedHeight(32)
        btn_load.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER});"
            f" color: white; padding: 4px 16px; border-radius: 7px;"
            f" font-weight: bold; font-size: 11px; border: none; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_load.clicked.connect(self.load_students_for_entry)

        # Row 1: Classe + Date + Heure
        row1_entry = QHBoxLayout()
        row1_entry.setSpacing(8)
        lbl_cl = QLabel("Classe:")
        lbl_cl.setFixedWidth(48)
        row1_entry.addWidget(lbl_cl)
        row1_entry.addWidget(self.combo_class_entry, 2)
        row1_entry.addSpacing(6)
        lbl_dt = QLabel("Date:")
        lbl_dt.setFixedWidth(36)
        row1_entry.addWidget(lbl_dt)
        row1_entry.addWidget(self.date_entry, 1)
        row1_entry.addSpacing(6)
        lbl_hr = QLabel("Heure:")
        lbl_hr.setFixedWidth(44)
        row1_entry.addWidget(lbl_hr)
        row1_entry.addWidget(self.time_entry, 1)

        # Row 2: Séance + btn_load
        row2_entry = QHBoxLayout()
        row2_entry.setSpacing(8)
        lbl_sc = QLabel("Séance:")
        lbl_sc.setFixedWidth(48)
        row2_entry.addWidget(lbl_sc)
        row2_entry.addWidget(self.combo_slot_entry, 3)
        row2_entry.addStretch()
        row2_entry.addWidget(btn_load)

        vlay_entry.addLayout(row1_entry)
        vlay_entry.addLayout(row2_entry)

        layout.addWidget(filter_card)

        self.table_entry = QTableWidget()
        style_table(self.table_entry)
        self.table_entry.setColumnCount(7)
        self.table_entry.setHorizontalHeaderLabels(["ID", "Élève", "Statut", "Justifié", "Motif", "Notes", "Action"])
        self.table_entry.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_entry)

        self.btn_save_all = QPushButton("💾 Enregistrer / حفظ")
        self.btn_save_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_all.setMinimumHeight(40)
        self.btn_save_all.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.SUCCESS}, stop:1 #16A34A);"
            f" color: white; padding: 10px; font-weight: bold; font-size: 13px;"
            f" border-radius: 8px; border: none; }}"
            f"QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
        self.btn_save_all.clicked.connect(self.save_daily_attendance)
        layout.addWidget(self.btn_save_all)

        self.tabs.addTab(tab, "  📝 Pointage par séance / تسجيل الحصة  ")

    # ---------------------------------------------------------
    # TAB 2: Reports
    # ---------------------------------------------------------
    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        filter_card = card_frame(with_shadow=True)
        vlay_rep = QVBoxLayout(filter_card)
        vlay_rep.setContentsMargins(12, 10, 12, 10)
        vlay_rep.setSpacing(8)

        self.combo_class_report = styled_combo(min_height=32)
        self.combo_class_report.addItem("Toutes les classes", None)
        self.combo_class_report.currentIndexChanged.connect(self.on_report_class_changed)
        self.combo_class_report.currentIndexChanged.connect(self._schedule_report_refresh)

        self.combo_period_report = styled_combo(min_height=32)
        self.combo_period_report.addItem("Toutes les périodes", None)
        self.combo_period_report.currentIndexChanged.connect(self._schedule_report_refresh)

        self.combo_subject_report = styled_combo(min_height=32)
        self.combo_subject_report.addItem("Toutes les matières", None)
        self.combo_subject_report.currentIndexChanged.connect(self.on_report_subject_changed)
        self.combo_subject_report.currentIndexChanged.connect(self._schedule_report_refresh)

        self.combo_slot_report = styled_combo(min_height=32)
        self.combo_slot_report.addItem("Toutes les séances", None)
        self.combo_slot_report.currentIndexChanged.connect(self._schedule_report_refresh)

        self.combo_student_report = styled_combo(min_height=32)
        self.combo_student_report.addItem("Tous les élèves", None)
        self.combo_student_report.currentIndexChanged.connect(self._schedule_report_refresh)

        self.date_from = styled_date_edit(min_height=32)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(self._schedule_report_refresh)

        self.date_to = styled_date_edit(min_height=32)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self._schedule_report_refresh)

        self._report_refresh_timer = QTimer(self)
        self._report_refresh_timer.setSingleShot(True)
        self._report_refresh_timer.setInterval(350)
        self._report_refresh_timer.timeout.connect(self.preview_report_data)

        colors = ThemeManager.get_colors()
        btn_style = (
            "QPushButton { color: white; font-weight: bold; border-radius: 7px;"
            " padding: 4px 12px; border: none; min-height: 32px; font-size: 11px; }"
        )

        btn_daily_pdf = QPushButton("📄 Journalier")
        btn_daily_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_daily_pdf.setStyleSheet(
            btn_style + f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.WARNING}, stop:1 #D97706); }}"
        )
        btn_daily_pdf.clicked.connect(lambda: self.generate_pdf_report("daily"))

        btn_indiv_pdf = QPushButton("👤 Individuel")
        btn_indiv_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_indiv_pdf.setStyleSheet(
            btn_style + f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER}); }}"
            f" QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_indiv_pdf.clicked.connect(lambda: self.generate_pdf_report("individual"))

        btn_global_pdf = QPushButton("📊 Stats")
        btn_global_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_global_pdf.setStyleSheet(
            btn_style + f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.SECONDARY}, stop:1 #0284C7); }}"
        )
        btn_global_pdf.clicked.connect(lambda: self.generate_pdf_report("stats"))

        # Row 1: 4 combos — placeholder text replaces labels
        row1_rep = QHBoxLayout()
        row1_rep.setSpacing(8)
        row1_rep.addWidget(self.combo_class_report, 1)
        row1_rep.addWidget(self.combo_period_report, 1)
        row1_rep.addWidget(self.combo_student_report, 1)
        row1_rep.addWidget(self.combo_subject_report, 1)

        # Row 2: slot combo + date range + PDF buttons
        row2_rep = QHBoxLayout()
        row2_rep.setSpacing(8)
        row2_rep.addWidget(self.combo_slot_report, 2)
        lbl_du = QLabel("Du:")
        lbl_du.setStyleSheet("font-size:11px;")
        row2_rep.addWidget(lbl_du)
        row2_rep.addWidget(self.date_from, 1)
        lbl_arrow = QLabel("→")
        lbl_arrow.setStyleSheet("font-size:13px;")
        row2_rep.addWidget(lbl_arrow)
        row2_rep.addWidget(self.date_to, 1)
        row2_rep.addSpacing(8)
        row2_rep.addWidget(btn_daily_pdf)
        row2_rep.addWidget(btn_indiv_pdf)
        row2_rep.addWidget(btn_global_pdf)

        vlay_rep.addLayout(row1_rep)
        vlay_rep.addLayout(row2_rep)

        layout.addWidget(filter_card)

        layout.addWidget(QLabel("Aperçu Rapide / معاينة سريعة:"))
        self.table_report = QTableWidget()
        style_table(self.table_report)
        self.table_report.setColumnCount(7)
        self.table_report.setHorizontalHeaderLabels(["Date", "Heure", "Matière", "Élève", "Classe", "Statut", "Motif"])
        self.table_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_report)

        self.tabs.addTab(tab, "  📈 Rapports & Statistiques / التقارير  ")

    def _schedule_report_refresh(self):
        self._report_refresh_timer.start()

    # ---------------------------------------------------------
    # Logic: Data Loading
    # ---------------------------------------------------------
    def _load_kpi_stats(self):
        try:
            today_str = date.today().isoformat()
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'studentattendance'"
                )
                cols = {r[0].lower() for r in cursor.fetchall()}
                date_col = "attendance_date" if "attendance_date" in cols else "date"

                cursor.execute(
                    f"SELECT COUNT(*) FROM StudentAttendance WHERE {date_col} = %s AND LOWER(status) IN ('présent', 'present')",
                    (today_str,),
                )
                row = cursor.fetchone()
                present = row[0] if row else 0
                cursor.execute(
                    f"SELECT COUNT(*) FROM StudentAttendance WHERE {date_col} = %s AND LOWER(status) = 'absent'",
                    (today_str,),
                )
                row = cursor.fetchone()
                absent = row[0] if row else 0
                cursor.execute(
                    f"SELECT COUNT(*) FROM StudentAttendance WHERE {date_col} = %s AND (LOWER(status) LIKE '%retard%' OR LOWER(status) LIKE '%late%')",
                    (today_str,),
                )
                row = cursor.fetchone()
                late = row[0] if row else 0
                total = present + absent + late
                rate = f"{present * 100 // total}%" if total > 0 else "0%"
            self._stat_present.set_value(str(present))
            self._stat_absent.set_value(str(absent))
            self._stat_late.set_value(str(late))
            self._stat_rate.set_value(rate)
        except Exception as e:
            AppLogger.warning("StudentAttendance", f"KPI load error: {e}")
            self._stat_present.set_value("0")
            self._stat_absent.set_value("0")
            self._stat_late.set_value("0")
            self._stat_rate.set_value("0%")

    def load_classes(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                classes = AttendanceRepository(conn).list_classes()

            self.combo_class_entry.clear()
            self.combo_class_entry.addItem("Choisir une Classe...", None)

            self.combo_class_report.clear()
            self.combo_class_report.addItem("Toutes les classes", None)
            self.combo_period_report.clear()
            self.combo_period_report.addItem("Toutes les périodes", None)

            for c in classes:
                self.combo_class_entry.addItem(c[1], c[0])
                self.combo_class_report.addItem(c[1], c[0])
        except Exception as e:
            AppLogger.error("StudentAttendance", f"Error loading classes: {e}")

    # ===== تعديل مهم: جلب الطلاب من SCN بناءً على السنة النشطة =====
    def load_students_for_entry(self):
        class_id = self.combo_class_entry.currentData()
        date_sel = self.date_entry.date().toString("yyyy-MM-dd")
        time_sel = self.time_entry.time().toString("HH:mm") if hasattr(self, "time_entry") else ""
        self.table_entry.setRowCount(0)
        self.lbl_period_entry_auto.setText("Détectée automatiquement")
        self.lbl_slot_entry_auto.setText("Détectée automatiquement")

        if not class_id:
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            QMessageBox.warning(self, "Attention", "Aucune année scolaire active n'a été trouvée.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AttendanceRepository(conn)
                resolved_period_id, resolved_period_name = self.get_entry_period_context(
                    class_id, date_sel, active_year
                )
                self.lbl_period_entry_auto.setText(
                    resolved_period_name or "Aucune période ne couvre cette date / لا توجد فترة تغطي هذا التاريخ"
                )
                if not resolved_period_id:
                    return

                resolved_slot_id, resolved_slot_label = self.get_entry_slot_context(class_id, date_sel, time_sel)
                self.lbl_slot_entry_auto.setText(
                    resolved_slot_label or "Aucune séance programmée à cette heure / لا توجد حصة مبرمجة في هذا الوقت"
                )
                if not resolved_slot_id:
                    return

                rows = repo.load_students_for_attendance(
                    class_id,
                    date_sel,
                    active_year,
                    resolved_period_id,
                    resolved_slot_id,
                )

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
                if r[2]:
                    cmb_status.setCurrentText(r[2])
                cmb_status.setStyleSheet("QComboBox { border: none; background: transparent; }")
                self.table_entry.setCellWidget(idx, 2, cmb_status)

                # Justified Checkbox
                chk_widget = QWidget()
                chk_box = QCheckBox()
                if r[3] == 1:
                    chk_box.setChecked(True)
                chk_layout = QHBoxLayout(chk_widget)
                chk_layout.addWidget(chk_box)
                chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chk_layout.setContentsMargins(0, 0, 0, 0)
                self.table_entry.setCellWidget(idx, 3, chk_widget)

                # Reason & Notes
                self.table_entry.setItem(idx, 4, QTableWidgetItem(r[4] or ""))
                self.table_entry.setItem(idx, 5, QTableWidgetItem(r[5] or ""))

                # Action
                btn_reset = QPushButton("↺")
                btn_reset.setToolTip("Réinitialiser")
                colors = ThemeManager.get_colors()
                btn_reset.setStyleSheet(
                    f"""
                    QPushButton {{ background-color: {colors.TEXT_SECONDARY}; color: white; border-radius: 4px; font-weight: bold; border: none; }}
                    QPushButton:hover {{ background-color: {colors.TEXT_PRIMARY}; }}
                """
                )
                btn_reset.clicked.connect(lambda ch, row=idx: self.reset_row(row))
                self.table_entry.setCellWidget(idx, 6, btn_reset)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de chargement: {e}")

    def reset_row(self, row):
        self.table_entry.cellWidget(row, 2).setCurrentIndex(0)  # Présent
        self.table_entry.cellWidget(row, 3).findChild(QCheckBox).setChecked(False)
        self.table_entry.item(row, 4).setText("")
        self.table_entry.item(row, 5).setText("")

    def save_daily_attendance(self):
        class_id = self.combo_class_entry.currentData()
        date_sel = self.date_entry.date().toString("yyyy-MM-dd")
        time_sel = self.time_entry.time().toString("HH:mm") if hasattr(self, "time_entry") else ""

        if not class_id:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner une classe.")
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AttendanceRepository(conn)
                resolved_period_id, _ = self.get_entry_period_context(class_id, date_sel, active_year)
                if not resolved_period_id:
                    QMessageBox.warning(
                        self,
                        "Attention",
                        "Aucune période académique ne couvre cette date pour cette classe. / لا توجد فترة أكاديمية تغطي هذا التاريخ لهذا الفصل.",
                    )
                    return
                resolved_slot_id, resolved_slot_label = self.get_entry_slot_context(class_id, date_sel, time_sel)
                if not resolved_slot_id:
                    QMessageBox.warning(
                        self,
                        "Attention",
                        (
                            resolved_slot_label
                            or "Aucune séance programmée ne correspond à cette classe, cette date et cette heure. / لا توجد حصة مبرمجة تطابق هذا الفصل وهذا التاريخ وهذا الوقت."
                        ),
                    )
                    return
                for row in range(self.table_entry.rowCount()):
                    sid = int(self.table_entry.item(row, 0).text())
                    status = self.table_entry.cellWidget(row, 2).currentText()
                    is_justified = 1 if self.table_entry.cellWidget(row, 3).findChild(QCheckBox).isChecked() else 0
                    reason = self.table_entry.item(row, 4).text()
                    notes = self.table_entry.item(row, 5).text()
                    repo.upsert_attendance(
                        sid,
                        date_sel,
                        status,
                        is_justified,
                        reason,
                        notes,
                        active_year,
                        resolved_period_id,
                        resolved_slot_id,
                    )
                conn.commit()
            QMessageBox.information(
                self,
                "Succès",
                f"Données enregistrées avec succès pour {resolved_slot_label or 'la séance sélectionnée'}!",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ---------------------------------------------------------
    # Logic: Reports
    # ---------------------------------------------------------
    # ===== تعديل مهم: جلب الطلاب للقائمة المنسدلة للتقارير =====
    def load_students_for_report_combo(self):
        class_id = self.combo_class_report.currentData()
        self.combo_student_report.clear()
        self.combo_student_report.addItem("Tous les élèves", None)

        if not class_id:
            return
        active_year = self.get_active_year_id()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                for r in AttendanceRepository(conn).load_students_for_report_combo(class_id, active_year):
                    self.combo_student_report.addItem(r[1], r[0])
        except Exception as e:
            AppLogger.error("StudentAttendance", f"Error loading students for report: {e}")

    def preview_report_data(self):
        data = self.fetch_report_data()
        self.table_report.setRowCount(0)
        for r in data:
            idx = self.table_report.rowCount()
            self.table_report.insertRow(idx)
            self.table_report.setItem(idx, 0, QTableWidgetItem(str(r['date']) if r['date'] else ""))
            self.table_report.setItem(idx, 1, QTableWidgetItem(r['time_range']))
            self.table_report.setItem(idx, 2, QTableWidgetItem(r['subject']))
            self.table_report.setItem(idx, 3, QTableWidgetItem(r['name']))
            self.table_report.setItem(idx, 4, QTableWidgetItem(r['class']))

            # Color coding the status for visual clarity
            status_item = QTableWidgetItem(r['status'])
            if r['status'] == 'Absent':
                status_item.setForeground(QColor(239, 68, 68))  # Red
            elif r['status'] == 'Retard':
                status_item.setForeground(QColor(245, 158, 11))  # Orange
            self.table_report.setItem(idx, 5, status_item)

            motif = r['reason']
            if r['justifie']:
                motif += " (Justifié)"
            self.table_report.setItem(idx, 6, QTableWidgetItem(motif))

    # ===== تعديل مهم: تقرير الحضور يعتمد على SCN وليس S.class_id =====
    def fetch_report_data(self):
        cid = self.combo_class_report.currentData()
        pid = self.combo_period_report.currentData()
        subject_id = self.combo_subject_report.currentData() if hasattr(self, "combo_subject_report") else None
        slot_id = self.combo_slot_report.currentData() if hasattr(self, "combo_slot_report") else None
        sid = self.combo_student_report.currentData()
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to = self.date_to.date().toString("yyyy-MM-dd")
        active_year = self.get_active_year_id()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = AttendanceRepository(conn).fetch_report_data(
                    active_year,
                    d_from,
                    d_to,
                    class_id=cid,
                    student_id=sid,
                    period_id=pid,
                    subject_id=subject_id,
                    timetable_slot_id=slot_id,
                )

            def _format_time_range(start_time, end_time):
                if not start_time or not end_time:
                    return "Journalier"
                start_txt = str(start_time)[:5]
                end_txt = str(end_time)[:5]
                return f"{start_txt}-{end_txt}"

            return [
                {
                    'date': r[0],
                    'name': r[1],
                    'class': r[2],
                    'status': r[3],
                    'justifie': r[4],
                    'reason': r[5],
                    'time_range': _format_time_range(r[6], r[7]),
                    'subject': r[8] or 'Séance non précisée',
                }
                for r in rows
            ]
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la récupération des données: {e}")
            return []

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
        date_from_str = self.date_from.date().toString('yyyy-MM-dd')
        date_to_str = self.date_to.date().toString('yyyy-MM-dd')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        class_slug = self.sanitize_filename(
            self.combo_class_report.currentText() if hasattr(self, 'combo_class_report') else "Toutes_Classes"
        )
        student_name = self.combo_student_report.currentText() if hasattr(self, 'combo_student_report') else ""
        student_slug = self.sanitize_filename(student_name)

        if report_type == "daily":
            default_name = f"Rapport_Journalier_{class_slug}_{date_str}_{timestamp}.pdf"
        elif report_type == "individual":
            default_name = (
                f"Rapport_Individuel_{student_slug}_{date_from_str}_{date_to_str}_{timestamp}.pdf"
                if student_slug
                else f"Rapport_Individuel_{date_from_str}_{date_to_str}_{timestamp}.pdf"
            )
        elif report_type == "stats":
            default_name = f"Rapport_Statistique_{class_slug}_{date_from_str}_{date_to_str}_{timestamp}.pdf"
        else:
            default_name = f"Rapport_Attendance_{class_slug}_{date_from_str}_{date_to_str}_{timestamp}.pdf"

        school_info = None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                school_info = FinanceRepository(conn).get_school_info()
        except Exception:
            pass
        try:
            pdf = AttendancePDF(school_info)
            pdf.add_page()
            pdf.set_font(pdf.font_name, '', 10)

            title = ""
            if report_type == "daily":
                title = f"RAPPORT JOURNALIER ({self.date_to.date().toString('yyyy-MM-dd')})"
            elif report_type == "individual":
                title = "HISTORIQUE INDIVIDUEL D'ASSIDUITE"
            elif report_type == "stats":
                title = "RAPPORT STATISTIQUE"

            pdf.set_font(pdf.font_name, 'B', 12)
            pdf.cell(0, 10, pdf.sanitize(title), 0, 1, 'C')
            pdf.set_font(pdf.font_name, '', 10)
            pdf.cell(0, 10, pdf.sanitize(f"Periode: {self.date_from.text()} - {self.date_to.text()}"), 0, 1, 'C')
            pdf.ln(5)

            apply_table_header_style(pdf, pdf.font_name, 10)
            if report_type == "stats":
                pdf.cell(80, 10, "Eleve", 1, 0, 'C', True)
                pdf.cell(30, 10, "Absences", 1, 0, 'C', True)
                pdf.cell(30, 10, "Retards", 1, 0, 'C', True)
                pdf.cell(50, 10, "Taux Presence", 1, 1, 'C', True)

                stats = {}
                for row in data:
                    name = row['name']
                    if name not in stats:
                        stats[name] = {'abs': 0, 'late': 0, 'total': 0}
                    stats[name]['total'] += 1
                    if row['status'] == 'Absent':
                        stats[name]['abs'] += 1
                    if row['status'] == 'Retard':
                        stats[name]['late'] += 1

                apply_table_body_style(pdf, pdf.font_name, 10)
                for idx, (name, val) in enumerate(stats.items()):
                    rate = 100 - ((val['abs'] / val['total']) * 100) if val['total'] > 0 else 100
                    set_zebra_row_fill(pdf, idx)
                    pdf.cell(80, 10, self.sanitize_text(name), 1, 0, 'L', True)
                    pdf.cell(30, 10, str(val['abs']), 1, 0, 'C', True)
                    pdf.cell(30, 10, str(val['late']), 1, 0, 'C', True)
                    pdf.cell(50, 10, f"{rate:.1f}%", 1, 1, 'C', True)

            else:
                pdf.cell(30, 10, "Date", 1, 0, 'C', True)
                pdf.cell(30, 10, "Heure", 1, 0, 'C', True)
                pdf.cell(40, 10, "Matiere", 1, 0, 'C', True)
                pdf.cell(45, 10, "Eleve", 1, 0, 'C', True)
                pdf.cell(30, 10, "Statut", 1, 0, 'C', True)
                pdf.cell(45, 10, "Motif / Remarque", 1, 1, 'C', True)

                apply_table_body_style(pdf, pdf.font_name, 10)
                for idx, row in enumerate(data):
                    set_zebra_row_fill(pdf, idx)
                    pdf.cell(30, 10, str(row['date']), 1, 0, 'L', True)
                    pdf.cell(30, 10, self.sanitize_text(row['time_range']), 1, 0, 'C', True)
                    pdf.cell(40, 10, self.sanitize_text(row['subject']), 1, 0, 'L', True)
                    pdf.cell(45, 10, self.sanitize_text(row['name']), 1, 0, 'L', True)

                    status_txt = self.sanitize_text(row['status'])
                    if row['justifie']:
                        status_txt += " (J)"

                    pdf.cell(30, 10, status_txt, 1, 0, 'C', True)

                    motif = self.sanitize_text(row['reason']) if row['reason'] else "-"
                    pdf.cell(45, 10, motif, 1, 1, 'L', True)

            output_pdf(
                pdf,
                self,
                default_name,
                mode=ATTENDANCE_REPORT_OUTPUT_MODE,
                dialog_title="Sauvegarder PDF",
                success_save_message="Le fichier PDF a été généré.",
                success_print_message="Rapport envoyé à l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur PDF: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentAttendanceWindow()
    window.show()
    sys.exit(app.exec())
