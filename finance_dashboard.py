import sys
from datetime import datetime

from fpdf import FPDF
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
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
from ui_components import BaseWindow, create_card, style_table, styled_button
from ui_styles import Colors, ThemeManager, get_module_caps, rgba

FINANCE_DASHBOARD_REPORT_MODE = get_report_output_mode("finance_dashboard_report_mode", "save")


def _to_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


class ModernFinanceDashboard(BaseWindow):
    def __init__(self):
        super().__init__(title="Tableau de Bord Financier / لوحة التحكم المالية", min_width=1100, min_height=700)
        self.last_income = 0.0
        self.last_expenses = 0.0
        self.last_balance = 0.0
        self.last_inventory = 0.0
        self.last_recent_transactions = []

        self.init_ui()
        self.refresh_data()

    def apply_rbac(self, role: str) -> None:
        """لوحة قراءة فقط — لا توجد أزرار كتابة للتحكم بها."""
        pass  # read-only dashboard

    def init_ui(self):
        self.main_layout.setSpacing(20)
        colors = ThemeManager.get_colors()

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {colors.BG_HEADER};
                border-radius: 10px;
            }}
        """
        )
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
        title_label.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        sub_label = QLabel("Vue d'ensemble des revenus et dépenses / نظرة عامة")
        sub_label.setFont(QFont("Cairo", 11))
        sub_label.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)

        date_label = QLabel(datetime.now().strftime("%d %B %Y"))
        date_label.setFont(QFont("Segoe UI", 12))
        date_label.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        header_layout.addWidget(icon_lbl)
        header_layout.addSpacing(15)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_export = styled_button(
            "📄 Rapport Exécutif",
            bg_color=ThemeManager.get_colors().SUCCESS,
            hover_color=ThemeManager.get_colors().SUCCESS_HOVER,
            min_height=38,
        )
        btn_export.clicked.connect(self.export_executive_report_pdf)

        header_layout.addWidget(btn_export)
        header_layout.addSpacing(10)
        header_layout.addWidget(date_label)

        self.main_layout.addWidget(header_frame)

        # --- Cards ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        self.card_income, self.lbl_income_val = self.create_modern_card(
            "REVENUS / المداخيل", "0.00", colors.SUCCESS, "↗"
        )
        self.card_expenses, self.lbl_expenses_val = self.create_modern_card(
            "DÉPENSES / المصاريف", "0.00", colors.DANGER, "↘"
        )
        self.card_profit, self.lbl_profit_val = self.create_modern_card("SOLDE / الرصيد", "0.00", colors.PRIMARY, "💰")
        self.card_inventory, self.lbl_inventory_val = self.create_modern_card(
            "STOCK / المخزون", "0.00", colors.WARNING, "📦"
        )

        cards_layout.addWidget(self.card_income)
        cards_layout.addWidget(self.card_expenses)
        cards_layout.addWidget(self.card_profit)
        cards_layout.addWidget(self.card_inventory)
        self.main_layout.addLayout(cards_layout)

        # --- Content Area (Chart + Table) ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Chart Container
        self.chart_frame, chart_layout = create_card("Analyse des Flux / تحليل التدفقات", with_shadow=True)
        # Use the object-oriented Figure so it is owned by the canvas and
        # garbage-collected — the pyplot helper keeps a global reference that would
        # leak a figure every time this dashboard is rebuilt.
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.figure.patch.set_facecolor(colors.BG_CARD)
        self.ax.set_facecolor(colors.BG_CARD)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        content_layout.addWidget(self.chart_frame, 4)

        # Recent Transactions Table Container
        self.table_frame, table_layout = create_card("Transactions Récentes / أحدث العمليات", with_shadow=True)
        self.table_recent = QTableWidget()
        style_table(self.table_recent)
        self.table_recent.setColumnCount(4)
        self.table_recent.setHorizontalHeaderLabels(["Type", "Source/Desc", "Montant", "Date"])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_recent.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        table_layout.addWidget(self.table_recent)
        content_layout.addWidget(self.table_frame, 6)

        self.main_layout.addLayout(content_layout)

    def create_modern_card(self, title, value, color, icon):
        colors = ThemeManager.get_colors()
        card = QFrame()
        card.setFixedHeight(140)
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {colors.BG_CARD};
                border-radius: 16px;
                border: 1px solid {colors.BORDER};
                border-left: 6px solid {color};
            }}
        """
        )

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
        lbl_title.setStyleSheet(
            f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; font-weight: bold; font-size: 12px; text-transform: uppercase;"
        )
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
        lbl_value.setStyleSheet(
            f"color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 28px; font-weight: 800; border: none; background: transparent;"
        )
        layout.addWidget(lbl_value)
        # FIX 1: Return the value label alongside the card so callers hold a
        # direct reference instead of using fragile findChild(QLabel, "val_label"),
        # which returns None if the layout hierarchy ever changes.
        return card, lbl_value

    def refresh_data(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                # FIX 2: Coerce to float here — repo returns None when no rows
                # exist, and `inc - exp` raises TypeError on NoneType operands.
                inc = float(repo.get_total_income() or 0)
                exp = float(repo.get_total_expenses() or 0)
                inventory_val = float(repo.get_total_inventory_value() or 0)
                try:
                    recent_rows = repo.get_recent_transactions(limit=15)
                    self.last_recent_transactions = recent_rows
                except Exception as e:
                    recent_rows = []
                    self.last_recent_transactions = []
                    AppLogger.error("FinanceDashboard", f"Dashboard Recent Transactions Error: {e}")

            solde = inc - exp
            self.last_income = inc
            self.last_expenses = exp
            self.last_balance = solde
            self.last_inventory = inventory_val

            # FIX 1: Use stored label references instead of fragile findChild().
            self.lbl_income_val.setText(f"{inc:,.0f} FCFA")
            self.lbl_expenses_val.setText(f"{exp:,.0f} FCFA")
            self.lbl_profit_val.setText(f"{solde:,.0f} FCFA")
            self.lbl_inventory_val.setText(f"{inventory_val:,.0f} FCFA")

            # Chart
            self.ax.clear()
            if inc > 0 or exp > 0:
                theme_colors = ThemeManager.get_colors()
                colors = [theme_colors.SUCCESS, theme_colors.DANGER]
                text_color = theme_colors.TEXT_PRIMARY
                wedges, texts, autotexts = self.ax.pie(
                    [inc, exp],
                    labels=['Recettes', 'Dépenses'],
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=colors,
                    wedgeprops={'width': 0.5, 'edgecolor': 'w'},  # Donut
                    textprops={'color': text_color},
                )
                # FIX 5: Use object-method calls instead of plt.setp() —
                # the global pyplot call can affect other embedded figures.
                for autotext in autotexts:
                    autotext.set_size(9)
                    autotext.set_weight("bold")
                    autotext.set_color("white")
            else:
                self.ax.text(
                    0.5, 0.5, "Pas de données", ha='center', va='center', color=ThemeManager.get_colors().TEXT_SECONDARY
                )
            self.canvas.draw()

            # Table (recent transactions)
            self.table_recent.setRowCount(0)
            for row in recent_rows:
                r_idx = self.table_recent.rowCount()
                self.table_recent.insertRow(r_idx)

                type_val = "Recette" if row[0] == 'Entrée' else "Dépense"
                type_item = QTableWidgetItem(type_val)
                if row[0] == 'Entrée':
                    type_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                else:
                    type_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                source_text = (str(row[1] or "-")).strip() or "-"
                amount_val = _to_float(row[2])
                date_text = str(row[3] or "-")

                self.table_recent.setItem(r_idx, 0, type_item)
                self.table_recent.setItem(r_idx, 1, QTableWidgetItem(source_text))
                self.table_recent.setItem(r_idx, 2, QTableWidgetItem(f"{amount_val:,.0f}"))
                self.table_recent.setItem(r_idx, 3, QTableWidgetItem(date_text))

        except Exception as e:
            AppLogger.error("FinanceDashboard", f"Dashboard Error: {e}")

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

        # FIX 3: FINANCE_DASHBOARD_REPORT_MODE is already the resolved value.
        mode = FINANCE_DASHBOARD_REPORT_MODE
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
