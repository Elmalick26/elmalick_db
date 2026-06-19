import os
import sys
from datetime import date, timedelta

import psycopg2

from app_logger import AppLogger
from database_setup import DatabaseManager
from repositories.academic_repo import AcademicRepository
from services.grade_service import is_primary_cycle

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
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
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

from ui_components import (
    BaseDialog,
    BaseWindow,
    create_card,
    dialog_button_row,
    dialog_error_label,
    style_table,
    styled_button,
    styled_combo,
    styled_date_edit,
    styled_input,
)
from ui_styles import (
    Colors,
    ModuleHeaderWidget,
    ThemeManager,
    apply_shadow_to_widget,
    friendly_db_error,
    get_card_style,
    get_module_caps,
    get_tabs_style,
)


class YearDialog(BaseDialog):
    def __init__(self, data: dict | None = None, parent=None):
        super().__init__("Modifier l'Année" if data else "Ajouter une Année", parent)
        self.setMinimumWidth(420)
        self.setModal(True)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        form = QFormLayout()
        form.setSpacing(12)
        self.txt_label = styled_input("Ex: 2025-2026")
        self.date_start = styled_date_edit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setMinimumDate(QDate(1900, 1, 1))
        self.date_start.setMaximumDate(QDate(2100, 12, 31))
        self.date_start.setDate(QDate(QDate.currentDate().year(), 9, 1))
        self.date_end = styled_date_edit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setMinimumDate(QDate(1900, 1, 1))
        self.date_end.setMaximumDate(QDate(2100, 12, 31))
        self.date_end.setDate(QDate(QDate.currentDate().year() + 1, 7, 31))
        if data:
            self.txt_label.setText(data.get("label", ""))
            if data.get("start"):
                self.date_start.setDate(QDate.fromString(str(data["start"]), "yyyy-MM-dd"))
            if data.get("end"):
                self.date_end.setDate(QDate.fromString(str(data["end"]), "yyyy-MM-dd"))
        form.addRow("Année:", self.txt_label)
        form.addRow("Début:", self.date_start)
        form.addRow("Fin:", self.date_end)
        self.dialog_layout.addLayout(form)
        self.dialog_layout.addLayout(dialog_button_row("💾 Enregistrer", self._validate, self.reject))

    def _validate(self):
        if not self.txt_label.text().strip():
            self._err_lbl.setText("Veuillez saisir le libellé de l'année.")
            self._err_lbl.setVisible(True)
            return
        if self.date_end.date() < self.date_start.date():
            self._err_lbl.setText("La date de fin doit être après la date de début.")
            self._err_lbl.setVisible(True)
            return
        self.accept()

    def get_values(self) -> dict:
        return {
            "label": self.txt_label.text().strip(),
            "start": self.date_start.date().toPyDate().isoformat(),
            "end": self.date_end.date().toPyDate().isoformat(),
        }


class CycleDialog(BaseDialog):
    def __init__(self, data: dict | None = None, parent=None):
        super().__init__("Modifier le Cycle" if data else "Ajouter un Cycle", parent)
        self.setMinimumWidth(380)
        self.setModal(True)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        form = QFormLayout()
        form.setSpacing(12)
        self.txt_fr = styled_input("Nom (FR)")
        self.txt_ar = styled_input("الاسم (عربي)")
        if data:
            self.txt_fr.setText(data.get("fr", ""))
            self.txt_ar.setText(data.get("ar", ""))
        form.addRow("Nom FR:", self.txt_fr)
        form.addRow("Nom AR:", self.txt_ar)
        self.dialog_layout.addLayout(form)
        self.dialog_layout.addLayout(dialog_button_row("💾 Enregistrer", self._validate, self.reject))

    def _validate(self):
        if not self.txt_fr.text().strip():
            self._err_lbl.setText("Veuillez saisir le nom du cycle.")
            self._err_lbl.setVisible(True)
            return
        self.accept()

    def get_values(self) -> dict:
        return {"fr": self.txt_fr.text().strip(), "ar": self.txt_ar.text().strip()}


class ClassDialog(BaseDialog):
    def __init__(self, cycles: list, data: dict | None = None, parent=None):
        super().__init__("Modifier la Classe" if data else "Ajouter une Classe", parent)
        self.setMinimumWidth(400)
        self.setModal(True)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        form = QFormLayout()
        form.setSpacing(12)
        self.cmb_cycle = styled_combo()
        for cid, name in cycles:
            self.cmb_cycle.addItem(name, cid)
        self.txt_fr = styled_input("Nom (FR)")
        self.txt_ar = styled_input("الاسم (عربي)")
        self.sp_order = QSpinBox()
        self.sp_order.setRange(1, 20)
        self.sp_order.setValue(1)
        self.sp_order.setMinimumHeight(42)
        if data:
            idx = self.cmb_cycle.findData(data.get("cycle_id"))
            if idx >= 0:
                self.cmb_cycle.setCurrentIndex(idx)
            self.txt_fr.setText(data.get("fr", ""))
            self.txt_ar.setText(data.get("ar", ""))
            self.sp_order.setValue(data.get("order", 1))
        form.addRow("Cycle:", self.cmb_cycle)
        form.addRow("Nom FR:", self.txt_fr)
        form.addRow("Nom AR:", self.txt_ar)
        form.addRow("Ordre:", self.sp_order)
        self.dialog_layout.addLayout(form)
        self.dialog_layout.addLayout(dialog_button_row("💾 Enregistrer", self._validate, self.reject))

    def _validate(self):
        if not self.txt_fr.text().strip():
            self._err_lbl.setText("Veuillez saisir le nom de la classe.")
            self._err_lbl.setVisible(True)
            return
        if not self.cmb_cycle.currentData():
            self._err_lbl.setText("Veuillez sélectionner un cycle.")
            self._err_lbl.setVisible(True)
            return
        self.accept()

    def get_values(self) -> dict:
        return {
            "cycle_id": self.cmb_cycle.currentData(),
            "fr": self.txt_fr.text().strip(),
            "ar": self.txt_ar.text().strip(),
            "order": self.sp_order.value(),
        }


class SubjectDialog(BaseDialog):
    def __init__(self, cycles: list, data: dict | None = None, parent=None):
        super().__init__("Modifier la Matière" if data else "Ajouter une Matière", parent)
        self.setMinimumWidth(400)
        self.setModal(True)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        form = QFormLayout()
        form.setSpacing(12)
        self.cmb_cycle = styled_combo()
        for cid, name in cycles:
            self.cmb_cycle.addItem(name, cid)
        self.txt_fr = styled_input("Matière (FR)")
        self.txt_ar = styled_input("المادة (عربي)")
        self.sp_coeff = QDoubleSpinBox()
        self.sp_coeff.setRange(0.1, 10.0)
        self.sp_coeff.setSingleStep(0.1)
        self.sp_coeff.setValue(1.0)
        self.sp_coeff.setMinimumHeight(42)
        self.cmb_lang = styled_combo()
        self.cmb_lang.addItems(["Français", "Arabe"])
        if data:
            idx = self.cmb_cycle.findData(data.get("cycle_id"))
            if idx >= 0:
                self.cmb_cycle.setCurrentIndex(idx)
            self.txt_fr.setText(data.get("fr", ""))
            self.txt_ar.setText(data.get("ar", ""))
            self.sp_coeff.setValue(float(data.get("coeff", 1.0)))
            idx_l = self.cmb_lang.findText(data.get("lang", "Français"))
            if idx_l >= 0:
                self.cmb_lang.setCurrentIndex(idx_l)
        form.addRow("Cycle:", self.cmb_cycle)
        form.addRow("Nom FR:", self.txt_fr)
        form.addRow("Nom AR:", self.txt_ar)
        form.addRow("Coeff:", self.sp_coeff)
        form.addRow("Langue:", self.cmb_lang)
        self.dialog_layout.addLayout(form)
        self.dialog_layout.addLayout(dialog_button_row("💾 Enregistrer", self._validate, self.reject))

    def _validate(self):
        if not self.txt_fr.text().strip():
            self._err_lbl.setText("Veuillez saisir le nom de la matière.")
            self._err_lbl.setVisible(True)
            return
        if not self.cmb_cycle.currentData():
            self._err_lbl.setText("Veuillez sélectionner un cycle.")
            self._err_lbl.setVisible(True)
            return
        self.accept()

    def get_values(self) -> dict:
        return {
            "cycle_id": self.cmb_cycle.currentData(),
            "fr": self.txt_fr.text().strip(),
            "ar": self.txt_ar.text().strip(),
            "coeff": self.sp_coeff.value(),
            "lang": self.cmb_lang.currentText(),
        }


# ─────────────────────────────────────────────────────────────────────────────
class AcademicSettingsWindow(BaseWindow):
    def __init__(self):
        super().__init__("Configuration Scolaire / الإعدادات المدرسية", min_width=1100, min_height=700)
        self.config = ConfigManager() if HAS_CONFIG_MANAGER else None

        self.current_year_id = None
        self.current_cycle_id = None
        self.current_class_id = None
        self.current_subject_id = None
        self.logo_path_value = ""
        self.current_generated_year_id = None
        self.current_generated_cycle_id = None
        self._period_ranges_loading = False
        self._cycles_cache: list = []
        # FIX 4: Cache year date ranges to avoid a DB round-trip on every keypress
        self._year_date_cache: dict[int, tuple] = {}

        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        self.init_ui()
        self.refresh_all_data()
        # FIX 6: KPI stats are now loaded inside refresh_all_data — no separate call needed

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "academic_settings")
        for btn in (
            self.btn_y,
            self.btn_c,
            self.btn_cls,
            self.btn_sub,
            self.btn_save_period_ranges,
            self.btn_auto_fix_period_ranges,
        ):
            btn.setEnabled(caps["can_write"])
            btn.setVisible(caps["can_write"])

    def init_ui(self):

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

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_school_info_tab()
        self.setup_structure_tab()
        self.setup_subjects_tab()
        self.setup_evaluations_tab()

        self.main_layout.addWidget(self.tabs)

    # ── Helpers ───────────────────────────────────────────────────────────────

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
        editor = styled_date_edit("yyyy-MM-dd", min_height=38)
        parsed = self._parse_period_date(iso_value)
        editor.setDate(QDate(parsed.year, parsed.month, parsed.day) if parsed else QDate.currentDate())
        editor.dateChanged.connect(self._on_period_date_widget_changed)
        return editor

    def style_table(self, table):
        style_table(table)

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
                f"background-color: {colors.WARNING}; color: white; border-radius: 6px; border: none;"
            )
            btn_edit.clicked.connect(lambda _, val=id_val: edit_func(val))
            layout.addWidget(btn_edit)

        if delete_func:
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 6px; border: none;")
            btn_del.clicked.connect(lambda _, val=id_val: delete_func(val))
            layout.addWidget(btn_del)

        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setCellWidget(row_idx, table.columnCount() - 1, widget)

    # ── Tab 1: School Info ────────────────────────────────────────────────────

    def setup_school_info_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        card, grid_lay = create_card("🏛️ Identification de l'Établissement / بيانات المؤسسة")
        grid = QGridLayout()
        grid.setSpacing(15)

        self.info_inputs = {
            'rep': styled_input("Ex: République du Sénégal"),
            'ia': styled_input("Inspection d'Académie (IA)"),
            'ief': styled_input("Inspection IEF"),
            'name': styled_input("Nom de l'établissement"),
            'auth': styled_input("N° Autorisation"),
            'director': styled_input("Nom du Directeur / اسم المدير"),
            'loc': styled_input("Adresse"),
            'tel': styled_input("Téléphone"),
        }

        self.logo_path_display = styled_input("Logo Path")
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
            v.setMaximumWidth(380)
            grid.addWidget(QLabel(labels[k]), r, 0)
            grid.addWidget(v, r, 1)
            r += 1

        grid.addWidget(QLabel("Logo:"), r, 0)
        logo_h = QHBoxLayout()
        self.logo_path_display.setMaximumWidth(330)
        logo_h.addWidget(self.logo_path_display)
        btn_logo = QPushButton("📁")
        btn_logo.setFixedSize(40, 38)
        btn_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors()
        # FIX 1: Added missing comma between gradient stop:0 and stop:1
        btn_logo.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER}); color: white; border-radius: 6px; font-weight: bold; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_logo.clicked.connect(self.browse_logo)
        logo_h.addWidget(btn_logo)
        grid.addLayout(logo_h, r, 1)

        btn_save = styled_button(
            "💾 Enregistrer / حفظ",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=46,
        )
        btn_save.clicked.connect(self.save_school_info)

        form_container = QWidget()
        form_container.setMaximumWidth(640)
        form_vlay = QVBoxLayout(form_container)
        form_vlay.setContentsMargins(0, 0, 0, 0)
        form_vlay.addLayout(grid)
        form_hbox = QHBoxLayout()
        form_hbox.addWidget(form_container)
        form_hbox.addStretch()
        grid_lay.addLayout(form_hbox)
        grid_lay.addWidget(btn_save)
        layout.addWidget(card)
        layout.addStretch()
        self.tabs.addTab(tab, "  🏛️ Infos / معلومات  ")

    # ── Tab 2: Structure ──────────────────────────────────────────────────────

    def setup_structure_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        colors = ThemeManager.get_colors()

        def _add_btn(text: str) -> QPushButton:
            return styled_button(
                text,
                bg_color=colors.SUCCESS,
                hover_color=colors.SUCCESS_HOVER,
                min_height=36,
            )

        y_card, y_lay = create_card("📅 Années / السنوات")
        self.btn_y = _add_btn("+ Ajouter Année")
        self.btn_y.clicked.connect(lambda: self.open_year_dialog())
        self.table_years = QTableWidget(0, 4)
        self.style_table(self.table_years)
        self.table_years.setHorizontalHeaderLabels(["ID", "Année", "Actif", "Action"])
        self.table_years.setColumnWidth(0, 40)
        self.table_years.setColumnWidth(2, 60)
        y_lay.addWidget(self.btn_y)
        y_lay.addWidget(self.table_years)

        c_card, c_lay = create_card("🏫 Cycles / المراحل")
        self.btn_c = _add_btn("+ Ajouter Cycle")
        self.btn_c.clicked.connect(lambda: self.open_cycle_dialog())
        self.table_cycles = QTableWidget(0, 4)
        self.style_table(self.table_cycles)
        self.table_cycles.setHorizontalHeaderLabels(["ID", "Cycle (FR)", "Cycle (AR)", "Action"])
        self.table_cycles.setColumnWidth(0, 40)
        c_lay.addWidget(self.btn_c)
        c_lay.addWidget(self.table_cycles)

        cls_card, cls_lay = create_card("👥 Classes / الفصول")
        self.btn_cls = _add_btn("+ Ajouter Classe")
        self.btn_cls.clicked.connect(lambda: self.open_class_dialog())
        self.table_classes = QTableWidget(0, 5)
        self.style_table(self.table_classes)
        self.table_classes.setHorizontalHeaderLabels(["ID", "Cycle", "Classe (FR)", "Classe (AR)", "Action"])
        self.table_classes.setColumnWidth(0, 40)
        cls_lay.addWidget(self.btn_cls)
        cls_lay.addWidget(self.table_classes)

        layout.addWidget(y_card, 1)
        layout.addWidget(c_card, 1)
        layout.addWidget(cls_card, 1)
        self.tabs.addTab(tab, "  📊 Structure / الهيكل  ")

    # ── Tab 3: Subjects ───────────────────────────────────────────────────────

    def setup_subjects_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        colors = ThemeManager.get_colors()

        toolbar = QHBoxLayout()
        lbl_title = QLabel("📚 Matières par Cycle / المواد حسب المرحلة")
        lbl_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {colors.TEXT_PRIMARY};")
        toolbar.addWidget(lbl_title)
        toolbar.addStretch()
        self.btn_sub = styled_button(
            "+ Ajouter Matière",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=36,
        )
        self.btn_sub.clicked.connect(lambda: self.open_subject_dialog())
        toolbar.addWidget(self.btn_sub)
        layout.addLayout(toolbar)

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
        layout.addWidget(self.table_subjects)

        self.tabs.addTab(tab, "  📖 Matières / المواد  ")

    # ── Tab 4: Evaluations ────────────────────────────────────────────────────

    def setup_evaluations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        colors = ThemeManager.get_colors()

        gen_card, gen_lay = create_card("⚙️ Génération Automatique (Périodes & Évaluations)")

        hbox = QHBoxLayout()
        hbox.setSpacing(15)
        self.combo_year_gen = styled_combo()
        self.combo_cycle_gen = styled_combo()
        self.combo_year_gen.currentIndexChanged.connect(self._on_generation_selection_changed)
        self.combo_cycle_gen.currentIndexChanged.connect(self._on_generation_selection_changed)
        btn_gen = styled_button(
            "⚡ Générer Configuration",
            bg_color=colors.WARNING,
            hover_color="#B45309",
            min_height=42,
        )
        btn_gen.clicked.connect(self.generate_academic_logic)
        hbox.addWidget(QLabel("Année:"))
        hbox.addWidget(self.combo_year_gen, 1)
        hbox.addWidget(QLabel("Cycle:"))
        hbox.addWidget(self.combo_cycle_gen, 1)
        hbox.addWidget(btn_gen)
        gen_lay.addLayout(hbox)

        split = QHBoxLayout()
        split.setSpacing(16)

        self.table_period_ranges = QTableWidget(0, 4)
        self.style_table(self.table_period_ranges)
        self.table_period_ranges.setHorizontalHeaderLabels(["ID", "Période", "Début", "Fin"])
        self.table_period_ranges.setColumnWidth(0, 50)
        self.table_period_ranges.setMaximumHeight(160)
        header_periods = self.table_period_ranges.horizontalHeader()
        if header_periods:
            header_periods.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header_periods.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header_periods.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_period_ranges.itemChanged.connect(self._on_period_range_item_changed)
        split.addWidget(self.table_period_ranges, 3)

        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        s_lay = QVBoxLayout(sidebar)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(10)

        self.btn_save_period_ranges = styled_button(
            "💾 Valider Dates",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=38,
        )
        self.btn_save_period_ranges.clicked.connect(self.save_period_ranges)
        s_lay.addWidget(self.btn_save_period_ranges)

        self.btn_auto_fix_period_ranges = styled_button(
            "🛠️ Corriger Auto (Plages)",
            bg_color=colors.PRIMARY,
            hover_color=colors.PRIMARY_HOVER,
            min_height=38,
        )
        self.btn_auto_fix_period_ranges.clicked.connect(self.auto_fix_period_ranges)
        s_lay.addWidget(self.btn_auto_fix_period_ranges)
        s_lay.addStretch()

        split.addWidget(sidebar, 0)
        gen_lay.addLayout(split)

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

    # ── Period range event handlers ───────────────────────────────────────────

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

        # FIX 4: Use cached year dates instead of opening a DB connection on every keypress
        year_start = None
        year_end = None
        year_id = self.current_generated_year_id or self.combo_year_gen.currentData()
        if year_id and year_id in self._year_date_cache:
            year_start, year_end = self._year_date_cache[year_id]

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
        # FIX 7: Block signals before the DB call so the finally always has a matching unblock
        self._period_ranges_loading = True
        self.table_period_ranges.blockSignals(True)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                periods = AcademicRepository(conn).list_periods_for_year_cycle(year_id, cycle_id)

            self.table_period_ranges.setRowCount(0)
            for p in periods:
                row = self.table_period_ranges.rowCount()
                self.table_period_ranges.insertRow(row)
                self.table_period_ranges.setItem(row, 0, QTableWidgetItem(self.safe_text(p[0])))
                self.table_period_ranges.setItem(row, 1, QTableWidgetItem(self.safe_text(p[1] or p[2])))
                self.table_period_ranges.setCellWidget(row, 2, self._create_period_date_editor(self.safe_text(p[4])))
                self.table_period_ranges.setCellWidget(row, 3, self._create_period_date_editor(self.safe_text(p[5])))

            self.current_generated_year_id = year_id
            self.current_generated_cycle_id = cycle_id
        except Exception as e:
            QMessageBox.warning(self, "Attention", f"Chargement des périodes impossible: {e}")
        finally:
            self._period_ranges_loading = False
            self.table_period_ranges.blockSignals(False)

        self._refresh_period_ranges_visual_validation()

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
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))
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

                    if end_val < start_val:
                        raise ValueError(
                            self.msg(
                                f"Date fin < date début pour {period_name}.",
                                f"تاريخ النهاية أصغر من تاريخ البداية للفترة {period_name}.",
                            )
                        )
                    if start_val < year_start or end_val > year_end:
                        raise ValueError(
                            self.msg(
                                f"{period_name} est hors plage de l'année scolaire.",
                                f"الفترة {period_name} خارج نطاق السنة الدراسية.",
                            )
                        )

                    rows_to_save.append((int(period_id_item.text()), period_name, start_val, end_val))

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
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ── CRUD: Years ───────────────────────────────────────────────────────────

    def open_year_dialog(self, year_id=None):
        data = None
        if year_id:
            # FIX 2: Wrap initial data fetch in try/except to handle DB errors gracefully
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    res = AcademicRepository(conn).get_year(year_id)
                if res:
                    data = {
                        "label": res[0],
                        "start": str(res[1]) if len(res) > 1 and res[1] else "",
                        "end": str(res[2]) if len(res) > 2 and res[2] else "",
                    }
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))
                return

        dlg = YearDialog(data=data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            values = dlg.get_values()
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).upsert_year(year_id, values["label"], values["start"], values["end"])
                    conn.commit()
                self.refresh_all_data()
            except psycopg2.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Cette année existe déjà. / هذه السنة موجودة مسبقاً.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    def activate_year(self, id):
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
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))

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
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ── CRUD: Cycles ──────────────────────────────────────────────────────────

    def open_cycle_dialog(self, cycle_id=None):
        data = None
        if cycle_id:
            # FIX 2: Wrap initial data fetch in try/except
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    res = AcademicRepository(conn).get_cycle(cycle_id)
                if res:
                    data = {"fr": res[0], "ar": res[1]}
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))
                return

        dlg = CycleDialog(data=data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            values = dlg.get_values()
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).upsert_cycle(cycle_id, values["fr"], values["ar"])
                    conn.commit()
                self.refresh_all_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

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
            # FIX 3: Added general Exception handler — previously missing, could crash silently
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ── CRUD: Classes ─────────────────────────────────────────────────────────

    def open_class_dialog(self, class_id=None):
        data = None
        if class_id:
            # FIX 2: Wrap initial data fetch in try/except
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    res = AcademicRepository(conn).get_class(class_id)
                if res:
                    data = {
                        "cycle_id": res[0],
                        "fr": res[1],
                        "ar": res[2],
                        "order": res[3] if len(res) > 3 else 1,
                    }
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))
                return

        dlg = ClassDialog(cycles=self._cycles_cache, data=data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            values = dlg.get_values()
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).upsert_class(
                        class_id, values["cycle_id"], values["fr"], values["ar"], values["order"]
                    )
                    conn.commit()
                self.refresh_all_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

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
            # FIX 3: Added general Exception handler — previously missing, could crash silently
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ── CRUD: Subjects ────────────────────────────────────────────────────────

    def open_subject_dialog(self, subject_id=None):
        data = None
        if subject_id:
            # FIX 2: Wrap initial data fetch in try/except
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    res = AcademicRepository(conn).get_subject(subject_id)
                if res:
                    data = {
                        "cycle_id": res[0],
                        "fr": res[1],
                        "ar": res[2],
                        "coeff": float(res[3]) if len(res) > 3 else 1.0,
                        "lang": res[4] if len(res) > 4 else "Français",
                    }
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))
                return

        dlg = SubjectDialog(cycles=self._cycles_cache, data=data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            values = dlg.get_values()
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    AcademicRepository(conn).upsert_subject(
                        subject_id, values["cycle_id"], values["fr"], values["ar"], values["coeff"], values["lang"]
                    )
                    conn.commit()
                self.refresh_all_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

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
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ── CRUD: Evaluations ─────────────────────────────────────────────────────

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
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ── School Info ───────────────────────────────────────────────────────────

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
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))

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
                is_elementary = is_primary_cycle(cycle_name)
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
            QMessageBox.information(self, "Succès", "Configuration générée avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    # ── Master refresh ────────────────────────────────────────────────────────

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
                # FIX 4: Rebuild year date cache on each refresh
                self._year_date_cache = {}

                years_data = repo.list_years()
                for r in years_data:
                    # Populate year date cache — r = (id, label, is_active, start, end)
                    if r[3] and r[4]:
                        try:
                            self._year_date_cache[r[0]] = (
                                date.fromisoformat(str(r[3])),
                                date.fromisoformat(str(r[4])),
                            )
                        except (ValueError, TypeError):
                            pass

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
                    is_active = bool(r[2])
                    btn_activate = QPushButton("✓ Actif" if is_active else "Activer")
                    btn_activate.setFixedHeight(28)
                    btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
                    # FIX 5: Disable the button for already-active years to prevent no-op DB calls
                    btn_activate.setEnabled(not is_active)
                    btn_activate.setStyleSheet(
                        f"background-color: {colors.SUCCESS}; color: white; border-radius: 6px; border: none; font-weight: bold;"
                        if is_active
                        else f"background-color: {colors.BORDER}; color: {colors.TEXT_SECONDARY}; border-radius: 6px; border: none;"
                    )
                    btn_activate.clicked.connect(lambda checked, id=r[0]: self.activate_year(id))
                    layout.addWidget(btn_activate)

                    btn_edit = QPushButton("✎")
                    btn_edit.setFixedSize(28, 28)
                    btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_edit.setStyleSheet(
                        f"background-color: {colors.WARNING}; color: white; border-radius: 6px; border: none;"
                    )
                    btn_edit.clicked.connect(lambda checked, id=r[0]: self.open_year_dialog(year_id=id))
                    layout.addWidget(btn_edit)

                    btn_del = QPushButton("✕")
                    btn_del.setFixedSize(28, 28)
                    btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del.setStyleSheet(
                        f"background-color: {colors.DANGER}; color: white; border-radius: 6px; border: none;"
                    )
                    btn_del.clicked.connect(lambda checked, id=r[0]: self.delete_year(id))
                    layout.addWidget(btn_del)

                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table_years.setCellWidget(idx, 3, widget)
                    self.combo_year_gen.addItem(self.safe_text(r[1]), r[0])

                # Cycles
                self.table_cycles.setRowCount(0)
                self._cycles_cache = []
                self.combo_cycle_gen.clear()
                cycles_data = repo.list_cycles()
                for r in cycles_data:
                    idx = self.table_cycles.rowCount()
                    self.table_cycles.insertRow(idx)
                    self.table_cycles.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_cycles.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    self.table_cycles.setItem(idx, 2, QTableWidgetItem(self.safe_text(r[2])))
                    self.add_action_buttons(
                        self.table_cycles, idx, r[0], lambda id: self.open_cycle_dialog(cycle_id=id), self.delete_cycle
                    )

                    cycle_label = self.safe_text(r[1])
                    self._cycles_cache.append((r[0], cycle_label))
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
                    self.add_action_buttons(
                        self.table_classes, idx, r[0], lambda id: self.open_class_dialog(class_id=id), self.delete_class
                    )

                # Subjects
                self.table_subjects.setRowCount(0)
                for r in repo.list_subjects_with_cycle():
                    idx = self.table_subjects.rowCount()
                    self.table_subjects.insertRow(idx)
                    for c, v in enumerate(r):
                        self.table_subjects.setItem(idx, c, QTableWidgetItem(self.safe_text(v)))
                    self.add_action_buttons(
                        self.table_subjects,
                        idx,
                        r[0],
                        lambda id: self.open_subject_dialog(subject_id=id),
                        self.delete_subject,
                    )

                # Evaluations (r[5]=type_code is internal, not displayed; r[6]=weight shown as "Poids")
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

                # FIX 6: Load KPI stats within the same connection — eliminates the second DB connection on init
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM AcademicYears")
                    kpi_years = cursor.fetchone()[0] or 0
                    cursor.execute("SELECT COUNT(*) FROM Classes")
                    kpi_classes = cursor.fetchone()[0] or 0
                    cursor.execute("SELECT COUNT(*) FROM Subjects")
                    kpi_subjects = cursor.fetchone()[0] or 0
                    cursor.execute("SELECT COUNT(*) FROM Cycles")
                    kpi_cycles = cursor.fetchone()[0] or 0
                    self._stat_years.set_value(str(kpi_years))
                    self._stat_classes.set_value(str(kpi_classes))
                    self._stat_subjects.set_value(str(kpi_subjects))
                    self._stat_cycles.set_value(str(kpi_cycles))
                except Exception as e:
                    AppLogger.error("AcademicSettingsWindow", f"Erreur KPI stats: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Erreur de chargement", friendly_db_error(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AcademicSettingsWindow()
    window.show()
    sys.exit(app.exec())
