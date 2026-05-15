import sys
from datetime import datetime
from fpdf import FPDF
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect,
                             QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from database_setup import DatabaseManager
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_grades_sheet_header, apply_table_header_style, apply_table_body_style, set_zebra_row_fill, get_school_info_row

from ui_styles import ThemeManager, Colors, rgba, get_table_style

THEME_AVAILABLE = True
FINANCE_DASHBOARD_REPORT_MODE = get_report_output_mode("finance_dashboard_report_mode", "save")

class ModernFinanceDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tableau de Bord Financier / لوحة التحكم المالية")
        self.setMinimumSize(1100, 700)
        self.last_income = 0.0
        self.last_expenses = 0.0
        self.last_balance = 0.0
        self.last_inventory = 0.0
        self.last_recent_transactions = []

        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors.BG_MAIN};
                }}
                QLabel {{
                    font-family: 'Segoe UI', 'Cairo', sans-serif;
                    color: {colors.TEXT_PRIMARY};
                }}
            """)

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors.BG_HEADER};
                border-radius: 10px;
            }}
        """)
        header_frame.setMaximumHeight(80)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 10, 20, 10)

        icon_lbl = QLabel("📊")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_box = QVBoxLayout()
        title_label = QLabel("TABLEAU DE BORD FINANCIER")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            title_label.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            title_label.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_label = QLabel("Vue d'ensemble des revenus et dépenses / نظرة عامة")
        sub_label.setFont(QFont("Cairo", 11))
        if THEME_AVAILABLE:
            sub_label.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        else:
            sub_label.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")

        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)

        date_label = QLabel(datetime.now().strftime("%d %B %Y"))
        date_label.setFont(QFont("Segoe UI", 12))
        if THEME_AVAILABLE:
            date_label.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            date_label.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")

        header_layout.addWidget(icon_lbl)
        header_layout.addSpacing(15)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_export = QPushButton("📄 Rapport Exécutif")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(36)
        if THEME_AVAILABLE:
            btn_export.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ThemeManager.get_colors().SUCCESS};
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    border: none;
                    padding: 6px 14px;
                }}
                QPushButton:hover {{ background-color: {ThemeManager.get_colors().SUCCESS_HOVER}; }}
            """)
        btn_export.clicked.connect(self.export_executive_report_pdf)

        header_layout.addWidget(btn_export)
        header_layout.addSpacing(10)
        header_layout.addWidget(date_label)

        self.main_layout.addWidget(header_frame)

        # --- Cards ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        self.card_income = self.create_modern_card("REVENUS / المداخيل", "0.00", colors.SUCCESS, "↗")
        self.card_expenses = self.create_modern_card("DÉPENSES / المصاريف", "0.00", colors.DANGER, "↘")
        self.card_profit = self.create_modern_card("SOLDE / الرصيد", "0.00", colors.PRIMARY, "💰")
        self.card_inventory = self.create_modern_card("STOCK / المخزون", "0.00", colors.WARNING, "📦")

        cards_layout.addWidget(self.card_income)
        cards_layout.addWidget(self.card_expenses)
        cards_layout.addWidget(self.card_profit)
        cards_layout.addWidget(self.card_inventory)
        self.main_layout.addLayout(cards_layout)

        # --- Content Area (Chart + Table) ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Chart Container
        self.chart_frame = self.create_container("Analyse des Flux / تحليل التدفقات")
        self.figure, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        if THEME_AVAILABLE:
            self.figure.patch.set_facecolor(colors.BG_CARD)
            self.ax.set_facecolor(colors.BG_CARD)
        else:
            self.figure.patch.set_facecolor(colors.BG_CARD)
        self.canvas = FigureCanvas(self.figure)
        self.chart_frame.layout().addWidget(self.canvas)
        content_layout.addWidget(self.chart_frame, 4)

        # Recent Transactions Table Container
        self.table_frame = self.create_container("Transactions Récentes / أحدث العمليات")
        self.table_recent = QTableWidget()
        self.style_table(self.table_recent)
        self.table_recent.setColumnCount(4)
        self.table_recent.setHorizontalHeaderLabels(["Type", "Source/Desc", "Montant", "Date"])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_recent.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.table_frame.layout().addWidget(self.table_recent)
        content_layout.addWidget(self.table_frame, 6)

        self.main_layout.addLayout(content_layout)

    def create_modern_card(self, title, value, color, icon):
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        card = QFrame()
        card.setFixedHeight(140)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {colors.BG_CARD};
                border-radius: 12px;
                border: 1px solid {colors.BORDER};
                border-left: 6px solid {color};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(15, 23, 42, 15))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Top row: Title and Icon
        top_layout = QHBoxLayout()
        lbl_title = QLabel(title)
        if THEME_AVAILABLE:
            lbl_title.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; font-weight: bold; font-size: 12px; text-transform: uppercase;")
        else:
            lbl_title.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-weight: bold; font-size: 12px; text-transform: uppercase;")
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(
            f"color: {color}; font-size: 20px; background-color: {rgba(color, 32)}; border-radius: 15px; padding: 5px;"
        )
        lbl_icon.setFixedSize(40, 40)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        top_layout.addWidget(lbl_title)
        top_layout.addStretch()
        top_layout.addWidget(lbl_icon)
        
        layout.addLayout(top_layout)
        
        # Value
        lbl_value = QLabel(value)
        lbl_value.setObjectName("val_label")
        if THEME_AVAILABLE:
            lbl_value.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 28px; font-weight: 800; border: none; background: transparent;")
        else:
            lbl_value.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-size: 28px; font-weight: 800; border: none; background: transparent;")
        
        layout.addWidget(lbl_value)
        return card

    def create_container(self, title_text):
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: %(bg)s; 
                border-radius: 12px; 
                border: 1px solid %(border)s;
            }
        """ % {
            "bg": colors.BG_CARD if colors else "white",
            "border": colors.BORDER,
        })
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(15, 23, 42, 15))
        shadow.setOffset(0, 4)
        frame.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            title.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_PRIMARY}; margin-bottom: 10px; border: none;")
        else:
            title.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; margin-bottom: 10px; border: none;")
        
        layout.addWidget(title)
        return frame

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())
        else:
            colors = Colors()
            table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {colors.BG_CARD};
                    border: none;
                    gridline-color: {colors.BORDER};
                    font-size: 13px;
                    color: {colors.TEXT_PRIMARY};
                }}
                QTableWidget::item {{
                    padding: 8px;
                    border-bottom: 1px solid {colors.BG_MAIN};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors.PRIMARY};
                    color: white;
                }}
                QHeaderView::section {{
                    background-color: {colors.BG_MAIN};
                    color: {colors.TEXT_SECONDARY};
                    padding: 10px;
                    border: none;
                    font-weight: bold;
                    text-transform: uppercase;
                    font-size: 11px;
                }}
            """)

    def refresh_data(self):
        try:
            with DatabaseManager() as db_manager:
                conn = db_manager.get_connection()
                cursor = conn.cursor()

                def _to_float(value):
                    try:
                        return float(value)
                    except Exception:
                        return 0.0

                # Income
                try:
                    cursor.execute("SELECT SUM(amount_paid) FROM Payments")
                    res_inc = cursor.fetchone()[0]
                    inc = _to_float(res_inc)
                except Exception:
                    inc = 0.0 
                
                # Expenses
                try:
                    cursor.execute("SELECT SUM(amount) FROM Expenses")
                    res_exp = cursor.fetchone()[0]
                    exp = _to_float(res_exp)
                except Exception:
                    exp = 0.0

                solde = inc - exp
                self.last_income = float(inc)
                self.last_expenses = float(exp)
                self.last_balance = float(solde)

                # Update Labels
                self.card_income.findChild(QLabel, "val_label").setText(f"{inc:,.0f} FCFA")
                self.card_expenses.findChild(QLabel, "val_label").setText(f"{exp:,.0f} FCFA")
                self.card_profit.findChild(QLabel, "val_label").setText(f"{solde:,.0f} FCFA")
                
                # Inventory Value
                try:
                    cursor.execute("SELECT SUM(quantity * unit_price) FROM InventoryItems")
                    res_inv = cursor.fetchone()[0]
                    inventory_val = _to_float(res_inv)
                    self.last_inventory = float(inventory_val)
                    self.card_inventory.findChild(QLabel, "val_label").setText(f"{inventory_val:,.0f} FCFA")
                except Exception:
                    self.last_inventory = 0.0
                    self.card_inventory.findChild(QLabel, "val_label").setText("0 FCFA")

                # Chart
                self.ax.clear()
                if inc > 0 or exp > 0:
                    if THEME_AVAILABLE:
                        theme_colors = ThemeManager.get_colors()
                        colors = [theme_colors.SUCCESS, theme_colors.DANGER]
                        text_color = theme_colors.TEXT_PRIMARY
                    else:
                        colors = [Colors().SUCCESS, Colors().DANGER]
                        text_color = Colors().TEXT_PRIMARY
                    wedges, texts, autotexts = self.ax.pie(
                        [inc, exp], labels=['Recettes', 'Dépenses'], 
                        autopct='%1.1f%%', startangle=90, colors=colors,
                        wedgeprops={'width': 0.5, 'edgecolor': 'w'}, # Donut
                        textprops={'color': text_color}
                    )
                    plt.setp(autotexts, size=9, weight="bold", color="white")
                else:
                    if THEME_AVAILABLE:
                        self.ax.text(0.5, 0.5, "Pas de données", ha='center', va='center', color=ThemeManager.get_colors().TEXT_SECONDARY)
                    else:
                        self.ax.text(0.5, 0.5, "Pas de données", ha='center', va='center', color=Colors().TEXT_SECONDARY)
                
                self.canvas.draw()

                # Table (Union of Income and Expenses - Date formatted for safe ordering)
                self.table_recent.setRowCount(0)
                try:
                    query = """
                        SELECT 'Entrée',
                               TRIM(COALESCE(S.last_name_fr, '') || ' ' || COALESCE(S.first_name_fr, '')),
                               COALESCE(P.amount_paid, 0),
                               substr(COALESCE(P.transaction_date, ''), 1, 10) AS t_date
                        FROM Payments P LEFT JOIN Students S ON P.student_id = S.id 
                        UNION ALL
                        SELECT 'Sortie', COALESCE(description, '-'), COALESCE(amount, 0), substr(COALESCE(expense_date, ''), 1, 10) AS t_date 
                        FROM Expenses
                        ORDER BY t_date DESC LIMIT 15
                    """
                    cursor.execute(query)
                    recent_rows = cursor.fetchall()
                    self.last_recent_transactions = recent_rows
                    
                    for row in recent_rows:
                        r_idx = self.table_recent.rowCount()
                        self.table_recent.insertRow(r_idx)
                        
                        type_val = "Recette" if row[0] == 'Entrée' else "Dépense"
                        type_item = QTableWidgetItem(type_val)
                        if row[0] == 'Entrée':
                            if THEME_AVAILABLE:
                                type_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                            else:
                                type_item.setForeground(QColor(Colors().SUCCESS))
                        else:
                            if THEME_AVAILABLE:
                                type_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                            else:
                                type_item.setForeground(QColor(Colors().DANGER))
                        
                        source_text = (str(row[1] or "-")).strip() or "-"
                        amount_val = _to_float(row[2])
                        date_text = str(row[3] or "-")

                        self.table_recent.setItem(r_idx, 0, type_item)
                        self.table_recent.setItem(r_idx, 1, QTableWidgetItem(source_text))
                        self.table_recent.setItem(r_idx, 2, QTableWidgetItem(f"{amount_val:,.0f}"))
                        self.table_recent.setItem(r_idx, 3, QTableWidgetItem(date_text))
                except Exception as e:
                    self.last_recent_transactions = []
                    print(f"Dashboard Recent Transactions Error: {e}")

        except Exception as e:
            print(f"Dashboard Error: {e}")

    def export_executive_report_pdf(self):
        pdf = FPDF()
        pdf.add_page()

        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, "RAPPORT EXECUTIF FINANCIER")

        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 7, f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
        pdf.ln(2)

        apply_table_header_style(pdf, "Arial", 10)
        pdf.cell(0, 8, "Indicateurs Financiers", 1, 1, 'L', True)
        apply_table_body_style(pdf, "Arial", 10)

        kpis = [
            ("Total Revenus", f"{self.last_income:,.0f} FCFA"),
            ("Total Dépenses", f"{self.last_expenses:,.0f} FCFA"),
            ("Solde Net", f"{self.last_balance:,.0f} FCFA"),
            ("Valeur du Stock", f"{self.last_inventory:,.0f} FCFA"),
        ]
        for idx, (label, value) in enumerate(kpis):
            set_zebra_row_fill(pdf, idx)
            pdf.cell(100, 8, label, 1, 0, 'L', True)
            pdf.cell(90, 8, value, 1, 1, 'R', True)

        pdf.ln(3)
        apply_table_header_style(pdf, "Arial", 10)
        pdf.cell(0, 8, "Transactions Récentes", 1, 1, 'L', True)

        headers = ["Type", "Source/Desc", "Montant", "Date"]
        widths = [30, 85, 35, 40]
        apply_table_header_style(pdf, "Arial", 9)
        for i, h in enumerate(headers):
            pdf.cell(widths[i], 8, h, 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, "Arial", 8)
        for idx, row in enumerate(self.last_recent_transactions[:12]):
            set_zebra_row_fill(pdf, idx)
            entry_type = "Recette" if row[0] == 'Entrée' else "Dépense"
            source = str(row[1] or "-")
            amount = f"{float(row[2] or 0):,.0f}"
            date_str = str(row[3] or "-")

            values = [entry_type, source, amount, date_str]
            for i, val in enumerate(values):
                text = str(val).encode('latin-1', 'ignore').decode('latin-1')
                align = 'R' if i == 2 else 'L'
                pdf.cell(widths[i], 7, text, 1, 0, align, True)
            pdf.ln()

        mode = get_report_output_mode("finance_dashboard_report_mode", FINANCE_DASHBOARD_REPORT_MODE)
        output_pdf(
            pdf,
            self,
            default_name=f"Rapport_Executif_Finance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=mode,
            dialog_title="Exporter Rapport Exécutif",
            success_save_message="Rapport exécutif exporté.",
            success_print_message="Rapport exécutif envoyé à l'imprimante.",
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernFinanceDashboard()
    window.show()
    sys.exit(app.exec())