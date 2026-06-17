import sys
from datetime import datetime

from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
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
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    get_school_info_row,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.staff_repo import StaffRepository
from ui_styles import ModuleHeaderWidget, ThemeManager, get_module_caps, get_tabs_style

STAFF_LEAVES_REPORT_OUTPUT_MODE = get_report_output_mode("staff_leaves_report_mode", "save")

from pdf_helpers import ARABIC_SUPPORT
from pdf_helpers import (
    contains_arabic as _contains_arabic,  # FIX 1: alias was `sanitize` but sanitize_text() called `_sanitize_latin(text)` —; NameError on every non-Arabic PDF cell, crashing all report exports.
)
from pdf_helpers import find_arabic_font_path as _get_arabic_font_path
from pdf_helpers import prepare_pdf_text as _prepare_pdf_text
from pdf_helpers import sanitize_latin as _sanitize_latin
from pdf_helpers import setup_pdf_arabic_font
from ui_components import (
    BaseDialog,
    card_frame,
    dialog_button_row,
    dialog_error_label,
    style_table,
    styled_combo,
    styled_date_edit,
    styled_text_edit,
)

# ---------------------------------------------------------------------------
# Dialog : Nouvelle Demande de Congé
# ---------------------------------------------------------------------------


class LeaveDialog(BaseDialog):
    def __init__(self, staff_items: list, parent=None):
        super().__init__("Nouvelle Demande de Congé / طلب إجازة جديد", parent)
        self.setMinimumWidth(480)
        self._staff_items = staff_items
        self._build_ui()

    def _build_ui(self):
        colors = ThemeManager.get_colors()

        self._err_lbl = dialog_error_label()
        self.add_widget(self._err_lbl)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.combo_staff = styled_combo()
        for name, staff_id in self._staff_items:
            self.combo_staff.addItem(name, staff_id)

        self.combo_type = styled_combo()
        self.combo_type.addItems(
            [
                "Maladie (مرضية)",
                "Annuel (سنوية)",
                "Sans Solde (بدون راتب)",
                "Maternité (أمومة)",
                "Urgence (طارئة)",
            ]
        )

        self.date_start = styled_date_edit()
        self.date_start.setDate(QDate.currentDate())

        self.date_end = styled_date_edit()
        self.date_end.setDate(QDate.currentDate())

        self.lbl_days = QLabel("⏱️ Durée: 1 jour(s)")
        self.lbl_days.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_days.setStyleSheet(
            f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN};"
            f" padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};"
        )

        self.date_start.dateChanged.connect(self._calculate_days)
        self.date_end.dateChanged.connect(self._calculate_days)

        self.txt_reason = styled_text_edit("Motif de l'absence / سبب الإجازة...")
        self.txt_reason.setMaximumHeight(90)

        form.addRow("Employé:", self.combo_staff)
        form.addRow("Type:", self.combo_type)
        form.addRow("Du:", self.date_start)
        form.addRow("Au:", self.date_end)
        self.dialog_layout.addLayout(form)
        self.add_widget(self.lbl_days)

        form2 = QFormLayout()
        form2.setSpacing(12)
        form2.addRow("Motif:", self.txt_reason)
        self.dialog_layout.addLayout(form2)

        self.dialog_layout.addLayout(dialog_button_row("✅ Enregistrer", self._validate, self.reject))

    def _calculate_days(self):
        colors = ThemeManager.get_colors()
        d1 = self.date_start.date()
        d2 = self.date_end.date()
        days = d1.daysTo(d2) + 1
        if days < 1:
            self.lbl_days.setText("Erreur: Date de fin invalide")
            self.lbl_days.setStyleSheet(
                f"color: {colors.DANGER}; font-weight: bold; background-color: {colors.BG_MAIN};"
                f" padding: 10px; border-radius: 6px; border: 1px solid {colors.DANGER};"
            )
        else:
            self.lbl_days.setText(f"⏱️ Durée: {days} jour(s)")
            self.lbl_days.setStyleSheet(
                f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN};"
                f" padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};"
            )

    def _validate(self):
        if not self.combo_staff.currentData():
            self._err_lbl.setText("Veuillez sélectionner un employé.")
            self._err_lbl.setVisible(True)
            return
        if self.date_start.date().daysTo(self.date_end.date()) + 1 < 1:
            self._err_lbl.setText("La date de fin doit être après la date de début.")
            self._err_lbl.setVisible(True)
            return
        self._err_lbl.setVisible(False)
        self.accept()

    def get_data(self) -> dict:
        return {
            "staff_id": self.combo_staff.currentData(),
            "leave_type": self.combo_type.currentText().split("(")[0].strip(),
            "date_start": self.date_start.date().toString("yyyy-MM-dd"),
            "date_end": self.date_end.date().toString("yyyy-MM-dd"),
            "days": self.date_start.date().daysTo(self.date_end.date()) + 1,
            "reason": self.txt_reason.toPlainText(),
        }


class StaffLeaveWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Congés / إدارة الإجازات")
        self.setMinimumSize(1100, 750)
        self.current_leave_report_rows = []
        self.current_leave_report_headers = []
        self.current_leave_report_title = ""
        self._staff_items: list = []

        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_staff()
        self.load_leaves()
        self._load_kpi_stats()

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "staff_leaves")
        self.btn_new_leave.setEnabled(caps["can_write"])
        self.btn_new_leave.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. En-tête unifié
        header = ModuleHeaderWidget(
            icon="🏖️",
            title="GESTION DES CONGÉS",
            subtitle="إدارة الإجازات والغيابات للموظفين",
        )
        self.main_layout.addWidget(header)
        self._stat_total = header.add_stat("📊", "Total Demandes", "—", "#3B82F6")
        self._stat_approved = header.add_stat("✅", "Approuvées", "—", "#22C55E")
        self._stat_pending = header.add_stat("⏳", "En Attente", "—", "#F59E0B")
        self._stat_refused = header.add_stat("❌", "Refusées", "—", "#EF4444")

        # 2. KPI Cards

        # 3. Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_history_tab()
        self.setup_reports_tab()

        self.main_layout.addWidget(self.tabs)

    def _load_kpi_stats(self):
        """Charge les statistiques des congés dans les KPI Cards."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Total demandes
                cursor.execute("SELECT COUNT(*) FROM StaffLeaves")
                total = cursor.fetchone()[0] or 0
                # Approuvées
                cursor.execute(
                    "SELECT COUNT(*) FROM StaffLeaves WHERE LOWER(status) IN ('approved', 'approuvé', 'approuve')"
                )
                approved = cursor.fetchone()[0] or 0
                # En attente
                cursor.execute(
                    "SELECT COUNT(*) FROM StaffLeaves WHERE LOWER(status) IN ('pending', 'en attente', 'attente')"
                )
                pending = cursor.fetchone()[0] or 0
                # Refusées
                cursor.execute(
                    "SELECT COUNT(*) FROM StaffLeaves WHERE LOWER(status) IN ('refused', 'rejected', 'refusé', 'refuse')"
                )
                refused = cursor.fetchone()[0] or 0

            self._stat_total.set_value(str(total))
            self._stat_approved.set_value(str(approved))
            self._stat_pending.set_value(str(pending))
            self._stat_refused.set_value(str(refused))
        except Exception as e:
            AppLogger.error("StaffLeaveWindow", f"Erreur KPI stats: {e}")

    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        colors = ThemeManager.get_colors()

        self.btn_new_leave = QPushButton("➕ Nouvelle Demande / طلب جديد")
        self.btn_new_leave.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_leave.setFixedHeight(32)
        self.btn_new_leave.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.SUCCESS}, stop:1 #16A34A);"
            f" color: white; font-weight: bold; font-size:11px;"
            f" padding: 4px 14px; border-radius: 7px; border: none; }}"
            f"QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
        self.btn_new_leave.clicked.connect(self._open_leave_dialog)

        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedHeight(32)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER});"
            f" color: white; font-weight: bold; font-size:11px;"
            f" padding: 4px 12px; border-radius: 7px; border: none; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_refresh.clicked.connect(self.load_leaves)

        toolbar.addStretch()
        toolbar.addWidget(self.btn_new_leave)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        self.table_leaves = QTableWidget()
        style_table(self.table_leaves)
        self.table_leaves.setColumnCount(8)
        self.table_leaves.setHorizontalHeaderLabels(
            ["ID", "Employé", "Type", "Début", "Fin", "Jours", "Statut", "Action"]
        )
        self.table_leaves.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_leaves.setColumnWidth(0, 50)
        self.table_leaves.setColumnWidth(7, 260)

        layout.addWidget(self.table_leaves)
        self.tabs.addTab(tab, "  📋 Historique & Validation / السجل  ")

    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        controls_card = card_frame()
        hlay_rep = QHBoxLayout(controls_card)
        hlay_rep.setContentsMargins(12, 10, 12, 10)
        hlay_rep.setSpacing(8)

        self.combo_leave_report_type = styled_combo(min_height=32)
        self.combo_leave_report_type.addItem("Synthèse par employé", "summary")
        self.combo_leave_report_type.addItem("Détails des demandes", "details")

        self.report_leave_from = styled_date_edit(min_height=32)
        self.report_leave_to = styled_date_edit(min_height=32)
        self.report_leave_from.setDate(QDate.currentDate().addMonths(-1))
        self.report_leave_to.setDate(QDate.currentDate())

        colors = ThemeManager.get_colors()

        btn_generate = QPushButton("📊 Générer")
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generate.setFixedHeight(32)
        btn_generate.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER});"
            f" color: white; font-weight: bold; border-radius: 7px;"
            f" border: none; padding: 4px 12px; font-size:11px; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_generate.clicked.connect(self.run_leave_report)

        btn_export = QPushButton("🖨 PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setFixedHeight(32)
        btn_export.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.SUCCESS}, stop:1 #16A34A);"
            f" color: white; font-weight: bold; border-radius: 7px;"
            f" border: none; padding: 4px 12px; font-size:11px; }}"
            f"QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
        btn_export.clicked.connect(self.export_leave_report_pdf)

        hlay_rep.addWidget(self.combo_leave_report_type, 2)
        lbl_du_r = QLabel("Du:")
        lbl_du_r.setStyleSheet("font-size:11px;")
        hlay_rep.addWidget(lbl_du_r)
        hlay_rep.addWidget(self.report_leave_from, 1)
        lbl_arrow_r = QLabel("→")
        lbl_arrow_r.setStyleSheet("font-size:13px;")
        hlay_rep.addWidget(lbl_arrow_r)
        hlay_rep.addWidget(self.report_leave_to, 1)
        hlay_rep.addSpacing(8)
        hlay_rep.addWidget(btn_generate)
        hlay_rep.addWidget(btn_export)

        self.table_leave_reports = QTableWidget(0, 1)
        style_table(self.table_leave_reports)
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
            self._staff_items = [(row[1] or "-", row[0]) for row in rows]
        except Exception as e:
            AppLogger.error("StaffLeaves", f"Error loading staff: {e}")

    def _open_leave_dialog(self):
        dlg = LeaveDialog(staff_items=self._staff_items, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._save_leave(dlg.get_data())

    def _save_leave(self, data: dict):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                repo.insert_leave(
                    data["staff_id"],
                    data["leave_type"],
                    data["date_start"],
                    data["date_end"],
                    data["days"],
                    data["reason"],
                )
                conn.commit()
            QMessageBox.information(self, "Succès", "Demande de congé enregistrée.")
            self.load_leaves()
            self._load_kpi_stats()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {e}")

    def load_leaves(self):
        self.table_leaves.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = StaffRepository(conn).list_leaves()

            colors = ThemeManager.get_colors()

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
                    btn_ok.setStyleSheet(
                        f"background-color: {colors.SUCCESS}; color: white; border-radius: 4px; font-weight: bold; border: none;"
                    )
                    btn_ok.clicked.connect(lambda ch, lid=r[0]: self.update_status(lid, "Approuvé"))

                    btn_no = QPushButton("✘")
                    btn_no.setFixedSize(30, 25)
                    btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_no.setToolTip("Rejeter")
                    btn_no.setStyleSheet(
                        f"background-color: {colors.DANGER}; color: white; border-radius: 4px; font-weight: bold; border: none;"
                    )
                    btn_no.clicked.connect(lambda ch, lid=r[0]: self.update_status(lid, "Rejeté"))

                    btn_layout.addWidget(btn_ok)
                    btn_layout.addWidget(btn_no)

                btn_report = QPushButton("📄")
                btn_report.setFixedSize(30, 25)
                btn_report.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_report.setToolTip("Rapport Demande")
                btn_report.setStyleSheet(
                    f"background-color: {colors.PRIMARY}; color: white; border-radius: 4px; font-weight: bold; border: none;"
                )
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
                        rows.append(
                            [
                                staff_name or "-",
                                int(requests_count or 0),
                                int(approved_days or 0),
                                int(pending_days or 0),
                                int(rejected_days or 0),
                            ]
                        )
                else:
                    title = "Rapport Détail des Demandes de Congés"
                    headers = ["Employé", "Type", "Début", "Fin", "Jours", "Statut", "Motif"]
                    for row in repo.get_leaves_detail_report(date_from, date_to):
                        staff_name, leave_type, start_date, end_date, days_count, status, reason = row
                        rows.append(
                            [
                                staff_name or "-",
                                leave_type or "-",
                                start_date or "-",
                                end_date or "-",
                                int(days_count or 0),
                                status or "-",
                                reason or "",
                            ]
                        )

            self.current_leave_report_title = title
            self.current_leave_report_headers = headers
            self.current_leave_report_rows = rows

            self.table_leave_reports.setColumnCount(len(headers) if headers else 1)
            self.table_leave_reports.setHorizontalHeaderLabels(headers or ["Données"])
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

        font_to_use = "ArabicFont" if setup_pdf_arabic_font(pdf) else "Arial"

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
            font_to_use = "ArabicFont" if setup_pdf_arabic_font(pdf) else "Arial"
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
