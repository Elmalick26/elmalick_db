import sys
import psycopg2
import os
from datetime import datetime
from database_setup import DatabaseManager
from app_logger import AppLogger
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QComboBox, QMessageBox,
                             QHeaderView, QGroupBox, QDateEdit, QTextEdit,
                             QTabWidget, QFrame, QGraphicsDropShadowEffect, QGridLayout)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_grades_sheet_header, apply_table_header_style, apply_table_body_style, set_zebra_row_fill, get_school_info_row

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style
from repositories.staff_repo import StaffRepository

THEME_AVAILABLE = True
STAFF_LEAVES_REPORT_OUTPUT_MODE = get_report_output_mode("staff_leaves_report_mode", "save")

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


class StaffLeaveWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Congés / إدارة الإجازات")
        self.setMinimumSize(1100, 750)
        self.current_leave_report_rows = []
        self.current_leave_report_headers = []
        self.current_leave_report_title = ""

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
        self.load_staff()
        self.load_leaves()

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
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)

        icon_lbl = QLabel("🏖️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DES CONGÉS")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("إدارة الإجازات والغيابات للموظفين")
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

        self.setup_request_tab()
        self.setup_history_tab()
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
        de.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        return de

    def styled_combo(self):
        combo = QComboBox()
        combo.setMinimumHeight(38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        return combo

    def styled_text_edit(self, placeholder=""):
        text_edit = QTextEdit()
        if placeholder:
            text_edit.setPlaceholderText(placeholder)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        text_edit.setStyleSheet(f"QTextEdit {{ padding: 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        return text_edit

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
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; }}
                QTableWidget::item:alternate {{ background-color: {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
            """)

    def setup_request_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        form_card = self.create_card()
        flay = QGridLayout(form_card)
        flay.setSpacing(15)
        flay.setContentsMargins(20, 20, 20, 20)

        card_title = QLabel("📝 Nouvelle Demande / طلب جديد")
        card_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        flay.addWidget(card_title, 0, 0, 1, 4)

        self.combo_staff = self.styled_combo()
        self.combo_type = self.styled_combo()
        self.combo_type.addItems(["Maladie (مرضية)", "Annuel (سنوية)", "Sans Solde (بدون راتب)", "Maternité (أمومة)", "Urgence (طارئة)"])

        flay.addWidget(QLabel("Employé:"), 1, 0)
        flay.addWidget(self.combo_staff, 1, 1)
        flay.addWidget(QLabel("Type:"), 1, 2)
        flay.addWidget(self.combo_type, 1, 3)

        self.date_start = self.styled_date()
        self.date_start.setDate(QDate.currentDate())

        self.date_end = self.styled_date()
        self.date_end.setDate(QDate.currentDate())

        self.lbl_days = QLabel("⏱️ Durée: 1 jour(s)")
        self.lbl_days.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};")
        self.lbl_days.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.date_start.dateChanged.connect(self.calculate_days)
        self.date_end.dateChanged.connect(self.calculate_days)

        flay.addWidget(QLabel("Du:"), 2, 0)
        flay.addWidget(self.date_start, 2, 1)
        flay.addWidget(QLabel("Au:"), 2, 2)
        flay.addWidget(self.date_end, 2, 3)

        flay.addWidget(self.lbl_days, 3, 0, 1, 4)

        self.txt_reason = self.styled_text_edit("Motif de l'absence / سبب الإجازة...")
        self.txt_reason.setMaximumHeight(100)

        flay.addWidget(QLabel("Motif:"), 4, 0)
        flay.addWidget(self.txt_reason, 4, 1, 1, 3)

        btn_save = QPushButton("✅ Enregistrer la Demande / حفظ الطلب")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setMinimumHeight(45)
        btn_save.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; border: none; font-size: 14px; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_save.clicked.connect(self.save_leave)

        flay.addWidget(btn_save, 5, 0, 1, 4)

        layout.addWidget(form_card)
        layout.addStretch()
        self.tabs.addTab(tab, "  ➕ Nouvelle Demande / طلب جديد  ")

    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        toolbar = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_refresh.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 8px 15px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_refresh.clicked.connect(self.load_leaves)

        toolbar.addWidget(QLabel("Historique des Demandes / سجل الطلبات"))
        toolbar.addStretch()
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        self.table_leaves = QTableWidget()
        self.style_table(self.table_leaves)
        self.table_leaves.setColumnCount(8)
        self.table_leaves.setHorizontalHeaderLabels(["ID", "Employé", "Type", "Début", "Fin", "Jours", "Statut", "Action"])
        self.table_leaves.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_leaves.setColumnWidth(0, 50)
        self.table_leaves.setColumnWidth(7, 260)

        layout.addWidget(self.table_leaves)
        self.tabs.addTab(tab, "  📋 Historique & Validation / السجل  ")

    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        controls_card = self.create_card()
        controls = QGridLayout(controls_card)
        controls.setContentsMargins(20, 20, 20, 20)
        controls.setSpacing(12)

        self.combo_leave_report_type = self.styled_combo()
        self.combo_leave_report_type.addItem("Synthèse par employé", "summary")
        self.combo_leave_report_type.addItem("Détails des demandes", "details")

        self.report_leave_from = self.styled_date()
        self.report_leave_to = self.styled_date()
        self.report_leave_from.setDate(QDate.currentDate().addMonths(-1))
        self.report_leave_to.setDate(QDate.currentDate())

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        btn_generate = QPushButton("Générer Rapport")
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generate.setMinimumHeight(40)
        btn_generate.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_generate.clicked.connect(self.run_leave_report)

        btn_export = QPushButton("Exporter PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(40)
        btn_export.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 6px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_export.clicked.connect(self.export_leave_report_pdf)

        controls.addWidget(QLabel("Type Rapport:"), 0, 0)
        controls.addWidget(self.combo_leave_report_type, 0, 1)
        controls.addWidget(QLabel("Du:"), 0, 2)
        controls.addWidget(self.report_leave_from, 0, 3)
        controls.addWidget(QLabel("Au:"), 0, 4)
        controls.addWidget(self.report_leave_to, 0, 5)
        controls.addWidget(btn_generate, 1, 4)
        controls.addWidget(btn_export, 1, 5)

        self.table_leave_reports = QTableWidget(0, 1)
        self.style_table(self.table_leave_reports)
        self.table_leave_reports.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(controls_card)
        layout.addWidget(self.table_leave_reports)
        self.tabs.addTab(tab, "  📊 Rapports Congés / التقارير  ")

    # ---------------------------------------------------------
    # Logic methods
    # ---------------------------------------------------------
    def sanitize_text(self, text):
        if not text:
            return ""
        if _contains_arabic(text) and ARABIC_SUPPORT and _get_arabic_font_path():
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def load_staff(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = StaffRepository(conn).list_active_staff_fullname()
            self.combo_staff.clear()
            for row in rows:
                self.combo_staff.addItem(row[1] or "-", row[0])
        except Exception as e:
            AppLogger.error("StaffLeaves", f"Error loading staff: {e}")

    def calculate_days(self):
        d1 = self.date_start.date()
        d2 = self.date_end.date()
        days = d1.daysTo(d2) + 1
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        if days < 1:
            self.lbl_days.setText("Erreur: Date invalide")
            self.lbl_days.setStyleSheet(f"color: {colors.DANGER}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.DANGER};")
        else:
            self.lbl_days.setText(f"Durée: {days} jour(s)")
            self.lbl_days.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};")

    def save_leave(self):
        staff_id = self.combo_staff.currentData()
        l_type = self.combo_type.currentText().split("(")[0].strip()
        d1 = self.date_start.date()
        d2 = self.date_end.date()
        days = d1.daysTo(d2) + 1
        reason = self.txt_reason.toPlainText()

        if days < 1:
            QMessageBox.warning(self, "Erreur", "La date de fin doit être après la date de début.")
            return
        if not staff_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un employé.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                repo.insert_leave(
                    staff_id, l_type,
                    d1.toString("yyyy-MM-dd"), d2.toString("yyyy-MM-dd"),
                    days, reason
                )
                conn.commit()

            QMessageBox.information(self, "Succès", "Demande de congé enregistrée.")
            self.txt_reason.clear()
            self.load_leaves()
            self.tabs.setCurrentIndex(1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {e}")

    def load_leaves(self):
        self.table_leaves.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = StaffRepository(conn).list_leaves()

            colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

            for r in rows:
                idx = self.table_leaves.rowCount()
                self.table_leaves.insertRow(idx)

                for i in range(7):
                    item = QTableWidgetItem(str(r[i] if r[i] is not None else "-"))
                    if i == 6:  # Status
                        if r[i] == 'Approuvé':
                            item.setForeground(QColor(colors.SUCCESS))
                            item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                        elif r[i] == 'Rejeté':
                            item.setForeground(QColor(colors.DANGER))
                            item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                        else:
                            item.setForeground(QColor(colors.WARNING))
                            item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.table_leaves.setItem(idx, i, item)

                # Action Buttons
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(5)

                if r[6] == 'En Attente':
                    btn_ok = QPushButton("✔")
                    btn_ok.setFixedSize(30, 25)
                    btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_ok.setToolTip("Approuver")
                    btn_ok.setStyleSheet(f"background-color: {colors.SUCCESS}; color: white; border-radius: 4px; font-weight: bold; border: none;")
                    btn_ok.clicked.connect(lambda ch, lid=r[0]: self.update_status(lid, "Approuvé"))

                    btn_no = QPushButton("✘")
                    btn_no.setFixedSize(30, 25)
                    btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_no.setToolTip("Rejeter")
                    btn_no.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 4px; font-weight: bold; border: none;")
                    btn_no.clicked.connect(lambda ch, lid=r[0]: self.update_status(lid, "Rejeté"))

                    btn_layout.addWidget(btn_ok)
                    btn_layout.addWidget(btn_no)

                btn_report = QPushButton("📄")
                btn_report.setFixedSize(30, 25)
                btn_report.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_report.setToolTip("Rapport Demande")
                btn_report.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; border-radius: 4px; font-weight: bold; border: none;")
                btn_report.clicked.connect(lambda ch, lid=r[0]: self.export_leave_request_pdf(lid))

                btn_layout.addWidget(btn_report)
                btn_layout.addStretch()
                self.table_leaves.setCellWidget(idx, 7, btn_widget)
        except Exception as e:
            AppLogger.error("StaffLeaves", f"Error loading leaves history: {e}")

    def update_status(self, leave_id, new_status):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                StaffRepository(conn).update_leave_status(leave_id, new_status)
                conn.commit()
            self.load_leaves()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la mise à jour: {e}")

    def run_leave_report(self):
        report_kind = self.combo_leave_report_type.currentData() or "summary"
        date_from = self.report_leave_from.date().toString("yyyy-MM-dd")
        date_to = self.report_leave_to.date().toString("yyyy-MM-dd")

        headers = []
        rows = []
        title = ""

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)

                if report_kind == "summary":
                    title = "Rapport Synthèse des Congés par Employé"
                    headers = ["Employé", "Demandes", "Jours Approuvés", "Jours En Attente", "Jours Rejetés"]
                    for row in repo.get_leaves_summary_report(date_from, date_to):
                        staff_name, requests_count, approved_days, pending_days, rejected_days = row
                        rows.append([
                            staff_name or "-",
                            int(requests_count or 0),
                            int(approved_days or 0),
                            int(pending_days or 0),
                            int(rejected_days or 0),
                        ])
                else:
                    title = "Rapport Détail des Demandes de Congés"
                    headers = ["Employé", "Type", "Début", "Fin", "Jours", "Statut", "Motif"]
                    for row in repo.get_leaves_detail_report(date_from, date_to):
                        staff_name, leave_type, start_date, end_date, days_count, status, reason = row
                        rows.append([
                            staff_name or "-",
                            leave_type or "-",
                            start_date or "-",
                            end_date or "-",
                            int(days_count or 0),
                            status or "-",
                            reason or "",
                        ])

            self.current_leave_report_title = title
            self.current_leave_report_headers = headers
            self.current_leave_report_rows = rows

            self.table_leave_reports.setColumnCount(len(headers) if headers else 1)
            self.table_leave_reports.setHorizontalHeaderLabels(headers if headers else ["Données"])
            self.table_leave_reports.setRowCount(0)

            for row_values in rows:
                row_idx = self.table_leave_reports.rowCount()
                self.table_leave_reports.insertRow(row_idx)
                for col_idx, value in enumerate(row_values):
                    self.table_leave_reports.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

            if not rows:
                QMessageBox.information(self, "Information", "Aucune donnée trouvée pour cette période.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de rapport: {e}")

    def export_leave_report_pdf(self):
        if not self.current_leave_report_rows:
            QMessageBox.warning(self, "Attention", "Générez d'abord un rapport avec des données.")
            return

        orientation = 'L' if len(self.current_leave_report_headers) >= 6 else 'P'
        pdf = FPDF(orientation=orientation)
        pdf.add_page()

        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, self.current_leave_report_title)

        period_line = (
            f"Période: {self.report_leave_from.date().toString('dd/MM/yyyy')} "
            f"- {self.report_leave_to.date().toString('dd/MM/yyyy')}"
        )
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 7, self.sanitize_text(period_line), 0, 1, 'C')
        pdf.ln(2)

        table_width = pdf.w - 20
        col_width = table_width / max(1, len(self.current_leave_report_headers))

        font_to_use = "ArabicFont" if _register_arabic_font(pdf) else "Arial"

        apply_table_header_style(pdf, font_to_use, 9)
        for header in self.current_leave_report_headers:
            pdf.cell(col_width, 8, self.sanitize_text(header), 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, font_to_use, 8)
        for row_idx, row_values in enumerate(self.current_leave_report_rows):
            set_zebra_row_fill(pdf, row_idx)
            for value in row_values:
                pdf.cell(col_width, 7, self.sanitize_text(str(value)), 1, 0, 'C', True)
            pdf.ln()

        mode = get_report_output_mode("staff_leaves_report_mode", STAFF_LEAVES_REPORT_OUTPUT_MODE)
        output_pdf(
            pdf,
            self,
            default_name=f"Rapport_Conges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=mode,
            dialog_title="Exporter Rapport Congés",
            success_save_message="Rapport des congés exporté.",
            success_print_message="Rapport des congés envoyé à l'imprimante.",
        )

    def export_leave_request_pdf(self, leave_id):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                row = StaffRepository(conn).get_leave_request_by_id(leave_id)

            if not row:
                QMessageBox.warning(self, "Erreur", "Demande introuvable.")
                return

            request_id, staff_name, leave_type, start_date, end_date, days_count, status, reason = row

            preview_text = (
                f"Demande N°: {request_id}\n"
                f"Employé: {staff_name}\n"
                f"Type: {leave_type}\n"
                f"Période: {start_date} -> {end_date}\n"
                f"Durée: {int(days_count or 0)} jour(s)\n"
                f"Statut: {status}\n\n"
                f"Continuer vers l'export/print ?"
            )
            proceed = QMessageBox.question(
                self,
                "Aperçu Rapide",
                preview_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

            pdf = FPDF()
            font_to_use = "ArabicFont" if _register_arabic_font(pdf) else "Arial"
            pdf.add_page()

            school_info = get_school_info_row()
            apply_grades_sheet_header(pdf, school_info, "RAPPORT DEMANDE DE CONGE")

            apply_table_header_style(pdf, font_to_use, 10)
            pdf.cell(0, 8, self.sanitize_text(f"Demande N° {request_id}"), 1, 1, 'L', True)

            apply_table_body_style(pdf, font_to_use, 10)
            details = [
                ("Employé", staff_name),
                ("Type de congé", leave_type),
                ("Date début", start_date),
                ("Date fin", end_date),
                ("Durée", f"{int(days_count or 0)} jour(s)"),
                ("Statut", status),
            ]

            for idx, (label, value) in enumerate(details):
                set_zebra_row_fill(pdf, idx)
                pdf.cell(70, 8, self.sanitize_text(str(label)), 1, 0, 'L', True)
                pdf.cell(120, 8, self.sanitize_text(str(value)), 1, 1, 'L', True)

            pdf.ln(4)
            apply_table_header_style(pdf, font_to_use, 10)
            pdf.cell(0, 8, self.sanitize_text("Motif"), 1, 1, 'L', True)

            apply_table_body_style(pdf, font_to_use, 10)
            clean_reason = self.sanitize_text(reason or "-")
            pdf.multi_cell(0, 8, clean_reason, 1, 'L')

            if pdf.get_y() > 235:
                pdf.add_page()
                apply_grades_sheet_header(pdf, school_info, "RAPPORT DEMANDE DE CONGE")

            left_x = 12
            right_x = 112
            y = pdf.get_y()

            y_line = y + 18
            pdf.line(left_x, y_line, left_x + 78, y_line)
            pdf.line(right_x, y_line, right_x + 78, y_line)

            pdf.set_xy(left_x, y_line + 2)
            pdf.set_font(font_to_use, '', 9)
            pdf.cell(80, 6, self.sanitize_text("Employé"), 0, 0, 'C')
            pdf.set_xy(right_x, y_line + 2)
            pdf.cell(80, 6, self.sanitize_text("Administration"), 0, 1, 'C')

            mode = get_report_output_mode("staff_leaves_report_mode", STAFF_LEAVES_REPORT_OUTPUT_MODE)
            output_pdf(
                pdf,
                self,
                default_name=f"Demande_Conge_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mode=mode,
                dialog_title="Exporter Demande Congé",
                success_save_message="Rapport de la demande exporté.",
                success_print_message="Rapport de la demande envoyé à l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Échec de l'export: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StaffLeaveWindow()
    window.show()
    sys.exit(app.exec())
