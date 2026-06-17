import os
import sys
from datetime import datetime

import psycopg2
from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from constants import PAGE_SIZE_DEFAULT, PASS_AVERAGE, STUDENT_CODE_PREFIX
from database_setup import DatabaseManager
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    get_school_info_row,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.inventory_repo import InventoryRepository
from ui_components import (
    BaseDialog,
    card_frame,
    dialog_button_row,
    dialog_error_label,
    style_table,
    styled_combo,
    styled_date_edit,
    styled_input,
)
from ui_components import styled_spinbox as styled_double_spin_uc
from ui_styles import Colors, ModuleHeaderWidget, ThemeManager, get_module_caps, get_table_style, get_tabs_style


class InventoryItemDialog(BaseDialog):
    """Popup for creating a new inventory item."""

    CATEGORIES = [
        "Fournitures (قرطاسية)",
        "Mobilier (أثاث)",
        "Électronique (إلكترونيات)",
        "Hygiène (نظافة)",
        "Autre",
    ]

    def __init__(self, parent=None):
        super().__init__("➕ Nouvel Article / مادة جديدة", parent)
        self.setModal(True)
        self.setMinimumWidth(560)
        self._build_ui()

    def _build_ui(self):
        colors = ThemeManager.get_colors()

        title = QLabel("📦 Nouvel Article")
        title.setStyleSheet(f"font-size:16px; font-weight:700; color:{colors.TEXT_PRIMARY};")
        self.dialog_layout.addWidget(title)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.txt_name_fr = styled_input("Nom (FR)")
        self.txt_name_ar = styled_input("الاسم (عربي)")
        self.combo_cat = styled_combo()
        self.combo_cat.addItems(self.CATEGORIES)
        self.txt_loc = styled_input("Emplacement / المكان")

        spinbox_style = (
            f"padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px;"
            f" background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};"
        )
        focus_style = f"border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS};"

        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(0, 100000)
        self.spin_qty.setMinimumHeight(42)
        self.spin_qty.setStyleSheet(f"QSpinBox {{{spinbox_style}}} QSpinBox:focus {{{focus_style}}}")

        self.spin_min = QSpinBox()
        self.spin_min.setRange(0, 100000)
        self.spin_min.setValue(5)
        self.spin_min.setMinimumHeight(42)
        self.spin_min.setStyleSheet(f"QSpinBox {{{spinbox_style}}} QSpinBox:focus {{{focus_style}}}")

        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0, 1000000)
        self.spin_price.setPrefix("FCFA ")
        self.spin_price.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_price.setMinimumHeight(42)
        self.spin_price.setStyleSheet(f"QDoubleSpinBox {{{spinbox_style}}} QDoubleSpinBox:focus {{{focus_style}}}")

        form.addWidget(QLabel("Nom FR:"), 0, 0)
        form.addWidget(self.txt_name_fr, 0, 1)
        form.addWidget(QLabel("Nom AR:"), 0, 2)
        form.addWidget(self.txt_name_ar, 0, 3)

        form.addWidget(QLabel("Catégorie:"), 1, 0)
        form.addWidget(self.combo_cat, 1, 1)
        form.addWidget(QLabel("Emplacement:"), 1, 2)
        form.addWidget(self.txt_loc, 1, 3)

        form.addWidget(QLabel("Qté initiale:"), 2, 0)
        form.addWidget(self.spin_qty, 2, 1)
        form.addWidget(QLabel("Seuil min:"), 2, 2)
        form.addWidget(self.spin_min, 2, 3)

        form.addWidget(QLabel("Prix unitaire:"), 3, 0)
        form.addWidget(self.spin_price, 3, 1)

        self.dialog_layout.addLayout(form)
        self.dialog_layout.addLayout(dialog_button_row("✔ Enregistrer", self._validate, self.reject))

    def get_values(self):
        return {
            "name_fr": self.txt_name_fr.text().strip(),
            "name_ar": self.txt_name_ar.text().strip(),
            "category": self.combo_cat.currentText(),
            "quantity": self.spin_qty.value(),
            "min_quantity": self.spin_min.value(),
            "unit_price": self.spin_price.value(),
            "location": self.txt_loc.text().strip(),
        }

    def _validate(self):
        if not self.txt_name_fr.text().strip():
            self._err_lbl.setText("Le nom de l'article (FR) est requis.")
            self._err_lbl.setVisible(True)
            return
        self._err_lbl.setVisible(False)
        self.accept()


class MovementDialog(BaseDialog):
    """Popup for recording a stock movement."""

    def __init__(self, items, parent=None):
        super().__init__("🔄 Nouveau Mouvement", parent)
        self.setModal(True)
        self.setMinimumWidth(560)
        self._items = items
        self._build_ui()

    def _build_ui(self):
        colors = ThemeManager.get_colors()

        title = QLabel("🔄 Enregistrer un Mouvement")
        title.setStyleSheet(f"font-size:15px; font-weight:700; color:{colors.TEXT_PRIMARY};")
        self.dialog_layout.addWidget(title)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        spinbox_style = (
            f"padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER};"
            f" border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};"
        )
        focus_style = f"border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS};"

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.combo_items_dlg = styled_combo()
        for name, item_id in self._items:
            self.combo_items_dlg.addItem(name, item_id)
        self.combo_type_dlg = styled_combo()
        self.combo_type_dlg.addItems(["ENTRÉE (Achat/Retour)", "SORTIE (Consommation/Perte)"])
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 100000)
        self.spin_qty.setMinimumHeight(42)
        self.spin_qty.setStyleSheet(f"QSpinBox {{{spinbox_style}}} QSpinBox:focus {{{focus_style}}}")
        row1.addWidget(QLabel("Article:"))
        row1.addWidget(self.combo_items_dlg, 3)
        row1.addWidget(QLabel("Type:"))
        row1.addWidget(self.combo_type_dlg, 2)
        row1.addWidget(QLabel("Qté:"))
        row1.addWidget(self.spin_qty, 1)
        self.dialog_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.date_move_dlg = styled_date_edit()
        self.date_move_dlg.setDate(QDate.currentDate())
        self.txt_notes_dlg = styled_input("Motif / Bénéficiaire...")
        row2.addWidget(QLabel("Date:"))
        row2.addWidget(self.date_move_dlg)
        row2.addWidget(QLabel("Notes:"))
        row2.addWidget(self.txt_notes_dlg, 2)
        self.dialog_layout.addLayout(row2)

        self.dialog_layout.addLayout(dialog_button_row("✔ Valider Mouvement", self._validate, self.reject))

    def _validate(self):
        if not self.combo_items_dlg.currentData():
            self._err_lbl.setText("Veuillez sélectionner un article.")
            self._err_lbl.setVisible(True)
            return
        self._err_lbl.setVisible(False)
        self.accept()

    def get_values(self):
        return {
            "item_id": self.combo_items_dlg.currentData(),
            "move_type": "IN" if "ENTRÉE" in self.combo_type_dlg.currentText() else "OUT",
            "qty": self.spin_qty.value(),
            "notes": self.txt_notes_dlg.text(),
            "date_str": (self.date_move_dlg.date().toString("yyyy-MM-dd") + datetime.now().strftime(" %H:%M:%S")),
        }


class InventoryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion de Stock / إدارة المخزون")
        self.setMinimumSize(1100, 700)
        self.current_inventory_report_rows = []
        self.current_inventory_report_headers = []
        self.current_inventory_report_title = ""

        # تطبيق المظهر
        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_inventory()
        self.load_history()

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "inventory")
        if hasattr(self, "btn_add"):
            self.btn_add.setEnabled(caps["can_write"])
            self.btn_add.setVisible(caps["can_write"])
        if hasattr(self, "btn_exec"):
            self.btn_exec.setEnabled(caps["can_write"])
            self.btn_exec.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. Header
        header = ModuleHeaderWidget("📦", "GESTION DE STOCK", "متابعة المخزون، المشتريات، والاستهلاك")
        self._stat_items = header.add_stat("📊", "Articles", "0", "#3B82F6")
        self._stat_alerts = header.add_stat("⚠️", "Alertes Stock", "0", "#EF4444")
        self._stat_value = header.add_stat("💰", "Valeur Totale", "—", "#22C55E")
        self.main_layout.addWidget(header)

        # 2. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_stock_tab()
        self.setup_movement_history_tab()
        self.setup_reports_tab()

        self.main_layout.addWidget(self.tabs)

    # --- Helper Methods ---
    def create_card(self):
        return card_frame()

    def styled_input(self, placeholder):
        return styled_input(placeholder)

    def styled_combo(self):
        return styled_combo()

    def styled_spinbox(self, suffix=""):
        colors = ThemeManager.get_colors()
        sb = QSpinBox()
        sb.setRange(0, 100000)
        sb.setSuffix(suffix)
        sb.setMinimumHeight(42)
        sb.setStyleSheet(
            f"QSpinBox {{ padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px;"
            f" background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
            f" QSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}"
        )
        return sb

    def styled_double_spin(self, prefix=""):
        return styled_double_spin_uc(prefix=prefix)

    def styled_date(self):
        return styled_date_edit()

    def style_table(self, table):
        style_table(table)

    # ---------------------------------------------------------
    # TAB 1: Stock Overview
    # ---------------------------------------------------------
    def setup_stock_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        colors = ThemeManager.get_colors()

        # Toolbar
        toolbar_card = self.create_card()
        tl = QHBoxLayout(toolbar_card)
        tl.setContentsMargins(12, 10, 12, 10)
        tl.setSpacing(10)

        self.btn_add = QPushButton("➕  Nouvel Article")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setMinimumHeight(38)
        self.btn_add.setStyleSheet(
            f"""
            QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS} stop:1 #16A34A); color: white; font-weight: 700; border-radius: 8px; border: none; padding: 8px 18px; font-size: 13px; }}
            QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}
            QPushButton:disabled {{ background:{colors.BORDER}; color:{colors.TEXT_SECONDARY}; }}
        """
        )
        self.btn_add.clicked.connect(self.open_item_dialog)

        self.lbl_stats = QLabel("💰 Valeur Totale: 0.00 FCFA   |   ⚠️ Alertes Rupture: 0")
        self.lbl_stats.setStyleSheet(
            f"background-color: {colors.BG_MAIN}; padding: 12px; border-radius: 8px; color: {colors.TEXT_PRIMARY}; font-weight: bold; border: 1px solid {colors.BORDER};"
        )
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tl.addWidget(self.btn_add)
        tl.addStretch()
        tl.addWidget(self.lbl_stats)
        layout.addWidget(toolbar_card)

        self.table_stock = QTableWidget(0, 8)
        self.style_table(self.table_stock)
        self.table_stock.setHorizontalHeaderLabels(
            ["ID", "Article (FR)", "Article (AR)", "Catégorie", "Qté", "Min", "Prix", "Total"]
        )
        self.table_stock.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_stock.setColumnWidth(0, 50)
        layout.addWidget(self.table_stock)
        self.tabs.addTab(tab, "  📦 État du Stock / المخزون  ")

    # ---------------------------------------------------------
    # TAB 2: Movements & History (combined)
    # ---------------------------------------------------------
    def setup_movement_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        colors = ThemeManager.get_colors()

        # Hidden combo — populated by load_inventory(), passed to MovementDialog
        self.combo_items = self.styled_combo()

        toolbar_card = self.create_card()
        tl = QHBoxLayout(toolbar_card)
        tl.setContentsMargins(12, 8, 12, 8)
        tl.setSpacing(8)

        self.btn_exec = QPushButton("🔄 Nouveau Mouvement")
        self.btn_exec.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exec.setFixedHeight(32)
        self.btn_exec.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.WARNING} stop:1 #D97706);"
            f" color: white; font-weight: 700; font-size:11px;"
            f" border-radius: 7px; border: none; padding: 4px 14px; }}"
            f"QPushButton:hover {{ background: #B45309; }}"
            f"QPushButton:disabled {{ background:{colors.BORDER}; color:{colors.TEXT_SECONDARY}; }}"
        )
        self.btn_exec.clicked.connect(self.open_movement_dialog)

        btn_refresh = QPushButton("🔃 Actualiser")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedHeight(32)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.PRIMARY} stop:1 {colors.PRIMARY_HOVER});"
            f" color: white; font-weight: bold; font-size:11px;"
            f" border-radius: 7px; border: none; padding: 4px 14px; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_refresh.clicked.connect(self.load_history)

        tl.addWidget(self.btn_exec)
        tl.addStretch()
        tl.addWidget(btn_refresh)
        layout.addWidget(toolbar_card)

        self.table_log = QTableWidget(0, 5)
        self.style_table(self.table_log)
        self.table_log.setHorizontalHeaderLabels(["Date", "Type", "Article", "Qté", "Notes / Motif"])
        self.table_log.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_log)

        self.tabs.addTab(tab, "  🔄 Mouvements & Historique / الحركات والسجل  ")

    # ---------------------------------------------------------
    # TAB 4: Reports
    # ---------------------------------------------------------
    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        colors = ThemeManager.get_colors()

        controls_card = self.create_card()
        controls_layout = QHBoxLayout(controls_card)
        controls_layout.setContentsMargins(20, 15, 20, 15)
        controls_layout.setSpacing(12)

        self.combo_report_type = self.styled_combo()
        self.combo_report_type.addItems(
            ["Valeur du stock par catégorie", "Articles en alerte de stock", "Mouvements par période"]
        )

        self.report_date_from = self.styled_date()
        self.report_date_to = self.styled_date()
        self.report_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.report_date_to.setDate(QDate.currentDate())

        btn_run = QPushButton("Générer")
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setMinimumHeight(40)
        btn_run.setStyleSheet(
            f"""
            QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.PRIMARY} stop:1 {colors.PRIMARY_HOVER}); color: white; font-weight: 700; border-radius: 8px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}
        """
        )
        btn_run.clicked.connect(self.run_inventory_report)

        btn_export = QPushButton("Exporter PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(40)
        btn_export.setStyleSheet(
            f"""
            QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS} stop:1 #16A34A); color: white; font-weight: 700; border-radius: 8px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """
        )
        btn_export.clicked.connect(self.export_inventory_report_pdf)

        controls_layout.addWidget(QLabel("Rapport:"))
        controls_layout.addWidget(self.combo_report_type, 2)
        controls_layout.addWidget(QLabel("Du:"))
        controls_layout.addWidget(self.report_date_from)
        controls_layout.addWidget(QLabel("Au:"))
        controls_layout.addWidget(self.report_date_to)
        controls_layout.addWidget(btn_run)
        controls_layout.addWidget(btn_export)

        self.table_reports = QTableWidget(0, 1)
        self.style_table(self.table_reports)
        self.table_reports.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(controls_card)
        layout.addWidget(self.table_reports)

        self.tabs.addTab(tab, "  📊 Rapports / التقارير  ")

    def run_inventory_report(self):
        report_type = self.combo_report_type.currentText()
        date_from = self.report_date_from.date().toString("yyyy-MM-dd")
        date_to = self.report_date_to.date().toString("yyyy-MM-dd")

        # إضافة نهاية اليوم لضمان شمولية حركات اليوم الأخير
        date_to_full = f"{date_to} 23:59:59"

        rows = []
        headers = []
        title = ""

        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                repo = InventoryRepository(conn)

                if report_type == "Valeur du stock par catégorie":
                    title = "Rapport de valeur du stock par catégorie"
                    headers = ["Catégorie", "Articles", "Quantité totale", "Valeur totale (FCFA)"]
                    for category, items_count, total_qty, total_value in repo.get_stock_value_by_category():
                        rows.append(
                            [
                                category or "-",
                                int(items_count or 0),
                                int(total_qty or 0),
                                f"{float(total_value or 0):,.2f}",
                            ]
                        )

                elif report_type == "Articles en alerte de stock":
                    title = "Rapport des articles en alerte de stock"
                    headers = ["Article", "Catégorie", "Stock actuel", "Seuil min", "Emplacement"]
                    for name_fr, category, quantity, min_quantity, location in repo.get_low_stock_items():
                        rows.append(
                            [
                                name_fr or "-",
                                category or "-",
                                int(quantity or 0),
                                int(min_quantity or 0),
                                location or "-",
                            ]
                        )

                else:
                    title = "Rapport des mouvements par période"
                    headers = ["Article", "Entrées", "Sorties", "Solde net"]
                    for name_fr, total_in, total_out, net_qty in repo.get_movements_by_period(date_from, date_to_full):
                        rows.append([name_fr or "-", int(total_in or 0), int(total_out or 0), int(net_qty or 0)])

            self.current_inventory_report_rows = rows
            self.current_inventory_report_headers = headers
            self.current_inventory_report_title = title

            self.table_reports.setColumnCount(len(headers) if headers else 1)
            self.table_reports.setHorizontalHeaderLabels(headers or ["Données"])
            self.table_reports.setRowCount(0)

            for row in rows:
                row_index = self.table_reports.rowCount()
                self.table_reports.insertRow(row_index)
                for col_index, value in enumerate(row):
                    self.table_reports.setItem(row_index, col_index, QTableWidgetItem(str(value)))

            if not rows:
                QMessageBox.information(self, "Information", "Aucune donnée trouvée pour ce rapport.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération du rapport: {e}")

    def _add_pdf_school_header(self, pdf):
        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, self.current_inventory_report_title)

    def export_inventory_report_pdf(self):
        if not self.current_inventory_report_rows:
            QMessageBox.warning(self, "Attention", "Générez d'abord un rapport avec des données.")
            return

        orientation = 'L' if len(self.current_inventory_report_headers) >= 5 else 'P'
        pdf = FPDF(orientation=orientation)
        pdf.add_page()
        self._add_pdf_school_header(pdf)

        if self.combo_report_type.currentText() == "Mouvements par période":
            period_text = f"Période: {self.report_date_from.date().toString('yyyy-MM-dd')} au {self.report_date_to.date().toString('yyyy-MM-dd')}"
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(0, 6, period_text.encode('latin-1', 'ignore').decode('latin-1'), 0, 1, 'C')

        pdf.ln(4)
        table_width = pdf.w - 20
        col_width = table_width / max(1, len(self.current_inventory_report_headers))

        apply_table_header_style(pdf, "Arial", 9)
        for header in self.current_inventory_report_headers:
            header_text = str(header).encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(col_width, 8, header_text, 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, "Arial", 9)
        for row_index, row in enumerate(self.current_inventory_report_rows):
            set_zebra_row_fill(pdf, row_index)
            for value in row:
                value_text = str(value).encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(col_width, 8, value_text, 1, 0, 'C', True)
            pdf.ln()

        mode = get_report_output_mode("inventory_report_mode", fallback="open")
        output_pdf(
            pdf,
            self,
            default_name=f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=mode,
            success_save_message="Rapport exporté avec succès.",
            success_print_message="Rapport envoyé à l'imprimante.",
        )

    # --- Logic ---
    def open_item_dialog(self):
        dialog = InventoryItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_item_from_dialog(dialog.get_values())

    def _save_item_from_dialog(self, values: dict):
        fr = values.get("name_fr", "")
        ar = values.get("name_ar", "")
        cat = values.get("category", "")
        qty = int(values.get("quantity", 0))
        min_q = int(values.get("min_quantity", 0))
        price = float(values.get("unit_price", 0.0))
        loc = values.get("location", "")

        if not fr:
            QMessageBox.warning(self, "Erreur", "Le nom FR est obligatoire.")
            return

        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                repo = InventoryRepository(conn)
                item_id = repo.insert_item(fr, ar, cat, qty, min_q, price, loc)
                conn.commit()

            if qty > 0:
                self.log_movement_db(item_id, "IN", qty, "Stock Initial")

            self.load_inventory()
            QMessageBox.information(self, "Succès", "Article ajouté.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {e}")

    def add_item(self):
        # Backward-compatible entry point.
        self.open_item_dialog()

    def log_movement_db(self, item_id, m_type, qty, notes):
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                InventoryRepository(conn).insert_movement_log(item_id, m_type, qty, date_str, notes)
                conn.commit()
        except Exception as e:
            AppLogger.error("InventoryManagement", f"Error logging movement: {e}")

    def load_inventory(self):
        self.table_stock.setRowCount(0)
        self.combo_items.clear()

        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                rows = InventoryRepository(conn).list_all_items()

            total_val = 0
            alert_count = 0

            for r in rows:
                item_id = r[0]
                name_fr = str(r[1] or "-")
                name_ar = str(r[2] or "")
                category = str(r[3] or "-")
                qty = int(r[4] or 0)
                min_qty = int(r[5] or 0)
                unit_price = float(r[6] or 0.0)

                idx = self.table_stock.rowCount()
                self.table_stock.insertRow(idx)

                self.combo_items.addItem(f"{name_fr} (Stock: {qty})", item_id)

                row_total = qty * unit_price
                total_val += row_total

                self.table_stock.setItem(idx, 0, QTableWidgetItem(str(item_id)))
                self.table_stock.setItem(idx, 1, QTableWidgetItem(name_fr))
                self.table_stock.setItem(idx, 2, QTableWidgetItem(name_ar))
                self.table_stock.setItem(idx, 3, QTableWidgetItem(category))

                qty_item = QTableWidgetItem(str(qty))
                if qty <= min_qty:  # Low Stock Alert
                    colors = ThemeManager.get_colors()
                    qty_item.setForeground(QColor(colors.DANGER))
                    bg_color = QColor(colors.DANGER)
                    bg_color.setAlpha(40)
                    qty_item.setBackground(bg_color)
                    qty_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    alert_count += 1
                else:
                    qty_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))

                self.table_stock.setItem(idx, 4, qty_item)
                self.table_stock.setItem(idx, 5, QTableWidgetItem(str(min_qty)))
                self.table_stock.setItem(idx, 6, QTableWidgetItem(f"{unit_price:.2f}"))
                self.table_stock.setItem(idx, 7, QTableWidgetItem(f"{row_total:.2f}"))

            self.lbl_stats.setText(f"💰 Valeur Totale: {total_val:,.2f} FCFA   |   ⚠️ Alertes Rupture: {alert_count}")

            # Update stat chips
            self._stat_items.set_value(str(len(rows)))
            self._stat_alerts.set_value(str(alert_count))
            self._stat_value.set_value(f"{total_val/1000:.0f}k")
        except Exception as e:
            AppLogger.error("InventoryManagement", f"Error loading inventory: {e}")

    def open_movement_dialog(self):
        items = [(self.combo_items.itemText(i), self.combo_items.itemData(i)) for i in range(self.combo_items.count())]
        dlg = MovementDialog(items, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.execute_movement(dlg.get_values())

    def execute_movement(self, vals: dict):
        item_id = vals["item_id"]
        move_type = vals["move_type"]
        qty = vals["qty"]
        notes = vals["notes"]
        date_str = vals["date_str"]

        if not item_id:
            return
        if qty <= 0:
            QMessageBox.warning(self, "Erreur", "La quantité doit être supérieure à zéro.")
            return

        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                repo = InventoryRepository(conn)

                if move_type == "OUT":
                    current = repo.get_item_quantity(item_id)
                    if current < qty:
                        QMessageBox.warning(self, "Erreur", f"Stock insuffisant! (Disponible: {current})")
                        return
                    new_qty = current - qty
                else:
                    current = repo.get_item_quantity(item_id)
                    new_qty = current + qty

                repo.update_item_quantity(item_id, new_qty)
                repo.insert_movement_log(item_id, move_type, qty, date_str, notes)

                conn.commit()

            self.load_inventory()
            self.load_history()
            QMessageBox.information(self, "Succès", "Mouvement enregistré.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de mouvement: {e}")

    def load_history(self):
        self.table_log.setRowCount(0)
        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                rows = InventoryRepository(conn).list_movement_history(limit=PAGE_SIZE_DEFAULT)
            for r in rows:
                idx = self.table_log.rowCount()
                self.table_log.insertRow(idx)

                # عرض التاريخ بدون الثواني للشكل الجمالي
                display_date = str(r[0] or "").split(".")[0]
                self.table_log.setItem(idx, 0, QTableWidgetItem(display_date))

                movement_type = str(r[1] or "")
                type_item = QTableWidgetItem(movement_type)
                if movement_type == "IN":
                    type_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                    type_item.setText("ENTRÉE")
                else:
                    type_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                    type_item.setText("SORTIE")

                self.table_log.setItem(idx, 1, type_item)
                self.table_log.setItem(idx, 2, QTableWidgetItem(str(r[2] or "-")))
                self.table_log.setItem(idx, 3, QTableWidgetItem(str(r[3] or 0)))
                self.table_log.setItem(idx, 4, QTableWidgetItem(str(r[4] or "")))
        except Exception as e:
            AppLogger.error("InventoryManagement", f"Error loading history: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InventoryWindow()
    window.show()
    sys.exit(app.exec())
