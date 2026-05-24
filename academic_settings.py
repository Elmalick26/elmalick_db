import os
import sys
from datetime import date, timedelta

import psycopg2

from app_logger import AppLogger
from database_setup import DatabaseManager
from repositories.academic_repo import AcademicRepository

# محاولة استيراد ConfigManager، وتجاوز الخطأ إن لم يكن متوفراً بالكامل بعد
try:
    from config_manager import ConfigManager

    HAS_CONFIG_MANAGER = True
except ImportError:
    HAS_CONFIG_MANAGER = False

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui_styles import (
    Colors,
    ModuleHeaderWidget,
    ThemeManager,
    apply_shadow_to_widget,
    get_card_style,
    get_table_style,
    get_tabs_style,
)


class AcademicSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Scolaire / الإعدادات المدرسية")
        self.setMinimumSize(1100, 700)

        self.config = ConfigManager() if HAS_CONFIG_MANAGER else None

        # --- تهيئة المتغيرات الأساسية لتجنب أخطاء (AttributeError) ---
        self.current_year_id = None
        self.current_cycle_id = None
        self.current_class_id = None
        self.current_subject_id = None
        self.logo_path_value = ""
        self.current_generated_year_id = None
        self.current_generated_cycle_id = None
        self._period_ranges_loading = False

        ThemeManager.apply_theme(self)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.init_ui()
        self.refresh_all_data()
        self._load_kpi_stats()

    def init_ui(self):
        colors = ThemeManager.get_colors()

        # En-tête unifié
        header = ModuleHeaderWidget(
            icon="⚙️",
            title="CONFIGURATION SCOLAIRE",
            subtitle="إعداد البيانات، الهيكل، المواد والتقييمات",
        )
        self.main_layout.addWidget(header)
        self._stat_years = header.add_stat("📅", "Années Scolaires", "—", "#3B82F6")
        self._stat_classes = header.add_stat("🏫", "Classes", "—", "#22C55E")
        self._stat_subjects = header.add_stat("📚", "Matières", "—", "#8B5CF6")
        self._stat_cycles = header.add_stat("🌀", "Cycles", "—", "#F59E0B")

        # KPI Cards

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_school_info_tab()
        self.setup_structure_tab()
        self.setup_subjects_tab()
        self.setup_evaluations_tab()

        self.main_layout.addWidget(self.tabs)

    # Helper Functions
    def create_card(self, title):
        frame = QFrame()
        frame.setStyleSheet(get_card_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        lbl = QLabel(title)
        lbl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        colors = ThemeManager.get_colors()
        lbl.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; margin-bottom: 10px;")
        layout.addWidget(lbl)
        return frame, layout

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        colors = ThemeManager.get_colors()
        le.setStyleSheet(
            f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors()
        combo.setStyleSheet(
            f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        combo.setMinimumHeight(38)
        return combo

    def styled_date_edit(self):
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setMinimumDate(QDate(1900, 1, 1))
        de.setMaximumDate(QDate(2100, 12, 31))
        de.setDate(QDate.currentDate())
        de.setMinimumHeight(38)
        colors = ThemeManager.get_colors()
        de.setStyleSheet(
            f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        return de

    def _period_date_editor_style(self, error: bool = False) -> str:
        colors = ThemeManager.get_colors()
        if error:
            return (
                f"QDateEdit {{ padding: 6px 10px; border: 2px solid {colors.DANGER}; border-radius: 6px; "
                f"background: #FEE2E2; color: {colors.TEXT_PRIMARY}; }}"
            )
        return (
            f"QDateEdit {{ padding: 6px 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; "
            f"background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} "
            f"QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )

    def _create_period_date_editor(self, iso_value: str = ""):
        editor = QDateEdit()
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        editor.setMinimumDate(QDate(1900, 1, 1))
        editor.setMaximumDate(QDate(2100, 12, 31))
        parsed = self._parse_period_date(iso_value)
        editor.setDate(QDate(parsed.year, parsed.month, parsed.day) if parsed else QDate.currentDate())
        editor.setStyleSheet(self._period_date_editor_style(error=False))
        editor.dateChanged.connect(self._on_period_date_widget_changed)
        return editor

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(get_table_style())

    def _load_kpi_stats(self):
        """Charge les statistiques de configuration scolaire."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM AcademicYears")
                years = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COUNT(*) FROM Classes")
                classes = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COUNT(*) FROM Subjects")
                subjects = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COUNT(*) FROM Cycles")
                cycles = cursor.fetchone()[0] or 0
            self._stat_years.set_value(str(years))
            self._stat_classes.set_value(str(classes))
            self._stat_subjects.set_value(str(subjects))
            self._stat_cycles.set_value(str(cycles))
        except Exception as e:
            AppLogger.error("AcademicSettingsWindow", f"Erreur KPI stats: {e}")

    def safe_text(self, value):
        return "" if value is None else str(value)

    def msg(self, fr: str, ar: str) -> str:
        return f"{fr} / {ar}"

    def add_action_buttons(self, table, row_idx, id_val, edit_func=None, delete_func=None):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)

        colors = ThemeManager.get_colors()

        if edit_func:
            btn_edit = QPushButton("✎")
            btn_edit.setFixedSize(28, 28)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet(
                f"background-color: {colors.WARNING}; color: white; border-radius: 4px; border: none;"
            )
            btn_edit.clicked.connect(lambda _, val=id_val: edit_func(val))
            layout.addWidget(btn_edit)

        if delete_func:
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 4px; border: none;")
            btn_del.clicked.connect(lambda _, val=id_val: delete_func(val))
            layout.addWidget(btn_del)

        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setCellWidget(row_idx, table.columnCount() - 1, widget)

    # --- 1. معلومات المؤسسة ---
    def setup_school_info_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        card, grid_lay = self.create_card("🏛️ Identification de l'Établissement / بيانات المؤسسة")
        grid = QGridLayout()
        grid.setSpacing(15)

        self.info_inputs = {
            'rep': self.styled_input("Ex: République du Sénégal"),
            'ia': self.styled_input("Inspection d'Académie (IA)"),
            'ief': self.styled_input("Inspection IEF"),
            'name': self.styled_input("Nom de l'établissement"),
            'auth': self.styled_input("N° Autorisation"),
            'director': self.styled_input("Nom du Directeur / اسم المدير"),
            'loc': self.styled_input("Adresse"),
            'tel': self.styled_input("Téléphone"),
        }

        self.logo_path_display = self.styled_input("Logo Path")
        self.logo_path_display.setReadOnly(True)

        labels = {
            'rep': "En-tête:",
            'ia': "IA:",
            'ief': "IEF:",
            'name': "Nom:",
            'auth': "Autorisation:",
            'director': "Directeur:",
            'loc': "Adresse:",
            'tel': "Tel:",
        }

        r = 0
        for k, v in self.info_inputs.items():
            grid.addWidget(QLabel(labels[k]), r, 0)
            grid.addWidget(v, r, 1)
            r += 1

        grid.addWidget(QLabel("Logo:"), r, 0)
        logo_h = QHBoxLayout()
        logo_h.addWidget(self.logo_path_display)
        btn_logo = QPushButton("📁")
        btn_logo.setFixedSize(40, 38)
        colors = ThemeManager.get_colors()
        btn_logo.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; border-radius: 6px; font-weight: bold;"
        )
        btn_logo.clicked.connect(self.browse_logo)
        logo_h.addWidget(btn_logo)
        grid.addLayout(logo_h, r, 1)

        btn_save = QPushButton("💾 Enregistrer / حفظ")
        btn_save.setMinimumHeight(45)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(
            f"background-color: {colors.SUCCESS}; color: white; border-radius: 8px; font-weight: bold; font-size: 14px;"
        )
        btn_save.clicked.connect(self.save_school_info)

        grid_lay.addLayout(grid)
        grid_lay.addWidget(btn_save)
        layout.addWidget(card)
        layout.addStretch()
        self.tabs.addTab(tab, "  🏛️ Infos / معلومات  ")

    # --- 2. الهيكل ---
    def setup_structure_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        colors = ThemeManager.get_colors()

        # Years
        y_card, y_lay = self.create_card("📅 Années / السنوات")
        self.txt_year = self.styled_input("Ex: 2025-2026")
        self.year_start_date = self.styled_date_edit()
        self.year_end_date = self.styled_date_edit()
        self.year_start_date.setDate(QDate(QDate.currentDate().year(), 9, 1))
        self.year_end_date.setDate(QDate(QDate.currentDate().year() + 1, 7, 31))
        self.btn_y = QPushButton("Ajouter")
        self.btn_y.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        self.btn_y.clicked.connect(self.save_year)
        self.table_years = QTableWidget(0, 4)
        self.style_table(self.table_years)
        self.table_years.setHorizontalHeaderLabels(["ID", "Année", "Actif", "Action"])
        self.table_years.setColumnWidth(0, 40)
        self.table_years.setColumnWidth(2, 80)
        y_lay.addWidget(self.txt_year)
        y_lay.addWidget(QLabel("Date début:"))
        y_lay.addWidget(self.year_start_date)
        y_lay.addWidget(QLabel("Date fin:"))
        y_lay.addWidget(self.year_end_date)
        y_lay.addWidget(self.btn_y)
        y_lay.addWidget(self.table_years)

        # Cycles
        c_card, c_lay = self.create_card("🏫 Cycles / المراحل")
        self.txt_c_fr = self.styled_input("Nom (FR)")
        self.txt_c_ar = self.styled_input("الاسم (عربي)")
        self.btn_c = QPushButton("Ajouter")
        self.btn_c.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        self.btn_c.clicked.connect(self.save_cycle)
        self.table_cycles = QTableWidget(0, 4)
        self.style_table(self.table_cycles)
        self.table_cycles.setHorizontalHeaderLabels(["ID", "Cycle (FR)", "Cycle (AR)", "Action"])
        self.table_cycles.setColumnWidth(0, 40)
        c_lay.addWidget(self.txt_c_fr)
        c_lay.addWidget(self.txt_c_ar)
        c_lay.addWidget(self.btn_c)
        c_lay.addWidget(self.table_cycles)

        # Classes
        cls_card, cls_lay = self.create_card("👥 Classes / الفصول")
        self.combo_cycles_cls = self.styled_combo()
        self.txt_cls_fr = self.styled_input("Nom (FR)")
        self.txt_cls_ar = self.styled_input("الاسم (عربي)")
        self.sp_order = QSpinBox()
        self.sp_order.setRange(1, 20)
        self.sp_order.setMinimumHeight(38)
        self.sp_order.setStyleSheet(
            f"border: 1px solid {colors.BORDER}; border-radius: 6px; padding: 5px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};"
        )

        self.btn_cls = QPushButton("Ajouter")
        self.btn_cls.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        self.btn_cls.clicked.connect(self.save_class)

        self.table_classes = QTableWidget(0, 5)
        self.style_table(self.table_classes)
        self.table_classes.setHorizontalHeaderLabels(["ID", "Cycle", "Classe (FR)", "Classe (AR)", "Action"])
        self.table_classes.setColumnWidth(0, 40)

        cls_lay.addWidget(QLabel("Cycle:"))
        cls_lay.addWidget(self.combo_cycles_cls)
        cls_lay.addWidget(self.txt_cls_fr)
        cls_lay.addWidget(self.txt_cls_ar)
        cls_lay.addWidget(QLabel("Ordre:"))
        cls_lay.addWidget(self.sp_order)
        cls_lay.addWidget(self.btn_cls)
        cls_lay.addWidget(self.table_classes)

        layout.addWidget(y_card, 1)
        layout.addWidget(c_card, 1)
        layout.addWidget(cls_card, 1)
        self.tabs.addTab(tab, "  📊 Structure / الهيكل  ")

    # --- 3. المواد ---
    def setup_subjects_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        colors = ThemeManager.get_colors()

        card, vlay = self.create_card("📚 Matières par Cycle / المواد حسب المرحلة")

        form = QGridLayout()
        form.setSpacing(10)

        self.combo_cycles_sub = self.styled_combo()
        self.txt_sub_fr = self.styled_input("Matière (FR)")
        self.txt_sub_ar = self.styled_input("المادة (عربي)")
        self.sp_coeff = QDoubleSpinBox()
        self.sp_coeff.setRange(0.1, 10.0)
        self.sp_coeff.setSingleStep(0.1)
        self.sp_coeff.setMinimumHeight(38)
        self.sp_coeff.setStyleSheet(
            f"border: 1px solid {colors.BORDER}; border-radius: 6px; padding: 5px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};"
        )

        self.combo_sub_lang = self.styled_combo()
        self.combo_sub_lang.addItems(["Français", "Arabe"])

        form.addWidget(QLabel("Cycle:"), 0, 0)
        form.addWidget(self.combo_cycles_sub, 0, 1)
        form.addWidget(QLabel("Nom FR:"), 1, 0)
        form.addWidget(self.txt_sub_fr, 1, 1)
        form.addWidget(QLabel("Nom AR:"), 2, 0)
        form.addWidget(self.txt_sub_ar, 2, 1)
        form.addWidget(QLabel("Coeff:"), 3, 0)
        form.addWidget(self.sp_coeff, 3, 1)
        form.addWidget(QLabel("Langue:"), 4, 0)
        form.addWidget(self.combo_sub_lang, 4, 1)

        self.btn_sub = QPushButton("Ajouter Matière")
        self.btn_sub.setMinimumHeight(40)
        self.btn_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sub.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; border-radius: 6px; font-weight: bold;"
        )
        self.btn_sub.clicked.connect(self.save_subject)

        vlay.addLayout(form)
        vlay.addWidget(self.btn_sub)

        self.table_subjects = QTableWidget(0, 7)
        self.style_table(self.table_subjects)
        self.table_subjects.setHorizontalHeaderLabels(
            ["ID", "Cycle", "Matière (FR)", "المادة (AR)", "Lang", "Coef", "Act"]
        )
        header_subjects = self.table_subjects.horizontalHeader()
        if header_subjects:
            header_subjects.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_subjects.setColumnWidth(0, 40)
        self.table_subjects.setColumnWidth(6, 80)
        vlay.addWidget(self.table_subjects)

        layout.addWidget(card)
        self.tabs.addTab(tab, "  📖 Matières / المواد  ")

    # --- 4. التقييمات ---
    def setup_evaluations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        colors = ThemeManager.get_colors()

        gen_card, gen_lay = self.create_card("⚙️ Génération Automatique (Périodes & Évaluations)")

        hbox = QHBoxLayout()
        hbox.setSpacing(15)
        self.combo_year_gen = self.styled_combo()
        self.combo_cycle_gen = self.styled_combo()
        self.combo_year_gen.currentIndexChanged.connect(self._on_generation_selection_changed)
        self.combo_cycle_gen.currentIndexChanged.connect(self._on_generation_selection_changed)
        btn_gen = QPushButton("⚡ Générer Configuration")
        btn_gen.setMinimumHeight(40)
        btn_gen.setStyleSheet(
            f"background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px;"
        )
        btn_gen.clicked.connect(self.generate_academic_logic)

        hbox.addWidget(QLabel("Année:"))
        hbox.addWidget(self.combo_year_gen, 1)
        hbox.addWidget(QLabel("Cycle:"))
        hbox.addWidget(self.combo_cycle_gen, 1)
        hbox.addWidget(btn_gen)
        gen_lay.addLayout(hbox)

        self.btn_save_period_ranges = QPushButton("💾 Valider Dates des Périodes")
        self.btn_save_period_ranges.setMinimumHeight(38)
        self.btn_save_period_ranges.setStyleSheet(
            f"background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 6px;"
        )
        self.btn_save_period_ranges.clicked.connect(self.save_period_ranges)
        gen_lay.addWidget(self.btn_save_period_ranges)

        self.btn_auto_fix_period_ranges = QPushButton("🛠️ Corriger Auto (Plages)")
        self.btn_auto_fix_period_ranges.setMinimumHeight(38)
        self.btn_auto_fix_period_ranges.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px;"
        )
        self.btn_auto_fix_period_ranges.clicked.connect(self.auto_fix_period_ranges)
        gen_lay.addWidget(self.btn_auto_fix_period_ranges)

        self.table_period_ranges = QTableWidget(0, 4)
        self.style_table(self.table_period_ranges)
        self.table_period_ranges.setHorizontalHeaderLabels(["ID", "Période", "Début", "Fin"])
        self.table_period_ranges.setColumnWidth(0, 50)
        header_periods = self.table_period_ranges.horizontalHeader()
        if header_periods:
            header_periods.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header_periods.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header_periods.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_period_ranges.itemChanged.connect(self._on_period_range_item_changed)
        gen_lay.addWidget(self.table_period_ranges)

        layout.addWidget(gen_card)

        self.table_evals = QTableWidget(0, 7)
        self.style_table(self.table_evals)
        self.table_evals.setHorizontalHeaderLabels(
            ["ID", "Cycle", "Période", "Type (FR)", "النوع (AR)", "Poids", "Act"]
        )
        header_evals = self.table_evals.horizontalHeader()
        if header_evals:
            header_evals.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_evals.setColumnWidth(0, 40)
        layout.addWidget(self.table_evals)

        self.tabs.addTab(tab, "  📝 Évaluations / التقييمات  ")

    def _on_generation_selection_changed(self):
        year_id = self.combo_year_gen.currentData()
        cycle_id = self.combo_cycle_gen.currentData()
        if year_id and cycle_id:
            self.load_period_ranges_editor(year_id, cycle_id)

    def _parse_period_date(self, value: str):
        text = (value or "").strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    def _split_year_range(self, start: date, end: date, count: int) -> list[tuple[date, date]]:
        total_days = (end - start).days + 1
        base_days = total_days // count
        remainder = total_days % count
        ranges = []
        cursor = start
        for idx in range(count):
            days = base_days + (1 if idx < remainder else 0)
            cursor_end = cursor + timedelta(days=days - 1)
            ranges.append((cursor, cursor_end))
            cursor = cursor_end + timedelta(days=1)
        return ranges

    def _on_period_range_item_changed(self, item):
        if not item:
            return
        if item.column() in (2, 3):
            self._refresh_period_ranges_visual_validation()

    def _on_period_date_widget_changed(self, _):
        if not self._period_ranges_loading:
            self._refresh_period_ranges_visual_validation()

    def _get_period_row_dates(self, row: int):
        start_widget = self.table_period_ranges.cellWidget(row, 2)
        end_widget = self.table_period_ranges.cellWidget(row, 3)

        start_val = None
        end_val = None

        if isinstance(start_widget, QDateEdit):
            d = start_widget.date().toPyDate()
            start_val = date(d.year, d.month, d.day)
        else:
            start_item = self.table_period_ranges.item(row, 2)
            start_val = self._parse_period_date(start_item.text() if start_item else "")

        if isinstance(end_widget, QDateEdit):
            d = end_widget.date().toPyDate()
            end_val = date(d.year, d.month, d.day)
        else:
            end_item = self.table_period_ranges.item(row, 3)
            end_val = self._parse_period_date(end_item.text() if end_item else "")

        return start_val, end_val

    def _mark_period_row_error(self, row: int, is_error: bool):
        for col in (2, 3):
            widget = self.table_period_ranges.cellWidget(row, col)
            if isinstance(widget, QDateEdit):
                widget.setStyleSheet(self._period_date_editor_style(error=is_error))
            else:
                item = self.table_period_ranges.item(row, col)
                if item:
                    item.setBackground(QColor("#FEE2E2") if is_error else QColor(Qt.GlobalColor.transparent))

    def _refresh_period_ranges_visual_validation(self):
        for row in range(self.table_period_ranges.rowCount()):
            self._mark_period_row_error(row, is_error=False)

        year_start = None
        year_end = None
        year_id = self.current_generated_year_id or self.combo_year_gen.currentData()
        if year_id:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    year_data = AcademicRepository(conn).get_year(year_id)
                    if year_data and year_data[1] and year_data[2]:
                        year_start = date.fromisoformat(str(year_data[1]))
                        year_end = date.fromisoformat(str(year_data[2]))
            except Exception:
                year_start = None
                year_end = None

        rows_data = []
        for row in range(self.table_period_ranges.rowCount()):
            start_val, end_val = self._get_period_row_dates(row)
            rows_data.append((row, start_val, end_val))

            invalid = False
            if not start_val or not end_val:
                invalid = True
            elif end_val < start_val:
                invalid = True
            elif year_start and year_end and (start_val < year_start or end_val > year_end):
                invalid = True

            if invalid:
                self._mark_period_row_error(row, is_error=True)

        sorted_rows = sorted(
            [r for r in rows_data if r[1] and r[2]],
            key=lambda t: t[1],
        )
        for i in range(1, len(sorted_rows)):
            prev_row, prev_start, prev_end = sorted_rows[i - 1]
            cur_row, cur_start, _ = sorted_rows[i]
            if cur_start <= prev_end or cur_start > (prev_end + date.resolution):
                for row in (prev_row, cur_row):
                    self._mark_period_row_error(row, is_error=True)

    def load_period_ranges_editor(self, year_id, cycle_id):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                periods = AcademicRepository(conn).list_periods_for_year_cycle(year_id, cycle_id)

            self._period_ranges_loading = True
            self.table_period_ranges.blockSignals(True)
            self.table_period_ranges.setRowCount(0)
            for p in periods:
                row = self.table_period_ranges.rowCount()
                self.table_period_ranges.insertRow(row)
                self.table_period_ranges.setItem(row, 0, QTableWidgetItem(self.safe_text(p[0])))
                self.table_period_ranges.setItem(row, 1, QTableWidgetItem(self.safe_text(p[1] or p[2])))

                self.table_period_ranges.setCellWidget(row, 2, self._create_period_date_editor(self.safe_text(p[4])))
                self.table_period_ranges.setCellWidget(row, 3, self._create_period_date_editor(self.safe_text(p[5])))
            self.table_period_ranges.blockSignals(False)
            self._refresh_period_ranges_visual_validation()

            self.current_generated_year_id = year_id
            self.current_generated_cycle_id = cycle_id
        except Exception as e:
            QMessageBox.warning(self, "Attention", f"Chargement des périodes impossible: {e}")
        finally:
            self._period_ranges_loading = False
            try:
                self.table_period_ranges.blockSignals(False)
            except Exception:
                pass

    def auto_fix_period_ranges(self):
        year_id = self.current_generated_year_id or self.combo_year_gen.currentData()
        if not year_id:
            QMessageBox.warning(
                self, "Attention", self.msg("Sélectionnez d'abord une année.", "يرجى اختيار السنة أولاً.")
            )
            return
        if self.table_period_ranges.rowCount() == 0:
            QMessageBox.warning(self, "Attention", self.msg("Aucune période à corriger.", "لا توجد فترات للتصحيح."))
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                year_data = AcademicRepository(conn).get_year(year_id)
            if not year_data or not year_data[1] or not year_data[2]:
                QMessageBox.warning(
                    self,
                    "Attention",
                    self.msg("Dates de l'année scolaire introuvables.", "تعذر العثور على تواريخ السنة الدراسية."),
                )
                return

            year_start = date.fromisoformat(str(year_data[1]))
            year_end = date.fromisoformat(str(year_data[2]))
            ranges = self._split_year_range(year_start, year_end, self.table_period_ranges.rowCount())

            self._period_ranges_loading = True
            self.table_period_ranges.blockSignals(True)
            for row, (r_start, r_end) in enumerate(ranges):
                start_widget = self.table_period_ranges.cellWidget(row, 2)
                end_widget = self.table_period_ranges.cellWidget(row, 3)
                if isinstance(start_widget, QDateEdit):
                    start_widget.setDate(QDate(r_start.year, r_start.month, r_start.day))
                else:
                    self.table_period_ranges.setItem(row, 2, QTableWidgetItem(r_start.isoformat()))
                if isinstance(end_widget, QDateEdit):
                    end_widget.setDate(QDate(r_end.year, r_end.month, r_end.day))
                else:
                    self.table_period_ranges.setItem(row, 3, QTableWidgetItem(r_end.isoformat()))
            self.table_period_ranges.blockSignals(False)

            self._refresh_period_ranges_visual_validation()
            QMessageBox.information(
                self,
                "Succès",
                self.msg("Plages de dates recalculées automatiquement.", "تمت إعادة حساب فترات التواريخ تلقائيًا."),
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
        finally:
            self._period_ranges_loading = False
            try:
                self.table_period_ranges.blockSignals(False)
            except Exception:
                pass

    def save_period_ranges(self):
        year_id = self.current_generated_year_id or self.combo_year_gen.currentData()
        cycle_id = self.current_generated_cycle_id or self.combo_cycle_gen.currentData()
        if not year_id or not cycle_id:
            QMessageBox.warning(
                self,
                "Attention",
                self.msg("Sélectionnez d'abord une année et un cycle.", "يرجى اختيار السنة والمرحلة أولاً."),
            )
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AcademicRepository(conn)
                year_data = repo.get_year(year_id)
                if not year_data or not year_data[1] or not year_data[2]:
                    QMessageBox.warning(
                        self,
                        "Attention",
                        self.msg("Dates de l'année scolaire introuvables.", "تعذر العثور على تواريخ السنة الدراسية."),
                    )
                    return

                year_start = date.fromisoformat(str(year_data[1]))
                year_end = date.fromisoformat(str(year_data[2]))
                rows_to_save = []

                for row in range(self.table_period_ranges.rowCount()):
                    period_id_item = self.table_period_ranges.item(row, 0)
                    period_name_item = self.table_period_ranges.item(row, 1)
                    period_name = self.safe_text(period_name_item.text()) if period_name_item else f"#{row + 1}"

                    if not period_id_item:
                        raise ValueError(
                            self.msg(
                                f"Données incomplètes pour la période {period_name}.",
                                f"بيانات غير مكتملة للفترة {period_name}.",
                            )
                        )

                    start_val, end_val = self._get_period_row_dates(row)
                    if not start_val or not end_val:
                        raise ValueError(
                            self.msg(
                                f"Veuillez renseigner début/fin pour {period_name}.",
                                f"يرجى إدخال تاريخ البداية والنهاية للفترة {period_name}.",
                            )
                        )

                    p_start = start_val
                    p_end = end_val
                    if p_end < p_start:
                        raise ValueError(
                            self.msg(
                                f"Date fin < date début pour {period_name}.",
                                f"تاريخ النهاية أصغر من تاريخ البداية للفترة {period_name}.",
                            )
                        )
                    if p_start < year_start or p_end > year_end:
                        raise ValueError(
                            self.msg(
                                f"{period_name} est hors plage de l'année scolaire.",
                                f"الفترة {period_name} خارج نطاق السنة الدراسية.",
                            )
                        )

                    rows_to_save.append((int(period_id_item.text()), period_name, p_start, p_end))

                # Validation overlap
                sorted_rows = sorted(rows_to_save, key=lambda r: r[2])
                for i in range(1, len(sorted_rows)):
                    prev_row = sorted_rows[i - 1]
                    cur_row = sorted_rows[i]
                    if cur_row[2] <= prev_row[3]:
                        raise ValueError(
                            self.msg(
                                f"Chevauchement entre {prev_row[1]} et {cur_row[1]}.",
                                f"يوجد تداخل بين {prev_row[1]} و {cur_row[1]}.",
                            )
                        )
                    if cur_row[2] > (prev_row[3] + date.resolution):
                        raise ValueError(
                            self.msg(
                                f"Gap détecté entre {prev_row[1]} et {cur_row[1]}.",
                                f"يوجد فراغ زمني بين {prev_row[1]} و {cur_row[1]}.",
                            )
                        )

                if sorted_rows and sorted_rows[0][2] != year_start:
                    raise ValueError(
                        self.msg(
                            "La première période doit commencer à la date de début de l'année scolaire.",
                            "يجب أن تبدأ الفترة الأولى من تاريخ بداية السنة الدراسية.",
                        )
                    )
                if sorted_rows and sorted_rows[-1][3] != year_end:
                    raise ValueError(
                        self.msg(
                            "La dernière période doit se terminer à la date de fin de l'année scolaire.",
                            "يجب أن تنتهي الفترة الأخيرة عند تاريخ نهاية السنة الدراسية.",
                        )
                    )

                for period_id, _, p_start, p_end in rows_to_save:
                    repo.update_period_dates(period_id, p_start.isoformat(), p_end.isoformat())

                conn.commit()

            self.refresh_all_data()
            self.load_period_ranges_editor(year_id, cycle_id)
            QMessageBox.information(
                self,
                "Succès",
                self.msg("Dates des périodes enregistrées avec succès.", "تم حفظ تواريخ الفترات بنجاح."),
            )
        except ValueError as ve:
            QMessageBox.warning(self, "Validation", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # --- CRUD Operations ---

    # 1. Years
    def save_year(self):
        label = self.txt_year.text().strip()
        if not label:
            return
        start_dt = self.year_start_date.date().toPyDate()
        end_dt = self.year_end_date.date().toPyDate()
        if end_dt < start_dt:
            QMessageBox.warning(
                self,
                "Erreur",
                "La date de fin doit être supérieure ou égale à la date de début. / تاريخ النهاية يجب أن يكون بعد البداية.",
            )
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                AcademicRepository(conn).upsert_year(
                    self.current_year_id,
                    label,
                    start_dt.isoformat(),
                    end_dt.isoformat(),
                )
                conn.commit()
            self.txt_year.clear()
            self.year_start_date.setDate(QDate(QDate.currentDate().year(), 9, 1))
            self.year_end_date.setDate(QDate(QDate.currentDate().year() + 1, 7, 31))
            self.current_year_id = None
            self.btn_y.setText("Ajouter")
            self.refresh_all_data()
        except psycopg2.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Cette année existe déjà. / هذه السنة موجودة مسبقاً.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur: {e}")

    def edit_year(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = AcademicRepository(conn).get_year(id)
        if res:
            self.txt_year.setText(res[0])
            if len(res) > 2 and res[1] and res[2]:
                self.year_start_date.setDate(QDate.fromString(str(res[1]), "yyyy-MM-dd"))
                self.year_end_date.setDate(QDate.fromString(str(res[2]), "yyyy-MM-dd"))
            self.current_year_id = id
            self.btn_y.setText("Modifier")

    def activate_year(self, id):
        """تنشيط السنة الدراسية - إزالة التنشيط من جميع السنوات الأخرى"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                AcademicRepository(conn).activate_year(id)
                conn.commit()
            self.refresh_all_data()
            QMessageBox.information(
                self, "Succès", "Année scolaire activée avec succès! / تم تنشيط هذه السنة الدراسية!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_year(self, id):
        if (
            QMessageBox.question(
                self,
                "Supprimer",
                "Voulez-vous vraiment supprimer cette année ? / هل تريد الحذف؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    repo = AcademicRepository(conn)
                    if repo.get_year_is_active(id):
                        QMessageBox.warning(
                            self, "Attention", "Impossible de supprimer l'année active. / لا يمكن حذف السنة النشطة."
                        )
                        return
                    repo.delete_year(id)
                    conn.commit()
                self.refresh_all_data()
            except psycopg2.IntegrityError:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Impossible de supprimer, données liées existantes. / توجد بيانات مرتبطة بهذه السنة.",
                )
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    # 2. Cycles
    def save_cycle(self):
        fr = self.txt_c_fr.text().strip()
        ar = self.txt_c_ar.text().strip()
        if not fr:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                AcademicRepository(conn).upsert_cycle(self.current_cycle_id, fr, ar)
                conn.commit()
            self.txt_c_fr.clear()
            self.txt_c_ar.clear()
            self.current_cycle_id = None
            self.btn_c.setText("Ajouter")
            self.refresh_all_data()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def edit_cycle(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = AcademicRepository(conn).get_cycle(id)
        if res:
            self.txt_c_fr.setText(res[0])
            self.txt_c_ar.setText(res[1])
            self.current_cycle_id = id
            self.btn_c.setText("Modifier")

    def delete_cycle(self, id):
        if (
            QMessageBox.question(
                self,
                "Supprimer",
                "Supprimer ce cycle ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).delete_cycle(id)
                    conn.commit()
                self.refresh_all_data()
            except psycopg2.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible de supprimer, des classes sont liées à ce cycle.")

    # 3. Classes
    def save_class(self):
        cid = self.combo_cycles_cls.currentData()
        fr = self.txt_cls_fr.text().strip()
        ar = self.txt_cls_ar.text().strip()
        order = self.sp_order.value()
        if not cid or not fr:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                AcademicRepository(conn).upsert_class(self.current_class_id, cid, fr, ar, order)
                conn.commit()

            self.txt_cls_fr.clear()
            self.txt_cls_ar.clear()
            self.sp_order.setValue(1)
            self.current_class_id = None
            self.btn_cls.setText("Ajouter")
            self.refresh_all_data()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def edit_class(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = AcademicRepository(conn).get_class(id)

        if res:
            idx = self.combo_cycles_cls.findData(res[0])
            self.combo_cycles_cls.setCurrentIndex(idx)
            self.txt_cls_fr.setText(res[1])
            self.txt_cls_ar.setText(res[2])
            self.sp_order.setValue(res[3])
            self.current_class_id = id
            self.btn_cls.setText("Modifier")

    def delete_class(self, id):
        if (
            QMessageBox.question(
                self,
                "Supprimer",
                "Supprimer cette classe ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).delete_class(id)
                    conn.commit()
                self.refresh_all_data()
            except psycopg2.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible, des étudiants sont liés à cette classe.")

    # 4. Subjects
    def save_subject(self):
        cid = self.combo_cycles_sub.currentData()
        fr = self.txt_sub_fr.text().strip()
        ar = self.txt_sub_ar.text().strip()
        coef = self.sp_coeff.value()
        lang = self.combo_sub_lang.currentText()
        if not cid or not fr:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                AcademicRepository(conn).upsert_subject(self.current_subject_id, cid, fr, ar, coef, lang)
                conn.commit()

            self.txt_sub_fr.clear()
            self.txt_sub_ar.clear()
            self.sp_coeff.setValue(1)
            self.current_subject_id = None
            self.btn_sub.setText("Ajouter Matière")
            self.refresh_all_data()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def edit_subject(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = AcademicRepository(conn).get_subject(id)

        if res:
            idx = self.combo_cycles_sub.findData(res[0])
            self.combo_cycles_sub.setCurrentIndex(idx)
            self.txt_sub_fr.setText(res[1])
            self.txt_sub_ar.setText(res[2])
            self.sp_coeff.setValue(float(res[3]))
            self.combo_sub_lang.setCurrentText(res[4] or "Français")
            self.current_subject_id = id
            self.btn_sub.setText("Modifier")

    def delete_subject(self, id):
        if (
            QMessageBox.question(
                self,
                "Supprimer",
                "Supprimer cette matière ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).delete_subject(id)
                    conn.commit()
                self.refresh_all_data()
            except psycopg2.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible, des notes existent pour cette matière.")

    # 5. Evaluations
    def delete_evaluation(self, id):
        if (
            QMessageBox.question(
                self,
                "Supprimer",
                "Supprimer cette évaluation ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).delete_evaluation(id)
                    conn.commit()
                self.refresh_all_data()
            except psycopg2.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible, des notes existent pour cette évaluation.")

    # --- Other Methods ---
    def save_school_info(self):
        republic = self.info_inputs['rep'].text()
        ia = self.info_inputs['ia'].text()
        ief = self.info_inputs['ief'].text()
        school_name = self.info_inputs['name'].text()
        auth = self.info_inputs['auth'].text()
        address = self.info_inputs['loc'].text()
        phone = self.info_inputs['tel'].text()
        director = self.info_inputs['director'].text()

        if self.config:
            try:
                self.config.set('APPLICATION', 'school_name', school_name)
                self.config.set('APPLICATION', 'school_location', address)
            except Exception:
                pass

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                AcademicRepository(conn).save_school_info(
                    republic, ia, ief, school_name, auth, address, phone, self.logo_path_value, director
                )
                conn.commit()
            QMessageBox.information(self, "Succès", "Informations enregistrées et mises à jour.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner le logo", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.logo_path_value = file_path
            self.logo_path_display.setText(os.path.basename(file_path))

    def generate_academic_logic(self):
        year_id = self.combo_year_gen.currentData()
        cycle_id = self.combo_cycle_gen.currentData()
        cycle_name = self.combo_cycle_gen.currentText().lower()

        if not year_id or not cycle_id:
            QMessageBox.warning(self, "Attention", "Sélectionnez l'année et le cycle.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AcademicRepository(conn)
                year_data = repo.get_year(year_id)
                if not year_data or not year_data[1] or not year_data[2]:
                    QMessageBox.warning(
                        self,
                        "Attention",
                        "Veuillez d'abord définir les dates de début et de fin de l'année scolaire. / يرجى تحديد تاريخ البداية والنهاية للسنة أولاً.",
                    )
                    return
                is_elementary = (
                    "elem" in cycle_name
                    or "prim" in cycle_name
                    or "\u0625\u0628\u062a\u062f\u0627\u0626\u064a" in cycle_name
                )
                repo.generate_periods_and_assessments(
                    year_id,
                    cycle_id,
                    is_elementary,
                    str(year_data[1]),
                    str(year_data[2]),
                )
                conn.commit()

            self.refresh_all_data()
            self.load_period_ranges_editor(year_id, cycle_id)
            QMessageBox.information(self, "Succ\u00e8s", "Configuration g\u00e9n\u00e9r\u00e9e avec succ\u00e8s.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def refresh_all_data(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AcademicRepository(conn)

                # School Info
                info = repo.get_school_info()
                if info:
                    if len(info) > 1:
                        self.info_inputs['rep'].setText(str(info[1] or ""))
                    if len(info) > 2:
                        self.info_inputs['ia'].setText(str(info[2] or ""))
                    if len(info) > 3:
                        self.info_inputs['ief'].setText(str(info[3] or ""))
                    if len(info) > 4:
                        self.info_inputs['name'].setText(str(info[4] or ""))
                    if len(info) > 5:
                        self.info_inputs['auth'].setText(str(info[5] or ""))
                    if len(info) > 6:
                        self.info_inputs['loc'].setText(str(info[6] or ""))
                    if len(info) > 7:
                        self.info_inputs['tel'].setText(str(info[7] or ""))
                    if len(info) > 8:
                        self.logo_path_value = info[8]
                        self.logo_path_display.setText(os.path.basename(info[8]) if info[8] else "")
                    if len(info) > 9:
                        self.info_inputs['director'].setText(str(info[9] or ""))
                else:
                    if self.config:
                        self.info_inputs['name'].setText(self.config.school_name)
                        self.info_inputs['loc'].setText(self.config.school_location)

                # Years
                self.table_years.setRowCount(0)
                self.combo_year_gen.clear()
                for r in repo.list_years():
                    idx = self.table_years.rowCount()
                    self.table_years.insertRow(idx)
                    self.table_years.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    year_label = self.safe_text(r[1])
                    if len(r) > 4 and r[3] and r[4]:
                        year_label = f"{year_label} ({r[3]} → {r[4]})"
                    self.table_years.setItem(idx, 1, QTableWidgetItem(year_label))

                    status_item = QTableWidgetItem("✓ Actif" if r[2] else "✕")
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    colors = ThemeManager.get_colors()
                    status_item.setForeground(QColor(colors.SUCCESS if r[2] else colors.TEXT_SECONDARY))
                    self.table_years.setItem(idx, 2, status_item)

                    widget = QWidget()
                    layout = QHBoxLayout(widget)
                    layout.setContentsMargins(2, 2, 2, 2)
                    layout.setSpacing(5)

                    colors = ThemeManager.get_colors()
                    btn_activate = QPushButton("Activer")
                    btn_activate.setFixedHeight(28)
                    btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_activate.setStyleSheet(
                        f"background-color: {colors.SUCCESS}; color: white; border-radius: 4px; border: none; font-weight: bold;"
                        if r[2]
                        else f"background-color: {colors.BORDER}; color: {colors.TEXT_SECONDARY}; border-radius: 4px; border: none;"
                    )
                    btn_activate.clicked.connect(lambda checked, id=r[0]: self.activate_year(id))
                    layout.addWidget(btn_activate)

                    btn_edit = QPushButton("✎")
                    btn_edit.setFixedSize(28, 28)
                    btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_edit.setStyleSheet(
                        f"background-color: {colors.WARNING}; color: white; border-radius: 4px; border: none;"
                    )
                    btn_edit.clicked.connect(lambda checked, id=r[0]: self.edit_year(id))
                    layout.addWidget(btn_edit)

                    btn_del = QPushButton("✕")
                    btn_del.setFixedSize(28, 28)
                    btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del.setStyleSheet(
                        f"background-color: {colors.DANGER}; color: white; border-radius: 4px; border: none;"
                    )
                    btn_del.clicked.connect(lambda checked, id=r[0]: self.delete_year(id))
                    layout.addWidget(btn_del)

                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table_years.setCellWidget(idx, 3, widget)
                    self.combo_year_gen.addItem(self.safe_text(r[1]), r[0])

                # Cycles
                self.table_cycles.setRowCount(0)
                self.combo_cycles_cls.clear()
                self.combo_cycles_sub.clear()
                self.combo_cycle_gen.clear()
                for r in repo.list_cycles():
                    idx = self.table_cycles.rowCount()
                    self.table_cycles.insertRow(idx)
                    self.table_cycles.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_cycles.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    self.table_cycles.setItem(idx, 2, QTableWidgetItem(self.safe_text(r[2])))
                    self.add_action_buttons(self.table_cycles, idx, r[0], self.edit_cycle, self.delete_cycle)

                    cycle_label = self.safe_text(r[1])
                    self.combo_cycles_cls.addItem(cycle_label, r[0])
                    self.combo_cycles_sub.addItem(cycle_label, r[0])
                    self.combo_cycle_gen.addItem(cycle_label, r[0])

                # Classes
                self.table_classes.setRowCount(0)
                for r in repo.list_classes_with_cycle():
                    idx = self.table_classes.rowCount()
                    self.table_classes.insertRow(idx)
                    self.table_classes.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_classes.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    self.table_classes.setItem(idx, 2, QTableWidgetItem(self.safe_text(r[2])))
                    self.table_classes.setItem(idx, 3, QTableWidgetItem(self.safe_text(r[3])))
                    self.add_action_buttons(self.table_classes, idx, r[0], self.edit_class, self.delete_class)

                # Subjects
                self.table_subjects.setRowCount(0)
                for r in repo.list_subjects_with_cycle():
                    idx = self.table_subjects.rowCount()
                    self.table_subjects.insertRow(idx)
                    for c, v in enumerate(r):
                        self.table_subjects.setItem(idx, c, QTableWidgetItem(self.safe_text(v)))
                    self.add_action_buttons(self.table_subjects, idx, r[0], self.edit_subject, self.delete_subject)

                # Evals
                self.table_evals.setRowCount(0)
                for r in repo.list_evaluations():
                    idx = self.table_evals.rowCount()
                    self.table_evals.insertRow(idx)
                    self.table_evals.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_evals.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    self.table_evals.setItem(idx, 2, QTableWidgetItem(self.safe_text(r[2])))
                    self.table_evals.setItem(idx, 3, QTableWidgetItem(self.safe_text(r[3])))
                    self.table_evals.setItem(idx, 4, QTableWidgetItem(self.safe_text(r[4])))
                    self.table_evals.setItem(idx, 5, QTableWidgetItem(self.safe_text(r[6])))
                    self.add_action_buttons(self.table_evals, idx, r[0], None, self.delete_evaluation)

        except Exception as e:
            QMessageBox.critical(self, "Erreur de chargement", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AcademicSettingsWindow()
    window.show()
    sys.exit(app.exec())
