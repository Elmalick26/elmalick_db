"""
timetable_manager.py — Phase 6.2
إدارة جدول الحصص الأسبوعي.

• عرض جدول الحصص في شبكة (7 أيام × فترات زمنية)
• إضافة/تعديل/حذف حصص
• فلترة حسب السنة والفصل
• طباعة/تصدير PDF
"""

from __future__ import annotations

import os
from datetime import datetime

from fpdf import FPDF
from PyQt6.QtCore import QSize, Qt, QTime
from PyQt6.QtGui import QAction, QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.finance_repo import FinanceRepository
from repositories.timetable_repo import TimetableRepository
from ui_styles import Colors, ModuleHeaderWidget, ThemeManager

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_display

    _ARABIC_SUPPORT = True
except ModuleNotFoundError:
    _ARABIC_SUPPORT = False

# ──────────────────────────────────────────────────────────────
DAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
DAYS_AR = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
DAY_COLORS = ["#1a3a5c", "#1a4a3c", "#3c2a1a", "#3c1a2a", "#2a1a4a", "#1a3a3c"]
DAYS_FR_AR = dict(zip(DAYS_FR, DAYS_AR))

TIMETABLE_PDF_MODE = get_report_output_mode("timetable_mode", "save")


def _ar_text(text: str) -> str:
    """Reshape + reorder Arabic text for RTL display in fpdf2."""
    if not text or not _ARABIC_SUPPORT:
        return text or ""
    try:
        return _bidi_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


# خلفيات الحصص حسب المادة
SLOT_PALETTE_LIGHT = [
    "#dbeafe",
    "#dcfce7",
    "#fef3c7",
    "#fee2e2",
    "#ede9fe",
    "#ccfbf1",
    "#ffedd5",
    "#e0f2fe",
    "#f3e8ff",
    "#fef9c3",
    "#cffafe",
    "#ffe4e6",
]

SLOT_PALETTE_DARK = [
    "#1e3a5f",
    "#1e5f3a",
    "#5f3a1e",
    "#5f1e3a",
    "#3a1e5f",
    "#1e5f5f",
    "#4a2a00",
    "#004a2a",
    "#2a004a",
    "#4a4a00",
    "#004a4a",
    "#4a0000",
]


# ──────────────────────────────────────────────────────────────
# Slot Cell Widget
# ──────────────────────────────────────────────────────────────
class SlotCell(QFrame):
    """خلية تعرض معلومات حصة واحدة في الشبكة."""

    def __init__(self, slot_data: dict, color: str, on_edit, on_delete, parent=None):
        super().__init__(parent)
        c = ThemeManager.get_colors()
        text_color = c.TEXT_PRIMARY if not ThemeManager.is_dark_mode() else c.HEADER_TEXT
        muted_color = c.TEXT_SECONDARY if not ThemeManager.is_dark_mode() else "#ccc"
        self.slot_id = slot_data.get("id")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {color}; border-radius: 6px;
                border: 1px solid {c.BORDER};
                margin: 2px;
            }}
            QFrame:hover {{ border: 1px solid {c.PRIMARY}; }}
        """
        )
        self.setMinimumHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        subject = slot_data.get("subject_name_fr", "—")
        teacher = slot_data.get("teacher_name", "")
        room = slot_data.get("room", "")
        start = slot_data.get("start_time", "")
        end = slot_data.get("end_time", "")
        class_name = slot_data.get("class_name_fr", "")  # only in teacher-view mode

        lbl_subject = QLabel(subject)
        lbl_subject.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_subject.setStyleSheet(f"color: {text_color};")
        lbl_subject.setWordWrap(True)

        lbl_info = QLabel(f"👤 {teacher}" if teacher else "")
        lbl_info.setStyleSheet(f"color: {muted_color}; font-size: 10px;")

        lbl_time = QLabel(f"⏱ {start}–{end}" if start else "")
        lbl_time.setStyleSheet(f"color: {muted_color}; font-size: 9px;")

        if class_name:
            lbl_extra = QLabel(f"🏫 {class_name}")
            lbl_extra.setStyleSheet(
                f"color: {c.SUCCESS if ThemeManager.is_dark_mode() else c.PRIMARY}; font-size: 9px;"
            )
        elif room:
            lbl_extra = QLabel(f"🚪 {room}")
            lbl_extra.setStyleSheet(f"color: {muted_color}; font-size: 9px;")
        else:
            lbl_extra = None

        layout.addWidget(lbl_subject)
        layout.addWidget(lbl_info)
        layout.addWidget(lbl_time)
        if lbl_extra:
            layout.addWidget(lbl_extra)
        layout.addStretch()

        # Buttons (edit/delete)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_edit = QToolButton()
        btn_edit.setText("✏️")
        btn_edit.setToolTip("Modifier")
        btn_edit.setStyleSheet(
            f"QToolButton {{ background: transparent; color: {text_color}; font-size: 12px; border: none; }}"
        )
        btn_edit.clicked.connect(lambda: on_edit(slot_data))

        btn_del = QToolButton()
        btn_del.setText("🗑️")
        btn_del.setToolTip("Supprimer")
        btn_del.setStyleSheet(
            f"QToolButton {{ background: transparent; color: {c.DANGER}; font-size: 12px; border: none; }}"
        )
        btn_del.clicked.connect(lambda: on_delete(slot_data))

        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)


# ──────────────────────────────────────────────────────────────
# Add/Edit Dialog
# ──────────────────────────────────────────────────────────────
class SlotDialog(QDialog):
    def __init__(self, classes: list, subjects: list, staff: list, slot_data: dict | None = None, parent=None):
        super().__init__(parent)
        c = ThemeManager.get_colors()
        self.setWindowTitle("Ajouter une Heure" if slot_data is None else "Modifier l'Heure")
        self.setMinimumWidth(420)
        self.setStyleSheet(
            f"""
            QDialog {{ background: {c.BG_MAIN}; color: {c.TEXT_PRIMARY}; }}
            QLabel  {{ color: {c.TEXT_PRIMARY}; }}
            QComboBox, QTimeEdit, QLineEdit {{
                background: {c.INPUT_BG}; color: {c.TEXT_PRIMARY}; border: 1px solid {c.BORDER};
                border-radius: 4px; padding: 5px 8px;
            }}
        """
        )

        form = QFormLayout(self)
        form.setSpacing(10)
        form.setContentsMargins(16, 16, 16, 12)

        # Day
        self.cmb_day = QComboBox()
        for d in DAYS_FR:
            self.cmb_day.addItem(d, d)
        form.addRow("Jour:", self.cmb_day)

        # Start / End times
        self.time_start = QTimeEdit()
        self.time_start.setDisplayFormat("HH:mm")
        self.time_start.setTime(QTime(8, 0))
        self.time_end = QTimeEdit()
        self.time_end.setDisplayFormat("HH:mm")
        self.time_end.setTime(QTime(9, 0))
        form.addRow("Heure début:", self.time_start)
        form.addRow("Heure fin:", self.time_end)

        # Subject
        self.cmb_subject = QComboBox()
        for sid, name in subjects:
            self.cmb_subject.addItem(name, sid)
        form.addRow("Matière:", self.cmb_subject)

        # Teacher
        self.cmb_teacher = QComboBox()
        self.cmb_teacher.addItem("— Aucun —", None)
        for tid, name in staff:
            self.cmb_teacher.addItem(name, tid)
        form.addRow("Enseignant:", self.cmb_teacher)

        # Room
        self.txt_room = QLineEdit()
        self.txt_room.setPlaceholderText("ex: Salle 01")
        form.addRow("Salle:", self.txt_room)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        # Pre-fill if editing
        if slot_data:
            idx = self.cmb_day.findData(slot_data.get("day_of_week"))
            if idx >= 0:
                self.cmb_day.setCurrentIndex(idx)
            if slot_data.get("start_time"):
                self.time_start.setTime(QTime.fromString(slot_data["start_time"], "HH:mm"))
            if slot_data.get("end_time"):
                self.time_end.setTime(QTime.fromString(slot_data["end_time"], "HH:mm"))
            idx = self.cmb_subject.findData(slot_data.get("subject_id"))
            if idx >= 0:
                self.cmb_subject.setCurrentIndex(idx)
            idx = self.cmb_teacher.findData(slot_data.get("teacher_id"))
            if idx >= 0:
                self.cmb_teacher.setCurrentIndex(idx)
            self.txt_room.setText(slot_data.get("room", ""))

    def _validate_and_accept(self):
        if self.time_end.time() <= self.time_start.time():
            QMessageBox.warning(self, "Erreur", "L'heure de fin doit être après l'heure de début.")
            return
        self.accept()

    def get_values(self) -> dict:
        return {
            "day_of_week": self.cmb_day.currentData(),
            "start_time": self.time_start.time().toString("HH:mm"),
            "end_time": self.time_end.time().toString("HH:mm"),
            "subject_id": self.cmb_subject.currentData(),
            "teacher_id": self.cmb_teacher.currentData(),
            "room": self.txt_room.text().strip(),
        }


# ──────────────────────────────────────────────────────────────
# Grid Widget
# ──────────────────────────────────────────────────────────────
class TimetableGrid(QScrollArea):
    """شبكة جدول الحصص الأسبوعية."""

    def __init__(self, on_add_slot, on_edit_slot, on_delete_slot, parent=None):
        super().__init__(parent)
        c = ThemeManager.get_colors()
        self.on_add = on_add_slot
        self.on_edit = on_edit_slot
        self.on_delete = on_delete_slot

        self.setWidgetResizable(True)
        self._container = QWidget()
        self.setWidget(self._container)
        self._grid_layout = QVBoxLayout(self._container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(f"background: {c.BG_MAIN};")
        self._subject_color_map: dict[int, str] = {}
        self._color_idx = 0

    def _get_subject_color(self, subject_id: int) -> str:
        palette = SLOT_PALETTE_DARK if ThemeManager.is_dark_mode() else SLOT_PALETTE_LIGHT
        if subject_id not in self._subject_color_map:
            self._subject_color_map[subject_id] = palette[self._color_idx % len(palette)]
            self._color_idx += 1
        return self._subject_color_map[subject_id]

    def render(self, slots: list[dict]):
        """إعادة رسم الشبكة الكاملة."""
        c = ThemeManager.get_colors()
        # Clear
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Group slots by day
        day_slots: dict[str, list] = {d: [] for d in DAYS_FR}
        for s in slots:
            day = s.get("day_of_week")
            if day in day_slots:
                day_slots[day].append(s)

        for day_idx, day in enumerate(DAYS_FR):
            day_frame = QFrame()
            day_frame.setStyleSheet(
                f"""
                QFrame {{ background: {c.BG_CARD}; border-radius: 8px;
                          border: 1px solid {c.BORDER}; border-left: 4px solid {DAY_COLORS[day_idx]}; margin-bottom: 4px; }}
            """
            )
            day_layout = QVBoxLayout(day_frame)
            day_layout.setContentsMargins(8, 6, 8, 6)
            day_layout.setSpacing(4)

            # Day header
            hdr = QHBoxLayout()
            lbl_day = QLabel(f"  {day}  /  {DAYS_AR[day_idx]}")
            lbl_day.setFont(QFont("Cairo", 12, QFont.Weight.Bold))
            lbl_day.setStyleSheet(f"color: {c.TEXT_PRIMARY};")
            hdr.addWidget(lbl_day)
            hdr.addStretch()

            btn_add = QPushButton("+ Ajouter")
            btn_add.setStyleSheet(
                f"QPushButton {{ background:{c.PRIMARY}; color:white; border-radius:4px; "
                f"padding:4px 10px; font-size:11px; }} QPushButton:hover {{ background:{c.PRIMARY_HOVER}; }}"
            )
            btn_add.clicked.connect(lambda checked, d=day: self.on_add(d))
            hdr.addWidget(btn_add)
            day_layout.addLayout(hdr)

            # Slots row
            slots_of_day = sorted(day_slots[day], key=lambda x: x.get("start_time", ""))
            if slots_of_day:
                row = QHBoxLayout()
                row.setSpacing(4)
                for s in slots_of_day:
                    color = self._get_subject_color(s.get("subject_id", 0))
                    cell = SlotCell(s, color, self.on_edit, self.on_delete)
                    row.addWidget(cell)
                row.addStretch()
                day_layout.addLayout(row)
            else:
                empty = QLabel("Aucune heure programmée — cliquez « + Ajouter »")
                empty.setStyleSheet(f"color: {c.TEXT_SECONDARY}; font-style: italic; padding: 8px;")
                day_layout.addWidget(empty)

            self._grid_layout.addWidget(day_frame)

        self._grid_layout.addStretch()


# ──────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────
class TimetableWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion du Emploi du Temps / جدول الحصص")
        self._class_id = None
        self._classes: list[tuple] = []
        self._subjects: list[tuple] = []
        self._staff: list[tuple] = []
        ThemeManager.apply_theme(self)
        self._setup_ui()
        self._load_filters()

    # ── UI ────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(10)

        # Header
        header = ModuleHeaderWidget("📅", "EMPLOI DU TEMPS", "جدول الحصص الأسبوعي")
        self._stat_classes = header.add_stat("🏫", "Classes", "0", "#3B82F6")
        self._stat_teachers = header.add_stat("👤", "Enseignants", "0", "#22C55E")
        self._stat_slots = header.add_stat("📌", "Créneaux", "0", "#8B5CF6")
        root.addWidget(header)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        lbl_class = QLabel("Classe:")
        lbl_class.setStyleSheet("font-weight: bold;")
        self.cmb_class = QComboBox()
        self.cmb_class.setMinimumWidth(160)
        self.cmb_class.currentIndexChanged.connect(self._on_class_changed)
        filter_row.addWidget(lbl_class)
        filter_row.addWidget(self.cmb_class)

        lbl_teacher = QLabel("Professeur:")
        lbl_teacher.setStyleSheet("font-weight: bold;")
        self.cmb_teacher = QComboBox()
        self.cmb_teacher.setMinimumWidth(160)
        self.cmb_teacher.currentIndexChanged.connect(self._on_teacher_changed)
        filter_row.addWidget(lbl_teacher)
        filter_row.addWidget(self.cmb_teacher)

        filter_row.addStretch()
        btn_print = QPushButton("🖨️ Imprimer")
        btn_print.clicked.connect(self._print_timetable)
        filter_row.addWidget(btn_print)
        root.addLayout(filter_row)

        # Timetable grid
        self.grid = TimetableGrid(
            on_add_slot=self._add_slot_for_day,
            on_edit_slot=self._edit_slot,
            on_delete_slot=self._confirm_delete_slot,
        )
        root.addWidget(self.grid, stretch=1)

    # ── Filters ───────────────────────────────────────────────
    def _load_filters(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = TimetableRepository(conn)

                # Classes
                self._classes = repo.list_classes()
                self.cmb_class.blockSignals(True)
                self.cmb_class.clear()
                self.cmb_class.addItem("— Sélectionner une classe —", None)
                for cid, name in self._classes:
                    self.cmb_class.addItem(name, cid)
                self.cmb_class.blockSignals(False)
                if self._classes:
                    self.cmb_class.setCurrentIndex(1)

                # Subjects
                self._subjects = repo.list_subjects()

                # Staff (teachers)
                self._staff = repo.list_active_staff()
                self.cmb_teacher.blockSignals(True)
                self.cmb_teacher.clear()
                self.cmb_teacher.addItem("— Tous les profs —", None)
                for tid, name in self._staff:
                    self.cmb_teacher.addItem(name, tid)
                self.cmb_teacher.blockSignals(False)

            # Update stat chips
            self._stat_classes.set_value(str(len(self._classes)))
            self._stat_teachers.set_value(str(len(self._staff)))

        except Exception as e:
            AppLogger.error("Timetable", f"_load_filters error: {e}")

    def _on_class_changed(self):
        self._class_id = self.cmb_class.currentData()
        if self._class_id:
            # Reset teacher filter when switching to class view
            self.cmb_teacher.blockSignals(True)
            self.cmb_teacher.setCurrentIndex(0)
            self.cmb_teacher.blockSignals(False)
            self._load_grid()

    def _on_teacher_changed(self):
        teacher_id = self.cmb_teacher.currentData()
        if teacher_id:
            # Reset class filter when switching to teacher view
            self._class_id = None
            self.cmb_class.blockSignals(True)
            self.cmb_class.setCurrentIndex(0)
            self.cmb_class.blockSignals(False)
            self._load_grid_teacher(teacher_id)
        elif self._class_id:
            self._load_grid()

    # ── Grid loading ──────────────────────────────────────────
    def _load_grid(self):
        if not self._class_id:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = TimetableRepository(conn).list_slots_for_class(self._class_id)

            slots = [
                {
                    "id": r[0],
                    "day_of_week": r[1],
                    "start_time": r[2],
                    "end_time": r[3],
                    "subject_id": r[4],
                    "teacher_id": r[5],
                    "room": r[6] or "",
                    "subject_name_fr": r[7],
                    "teacher_name": r[8] or "",
                }
                for r in rows
            ]
            self.grid.render(slots)
            self._stat_slots.set_value(str(len(slots)))

        except Exception as e:
            AppLogger.error("Timetable", f"_load_grid error: {e}")
            QMessageBox.warning(self, "Erreur", f"Chargement du planning: {e}")

    def _load_grid_teacher(self, teacher_id: int):
        """Load and render the weekly schedule for a specific teacher (all classes)."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = TimetableRepository(conn).list_slots_for_teacher(teacher_id)

            slots = [
                {
                    "id": r[0],
                    "day_of_week": r[1],
                    "start_time": r[2],
                    "end_time": r[3],
                    "subject_id": r[4],
                    "teacher_id": r[5],
                    "room": r[6] or "",
                    "subject_name_fr": r[7],
                    "teacher_name": r[8] or "",
                    "class_name_fr": r[9] or "",  # shown instead of room in teacher view
                }
                for r in rows
            ]
            self.grid.render(slots)
            self._stat_slots.set_value(str(len(slots)))

        except Exception as e:
            AppLogger.error("Timetable", f"_load_grid_teacher error: {e}")
            QMessageBox.warning(self, "Erreur", f"Chargement du planning professeur: {e}")

    # ── CRUD operations ───────────────────────────────────────
    def _add_slot_for_day(self, day: str):
        if not self._class_id:
            QMessageBox.information(self, "Info", "Veuillez d'abord sélectionner une classe.")
            return
        dlg = SlotDialog(self._classes, self._subjects, self._staff, parent=self)
        # Pre-select the day
        idx = dlg.cmb_day.findData(day)
        if idx >= 0:
            dlg.cmb_day.setCurrentIndex(idx)
        if dlg.exec():
            values = dlg.get_values()
            self._save_slot(values)

    def _edit_slot(self, slot_data: dict):
        dlg = SlotDialog(self._classes, self._subjects, self._staff, slot_data=slot_data, parent=self)
        if dlg.exec():
            values = dlg.get_values()
            self._update_slot(slot_data["id"], values)

    def _confirm_delete_slot(self, slot_data: dict):
        subject = slot_data.get("subject_name_fr", "cette heure")
        day = slot_data.get("day_of_week", "")
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Supprimer la séance de « {subject} » ({day}) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_slot(slot_data["id"])

    # ── Conflict detection ────────────────────────────────────
    def _check_conflict(
        self, conn, class_id: int, values: dict, exclude_slot_id: int | None = None
    ) -> tuple[bool, str]:
        """Return (is_conflict, message).

        Checks both teacher overlap and class overlap for the given slot values.
        Pass *exclude_slot_id* when editing so the existing row is not compared
        against itself.
        """
        try:
            t_start = datetime.strptime(values["start_time"], "%H:%M").time()
            t_end = datetime.strptime(values["end_time"], "%H:%M").time()
        except ValueError:
            return True, "Format d'heure invalide (HH:MM attendu, ex: 08:00)."
        if t_start >= t_end:
            return True, "L'heure de fin doit être après l'heure de début."

        repo = TimetableRepository(conn)
        day = values["day_of_week"]
        teacher_id = values.get("teacher_id")

        # 1. Teacher conflict
        if teacher_id:
            for cname, ex_start, ex_end in repo.get_teacher_slots_for_day(teacher_id, day, exclude_slot_id):
                s = datetime.strptime(ex_start, "%H:%M").time()
                e = datetime.strptime(ex_end, "%H:%M").time()
                if t_start < e and t_end > s:
                    # Find teacher name for the message
                    teacher_name = next((n for tid, n in self._staff if tid == teacher_id), "ce professeur")
                    return (
                        True,
                        f"⚠️ Conflit : {teacher_name} est déjà assigné(e) à {cname} "
                        f"le {day} de {ex_start} à {ex_end}.",
                    )

        # 2. Class conflict
        for prof, subj, ex_start, ex_end in repo.get_class_slots_for_day(class_id, day, exclude_slot_id):
            s = datetime.strptime(ex_start, "%H:%M").time()
            e = datetime.strptime(ex_end, "%H:%M").time()
            if t_start < e and t_end > s:
                class_name = self.cmb_class.currentText()
                return (
                    True,
                    f"⚠️ Conflit : la classe {class_name} a déjà cours de {subj} "
                    f"avec {prof} le {day} de {ex_start} à {ex_end}.",
                )

        return False, ""

    def _save_slot(self, values: dict):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                is_conflict, msg = self._check_conflict(conn, self._class_id, values)
                if is_conflict:
                    QMessageBox.critical(self, "Conflit d'horaire / تداخل في الجدول", msg)
                    return
                TimetableRepository(conn).insert_slot(
                    self._class_id,
                    values["day_of_week"],
                    values["start_time"],
                    values["end_time"],
                    values["subject_id"],
                    values["teacher_id"],
                    values["room"],
                )
                conn.commit()
            AppLogger.info("Timetable", f"Heure ajoutée pour class_id={self._class_id}")
            self._load_grid()
        except Exception as e:
            AppLogger.error("Timetable", f"_save_slot error: {e}")
            QMessageBox.critical(self, "Erreur", str(e))

    def _update_slot(self, slot_id: int, values: dict):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                is_conflict, msg = self._check_conflict(conn, self._class_id, values, exclude_slot_id=slot_id)
                if is_conflict:
                    QMessageBox.critical(self, "Conflit d'horaire / تداخل في الجدول", msg)
                    return
                TimetableRepository(conn).update_slot(
                    slot_id,
                    values["day_of_week"],
                    values["start_time"],
                    values["end_time"],
                    values["subject_id"],
                    values["teacher_id"],
                    values["room"],
                )
                conn.commit()
            AppLogger.info("Timetable", f"Heure modifiée id={slot_id}")
            self._load_grid()
        except Exception as e:
            AppLogger.error("Timetable", f"_update_slot error: {e}")
            QMessageBox.critical(self, "Erreur", str(e))

    def _delete_slot(self, slot_id: int):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                TimetableRepository(conn).delete_slot(slot_id)
                conn.commit()
            AppLogger.info("Timetable", f"Heure supprimée id={slot_id}")
            self._load_grid()
        except Exception as e:
            AppLogger.error("Timetable", f"_delete_slot error: {e}")
            QMessageBox.critical(self, "Erreur", str(e))

    # ── Print ─────────────────────────────────────────────────
    def _print_timetable(self):
        """Generate an official PDF timetable — Portrait A4 with Arabic support."""
        class_id = self._class_id
        teacher_id = self.cmb_teacher.currentData()

        if not class_id and not teacher_id:
            QMessageBox.information(self, "Info", "Sélectionnez une classe ou un professeur avant d'imprimer.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = TimetableRepository(conn)
                school_info = FinanceRepository(conn).get_school_info()

                if class_id:
                    entity_name = self.cmb_class.currentText()
                    title = f"EMPLOI DU TEMPS — {entity_name.upper()}"
                    col5_header = "Enseignant"
                    rows = repo.list_slots_for_print(class_id)
                else:
                    entity_name = self.cmb_teacher.currentText()
                    title = f"EMPLOI DU TEMPS — {entity_name.upper()}"
                    col5_header = "Classe"
                    rows = repo.list_slots_for_teacher_print(teacher_id)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return

        if not rows:
            QMessageBox.information(self, "Vide", "Aucune séance à imprimer pour cette sélection.")
            return

        # ── Build PDF (Portrait A4) ────────────────────────────
        pdf = FPDF(orientation="P", format="A4")
        pdf.set_margins(10, 10, 10)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        font = self._register_arabic_font(pdf)

        # Official header (school info + title — uses Helvetica + latin sanitize internally)
        apply_grades_sheet_header(pdf, school_info, title)

        # Date subtitle
        pdf.set_font(font, "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(
            0,
            5,
            f"Imprimé le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        pdf.ln(2)

        self._render_timetable_rows(pdf, font, col5_header, rows)

        # Footer note
        pdf.ln(3)
        pdf.set_font(font, "", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(0, 5, "El Malick Gest — Gestion Scolaire", align="C")

        safe_name = entity_name.replace(" ", "_").replace("/", "-")
        output_pdf(
            pdf,
            self,
            f"EmploiDuTemps_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=TIMETABLE_PDF_MODE,
            dialog_title="Sauvegarder l'Emploi du Temps",
            success_save_message="Emploi du temps généré avec succès.",
            success_print_message="Emploi du temps envoyé à l'imprimante.",
        )
        AppLogger.info("Timetable", f"PDF emploi du temps généré: {entity_name}")

    @staticmethod
    def _register_arabic_font(pdf: FPDF) -> str:
        """Register Cairo/Amiri TTF font and return the font name to use."""
        _base = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            (
                os.path.join(_base, "Fonts", "Cairo", "static", "Cairo-Regular.ttf"),
                os.path.join(_base, "Fonts", "Cairo", "static", "Cairo-Bold.ttf"),
            ),
            (
                os.path.join(_base, "Fonts", "Amiri", "Amiri-Regular.ttf"),
                os.path.join(_base, "Fonts", "Amiri", "Amiri-Bold.ttf"),
            ),
        ]
        for reg, bold in candidates:
            if os.path.exists(reg):
                try:
                    pdf.add_font("ArabicFont", "", reg)
                    pdf.add_font("ArabicFont", "B", bold if os.path.exists(bold) else reg)
                    return "ArabicFont"
                except Exception:
                    pass
                break
        return "Helvetica"

    @staticmethod
    def _render_timetable_rows(pdf: FPDF, font: str, col5_header: str, rows: list) -> None:
        """Render the timetable table (header + body rows) into *pdf*."""
        # col widths: 28+18+18+52+50+24 = 190mm (Portrait A4 usable)
        col_w = [28, 18, 18, 52, 50, 24]
        headers = ["Jour", "Début", "Fin", "Matière", col5_header, "Salle"]

        apply_table_header_style(pdf, font, 9)
        for w, h_text in zip(col_w, headers):
            pdf.cell(w, 8, h_text, border=1, fill=True)
        pdf.ln()

        apply_table_body_style(pdf, font, 9)
        current_day = ""
        for row_idx, row in enumerate(rows):
            day, start, end, subject, col5, room = (str(v or "") for v in row)
            if day != current_day:
                current_day = day
                day_ar = _ar_text(DAYS_FR_AR.get(day, ""))
                day_display = f"  {day}    {day_ar}" if day_ar else f"  {day}"
                pdf.set_fill_color(30, 41, 59)
                pdf.set_text_color(248, 250, 252)
                pdf.set_font(font, "B", 9)
                pdf.cell(sum(col_w), 7, day_display, border=1, new_x="LMARGIN", new_y="NEXT", fill=True)
                apply_table_body_style(pdf, font, 9)
            set_zebra_row_fill(pdf, row_idx)
            pdf.cell(col_w[0], 7, day, border=1, fill=True)
            pdf.cell(col_w[1], 7, start, border=1, fill=True)
            pdf.cell(col_w[2], 7, end, border=1, fill=True)
            pdf.cell(col_w[3], 7, _ar_text(subject), border=1, fill=True)
            pdf.cell(col_w[4], 7, _ar_text(col5), border=1, fill=True)
            pdf.cell(col_w[5], 7, room, border=1, new_x="LMARGIN", new_y="NEXT", fill=True)

    # Called by main_dashbord refresh system
    def refresh_data(self):
        self._load_filters()
        if self._class_id:
            self._load_grid()
