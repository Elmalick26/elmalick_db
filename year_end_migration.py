import os
import sys
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import psycopg2
from fpdf import FPDF
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
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
from repositories.year_end_repo import YearEndRepository
from services.grade_service import GradeService
from services.migration_service import MigrationService
from ui_styles import (
    Colors,
    ModuleHeaderWidget,
    ThemeManager,
    apply_shadow_to_widget,
    get_card_style,
    get_table_style,
    get_tabs_style,
)


class MigrationCalculator(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, current_year_id, filter_class_id=None):
        super().__init__()
        self.current_year_id = current_year_id
        self.filter_class_id = filter_class_id
        self.grade_service = GradeService()

    def run(self):
        results = []
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = YearEndRepository(conn)

                class_map = {}
                try:
                    for cid, name, cycle_id, order_val in repo.list_classes_with_order():
                        class_map[cid] = {'name': name, 'cycle': cycle_id, 'order': order_val}
                except Exception:
                    for cid, name, cycle_id in repo.list_classes_basic():
                        class_map[cid] = {'name': name, 'cycle': cycle_id, 'order': cid}

                period_ids = []
                try:
                    period_ids = repo.list_period_ids(self.current_year_id)
                except Exception as e:
                    AppLogger.error("YearEndMigration", f"Error fetching periods: {e}")
                    period_ids = []

                if self.filter_class_id:
                    students = repo.list_active_students_in_class(self.current_year_id, self.filter_class_id)
                else:
                    students = repo.list_all_active_students(self.current_year_id)

                total = max(len(students), 1)
                for i, (std_id, fname, lname, class_id) in enumerate(students):
                    cycle_id = class_map.get(class_id, {}).get('cycle', 0)
                    subjects = []
                    try:
                        subjects = repo.list_subjects_with_coefficient(cycle_id)
                    except Exception:
                        pass

                    period_avgs = []
                    if period_ids and subjects:
                        for pid in period_ids:
                            weighted_scores = []
                            for sub_id, coef in subjects:
                                avg_val = repo.get_grade_average(std_id, sub_id, pid, self.current_year_id)
                                if avg_val is not None:
                                    weighted_scores.append((avg_val, float(coef)))
                            period_avgs.append(self.grade_service.calculate_period_average(weighted_scores))

                    fallback_average = 0.0
                    if not period_avgs:
                        fallback_average = repo.get_fallback_average(std_id, self.current_year_id)

                    avg_annual = self.grade_service.calculate_annual_average(period_avgs, fallback_average)

                    # --- Decision Logic ---
                    cycle_name = repo.get_cycle_name(cycle_id)
                    decision = self.grade_service.get_promotion_decision(avg_annual, cycle_name)

                    # --- Next Class Logic ---
                    next_class_id, next_class_name = self.grade_service.get_next_class(
                        class_map,
                        class_id,
                        cycle_id,
                        decision,
                    )

                    results.append(
                        {
                            'id': std_id,
                            'name': f"{fname} {lname}",
                            'current_class': class_map.get(class_id, {}).get('name', '?'),
                            'avg': avg_annual,
                            'decision': decision,
                            'next_class_id': next_class_id,
                            'next_class_name': next_class_name,
                            'current_class_id': class_id,
                        }
                    )

                    self.progress.emit(int((i + 1) / total * 100))
        except Exception as e:
            AppLogger.error("YearEndMigration", f"Background thread error: {e}")

        self.finished.emit(results)


class MigrationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.migration_service = MigrationService()
        self.setWindowTitle("Clôture de l'Année & Migration / الترحيل السنوي")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر (Dark Mode أو Light Mode)
        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_initial_data()
        self.migration_data = []

    def init_ui(self):
        fallback_colors = Colors()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # 1. Header
        header = ModuleHeaderWidget("🔄", "MIGRATION ANNUELLE", "إغلاق السنة الدراسية وترحيل الطلاب للعام الجديد")
        self._stat_students = header.add_stat("👥", "Élèves", "0", "#3B82F6")
        self._stat_classes = header.add_stat("🏫", "Classes", "0", "#8B5CF6")
        self._stat_promoted = header.add_stat("✅", "Admis", "0", "#22C55E")
        self._stat_failed = header.add_stat("🔁", "Redoublants", "0", "#EF4444")
        self.main_layout.addWidget(header)

        # 2. Configuration Card
        config_card = self.create_card()
        grid_config = QGridLayout(config_card)
        grid_config.setSpacing(15)
        grid_config.setContentsMargins(20, 20, 20, 20)

        card_title = QLabel("1. Configuration & Filtrage / الإعدادات")
        card_title.setStyleSheet(
            f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 10px;"
        )
        grid_config.addWidget(card_title, 0, 0, 1, 4)

        self.combo_current_year = self.styled_combo()
        self.combo_target_year = self.styled_combo()

        grid_config.addWidget(QLabel("Année Source (الحالية):"), 1, 0)
        grid_config.addWidget(self.combo_current_year, 1, 1)
        grid_config.addWidget(QLabel("➡ Année Cible (القادمة):"), 1, 2)
        grid_config.addWidget(self.combo_target_year, 1, 3)

        self.combo_filter_class = self.styled_combo()
        self.combo_filter_class.addItem("Toutes les Classes / كل الفصول", None)

        btn_calc = QPushButton("Calculer les Décisions / حساب")
        btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_calc.setMinimumHeight(40)
        colors = ThemeManager.get_colors()
        btn_calc.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; font-size: 13px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """
        )
        btn_calc.clicked.connect(self.start_calculation)

        grid_config.addWidget(QLabel("Filtrer par Classe:"), 2, 0)
        grid_config.addWidget(self.combo_filter_class, 2, 1)
        grid_config.addWidget(btn_calc, 2, 3)

        self.main_layout.addWidget(config_card)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # 3. Preview Table
        preview_label = QLabel("2. Aperçu et Validation / المعاينة والتنقيح:")
        preview_label.setStyleSheet(
            f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; margin-left: 5px;"
        )
        self.main_layout.addWidget(preview_label)

        self.table_preview = QTableWidget()
        self.style_table(self.table_preview)
        self.table_preview.setColumnCount(6)
        self.table_preview.setHorizontalHeaderLabels(
            ["ID", "Élève", "Classe Actuelle", "Moyenne", "Décision", "Classe Future"]
        )
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_preview.setColumnWidth(0, 60)
        self.table_preview.verticalHeader().setDefaultSectionSize(40)

        self.main_layout.addWidget(self.table_preview)

        # 4. Execution Area
        action_layout = QHBoxLayout()
        self.chk_archive = QCheckBox("Activer automatiquement la nouvelle année / تفعيل السنة الجديدة آلياً")
        self.chk_archive.setChecked(True)
        self.chk_archive.setStyleSheet(f"font-size: 14px; color: {ThemeManager.get_colors().TEXT_PRIMARY};")
        btn_execute = QPushButton("🚀 CONFIRMER LA MIGRATION / تنفيذ الترحيل")
        btn_execute.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_execute.setMinimumHeight(50)
        colors = ThemeManager.get_colors()
        btn_execute.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; padding: 0 20px; font-size: 14px; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
        """
        )
        btn_execute.clicked.connect(self.execute_migration)

        action_layout.addWidget(self.chk_archive)
        action_layout.addStretch()
        action_layout.addWidget(btn_execute)

        self.main_layout.addLayout(action_layout)

    # --- Helper Styling Methods ---
    def create_card(self):
        frame = QFrame()
        frame.setStyleSheet(get_card_style())
        apply_shadow_to_widget(frame)
        return frame

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors()
        combo.setStyleSheet(
            f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        combo.setMinimumHeight(40)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(get_table_style())

    # --- Logic Methods ---
    def load_initial_data(self):
        with DatabaseManager() as db:
            conn = db.get_connection()
            repo = YearEndRepository(conn)

            years = repo.list_academic_years()

            self.combo_current_year.clear()
            self.combo_target_year.clear()

            active_idx = -1
            for i, y in enumerate(years):
                self.combo_current_year.addItem(y[1], y[0])
                self.combo_target_year.addItem(y[1], y[0])
                if y[2] == 1:
                    active_idx = i

            if active_idx != -1:
                self.combo_current_year.setCurrentIndex(active_idx)
                # الافتراضي أن السنة المستهدفة هي السنة التي تلي السنة النشطة
                if active_idx + 1 < len(years):
                    self.combo_target_year.setCurrentIndex(active_idx + 1)
                else:
                    self.combo_target_year.setCurrentIndex(active_idx)

            classes = repo.list_classes_for_combo()
            self.combo_filter_class.clear()
            self.combo_filter_class.addItem("Toutes les Classes / كل الفصول", None)
            for c in classes:
                self.combo_filter_class.addItem(c[1], c[0])

    def start_calculation(self):
        curr_id = self.combo_current_year.currentData()
        targ_id = self.combo_target_year.currentData()
        filter_cls = self.combo_filter_class.currentData()

        if curr_id == targ_id:
            QMessageBox.warning(self, "Attention", "L'année source et cible doivent être différentes !")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.table_preview.setRowCount(0)

        self.calc_thread = MigrationCalculator(curr_id, filter_cls)
        self.calc_thread.progress.connect(self.progress_bar.setValue)
        self.calc_thread.finished.connect(self.display_results)
        self.calc_thread.start()

    def display_results(self, results):
        self.migration_data = results
        self.progress_bar.setVisible(False)
        self.table_preview.setRowCount(0)
        fallback_colors = Colors()

        if not results:
            QMessageBox.information(self, "Info", "Aucun élève trouvé pour les critères sélectionnés.")
            return

        for r in results:
            idx = self.table_preview.rowCount()
            self.table_preview.insertRow(idx)

            id_item = QTableWidgetItem(str(r['id']))
            id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_preview.setItem(idx, 0, id_item)

            name_item = QTableWidgetItem(r['name'])
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_preview.setItem(idx, 1, name_item)

            cls_item = QTableWidgetItem(r['current_class'])
            cls_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_preview.setItem(idx, 2, cls_item)

            avg_item = QTableWidgetItem(f"{r['avg']:.2f}")
            avg_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            colors = ThemeManager.get_colors()
            avg_item.setForeground(QColor(colors.SUCCESS) if r['decision'] == "Admis" else QColor(colors.DANGER))
            avg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_preview.setItem(idx, 3, avg_item)

            combo_dec = QComboBox()
            combo_dec.addItems(["Admis", "Redouble", "Exclu"])
            combo_dec.setCurrentText(r['decision'])
            combo_dec.setStyleSheet("QComboBox { border: none; background: transparent; }")
            self.table_preview.setCellWidget(idx, 4, combo_dec)

            dest_txt = r['next_class_name']
            dest_item = QTableWidgetItem(dest_txt)
            dest_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if "Fin de Cycle" in dest_txt:
                colors = ThemeManager.get_colors()
                dest_item.setBackground(QColor(colors.WARNING))
                dest_item.setForeground(QColor(colors.BG_MAIN))
            self.table_preview.setItem(idx, 5, dest_item)

        # Update stat chips
        total = len(results)
        promoted = sum(1 for r in results if r['decision'] == "Admis")
        failed = sum(1 for r in results if r['decision'] == "Redouble")
        unique_classes = len(set(r['current_class'] for r in results))
        self._stat_students.set_value(str(total))
        self._stat_classes.set_value(str(unique_classes))
        self._stat_promoted.set_value(str(promoted))
        self._stat_failed.set_value(str(failed))

    # ===== تعديل استراتيجي: الترحيل يتم بإضافة سجلات جديدة في SCN =====
    def execute_migration(self):
        if not self.migration_data:
            return

        msg = f"Êtes-vous sûr de vouloir traiter {len(self.migration_data)} élèves ?\n"
        if self.combo_filter_class.currentData():
            msg += "(Filtre appliqué : Seulement la classe sélectionnée)"

        reply = QMessageBox.question(
            self, "Confirmation", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        change_active_year = self.chk_archive.isChecked()
        target_year_id = self.combo_target_year.currentData()

        migration_rows = []
        for idx in range(self.table_preview.rowCount()):
            student_id = int(self.table_preview.item(idx, 0).text())
            original_data = next((item for item in self.migration_data if item['id'] == student_id), None)
            if not original_data:
                continue

            decision_widget = self.table_preview.cellWidget(idx, 4)
            migration_rows.append(
                {
                    'student_id': student_id,
                    'decision': decision_widget.currentText(),
                    'current_class_id': original_data['current_class_id'],
                    'next_class_id': original_data['next_class_id'],
                }
            )

        with DatabaseManager() as db:
            conn = db.get_connection()

            try:
                count = self.migration_service.execute_migration(
                    conn,
                    migration_rows,
                    target_year_id,
                    change_active_year,
                )
                conn.commit()
                QMessageBox.information(
                    self, "Succès", f"Opération terminée. {count} dossiers mis à jour pour l'année cible."
                )
                self.table_preview.setRowCount(0)
                self.migration_data = []
                self.load_initial_data()  # تحديث القوائم لتظهر السنة النشطة الجديدة

            except Exception as e:
                QMessageBox.critical(self, "Erreur lors de la migration", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MigrationWindow()
    window.show()
    sys.exit(app.exec())
