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
from database_setup import DatabaseManager, log_audit
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    get_school_info_row,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.year_end_repo import YearEndRepository
from services.grade_service import GradeService, is_primary_cycle
from services.migration_service import MigrationService
from ui_components import card_frame, style_table, styled_combo
from ui_styles import (
    Colors,
    ModuleHeaderWidget,
    ThemeManager,
    apply_shadow_to_widget,
    get_card_style,
    get_module_caps,
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

                # Pre-fetch everything the per-student loop needs, to avoid an
                # N×P×S query storm: all grades in one bulk query, assessment types
                # once per period, and cycle name/subjects cached per cycle.
                grade_index = repo.get_grades_for_students_year([s[0] for s in students], self.current_year_id)
                assess_by_period = {pid: repo.get_period_assessment_types(pid) for pid in period_ids}
                cycle_name_cache: dict = {}
                subjects_cache: dict = {}

                def _cycle_name(cid):
                    if cid not in cycle_name_cache:
                        cycle_name_cache[cid] = repo.get_cycle_name(cid)
                    return cycle_name_cache[cid]

                def _subjects(cid):
                    if cid not in subjects_cache:
                        try:
                            subjects_cache[cid] = repo.list_subjects_with_coefficient(cid)
                        except Exception:
                            subjects_cache[cid] = []
                    return subjects_cache[cid]

                total = max(len(students), 1)
                for i, (std_id, fname, lname, class_id) in enumerate(students):
                    if self.isInterruptionRequested():  # cooperative cancel (window closed)
                        break
                    cycle_id = class_map.get(class_id, {}).get('cycle', 0)
                    cycle_name = _cycle_name(cycle_id)
                    is_primary = is_primary_cycle(cycle_name)
                    subjects = _subjects(cycle_id)

                    period_avgs = []
                    if period_ids and subjects:
                        for pid in period_ids:
                            assess_types = assess_by_period.get(pid, [])  # (id, code, name)
                            weighted_scores = []
                            for sub_id, coef in subjects:
                                gmap = grade_index.get((std_id, sub_id, pid))
                                if not gmap:
                                    continue  # subject not graded this period
                                # Missing assessment counts as 0 (school policy) — same as the bulletin.
                                devoirs = [
                                    gmap.get(aid, 0)
                                    for aid, code, name in assess_types
                                    if GradeService.is_devoir_assessment(code, name)
                                ]
                                compo_ids = [
                                    aid
                                    for aid, code, name in assess_types
                                    if not GradeService.is_devoir_assessment(code, name)
                                ]
                                compo = gmap.get(compo_ids[0], 0) if compo_ids else None
                                subj_avg = self.grade_service.subject_average(devoirs, compo, is_primary)
                                weighted_scores.append((subj_avg, float(coef)))
                            period_avgs.append(self.grade_service.calculate_period_average(weighted_scores))

                    fallback_average = 0.0
                    if not period_avgs:
                        fallback_average = repo.get_fallback_average(std_id, self.current_year_id)

                    avg_annual = self.grade_service.calculate_annual_average(period_avgs, fallback_average)

                    # --- Decision Logic --- (cycle_name computed above)
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


# ---------------------------------------------------------------------------
# Pure functions — no Qt dependency, fully unit-testable
# ---------------------------------------------------------------------------


def validate_migration_data(migration_rows, current_year_id, target_year_id):
    """Return (ok, message) — validate migration rules without Qt."""
    if not migration_rows:
        return False, "Aucune donnée à migrer / لا توجد بيانات للترحيل."
    if not target_year_id:
        return False, "Veuillez sélectionner une année cible valide."
    if current_year_id and current_year_id == target_year_id:
        return False, "L'année source et cible doivent être différentes !"
    total = len(migration_rows)
    excluded = sum(1 for r in migration_rows if r['decision'] == "Exclu")
    if total > 0 and excluded / total > 0.20:
        return False, (
            f"Attention : {excluded}/{total} élèves sont marqués 'Exclu' ({excluded * 100 // total}%).\n"
            "Vérifiez les décisions avant de confirmer."
        )
    return True, ""


def build_migration_summary(migration_rows, count, current_year_name="", target_year_name=""):
    """Build a human-readable migration summary string without Qt."""
    total = len(migration_rows)
    promoted = sum(1 for r in migration_rows if r['decision'] == "Admis")
    retained = sum(1 for r in migration_rows if r['decision'] == "Redouble")
    excluded = sum(1 for r in migration_rows if r['decision'] == "Exclu")
    return (
        f"✅ Migration terminée avec succès\n"
        f"تم الترحيل بنجاح\n\n"
        f"Année source : {current_year_name}\n"
        f"Année cible  : {target_year_name}\n\n"
        f"{'─' * 40}\n"
        f"  Total élèves traités : {total}\n"
        f"  ✅ Admis (ناجح)      : {promoted}\n"
        f"  🔁 Redoublants (راسب): {retained}\n"
        f"  ❌ Exclus (مفصول)   : {excluded}\n"
        f"{'─' * 40}\n"
        f"Enregistrements créés : {count}"
    )


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

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "year_end_migration")
        self.btn_calc.setEnabled(caps["can_write"])
        self.btn_calc.setVisible(caps["can_write"])
        self.btn_execute.setEnabled(caps["can_write"])
        self.btn_execute.setVisible(caps["can_write"])

    def _audit_decision_overrides(self, conn, migration_rows: list) -> int:
        """Log to AuditLogs each row whose final decision differs from the
        auto-computed one (a manual director override / rachat). Returns the count.

        Documents the authorised override required by school policy: actor +
        student + auto-decision -> manual-decision, in the migration transaction.
        """
        actor = getattr(self, "current_user", "system")
        auto_decisions = {r["id"]: r["decision"] for r in self.migration_data}
        overrides = 0
        for row in migration_rows:
            auto = auto_decisions.get(row["student_id"])
            if auto is not None and row["decision"] != auto:
                log_audit(
                    conn,
                    actor,
                    "GRADE_DECISION_OVERRIDE",
                    f"student={row['student_id']}: {auto} -> {row['decision']}",
                )
                overrides += 1
        return overrides

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

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
        grid_config.setSpacing(8)
        grid_config.setContentsMargins(12, 8, 12, 8)

        card_title = QLabel("1. Configuration & Filtrage / الإعدادات")
        card_title.setStyleSheet(
            f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 13px; margin-bottom: 2px;"
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

        self.btn_calc = QPushButton("Calculer les Décisions / حساب")
        self.btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calc.setFixedHeight(32)
        colors = ThemeManager.get_colors()
        self.btn_calc.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; font-size: 13px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """
        )
        self.btn_calc.clicked.connect(self.start_calculation)

        grid_config.addWidget(QLabel("Filtrer par Classe:"), 2, 0)
        grid_config.addWidget(self.combo_filter_class, 2, 1)
        grid_config.addWidget(self.btn_calc, 2, 3)

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
        self.btn_execute = QPushButton("🚀 CONFIRMER LA MIGRATION / تنفيذ الترحيل")
        self.btn_execute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_execute.setMinimumHeight(50)
        colors = ThemeManager.get_colors()
        self.btn_execute.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; padding: 0 20px; font-size: 14px; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
        """
        )
        self.btn_execute.clicked.connect(self.execute_migration)

        action_layout.addWidget(self.chk_archive)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_execute)

        self.main_layout.addLayout(action_layout)

    # --- Helper Styling Methods ---
    def create_card(self):
        return card_frame(with_shadow=True)

    def styled_combo(self):
        return styled_combo(min_height=32)

    def style_table(self, table):
        style_table(table)

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

    def stop_background_workers(self) -> None:
        """Stop a running migration-calculation thread before the DB pool closes.

        This window is embedded in the main dashboard, so its own closeEvent
        never fires — the main window calls this on application shutdown.
        """
        thread = getattr(self, "calc_thread", None)
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            thread.quit()
            thread.wait(3000)

    def display_results(self, results):
        self.migration_data = results
        self.progress_bar.setVisible(False)
        self.table_preview.setRowCount(0)

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

    def _validate_before_migration(self, migration_rows, target_year_id):
        """Delegate to module-level pure function (reads current year from widget)."""
        current_year_id = self.combo_current_year.currentData()
        return validate_migration_data(migration_rows, current_year_id, target_year_id)

    def _build_summary_message(self, migration_rows, count):
        """Delegate to module-level pure function (reads year names from widgets)."""
        return build_migration_summary(
            migration_rows,
            count,
            current_year_name=self.combo_current_year.currentText(),
            target_year_name=self.combo_target_year.currentText(),
        )

    # ===== تنفيذ الترحيل مع rollback وملخص نتائج =====
    def execute_migration(self):
        if not self.migration_data:
            QMessageBox.warning(
                self, "Données manquantes", "Calculez d'abord les décisions avant d'exécuter la migration."
            )
            return

        target_year_id = self.combo_target_year.currentData()
        change_active_year = self.chk_archive.isChecked()

        # Collect rows from table (honour user edits to decisions)
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

        # Pre-migration validation
        ok, err_msg = self._validate_before_migration(migration_rows, target_year_id)
        if not ok:
            QMessageBox.warning(self, "Validation", err_msg)
            return

        # Confirmation dialog with summary
        total = len(migration_rows)
        filter_note = "\n(Filtre : classe sélectionnée seulement)" if self.combo_filter_class.currentData() else ""
        promoted_preview = sum(1 for r in migration_rows if r['decision'] == "Admis")
        retained_preview = sum(1 for r in migration_rows if r['decision'] == "Redouble")
        excluded_preview = sum(1 for r in migration_rows if r['decision'] == "Exclu")
        confirm_msg = (
            f"Confirmer la migration de {total} élèves ?\n{filter_note}\n\n"
            f"  Admis     : {promoted_preview}\n"
            f"  Redoublants: {retained_preview}\n"
            f"  Exclus    : {excluded_preview}\n\n"
            f"{'⚠️ La nouvelle année sera activée.' if change_active_year else ''}"
        )
        reply = QMessageBox.question(
            self, "Confirmation / تأكيد", confirm_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Execute with explicit rollback on failure
        db = DatabaseManager()
        with db.get_connection() as conn:
            try:
                count = self.migration_service.execute_migration(
                    conn,
                    migration_rows,
                    target_year_id,
                    change_active_year,
                )

                # Audit manual overrides of the auto-computed decision (rachat).
                overrides = self._audit_decision_overrides(conn, migration_rows)

                conn.commit()
                AppLogger.info(
                    "YearEndMigration",
                    f"Migration succeeded: {count} records, year={target_year_id}, manual_overrides={overrides}",
                )

                summary = self._build_summary_message(migration_rows, count)
                QMessageBox.information(self, "Migration réussie / الترحيل ناجح", summary)

                self.table_preview.setRowCount(0)
                self.migration_data = []
                self.load_initial_data()

            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                AppLogger.error("YearEndMigration", f"Migration failed, rolled back: {e}")
                QMessageBox.critical(
                    self,
                    "Erreur — Rollback effectué / خطأ — تم التراجع",
                    f"La migration a échoué. Toutes les modifications ont été annulées.\n\nDétail :\n{e}",
                )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MigrationWindow()
    window.show()
    sys.exit(app.exec())
