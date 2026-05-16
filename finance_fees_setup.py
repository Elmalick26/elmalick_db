import sys
from datetime import datetime

import psycopg2
from fpdf import FPDF
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QGroupBox,
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
from repositories.finance_repo import FinanceRepository
from ui_styles import Colors, ThemeManager, apply_shadow_to_widget, get_card_style, get_table_style, get_tabs_style

THEME_AVAILABLE = True
FEES_REPORT_OUTPUT_MODE = get_report_output_mode("fees_report_mode", "save")


class FeesSetupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Financière / الإعداد المالي")
        self.setMinimumSize(1100, 700)
        self.current_fees_report_rows = []
        self.current_fees_report_headers = []
        self.current_fees_report_title = ""

        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            # تطبيق نمط Deep Slate
            self.setStyleSheet(
                f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER}; border-radius: 8px; margin-top: 10px;
                    background-color: {colors.BG_CARD}; font-weight: bold; color: {colors.TEXT_SECONDARY};
                }}
                QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }}
            """
            )

        self.init_ui()
        self.load_classes()

    def get_active_year_id(self):
        """جلب معرف السنة الدراسية النشطة حالياً لاستخدامه في التقارير"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return FinanceRepository(conn).get_active_year_id()
        except Exception:
            return -1

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

        header_frame.setStyleSheet(
            f"""
            QFrame {{ background-color: {bg_header}; border-radius: 10px; }}
        """
        )
        header_frame.setMaximumHeight(80)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)

        icon_lbl = QLabel("⚙️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_layout = QVBoxLayout()
        header_lbl = QLabel("CONFIGURATION FINANCIÈRE")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("إعداد رسوم التسجيل وجدولة الأقساط الشهرية")
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

        self.setup_registration_tab()
        self.setup_monthly_tab()
        self.setup_reports_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(
                f"""
                QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}
            """
            )
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(
            f"""
            QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
            QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """
        )
        combo.setMinimumHeight(40)
        return combo

    def styled_spinbox(self):
        sb = QDoubleSpinBox()
        sb.setRange(0, 1000000)
        sb.setPrefix("FCFA ")
        sb.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        sb.setStyleSheet(
            f"""
            QDoubleSpinBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-weight: bold; }}
            QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """
        )
        sb.setMinimumHeight(40)
        return sb

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())

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

        self.combo_class_reg = self.styled_combo()
        self.spin_reg_amount = self.styled_spinbox()

        btn_save_reg = QPushButton("Enregistrer")
        btn_save_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_save_reg.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 10px 20px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """
        )
        btn_save_reg.clicked.connect(self.save_registration_fee)

        hlay.addWidget(QLabel("Classe:"))
        hlay.addWidget(self.combo_class_reg, 1)
        hlay.addWidget(QLabel("Montant:"))
        hlay.addWidget(self.spin_reg_amount, 1)
        hlay.addWidget(btn_save_reg)

        layout.addWidget(reg_card)

        self.table_reg = QTableWidget(0, 2)
        self.style_table(self.table_reg)
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

        self.combo_class_month = self.styled_combo()
        self.combo_class_month.currentIndexChanged.connect(self.load_monthly_schedule)

        slay.addWidget(QLabel("Configurer pour la classe:"))
        slay.addWidget(self.combo_class_month, 1)
        layout.addWidget(sel_card)

        tool_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
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
        self.spin_base_price = self.styled_spinbox()
        self.spin_base_price.setValue(5000)
        self.spin_base_price.setStyleSheet(
            f"""
            QDoubleSpinBox {{ background: {colors.INPUT_BG}; border: 1px solid {colors.SUCCESS}; border-radius: 4px; padding: 5px; color: {colors.TEXT_PRIMARY}; }}
            QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """
        )

        btn_apply_smart = QPushButton("Répartition 4+4 (Smart)")
        btn_apply_smart.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_smart.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 4px; padding: 8px; border: none; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """
        )
        btn_apply_smart.clicked.connect(self.apply_smart_distribution)

        btn_apply_flat = QPushButton("Prix Unique (Flat)")
        btn_apply_flat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_flat.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.PRIMARY_DARK}; color: white; font-weight: bold; border-radius: 4px; padding: 8px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """
        )
        btn_apply_flat.clicked.connect(self.apply_flat_distribution)

        tlay.addWidget(QLabel("Prix de base:"))
        tlay.addWidget(self.spin_base_price)
        tlay.addWidget(btn_apply_smart)
        tlay.addWidget(btn_apply_flat)
        tool_layout.addLayout(tlay)

        layout.addWidget(tool_frame)

        self.table_months = QTableWidget(9, 2)
        self.style_table(self.table_months)
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

        btn_save_schedule = QPushButton("💾 ENREGISTRER L'ÉCHÉANCIER")
        btn_save_schedule.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_schedule.setMinimumHeight(50)
        btn_save_schedule.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; font-weight: bold; font-size: 14px; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background-color: {colors.BORDER}; color: {colors.TEXT_PRIMARY}; }}
        """
        )
        btn_save_schedule.clicked.connect(self.save_monthly_schedule)
        layout.addWidget(btn_save_schedule)

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

        self.combo_fees_report = self.styled_combo()
        self.combo_fees_report.addItem("Comparaison des Frais par Classe", "comparison")
        self.combo_fees_report.addItem("Projection Revenu Annuel", "projection")

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        btn_generate = QPushButton("Générer Rapport")
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generate.setMinimumHeight(40)
        btn_generate.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """
        )

        btn_export = QPushButton("Exporter PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(40)
        btn_export.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 6px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """
        )

        btn_generate.clicked.connect(self.run_fees_report)
        btn_export.clicked.connect(self.export_fees_report_pdf)

        controls.addWidget(QLabel("Rapport:"))
        controls.addWidget(self.combo_fees_report, 2)
        controls.addWidget(btn_generate)
        controls.addWidget(btn_export)

        self.table_fees_report = QTableWidget(0, 1)
        self.style_table(self.table_fees_report)
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
            QMessageBox.critical(self, "Erreur", f"Erreur de chargement: {e}")

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
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {e}")

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
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde de l'échéancier: {e}")

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
        active_year = self.get_active_year_id()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:

                if report_key == "comparison":
                    title = "Rapport Comparatif des Frais par Classe"
                    headers = ["Classe", "Inscription", "Total Mensualités", "Frais Annuels (1 élève)"]
                    for class_name, registration_fee, monthly_total in FinanceRepository(
                        conn
                    ).get_fees_comparison_report():
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
                    for class_name, active_students, registration_fee, monthly_total in FinanceRepository(
                        conn
                    ).get_fees_projection_report(active_year):
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
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération du rapport : {e}")

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

        mode = get_report_output_mode("fees_report_mode", FEES_REPORT_OUTPUT_MODE)
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
