import sys
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QMessageBox, QGroupBox, QTabWidget, QFrame, 
                             QGridLayout, QGraphicsDropShadowEffect, QDateEdit,
                             QFileDialog, QProgressBar)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, LineChart, Reference
from fpdf import FPDF
from database_setup import DatabaseManager

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, Colors, get_tabs_style

THEME_AVAILABLE = True

# --- Worker Thread for Heavy Report Generation ---
class ReportWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)  # Success message or file path
    error = pyqtSignal(str)

    def __init__(self, report_type, params):
        super().__init__()
        self.report_type = report_type
        self.params = params

    def _get_active_year_context(self, cursor):
        cursor.execute("SELECT id, year_label FROM AcademicYears WHERE is_active=1 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

        cursor.execute("SELECT id, year_label FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

        return None, "N/A"

    def run(self):
        try:
            if self.report_type == "excel_financial":
                result = self.generate_financial_excel()
            elif self.report_type == "excel_students":
                result = self.generate_students_excel()
            elif self.report_type == "excel_attendance":
                result = self.generate_attendance_excel()
            elif self.report_type == "excel_grades":
                result = self.generate_grades_excel()
            elif self.report_type == "pdf_comprehensive":
                result = self.generate_comprehensive_pdf()
            else:
                result = "Type de rapport inconnu"
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def generate_financial_excel(self):
        """Generate comprehensive financial Excel report"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Rapport Financier"
        selected_period = self.params.get("period", "12 derniers mois") if self.params else "12 derniers mois"
        
        # Header styling
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        
        # Title
        ws['A1'] = "RAPPORT FINANCIER COMPLET"
        ws['A1'].font = Font(bold=True, size=16, color="1E293B")
        ws.merge_cells('A1:F1')
        
        ws['A2'] = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws.merge_cells('A2:F2')
        ws['A3'] = f"Période: {selected_period}"
        ws.merge_cells('A3:F3')
        
        self.progress.emit(20)
        
        # Income Section
        ws['A4'] = "RECETTES (Paiements Étudiants)"
        ws['A4'].font = Font(bold=True, size=14)
        
        ws['A5'] = "Mois"
        ws['B5'] = "Nb Paiements"
        ws['C5'] = "Montant Total"
        for cell in ['A5', 'B5', 'C5']:
            ws[cell].fill = header_fill
            ws[cell].font = header_font
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()

            income_filter = "transaction_date IS NOT NULL"
            expense_filter = "expense_date IS NOT NULL"
            income_params = []
            expense_params = []

            if selected_period == "6 derniers mois":
                income_filter += " AND date(transaction_date) >= date('now', 'start of month', '-5 months')"
                expense_filter += " AND date(expense_date) >= date('now', 'start of month', '-5 months')"
            elif selected_period == "12 derniers mois":
                income_filter += " AND date(transaction_date) >= date('now', 'start of month', '-11 months')"
                expense_filter += " AND date(expense_date) >= date('now', 'start of month', '-11 months')"
            elif selected_period == "Année en cours":
                current_year = datetime.now().strftime('%Y')
                income_filter += " AND strftime('%Y', transaction_date) = ?"
                expense_filter += " AND strftime('%Y', expense_date) = ?"
                income_params.append(current_year)
                expense_params.append(current_year)
            
            # Get monthly income
            cursor.execute(f"""
                SELECT strftime('%Y-%m', transaction_date) as month,
                    COUNT(*) as count,
                    SUM(amount_paid) as total
                FROM Payments
                WHERE {income_filter}
                GROUP BY month
                ORDER BY month
            """, income_params)
            
            row = 6
            total_income = 0
            for month, count, total in cursor.fetchall():
                ws[f'A{row}'] = month
                ws[f'B{row}'] = count
                ws[f'C{row}'] = f"{total:,.0f} FCFA"
                total_income += total if total else 0
                row += 1
            
            ws[f'A{row}'] = "TOTAL RECETTES"
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'C{row}'] = f"{total_income:,.0f} FCFA"
            ws[f'C{row}'].font = Font(bold=True, color="10B981")
            
            self.progress.emit(50)
            
            # Expenses Section
            ws[f'A{row+2}'] = "DÉPENSES"
            ws[f'A{row+2}'].font = Font(bold=True, size=14)
            
            header_row = row + 3
            ws[f'A{header_row}'] = "Mois"
            ws[f'B{header_row}'] = "Nb Dépenses"
            ws[f'C{header_row}'] = "Montant Total"
            for cell in [f'A{header_row}', f'B{header_row}', f'C{header_row}']:
                ws[cell].fill = header_fill
                ws[cell].font = header_font
            
            cursor.execute(f"""
                SELECT strftime('%Y-%m', expense_date) as month,
                    COUNT(*) as count,
                    SUM(amount) as total
                FROM Expenses
                WHERE {expense_filter}
                GROUP BY month
                ORDER BY month
            """, expense_params)
            
            exp_row = header_row + 1
            total_expenses = 0
            for month, count, total in cursor.fetchall():
                ws[f'A{exp_row}'] = month
                ws[f'B{exp_row}'] = count
                ws[f'C{exp_row}'] = f"{total:,.0f} FCFA"
                total_expenses += total if total else 0
                exp_row += 1
            
            ws[f'A{exp_row}'] = "TOTAL DÉPENSES"
            ws[f'A{exp_row}'].font = Font(bold=True)
            ws[f'C{exp_row}'] = f"{total_expenses:,.0f} FCFA"
            ws[f'C{exp_row}'].font = Font(bold=True, color="EF4444")
            
            self.progress.emit(80)
            
            # Balance
            balance = total_income - total_expenses
            ws[f'A{exp_row+2}'] = "SOLDE NET"
            ws[f'A{exp_row+2}'].font = Font(bold=True, size=14)
            ws[f'C{exp_row+2}'] = f"{balance:,.0f} FCFA"
            ws[f'C{exp_row+2}'].font = Font(bold=True, size=14, color="10B981" if balance >= 0 else "EF4444")
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 20
        
        # Save file
        safe_period = selected_period.encode('ascii', 'ignore').decode('ascii')
        safe_period = safe_period.replace(" ", "_").replace("'", "").replace("/", "-")
        if not safe_period:
            safe_period = "periode"
        filename = f"Rapport_Financier_{safe_period}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        filepath = self.params.get("output_path") if self.params else None
        if not filepath:
            filepath = os.path.join(os.getcwd(), filename)
        wb.save(filepath)
        
        self.progress.emit(100)
        return filepath

    def generate_students_excel(self):
        """Generate student list with statistics"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Liste Étudiants"
        
        # Header
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            active_year_id, active_year_label = self._get_active_year_context(cursor)

        ws['A1'] = "LISTE DES ÉTUDIANTS"
        ws['A1'].font = Font(bold=True, size=16, color="1E293B")
        ws.merge_cells('A1:F1')
        ws['A2'] = f"Année scolaire: {active_year_label}"
        ws.merge_cells('A2:F2')

        headers = ["ID", "Nom Complet", "Classe", "Sexe", "Date Naissance", "Statut"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        
        self.progress.emit(30)
        
        # Get students
        with db.get_connection() as conn:
            cursor = conn.cursor()
            if active_year_id:
                cursor.execute("SELECT COUNT(*) FROM StudentClassNumbers WHERE year_id=?", (active_year_id,))
                has_year_rows = cursor.fetchone()[0] > 0
            else:
                has_year_rows = False

            if has_year_rows:
                cursor.execute("""
                    SELECT s.id,
                        s.first_name_fr || ' ' || s.last_name_fr as name,
                        c.class_name_fr,
                        CASE WHEN s.gender=0 THEN 'M' ELSE 'F' END as gender,
                        s.birth_date,
                        s.status
                    FROM Students s
                    LEFT JOIN Classes c ON s.class_id = c.id
                    JOIN StudentClassNumbers scn ON scn.student_id = s.id AND scn.year_id = ?
                    WHERE s.status='Active'
                    ORDER BY c.class_name_fr, name
                """, (active_year_id,))
            else:
                cursor.execute("""
                    SELECT s.id,
                        s.first_name_fr || ' ' || s.last_name_fr as name,
                        c.class_name_fr,
                        CASE WHEN s.gender=0 THEN 'M' ELSE 'F' END as gender,
                        s.birth_date,
                        s.status
                    FROM Students s
                    LEFT JOIN Classes c ON s.class_id = c.id
                    WHERE s.status='Active'
                    ORDER BY c.class_name_fr, name
                """)
            rows = cursor.fetchall()
            
        for row, student in enumerate(rows, 5):
            for col, value in enumerate(student, 1):
                ws.cell(row=row, column=col, value=value)
            
            if row % 20 == 0:
                self.progress.emit(30 + (row * 60 // 200))
        
        # Adjust widths
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 12
        
        # Save
        filename = f"Liste_Etudiants_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        filepath = self.params.get("output_path") if self.params else None
        if not filepath:
            filepath = os.path.join(os.getcwd(), filename)
        wb.save(filepath)
        
        self.progress.emit(100)
        return filepath

    def generate_attendance_excel(self):
        """Generate attendance report grouped by class"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Assiduite"

        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        ws['A1'] = "RAPPORT D'ASSIDUITÉ"
        ws['A1'].font = Font(bold=True, size=16, color="1E293B")
        ws.merge_cells('A1:G1')
        ws['A2'] = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws.merge_cells('A2:G2')

        headers = ["Classe", "Nb Étudiants", "Présents", "Absents", "Retards", "Total Pointages", "Taux Absence %"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font

        self.progress.emit(20)

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            active_year_id, active_year_label = self._get_active_year_context(cursor)

            ws['A3'] = f"Année scolaire: {active_year_label}"
            ws.merge_cells('A3:G3')

            if active_year_id:
                cursor.execute("SELECT COUNT(*) FROM StudentAttendance WHERE year_id=?", (active_year_id,))
                has_year_rows = cursor.fetchone()[0] > 0
            else:
                has_year_rows = False

            attendance_join_filter = "AND SA.year_id=?"
            attendance_params = [active_year_id]

            if not has_year_rows:
                attendance_join_filter = "AND (SA.year_id IS NULL OR SA.year_id=?)" if active_year_id else ""
                attendance_params = [active_year_id] if active_year_id else []

            cursor.execute(f"""
                SELECT C.class_name_fr,
                       COUNT(DISTINCT S.id) AS students_count,
                       SUM(CASE WHEN SA.status='Present' THEN 1 ELSE 0 END) AS presents,
                       SUM(CASE WHEN SA.status='Absent' THEN 1 ELSE 0 END) AS absents,
                       SUM(CASE WHEN SA.status='Retard' THEN 1 ELSE 0 END) AS lates,
                       COUNT(SA.id) AS attendance_rows
                FROM Classes C
                LEFT JOIN Students S ON S.class_id = C.id AND S.status='Active'
                LEFT JOIN StudentAttendance SA ON SA.student_id = S.id {attendance_join_filter}
                GROUP BY C.id, C.class_name_fr
                ORDER BY C.sort_order, C.class_name_fr
            """, attendance_params)
            rows = cursor.fetchall()

        row_idx = 5
        for idx, row in enumerate(rows, 1):
            class_name, students_count, presents, absents, lates, attendance_rows = row
            presents = presents or 0
            absents = absents or 0
            lates = lates or 0
            attendance_rows = attendance_rows or 0
            absence_rate = (absents / attendance_rows * 100) if attendance_rows else 0

            ws.cell(row=row_idx, column=1, value=class_name or "-")
            ws.cell(row=row_idx, column=2, value=students_count or 0)
            ws.cell(row=row_idx, column=3, value=presents)
            ws.cell(row=row_idx, column=4, value=absents)
            ws.cell(row=row_idx, column=5, value=lates)
            ws.cell(row=row_idx, column=6, value=attendance_rows)
            ws.cell(row=row_idx, column=7, value=round(absence_rate, 2))
            row_idx += 1

            if idx % 5 == 0:
                self.progress.emit(min(90, 20 + idx * 5))

        for col, width in zip(['A', 'B', 'C', 'D', 'E', 'F', 'G'], [24, 15, 12, 12, 12, 16, 14]):
            ws.column_dimensions[col].width = width

        filename = f"Rapport_Assiduite_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        filepath = self.params.get("output_path") if self.params else None
        if not filepath:
            filepath = os.path.join(os.getcwd(), filename)
        wb.save(filepath)

        self.progress.emit(100)
        return filepath

    def generate_grades_excel(self):
        """Generate grade summary report grouped by class"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Notes"

        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        ws['A1'] = "RAPPORT GLOBAL DES NOTES"
        ws['A1'].font = Font(bold=True, size=16, color="1E293B")
        ws.merge_cells('A1:F1')
        ws['A2'] = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws.merge_cells('A2:F2')

        headers = ["Classe", "Nb Étudiants", "Nb Notes", "Min", "Moyenne", "Max"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font

        self.progress.emit(20)

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            active_year_id, active_year_label = self._get_active_year_context(cursor)

            ws['A3'] = f"Année scolaire: {active_year_label}"
            ws.merge_cells('A3:F3')

            if active_year_id:
                cursor.execute("SELECT COUNT(*) FROM Grades WHERE year_id=?", (active_year_id,))
                has_year_rows = cursor.fetchone()[0] > 0
            else:
                has_year_rows = False

            grades_join_filter = "AND G.year_id=?"
            grades_params = [active_year_id]

            if not has_year_rows:
                grades_join_filter = "AND (G.year_id IS NULL OR G.year_id=?)" if active_year_id else ""
                grades_params = [active_year_id] if active_year_id else []

            cursor.execute(f"""
                SELECT C.class_name_fr,
                       COUNT(DISTINCT S.id) AS students_count,
                       COUNT(G.id) AS grades_count,
                       MIN(G.score) AS min_score,
                       AVG(G.score) AS avg_score,
                       MAX(G.score) AS max_score
                FROM Classes C
                LEFT JOIN Students S ON S.class_id = C.id AND S.status='Active'
                LEFT JOIN Grades G ON G.student_id = S.id AND G.score IS NOT NULL {grades_join_filter}
                GROUP BY C.id, C.class_name_fr
                ORDER BY C.sort_order, C.class_name_fr
            """, grades_params)
            rows = cursor.fetchall()

        row_idx = 5
        for idx, row in enumerate(rows, 1):
            class_name, students_count, grades_count, min_score, avg_score, max_score = row
            ws.cell(row=row_idx, column=1, value=class_name or "-")
            ws.cell(row=row_idx, column=2, value=students_count or 0)
            ws.cell(row=row_idx, column=3, value=grades_count or 0)
            ws.cell(row=row_idx, column=4, value=round(min_score, 2) if min_score is not None else "-")
            ws.cell(row=row_idx, column=5, value=round(avg_score, 2) if avg_score is not None else "-")
            ws.cell(row=row_idx, column=6, value=round(max_score, 2) if max_score is not None else "-")
            row_idx += 1

            if idx % 5 == 0:
                self.progress.emit(min(90, 20 + idx * 5))

        for col, width in zip(['A', 'B', 'C', 'D', 'E', 'F'], [24, 15, 12, 10, 12, 10]):
            ws.column_dimensions[col].width = width

        filename = f"Rapport_Notes_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        filepath = self.params.get("output_path") if self.params else None
        if not filepath:
            filepath = os.path.join(os.getcwd(), filename)
        wb.save(filepath)

        self.progress.emit(100)
        return filepath

    def generate_comprehensive_pdf(self):
        """Generate PDF with embedded charts"""
        return "Génération PDF en développement... Veuillez utiliser l'export Excel pour le moment."


class AdvancedReportsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rapports Avancés / التقارير المتقدمة")
        self.setMinimumSize(1100, 700)
        
        # Apply theme
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
                QGroupBox {{
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    margin-top: 10px;
                    background-color: {colors.BG_CARD};
                    font-weight: bold;
                    color: {colors.TEXT_SECONDARY};
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                    left: 10px;
                }}
                QTabWidget::pane {{
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    background: {colors.BG_CARD};
                }}
                QTabBar::tab {{
                    background: {colors.BG_MAIN};
                    color: {colors.TEXT_SECONDARY};
                    padding: 12px 20px;
                    margin-right: 2px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: bold;
                }}
                QTabBar::tab:selected {{
                    background: {colors.BG_HEADER};
                    color: {colors.HEADER_TEXT};
                }}
            """)
        
        self.worker = None
        self.init_ui()

    def _get_active_year_context(self, cursor):
        cursor.execute("SELECT id, year_label FROM AcademicYears WHERE is_active=1 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

        cursor.execute("SELECT id, year_label FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

        return None, "N/A"

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        if THEME_AVAILABLE:
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {ThemeManager.get_colors().BG_HEADER};
                    border-radius: 12px;
                }}
            """)
        else:
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_HEADER};
                    border-radius: 12px;
                }}
            """)
        header_frame.setFixedHeight(80)
        
        # Shadow
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
        title = QLabel("RAPPORTS AVANCÉS & ANALYSES")
        if THEME_AVAILABLE:
            title.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; font-size: 20px; font-weight: bold; background: transparent;")
        else:
            title.setStyleSheet(f"color: {colors.HEADER_TEXT}; font-size: 20px; font-weight: bold; background: transparent;")
        
        subtitle = QLabel("Visualisations, Graphiques & Export Excel")
        if THEME_AVAILABLE:
            subtitle.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        else:
            subtitle.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        
        header_layout.addWidget(icon_lbl)
        header_layout.addSpacing(15)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)

        # Tabs
        tabs = QTabWidget()
        if THEME_AVAILABLE:
            tabs.setStyleSheet(get_tabs_style())
        
        # Tab 1: Financial Charts
        tabs.addTab(self.create_financial_charts_tab(), "📊 Graphiques Financiers")
        
        # Tab 2: Student Performance
        tabs.addTab(self.create_student_reports_tab(), "📈 Performance Étudiants")
        
        # Tab 3: Excel Exports
        tabs.addTab(self.create_excel_exports_tab(), "📑 Export Excel")
        
        layout.addWidget(tabs)

    def create_card(self):
        """Helper to create a white card"""
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_CARD}; 
                    border-radius: 12px; 
                    border: 1px solid {colors.BORDER};
                }}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 10))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame
        
    def styled_combo(self):
        combo = QComboBox()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 6px 12px;
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    background: {colors.INPUT_BG};
                    color: {colors.TEXT_PRIMARY};
                }}
                QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 6px 12px;
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    background: {colors.INPUT_BG};
                    color: {colors.TEXT_PRIMARY};
                }}
                QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        combo.setMinimumHeight(38)
        return combo

    def create_financial_charts_tab(self):
        """Financial visualizations with matplotlib"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Controls Card
        control_card = self.create_card()
        controls_layout = QHBoxLayout(control_card)
        controls_layout.setContentsMargins(15, 15, 15, 15)
        
        controls_layout.addWidget(QLabel("Période:"))
        self.period_combo = self.styled_combo()
        self.period_combo.addItems(["6 derniers mois", "12 derniers mois", "Année en cours"])
        controls_layout.addWidget(self.period_combo)
        
        btn_generate = QPushButton("🔄 Actualiser Graphique")
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_generate.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.PRIMARY};
                    color: white;
                    padding: 8px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_generate.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.PRIMARY};
                    color: white;
                    padding: 8px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_generate.clicked.connect(self.generate_financial_chart)
        controls_layout.addWidget(btn_generate)
        controls_layout.addStretch()
        
        layout.addWidget(control_card)
        
        # Chart Card
        chart_card = self.create_card()
        c_layout = QVBoxLayout(chart_card)
        
        self.financial_figure = Figure(figsize=(10, 6))
        if THEME_AVAILABLE:
            self.financial_figure.patch.set_facecolor(ThemeManager.get_colors().BG_CARD)
        else:
            self.financial_figure.patch.set_facecolor(Colors().BG_CARD)
        self.financial_canvas = FigureCanvas(self.financial_figure)
        c_layout.addWidget(self.financial_canvas)
        
        layout.addWidget(chart_card)
        
        # Generate initial chart
        self.generate_financial_chart()
        
        return widget

    def generate_financial_chart(self):
        """Generate income vs expenses chart"""
        self.financial_figure.clear()
        ax = self.financial_figure.add_subplot(111)
        selected_period = self.period_combo.currentText() if hasattr(self, 'period_combo') else "12 derniers mois"

        income_filter = "transaction_date IS NOT NULL"
        expense_filter = "expense_date IS NOT NULL"
        income_params = []
        expense_params = []

        if selected_period == "6 derniers mois":
            income_filter += " AND date(transaction_date) >= date('now', 'start of month', '-5 months')"
            expense_filter += " AND date(expense_date) >= date('now', 'start of month', '-5 months')"
        elif selected_period == "12 derniers mois":
            income_filter += " AND date(transaction_date) >= date('now', 'start of month', '-11 months')"
            expense_filter += " AND date(expense_date) >= date('now', 'start of month', '-11 months')"
        elif selected_period == "Année en cours":
            current_year = datetime.now().strftime('%Y')
            income_filter += " AND strftime('%Y', transaction_date) = ?"
            expense_filter += " AND strftime('%Y', expense_date) = ?"
            income_params.append(current_year)
            expense_params.append(current_year)
        
        # Get data from database
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get monthly income
            cursor.execute(f"""
                SELECT strftime('%Y-%m', transaction_date) as month,
                    SUM(amount_paid) as total
                FROM Payments
                WHERE {income_filter}
                GROUP BY month
                ORDER BY month
            """, income_params)
            income_data = cursor.fetchall()
            
            # Get monthly expenses
            cursor.execute(f"""
                SELECT strftime('%Y-%m', expense_date) as month,
                    SUM(amount) as total
                FROM Expenses
                WHERE {expense_filter}
                GROUP BY month
                ORDER BY month
            """, expense_params)
            expense_data = cursor.fetchall()
        
        # Prepare data
        income_dict = {item[0]: item[1] if item[1] else 0 for item in income_data}
        expense_dict = {item[0]: item[1] if item[1] else 0 for item in expense_data}
        months = sorted(set(income_dict.keys()) | set(expense_dict.keys()))
        income = [income_dict.get(month, 0) for month in months]
        expenses = [expense_dict.get(month, 0) for month in months]
        
        if not months:
            text_color = ThemeManager.get_colors().TEXT_SECONDARY if THEME_AVAILABLE else Colors().TEXT_SECONDARY
            ax.text(0.5, 0.5, 'Aucune donnée disponible', 
                    ha='center', va='center', fontsize=14, color=text_color)
            ax.axis('off')
        else:
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                income_color = colors.SUCCESS
                expense_color = colors.DANGER
                text_color = colors.TEXT_SECONDARY
                title_color = colors.TEXT_PRIMARY
                ax.set_facecolor(colors.BG_CARD)
            else:
                colors = Colors()
                income_color = colors.SUCCESS
                expense_color = colors.DANGER
                text_color = colors.TEXT_SECONDARY
                title_color = colors.TEXT_PRIMARY
            x = range(len(months))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], income, width, label='Recettes', color=income_color)
            ax.bar([i + width/2 for i in x], expenses, width, label='Dépenses', color=expense_color)
            
            ax.set_xlabel('Mois', fontsize=10, fontweight='bold', color=text_color)
            ax.set_ylabel('Montant (FCFA)', fontsize=10, fontweight='bold', color=text_color)
            ax.set_title('Évolution Financière Mensuelle', fontsize=12, fontweight='bold', pad=15, color=title_color)
            ax.set_xticks(x)
            ax.set_xticklabels(months, rotation=45, ha='right')
            legend = ax.legend(loc='upper left', frameon=True)
            ax.grid(axis='y', alpha=0.2, linestyle='--')
            ax.tick_params(axis='x', colors=text_color)
            ax.tick_params(axis='y', colors=text_color)
            for spine in ax.spines.values():
                spine.set_color(colors.BORDER)
            if legend:
                for text in legend.get_texts():
                    text.set_color(text_color)
            
            # Remove top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
        
        self.financial_figure.tight_layout()
        self.financial_canvas.draw()

    def create_student_reports_tab(self):
        """Student performance analytics"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Controls Card
        control_card = self.create_card()
        controls_layout = QHBoxLayout(control_card)
        controls_layout.setContentsMargins(15, 15, 15, 15)
        
        controls_layout.addWidget(QLabel("Classe:"))
        self.class_combo = self.styled_combo()
        self.load_classes_combo()
        controls_layout.addWidget(self.class_combo)
        
        btn_analyze = QPushButton("📈 Analyser Performance")
        btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_analyze.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.SUCCESS};
                    color: white;
                    padding: 8px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_analyze.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.SUCCESS};
                    color: white;
                    padding: 8px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_analyze.clicked.connect(self.generate_student_chart)
        controls_layout.addWidget(btn_analyze)
        
        controls_layout.addStretch()
        layout.addWidget(control_card)
        
        # Chart Card
        chart_card = self.create_card()
        c_layout = QVBoxLayout(chart_card)
        
        self.student_figure = Figure(figsize=(10, 6))
        if THEME_AVAILABLE:
            self.student_figure.patch.set_facecolor(ThemeManager.get_colors().BG_CARD)
        else:
            self.student_figure.patch.set_facecolor(Colors().BG_CARD)
        self.student_canvas = FigureCanvas(self.student_figure)
        c_layout.addWidget(self.student_canvas)
        
        layout.addWidget(chart_card)
        
        return widget

    def generate_student_chart(self):
        """Generate student performance chart"""
        self.student_figure.clear()
        ax = self.student_figure.add_subplot(111)
        
        class_id = self.class_combo.currentData()
        if not class_id:
            text_color = ThemeManager.get_colors().TEXT_SECONDARY if THEME_AVAILABLE else Colors().TEXT_SECONDARY
            ax.text(0.5, 0.5, 'Veuillez sélectionner une classe', 
                ha='center', va='center', fontsize=14, color=text_color)
            ax.axis('off')
            self.student_canvas.draw()
            return
        
        # Get grades distribution
        db = DatabaseManager()
        grades = []
        active_year_label = "N/A"
        with db.get_connection() as conn:
            cursor = conn.cursor()
            active_year_id, active_year_label = self._get_active_year_context(cursor)

            if active_year_id:
                cursor.execute("SELECT COUNT(*) FROM Grades WHERE year_id=?", (active_year_id,))
                has_year_rows = cursor.fetchone()[0] > 0
            else:
                has_year_rows = False
            
            # Note: Assuming 'Grades' table has 'score' column
            if has_year_rows:
                cursor.execute("""
                    SELECT g.score
                    FROM Grades g
                    JOIN Students s ON g.student_id = s.id
                    WHERE s.class_id = ? AND g.score IS NOT NULL AND g.year_id = ?
                """, (class_id, active_year_id))
            else:
                if active_year_id:
                    cursor.execute("""
                        SELECT g.score
                        FROM Grades g
                        JOIN Students s ON g.student_id = s.id
                        WHERE s.class_id = ? AND g.score IS NOT NULL
                        AND (g.year_id = ? OR g.year_id IS NULL)
                    """, (class_id, active_year_id))
                else:
                    cursor.execute("""
                        SELECT g.score
                        FROM Grades g
                        JOIN Students s ON g.student_id = s.id
                        WHERE s.class_id = ? AND g.score IS NOT NULL
                    """, (class_id,))
            
            grades = [row[0] for row in cursor.fetchall()]
        
        if not grades:
            text_color = ThemeManager.get_colors().TEXT_SECONDARY if THEME_AVAILABLE else Colors().TEXT_SECONDARY
            ax.text(0.5, 0.5, 'Aucune note disponible pour cette classe', 
                    ha='center', va='center', fontsize=14, color=text_color)
            ax.axis('off')
        else:
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                hist_color = colors.PRIMARY
                text_color = colors.TEXT_SECONDARY
                title_color = colors.TEXT_PRIMARY
                avg_color = colors.DANGER
                ax.set_facecolor(colors.BG_CARD)
            else:
                colors = Colors()
                hist_color = colors.PRIMARY
                text_color = colors.TEXT_SECONDARY
                title_color = colors.TEXT_PRIMARY
                avg_color = colors.DANGER
            # Create histogram
            bins = [0, 5, 10, 12, 14, 16, 20]
            ax.hist(grades, bins=bins, color=hist_color, edgecolor='white', alpha=0.8, rwidth=0.9)
            ax.set_xlabel('Notes (Intervalle)', fontsize=10, fontweight='bold', color=text_color)
            ax.set_ylabel("Nombre d'étudiants", fontsize=10, fontweight='bold', color=text_color)
            ax.set_title(f'Distribution des Notes - {self.class_combo.currentText()}', 
                         fontsize=12, fontweight='bold', pad=20, color=title_color)
            subtitle = f"Année scolaire: {active_year_label}"
            ax.text(0.5, 1.01, subtitle, transform=ax.transAxes, ha='center', va='bottom', fontsize=9, color=text_color)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Add average line
            avg = sum(grades) / len(grades)
            ax.axvline(avg, color=avg_color, linestyle='--', linewidth=2, 
                       label=f'Moyenne Classe: {avg:.1f}')
            legend = ax.legend()
            ax.tick_params(axis='x', colors=text_color)
            ax.tick_params(axis='y', colors=text_color)
            for spine in ax.spines.values():
                spine.set_color(colors.BORDER)
            if legend:
                for text in legend.get_texts():
                    text.set_color(text_color)
            
            # Remove spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
        
        self.student_figure.tight_layout()
        self.student_canvas.draw()

    def create_excel_exports_tab(self):
        """Excel export features"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Grid for cards
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Financial Report
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_financial = self.create_export_button(
            "💰 Rapport Financier",
            "Export complet des recettes et dépenses",
            colors.SUCCESS
        )
        btn_financial.clicked.connect(lambda: self.export_excel("financial"))
        grid.addWidget(btn_financial, 0, 0)
        
        # Student List
        btn_students = self.create_export_button(
            "👨‍🎓 Liste des Étudiants",
            "Export de tous les élèves inscrits",
            colors.PRIMARY
        )
        btn_students.clicked.connect(lambda: self.export_excel("students"))
        grid.addWidget(btn_students, 0, 1)
        
        # Attendance Report
        btn_attendance = self.create_export_button(
            "📅 Rapport d'Assiduité",
            "Statistiques de présence par classe",
            colors.WARNING
        )
        btn_attendance.clicked.connect(lambda: self.export_excel("attendance"))
        grid.addWidget(btn_attendance, 1, 0)
        
        # Grade Report
        btn_grades = self.create_export_button(
            "📝 Relevé de Notes",
            "Tableau global des notes et moyennes",
            colors.SECONDARY if hasattr(colors, "SECONDARY") else Colors().PRIMARY
        )
        btn_grades.clicked.connect(lambda: self.export_excel("grades"))
        grid.addWidget(btn_grades, 1, 1)
        
        layout.addLayout(grid)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    border-radius: 4px;
                    text-align: center;
                    background-color: {colors.BG_MAIN};
                    color: {colors.TEXT_PRIMARY};
                }}
                QProgressBar::chunk {{
                    background-color: {colors.PRIMARY};
                    border-radius: 4px;
                }}
            """)
        else:
            colors = Colors()
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    border-radius: 4px;
                    text-align: center;
                    background-color: {colors.BG_MAIN};
                    color: {colors.TEXT_PRIMARY};
                }}
                QProgressBar::chunk {{
                    background-color: {colors.PRIMARY};
                    border-radius: 4px;
                }}
            """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if THEME_AVAILABLE:
            self.status_label.setStyleSheet(f"font-size: 13px; color: {ThemeManager.get_colors().TEXT_SECONDARY}; font-weight: bold;")
        else:
            self.status_label.setStyleSheet(f"font-size: 13px; color: {Colors().TEXT_SECONDARY}; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        return widget

    def create_export_button(self, title, description, color):
        """Create styled export button behaving like a card"""
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(110)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.BG_CARD};
                    border: 1px solid {colors.BORDER};
                    border-radius: 12px;
                    text-align: left;
                    padding: 15px;
                    border-left: 6px solid {color};
                }}
                QPushButton:hover {{
                    background-color: {colors.BG_MAIN};
                    border: 1px solid {color};
                    border-left: 6px solid {color};
                }}
            """)
        else:
            colors = Colors()
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.BG_CARD};
                    border: 1px solid {colors.BORDER};
                    border-radius: 12px;
                    text-align: left;
                    padding: 15px;
                    border-left: 6px solid {color};
                }}
                QPushButton:hover {{
                    background-color: {colors.BG_MAIN};
                    border: 1px solid {color};
                    border-left: 6px solid {color};
                }}
            """)
        
        # Create layout inside button
        layout = QVBoxLayout(btn)
        layout.setContentsMargins(15, 10, 15, 10)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color}; border: none; background: transparent;")
        
        desc_label = QLabel(description)
        if THEME_AVAILABLE:
            desc_label.setStyleSheet(f"font-size: 12px; color: {ThemeManager.get_colors().TEXT_SECONDARY}; border: none; background: transparent;")
        else:
            desc_label.setStyleSheet(f"font-size: 12px; color: {Colors().TEXT_SECONDARY}; border: none; background: transparent;")
        
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        
        # Add shadow to button (Simulated via QGraphicsEffect on the button itself)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 4)
        btn.setGraphicsEffect(shadow)
        
        return btn

    def export_excel(self, report_type):
        """Export Excel report in background thread"""
        default_name = f"Rapport_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        params = {}

        if report_type == "financial":
            selected_period = self.period_combo.currentText() if hasattr(self, 'period_combo') else "12 derniers mois"
            safe_period = selected_period.encode('ascii', 'ignore').decode('ascii')
            safe_period = safe_period.replace(" ", "_").replace("'", "").replace("/", "-")
            if not safe_period:
                safe_period = "periode"
            default_name = f"Rapport_Financier_{safe_period}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
            params["period"] = selected_period
        elif report_type == "students":
            default_name = f"Liste_Etudiants_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        elif report_type == "attendance":
            default_name = f"Rapport_Assiduite_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        elif report_type == "grades":
            default_name = f"Rapport_Notes_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"

        output_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le rapport", default_name, "Excel Files (*.xlsx)")
        if not output_path:
            self.progress_bar.hide()
            self.status_label.setText("")
            return

        params["output_path"] = output_path

        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ Génération du rapport en cours...")
        
        # Create worker
        if report_type == "financial":
            self.worker = ReportWorker("excel_financial", params)
        elif report_type == "students":
            self.worker = ReportWorker("excel_students", params)
        elif report_type == "attendance":
            self.worker = ReportWorker("excel_attendance", params)
        elif report_type == "grades":
            self.worker = ReportWorker("excel_grades", params)
        else:
            QMessageBox.information(self, "En développement", 
                                   f"Export '{report_type}' sera disponible prochainement!")
            self.progress_bar.hide()
            self.status_label.setText("")
            return
        
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.error.connect(self.on_export_error)
        self.worker.start()

    def on_export_finished(self, filepath):
        """Handle successful export"""
        self.progress_bar.hide()
        self.status_label.setText(f"✅ Export réussi: {os.path.basename(filepath)}")
        if THEME_AVAILABLE:
            self.status_label.setStyleSheet(f"color: {ThemeManager.get_colors().SUCCESS}; font-weight: bold;")
        else:
            self.status_label.setStyleSheet(f"color: {Colors().SUCCESS}; font-weight: bold;")
        
        reply = QMessageBox.question(
            self,
            "Export Réussi",
            f"Le fichier a été généré avec succès!\n\n{filepath}\n\nVoulez-vous l'ouvrir?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.name == 'nt':
                    os.startfile(filepath)
                else:
                    import subprocess
                    subprocess.call(('xdg-open', filepath))
            except:
                pass

    def on_export_error(self, error):
        """Handle export error"""
        self.progress_bar.hide()
        self.status_label.setText("❌ Erreur lors de l'export")
        if THEME_AVAILABLE:
            self.status_label.setStyleSheet(f"color: {ThemeManager.get_colors().DANGER}; font-weight: bold;")
        else:
            self.status_label.setStyleSheet(f"color: {Colors().DANGER}; font-weight: bold;")
        QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export:\n{error}")

    def load_classes_combo(self):
        """Load classes into combo box"""
        self.class_combo.clear()
        self.class_combo.addItem("-- Sélectionnez une classe --", None)
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY sort_order")
                rows = cursor.fetchall()
            
            for class_id, class_name in rows:
                self.class_combo.addItem(class_name, class_id)
            
        except:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdvancedReportsWindow()
    window.show()
    sys.exit(app.exec())