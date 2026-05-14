import sys
import psycopg2
import os
from datetime import datetime
from fpdf import FPDF
from database_setup import DatabaseManager
from app_logger import AppLogger
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QSpinBox, 
                             QDoubleSpinBox, QTabWidget, QFrame, QDateEdit, 
                             QGridLayout, QGraphicsDropShadowEffect, QScrollArea)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QIcon
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_grades_sheet_header, apply_table_header_style, apply_table_body_style, set_zebra_row_fill, get_school_info_row

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style, Colors
from repositories.inventory_repo import InventoryRepository

THEME_AVAILABLE = True

class InventoryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion de Stock / إدارة المخزون")
        self.setMinimumSize(1100, 700)
        self.current_inventory_report_rows = []
        self.current_inventory_report_headers = []
        self.current_inventory_report_title = ""
        
        # تطبيق المظهر
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
            """)
        
        self.init_ui()
        self.load_inventory()
        self.load_history()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame
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
        hl.setContentsMargins(20, 10, 20, 10)
        
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DE STOCK")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("متابعة المخزون، المشتريات، والاستهلاك")
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
        
        self.setup_stock_tab()
        self.setup_movement_tab()
        self.setup_history_tab()
        self.setup_reports_tab()
        
        self.main_layout.addWidget(self.tabs)

    # --- Helper Methods ---
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
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        le.setStyleSheet(f"""
            QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
            QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """)
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"""
            QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
            QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """)
        combo.setMinimumHeight(38)
        return combo

    def styled_spinbox(self, suffix=""):
        sb = QSpinBox()
        sb.setRange(0, 100000)
        sb.setSuffix(suffix)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        sb.setStyleSheet(f"""
            QSpinBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
            QSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """)
        sb.setMinimumHeight(38)
        return sb

    def styled_double_spin(self, prefix=""):
        spin = QDoubleSpinBox()
        spin.setRange(0, 1000000)
        spin.setPrefix(prefix)
        spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        spin.setStyleSheet(f"QDoubleSpinBox {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        spin.setMinimumHeight(38)
        return spin

    def styled_date(self):
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        date_edit.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        date_edit.setMinimumHeight(38)
        return date_edit

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
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
            """)

    # ---------------------------------------------------------
    # TAB 1: Stock Overview
    # ---------------------------------------------------------
    def setup_stock_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        
        # --- Form Card (Left) ---
        form_card = self.create_card()
        form_card.setMinimumWidth(360)
        flay = QVBoxLayout(form_card)
        flay.setContentsMargins(20, 20, 20, 20)
        flay.setSpacing(15)
        
        lbl_title = QLabel("Nouveau Article / مادة جديدة")
        lbl_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        flay.addWidget(lbl_title)
        
        self.txt_name_fr = self.styled_input("Nom (FR)")
        self.txt_name_ar = self.styled_input("الاسم (عربي)")
        
        self.combo_cat = self.styled_combo()
        self.combo_cat.addItems(["Fournitures (قرطاسية)", "Mobilier (أثاث)", "Électronique (إلكترونيات)", "Hygiène (نظافة)", "Autre"])
        
        self.spin_qty = self.styled_spinbox()
        self.spin_min = self.styled_spinbox()
        self.spin_min.setValue(5)
        
        self.spin_price = self.styled_double_spin("FCFA ")
        self.txt_loc = self.styled_input("Emplacement / المكان")
        
        btn_add = QPushButton("Ajouter Article")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setMinimumHeight(45)
        btn_add.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_add.clicked.connect(self.add_item)

        flay.addWidget(QLabel("Nom FR:"))
        flay.addWidget(self.txt_name_fr)
        flay.addWidget(QLabel("Nom AR:"))
        flay.addWidget(self.txt_name_ar)
        flay.addWidget(QLabel("Catégorie:"))
        flay.addWidget(self.combo_cat)
        
        row_qty = QHBoxLayout()
        row_qty.addWidget(QLabel("Qté Init:"))
        row_qty.addWidget(self.spin_qty)
        row_qty.addWidget(QLabel("Min:"))
        row_qty.addWidget(self.spin_min)
        flay.addLayout(row_qty)
        
        flay.addWidget(QLabel("Prix Unitaire:"))
        flay.addWidget(self.spin_price)
        flay.addWidget(QLabel("Emplacement:"))
        flay.addWidget(self.txt_loc)
        flay.addSpacing(10)
        flay.addWidget(btn_add)
        flay.addStretch()

        scroll_form = QScrollArea()
        scroll_form.setWidgetResizable(True)
        scroll_form.setFrameShape(QFrame.Shape.NoFrame)
        scroll_form.setFixedWidth(380)
        scroll_form.setWidget(form_card)
        scroll_form.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        layout.addWidget(scroll_form)

        # --- Table (Right) ---
        table_layout = QVBoxLayout()
        
        self.lbl_stats = QLabel("Valeur: 0.00 FCFA | Rupture: 0")
        self.lbl_stats.setStyleSheet(f"background-color: {colors.BG_MAIN}; padding: 12px; border-radius: 8px; color: {colors.TEXT_PRIMARY}; font-weight: bold; border: 1px solid {colors.BORDER};")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table_layout.addWidget(self.lbl_stats)

        self.table_stock = QTableWidget(0, 8)
        self.style_table(self.table_stock)
        self.table_stock.setHorizontalHeaderLabels(["ID", "Article (FR)", "Article (AR)", "Catégorie", "Qté", "Min", "Prix", "Total"])
        self.table_stock.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_stock.setColumnWidth(0, 50)
        table_layout.addWidget(self.table_stock)
        
        layout.addLayout(table_layout)
        self.tabs.addTab(tab, "  📦 État du Stock / المخزون  ")

    # ---------------------------------------------------------
    # TAB 2: Movements
    # ---------------------------------------------------------
    def setup_movement_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        move_card = self.create_card()
        vlay = QVBoxLayout(move_card)
        vlay.setContentsMargins(20, 20, 20, 20)
        vlay.setSpacing(15)
        
        lbl_title = QLabel("Enregistrer un Mouvement / تسجيل حركة")
        lbl_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        vlay.addWidget(lbl_title)
        
        row1 = QHBoxLayout()
        self.combo_items = self.styled_combo()
        self.combo_type = self.styled_combo()
        self.combo_type.addItems(["ENTRÉE (Achat/Retour)", "SORTIE (Consommation/Perte)"])
        
        self.spin_move_qty = self.styled_spinbox()
        self.spin_move_qty.setRange(1, 1000)
        
        row1.addWidget(QLabel("Article:"))
        row1.addWidget(self.combo_items, 2)
        row1.addWidget(QLabel("Type:"))
        row1.addWidget(self.combo_type, 1)
        row1.addWidget(QLabel("Quantité:"))
        row1.addWidget(self.spin_move_qty, 1)
        
        row2 = QHBoxLayout()
        self.date_move = self.styled_date()
        self.date_move.setDate(QDate.currentDate())
        
        self.txt_notes = self.styled_input("Motif / Bénéficiaire...")
        
        btn_exec = QPushButton("Valider Mouvement")
        btn_exec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exec.setMinimumHeight(40)
        btn_exec.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_exec.clicked.connect(self.execute_movement)
        
        row2.addWidget(QLabel("Date:"))
        row2.addWidget(self.date_move)
        row2.addWidget(QLabel("Notes:"))
        row2.addWidget(self.txt_notes, 2)
        row2.addWidget(btn_exec)
        
        vlay.addLayout(row1)
        vlay.addLayout(row2)
        layout.addWidget(move_card)
        layout.addStretch()
        
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background-color: {colors.BG_MAIN}; border-radius: 8px; border: 1px dashed {colors.WARNING}; padding: 10px;")
        ilay = QHBoxLayout(info_frame)
        ilay.addWidget(QLabel("💡 Astuce: Les 'Sorties' diminuent le stock, les 'Entrées' l'augmentent."))
        layout.addWidget(info_frame)
        
        self.tabs.addTab(tab, "  🔄 Mouvements / الحركات  ")

    # ---------------------------------------------------------
    # TAB 3: History
    # ---------------------------------------------------------
    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        toolbar = QHBoxLayout()
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_refresh.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 15px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_refresh.clicked.connect(self.load_history)
        
        toolbar.addWidget(QLabel("Historique des Demandes / سجل الطلبات"))
        toolbar.addStretch()
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)
        
        self.table_log = QTableWidget(0, 5)
        self.style_table(self.table_log)
        self.table_log.setHorizontalHeaderLabels(["Date", "Type", "Article", "Qté", "Notes / Motif"])
        self.table_log.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table_log)
        
        self.tabs.addTab(tab, "  📜 Historique / السجل  ")

    # ---------------------------------------------------------
    # TAB 4: Reports
    # ---------------------------------------------------------
    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        controls_card = self.create_card()
        controls_layout = QHBoxLayout(controls_card)
        controls_layout.setContentsMargins(20, 15, 20, 15)
        controls_layout.setSpacing(12)

        self.combo_report_type = self.styled_combo()
        self.combo_report_type.addItems([
            "Valeur du stock par catégorie",
            "Articles en alerte de stock",
            "Mouvements par période"
        ])

        self.report_date_from = self.styled_date()
        self.report_date_to = self.styled_date()
        self.report_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.report_date_to.setDate(QDate.currentDate())

        btn_run = QPushButton("Générer")
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setMinimumHeight(40)
        btn_run.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_run.clicked.connect(self.run_inventory_report)

        btn_export = QPushButton("Exporter PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(40)
        btn_export.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 6px; border: none; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
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
                        rows.append([category or "-", int(items_count or 0), int(total_qty or 0), f"{float(total_value or 0):,.2f}"])

                elif report_type == "Articles en alerte de stock":
                    title = "Rapport des articles en alerte de stock"
                    headers = ["Article", "Catégorie", "Stock actuel", "Seuil min", "Emplacement"]
                    for name_fr, category, quantity, min_quantity, location in repo.get_low_stock_items():
                        rows.append([name_fr or "-", category or "-", int(quantity or 0), int(min_quantity or 0), location or "-"])

                else:
                    title = "Rapport des mouvements par période"
                    headers = ["Article", "Entrées", "Sorties", "Solde net"]
                    for name_fr, total_in, total_out, net_qty in repo.get_movements_by_period(date_from, date_to_full):
                        rows.append([name_fr or "-", int(total_in or 0), int(total_out or 0), int(net_qty or 0)])

            self.current_inventory_report_rows = rows
            self.current_inventory_report_headers = headers
            self.current_inventory_report_title = title

            self.table_reports.setColumnCount(len(headers) if headers else 1)
            self.table_reports.setHorizontalHeaderLabels(headers if headers else ["Données"])
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
    def add_item(self):
        fr = self.txt_name_fr.text()
        ar = self.txt_name_ar.text()
        cat = self.combo_cat.currentText()
        qty = self.spin_qty.value()
        min_q = self.spin_min.value()
        price = self.spin_price.value()
        loc = self.txt_loc.text()
        
        if not fr: return
        
        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                repo = InventoryRepository(conn)
                item_id = repo.insert_item(fr, ar, cat, qty, min_q, price, loc)
                conn.commit()
            
            # ===== استخدام IN بدلاً من ENTRÉE =====
            if qty > 0:
                self.log_movement_db(item_id, "IN", qty, "Stock Initial")

            self.txt_name_fr.clear(); self.txt_name_ar.clear()
            self.load_inventory()
            QMessageBox.information(self, "Succès", "Article ajouté.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {e}")

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
                if qty <= min_qty: # Low Stock Alert
                    if THEME_AVAILABLE:
                        colors = ThemeManager.get_colors()
                        qty_item.setForeground(QColor(colors.DANGER))
                        bg_color = QColor(colors.DANGER)
                        bg_color.setAlpha(40)
                        qty_item.setBackground(bg_color)
                    qty_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    alert_count += 1
                else:
                    if THEME_AVAILABLE:
                        qty_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                
                self.table_stock.setItem(idx, 4, qty_item)
                self.table_stock.setItem(idx, 5, QTableWidgetItem(str(min_qty)))
                self.table_stock.setItem(idx, 6, QTableWidgetItem(f"{unit_price:.2f}"))
                self.table_stock.setItem(idx, 7, QTableWidgetItem(f"{row_total:.2f}"))

            self.lbl_stats.setText(f"💰 Valeur Totale: {total_val:,.2f} FCFA   |   ⚠️ Alertes Rupture: {alert_count}")
        except Exception as e:
            AppLogger.error("InventoryManagement", f"Error loading inventory: {e}")

    def execute_movement(self):
        item_id = self.combo_items.currentData()
        move_type = "IN" if "ENTRÉE" in self.combo_type.currentText() else "OUT"
        qty = self.spin_move_qty.value()
        notes = self.txt_notes.text()
        date_str = self.date_move.date().toString("yyyy-MM-dd") + datetime.now().strftime(" %H:%M:%S")
        
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
            self.txt_notes.clear()
            self.spin_move_qty.setValue(1)
            QMessageBox.information(self, "Succès", "Mouvement enregistré.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de mouvement: {e}")

    def load_history(self):
        self.table_log.setRowCount(0)
        try:
            with DatabaseManager() as db:
                conn = db.get_connection()
                rows = InventoryRepository(conn).list_movement_history(limit=50)
            for r in rows:
                idx = self.table_log.rowCount()
                self.table_log.insertRow(idx)
                
                # عرض التاريخ بدون الثواني للشكل الجمالي
                display_date = str(r[0] or "").split(".")[0]
                self.table_log.setItem(idx, 0, QTableWidgetItem(display_date))
                
                movement_type = str(r[1] or "")
                type_item = QTableWidgetItem(movement_type)
                if movement_type == "IN": 
                    if THEME_AVAILABLE:
                        type_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                    type_item.setText("ENTRÉE")
                else: 
                    if THEME_AVAILABLE:
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