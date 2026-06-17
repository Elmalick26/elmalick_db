import sys
from datetime import datetime

from fpdf import FPDF
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from error_codes import DB_QUERY, DB_TRANSACTION, IO_EXPORT, log_op_error, new_op_id
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    get_school_info_row,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.finance_repo import FinanceRepository
from ui_components import BaseWindow, card_frame, style_table, styled_button, styled_combo, styled_spinbox
from ui_styles import ModuleHeaderWidget, ThemeManager, get_module_caps, get_tabs_style

FEES_REPORT_OUTPUT_MODE = get_report_output_mode("fees_report_mode", "save")


class FeesSetupWindow(BaseWindow):
    def __init__(self):
        super().__init__(title="Configuration Financière / الإعداد المالي", min_width=1100, min_height=700)
        self.current_fees_report_rows = []
        self.current_fees_report_headers = []
        self.current_fees_report_title = ""

        self.init_ui()
        self.load_classes()
        self._load_kpi_stats()

    def get_active_year_id(self):
        """جلب معرف السنة الدراسية النشطة حالياً لاستخدامه في التقارير"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return FinanceRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "fees_setup")
        self.btn_save_reg.setEnabled(caps["can_write"])
        self.btn_save_reg.setVisible(caps["can_write"])
        self.btn_save_schedule.setEnabled(caps["can_write"])
        self.btn_save_schedule.setVisible(caps["can_write"])

    def init_ui(self):
        # 1. En-tête unifié
        header = ModuleHeaderWidget(
            icon="⚙️",
            title="CONFIGURATION FINANCIÈRE",
            subtitle="إعداد رسوم التسجيل وجدولة الأقساط الشهرية",
        )
        self.main_layout.addWidget(header)
        self._stat_classes = header.add_stat("🏫", "Classes Config", "—", "#3B82F6")
        self._stat_fees = header.add_stat("💰", "Types de Frais", "—", "#22C55E")
        self._stat_total_month = header.add_stat("📅", "Total Mensualité", "—", "#8B5CF6")
        self._stat_total_reg = header.add_stat("📝", "Frais Inscription", "—", "#F59E0B")

        # 2. KPI Cards

        # 3. Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_registration_tab()
        self.setup_monthly_tab()
        self.setup_reports_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        return card_frame()

    def _load_kpi_stats(self):
        """Charge les statistiques de configuration financière."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Classes configurées
                cursor.execute("SELECT COUNT(*) FROM Classes")
                classes = cursor.fetchone()[0] or 0
                # Types de frais (fallback cross-schema: fee_type when present, otherwise count rows)
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'registrationfees'"
                )
                reg_cols = {r[0].lower() for r in cursor.fetchall()}
                if "fee_type" in reg_cols:
                    cursor.execute("SELECT COUNT(DISTINCT fee_type) FROM RegistrationFees")
                else:
                    cursor.execute("SELECT COUNT(*) FROM RegistrationFees")
                fee_types = cursor.fetchone()[0] or 0

                # Total mensualité moyenne (MonthlyFeeSchedule is the active table in current schema)
                cursor.execute("SELECT to_regclass('public.monthlyfeeschedule')")
                has_schedule = cursor.fetchone()[0] is not None
                if has_schedule:
                    cursor.execute("SELECT COALESCE(AVG(amount), 0) FROM MonthlyFeeSchedule")
                    avg_monthly = cursor.fetchone()[0] or 0
                else:
                    avg_monthly = 0

                # Total frais d'inscription moyen
                cursor.execute("SELECT AVG(amount) FROM RegistrationFees")
                avg_reg_row = cursor.fetchone()
                avg_reg = avg_reg_row[0] if avg_reg_row and avg_reg_row[0] else 0

            self._stat_classes.set_value(str(classes))
            self._stat_fees.set_value(str(fee_types))
            self._stat_total_month.set_value(f"{avg_monthly:,.0f} F")
            self._stat_total_reg.set_value(f"{avg_reg:,.0f} F")
        except Exception as e:
            AppLogger.error("FeesSetupWindow", f"Erreur KPI stats: {e}")

    # ============================================
    # TAB 1: REGISTRATION FEES
    # ============================================
    def setup_registration_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        reg_card = self.create_card()
        hlay = QHBoxLayout(reg_card)
        hlay.setContentsMargins(20, 20, 20, 20)
        hlay.setSpacing(15)

        self.combo_class_reg = styled_combo()
        self.spin_reg_amount = styled_spinbox()

        self.btn_save_reg = styled_button("Enregistrer")
        self.btn_save_reg.clicked.connect(self.save_registration_fee)

        hlay.addWidget(QLabel("Classe:"))
        hlay.addWidget(self.combo_class_reg, 1)
        hlay.addWidget(QLabel("Montant:"))
        hlay.addWidget(self.spin_reg_amount, 1)
        hlay.addWidget(self.btn_save_reg)

        layout.addWidget(reg_card)

        self.table_reg = QTableWidget(0, 2)
        style_table(self.table_reg)
        self.table_reg.setHorizontalHeaderLabels(["Classe / الفصل", "Montant Inscription / مبلغ التسجيل"])
        self.table_reg.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_reg)

        self.tabs.addTab(tab, "  📝 Inscription / التسجيل  ")

    # ============================================
    # TAB 2: MONTHLY FEE SCHEDULE
    # ============================================
    def setup_monthly_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        sel_card = self.create_card()
        slay = QHBoxLayout(sel_card)
        slay.setContentsMargins(20, 20, 20, 20)

        self.combo_class_month = styled_combo()
        self.combo_class_month.currentIndexChanged.connect(self.load_monthly_schedule)

        slay.addWidget(QLabel("Configurer pour la classe:"))
        slay.addWidget(self.combo_class_month, 1)
        layout.addWidget(sel_card)

        tool_frame = QFrame()
        colors = ThemeManager.get_colors()
        tool_frame.setStyleSheet(
            f"""
            QFrame {{ background-color: {colors.BG_CARD}; border: 1px dashed {colors.SUCCESS}; border-radius: 8px; }}
            QLabel {{ color: {colors.TEXT_PRIMARY}; font-weight: bold; }}
        """
        )
        tool_layout = QVBoxLayout(tool_frame)

        tool_header = QLabel("⚡ Outil de Calcul Rapide / أداة الحساب السريع")
        tool_layout.addWidget(tool_header)

        tlay = QHBoxLayout()
        self.spin_base_price = styled_spinbox()
        self.spin_base_price.setValue(5000)
        self.spin_base_price.setStyleSheet(
            f"""
            QDoubleSpinBox {{ background: {colors.INPUT_BG}; border: 1px solid {colors.SUCCESS}; border-radius: 4px; padding: 5px; color: {colors.TEXT_PRIMARY}; }}
            QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """
        )

        btn_apply_smart = styled_button(
            "Répartition 4+4 (Smart)",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=40,
        )
        btn_apply_smart.clicked.connect(self.apply_smart_distribution)

        btn_apply_flat = styled_button(
            "Prix Unique (Flat)",
            bg_color=colors.PRIMARY,
            hover_color=colors.PRIMARY_HOVER,
            min_height=40,
        )
        btn_apply_flat.clicked.connect(self.apply_flat_distribution)

        tlay.addWidget(QLabel("Prix de base:"))
        tlay.addWidget(self.spin_base_price)
        tlay.addWidget(btn_apply_smart)
        tlay.addWidget(btn_apply_flat)
        tool_layout.addLayout(tlay)

        layout.addWidget(tool_frame)

        self.table_months = QTableWidget(9, 2)
        style_table(self.table_months)
        self.table_months.setHorizontalHeaderLabels(["Mois / الشهر", "Montant à Payer (FCFA)"])
        self.table_months.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_months.verticalHeader().setDefaultSectionSize(40)

        self.academic_months = [
            (10, "Octobre / أكتوبر"),
            (11, "Novembre / نوفمبر"),
            (12, "Décembre / ديسمبر"),
            (1, "Janvier / يناير"),
            (2, "Février / فبراير"),
            (3, "Mars / مارس"),
            (4, "Avril / أبريل"),
            (5, "Mai / مايو"),
            (6, "Juin / يونيو"),
        ]

        for i, (idx, name) in enumerate(self.academic_months):
            self.table_months.setItem(i, 0, QTableWidgetItem(name))
            sp = QDoubleSpinBox()
            sp.setRange(0, 100000)
            sp.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            sp.setStyleSheet(f"background: transparent; border: none; font-weight: bold; color: {colors.TEXT_PRIMARY};")
            self.table_months.setCellWidget(i, 1, sp)

        layout.addWidget(self.table_months)

        self.btn_save_schedule = styled_button(
            "💾 ENREGISTRER L'ÉCHÉANCIER",
            bg_color=colors.BG_HEADER,
            text_color=colors.HEADER_TEXT,
            hover_color=colors.BORDER,
            min_height=50,
        )
        self.btn_save_schedule.clicked.connect(self.save_monthly_schedule)
        layout.addWidget(self.btn_save_schedule)

        self.tabs.addTab(tab, "  📅 Mensualités / الأقساط الشهرية  ")

    # ============================================
    # TAB 3: FEES REPORTS
    # ============================================
    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        controls_card = self.create_card()
        controls = QHBoxLayout(controls_card)
        controls.setContentsMargins(20, 20, 20, 20)
        controls.setSpacing(12)

        self.combo_fees_report = styled_combo()
        self.combo_fees_report.addItem("Comparaison des Frais par Classe", "comparison")
        self.combo_fees_report.addItem("Projection Revenu Annuel", "projection")

        colors = ThemeManager.get_colors()

        btn_generate = styled_button(
            "Générer Rapport",
            bg_color=colors.PRIMARY,
            hover_color=colors.PRIMARY_HOVER,
            min_height=42,
        )

        btn_export = styled_button(
            "Exporter PDF",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=42,
        )

        btn_generate.clicked.connect(self.run_fees_report)
        btn_export.clicked.connect(self.export_fees_report_pdf)

        controls.addWidget(QLabel("Rapport:"))
        controls.addWidget(self.combo_fees_report, 2)
        controls.addWidget(btn_generate)
        controls.addWidget(btn_export)

        self.table_fees_report = QTableWidget(0, 1)
        style_table(self.table_fees_report)
        self.table_fees_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(controls_card)
        layout.addWidget(self.table_fees_report)
        self.tabs.addTab(tab, "  📊 Rapports Frais / التقارير  ")

    # --- Database / Logic Methods ---
    def load_classes(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                classes = FinanceRepository(conn).list_classes()

                self.combo_class_reg.clear()
                self.combo_class_month.clear()
                self.combo_class_reg.addItem("- Choisir -", None)
                self.combo_class_month.addItem("- Choisir -", None)

                for c in classes:
                    class_name = c[1] or "-"
                    self.combo_class_reg.addItem(class_name, c[0])
                    self.combo_class_month.addItem(class_name, c[0])

            self.load_reg_table()
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceFeesSetup", DB_QUERY, e, _op_id)
            QMessageBox.critical(self, f"Erreur [{DB_QUERY}]", f"Erreur de chargement.\n\nID: {_op_id}")

    def save_registration_fee(self):
        class_id = self.combo_class_reg.currentData()
        amount = self.spin_reg_amount.value()
        if not class_id:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                FinanceRepository(conn).upsert_registration_fee(class_id, amount)
                conn.commit()
            self.load_reg_table()
            QMessageBox.information(self, "Succès", "Frais d'inscription mis à jour.")
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceFeesSetup", DB_TRANSACTION, e, _op_id)
            QMessageBox.critical(
                self, f"Erreur [{DB_TRANSACTION}]", f"Erreur lors de l'enregistrement.\n\nID: {_op_id}"
            )

    def load_reg_table(self):
        self.table_reg.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = FinanceRepository(conn).get_registration_fees_table()
            for r in rows:
                idx = self.table_reg.rowCount()
                self.table_reg.insertRow(idx)
                amount = float(r[1] or 0)
                self.table_reg.setItem(idx, 0, QTableWidgetItem(r[0] or "-"))
                self.table_reg.setItem(idx, 1, QTableWidgetItem(f"{amount:,.0f} FCFA"))
        except Exception as e:
            AppLogger.error("FinanceFeesSetup", f"Error loading registration table: {e}")

    def apply_smart_distribution(self):
        base = self.spin_base_price.value()
        extra = base / 4
        for i in range(9):
            sp = self.table_months.cellWidget(i, 1)
            if i < 4:
                sp.setValue(base)
            elif i < 8:
                sp.setValue(base + extra)
            else:
                sp.setValue(0)

    def apply_flat_distribution(self):
        base = self.spin_base_price.value()
        for i in range(9):
            self.table_months.cellWidget(i, 1).setValue(base)

    def save_monthly_schedule(self):
        class_id = self.combo_class_month.currentData()
        if not class_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une classe.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                entries = [
                    (month_idx, month_name, self.table_months.cellWidget(i, 1).value())
                    for i, (month_idx, month_name) in enumerate(self.academic_months)
                ]
                FinanceRepository(conn).save_monthly_fee_schedule(class_id, entries)
                conn.commit()
            QMessageBox.information(self, "Succès", "Échéancier enregistré avec succès.")
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceFeesSetup", DB_TRANSACTION, e, _op_id)
            QMessageBox.critical(
                self, f"Erreur [{DB_TRANSACTION}]", f"Erreur lors de la sauvegarde de l'échéancier.\n\nID: {_op_id}"
            )

    def load_monthly_schedule(self):
        class_id = self.combo_class_month.currentData()
        for i in range(9):
            self.table_months.cellWidget(i, 1).setValue(0)

        if not class_id:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = FinanceRepository(conn).get_monthly_fee_schedule(class_id)

            data_map = {r[0]: r[2] for r in rows}

            for i, (m_idx, _) in enumerate(self.academic_months):
                if m_idx in data_map:
                    self.table_months.cellWidget(i, 1).setValue(data_map[m_idx])
        except Exception as e:
            AppLogger.error("FinanceFeesSetup", f"Error loading monthly schedule: {e}")

    # ================== تعديل جوهري للتقارير بناءً على قاعدة البيانات ==================
    def run_fees_report(self):
        report_key = self.combo_fees_report.currentData() or "comparison"

        headers = []
        rows = []
        title = ""

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                # FIX 2: Reuse the open connection instead of calling
                # self.get_active_year_id() which opens a second connection.
                active_year = repo.get_active_year_id()

                if report_key == "comparison":
                    title = "Rapport Comparatif des Frais par Classe"
                    headers = ["Classe", "Inscription", "Total Mensualités", "Frais Annuels (1 élève)"]
                    for class_name, registration_fee, monthly_total in repo.get_fees_comparison_report():
                        annual_total = float(registration_fee or 0) + float(monthly_total or 0)
                        rows.append(
                            [
                                class_name or "-",
                                f"{float(registration_fee or 0):,.0f} FCFA",
                                f"{float(monthly_total or 0):,.0f} FCFA",
                                f"{annual_total:,.0f} FCFA",
                            ]
                        )
                else:
                    if active_year == -1:
                        QMessageBox.warning(
                            self, "Attention", "Aucune année scolaire active n'a été trouvée pour la projection."
                        )
                        return
                    title = "Rapport Projection du Revenu Annuel"
                    headers = ["Classe", "Élèves Actifs", "Frais Annuels (1 élève)", "Projection Totale"]
                    for class_name, active_students, registration_fee, monthly_total in repo.get_fees_projection_report(
                        active_year
                    ):
                        annual_per_student = float(registration_fee or 0) + float(monthly_total or 0)
                        projection = annual_per_student * int(active_students or 0)
                        rows.append(
                            [
                                class_name or "-",
                                int(active_students or 0),
                                f"{annual_per_student:,.0f} FCFA",
                                f"{projection:,.0f} FCFA",
                            ]
                        )

            self.current_fees_report_title = title
            self.current_fees_report_headers = headers
            self.current_fees_report_rows = rows

            self.table_fees_report.setColumnCount(len(headers) if headers else 1)
            self.table_fees_report.setHorizontalHeaderLabels(headers or ["Données"])
            self.table_fees_report.setRowCount(0)

            for row_values in rows:
                idx = self.table_fees_report.rowCount()
                self.table_fees_report.insertRow(idx)
                for col_idx, value in enumerate(row_values):
                    self.table_fees_report.setItem(idx, col_idx, QTableWidgetItem(str(value)))

            if not rows:
                QMessageBox.information(self, "Information", "Aucune donnée trouvée pour ce rapport.")
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceFeesSetup", IO_EXPORT, e, _op_id)
            QMessageBox.critical(
                self, f"Erreur [{IO_EXPORT}]", f"Erreur lors de la génération du rapport.\n\nID: {_op_id}"
            )

    def export_fees_report_pdf(self):
        if not self.current_fees_report_rows:
            QMessageBox.warning(self, "Attention", "Générez d'abord un rapport avec des données.")
            return

        orientation = 'L' if len(self.current_fees_report_headers) >= 5 else 'P'
        pdf = FPDF(orientation=orientation)
        pdf.add_page()

        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, self.current_fees_report_title)

        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 7, f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
        pdf.ln(2)

        table_width = pdf.w - 20
        col_width = table_width / max(1, len(self.current_fees_report_headers))

        apply_table_header_style(pdf, "Arial", 9)
        for header in self.current_fees_report_headers:
            text = str(header).encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(col_width, 8, text, 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, "Arial", 8)
        for row_idx, row_values in enumerate(self.current_fees_report_rows):
            set_zebra_row_fill(pdf, row_idx)
            for value in row_values:
                text = str(value).encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(col_width, 7, text, 1, 0, 'C', True)
            pdf.ln()

        # FIX 3: FEES_REPORT_OUTPUT_MODE is already the resolved value.
        mode = FEES_REPORT_OUTPUT_MODE
        output_pdf(
            pdf,
            self,
            default_name=f"Rapport_Frais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=mode,
            dialog_title="Exporter Rapport Frais",
            success_save_message="Rapport des frais exporté.",
            success_print_message="Rapport des frais envoyé à l'imprimante.",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FeesSetupWindow()
    window.show()
    sys.exit(app.exec())
