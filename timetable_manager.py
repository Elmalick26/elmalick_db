"""
timetable_manager.py — Phase 6.2
إدارة جدول الحصص الأسبوعي.

• عرض جدول الحصص في شبكة (7 أيام × فترات زمنية)
• إضافة/تعديل/حذف حصص
• فلترة حسب السنة والفصل
• طباعة/تصدير PDF
"""

from __future__ import annotations

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
from repositories.timetable_repo import TimetableRepository
from ui_styles import Colors, ThemeManager

# ──────────────────────────────────────────────────────────────
DAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
DAYS_AR = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
DAY_COLORS = ["#1a3a5c", "#1a4a3c", "#3c2a1a", "#3c1a2a", "#2a1a4a", "#1a3a3c"]

# خلفيات الحصص حسب المادة
SLOT_PALETTE = [
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
        self.slot_id = slot_data.get("id")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {color}; border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.15);
                margin: 2px;
            }}
            QFrame:hover {{ border: 1px solid #4fc3f7; }}
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

        lbl_subject = QLabel(subject)
        lbl_subject.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_subject.setStyleSheet("color: white;")
        lbl_subject.setWordWrap(True)

        lbl_info = QLabel(f"👤 {teacher}" if teacher else "")
        lbl_info.setStyleSheet("color: #ccc; font-size: 10px;")

        lbl_time = QLabel(f"⏱ {start}–{end}" if start else "")
        lbl_time.setStyleSheet("color: #aaa; font-size: 9px;")

        if room:
            lbl_room = QLabel(f"🚪 {room}")
            lbl_room.setStyleSheet("color: #aaa; font-size: 9px;")
        else:
            lbl_room = None

        layout.addWidget(lbl_subject)
        layout.addWidget(lbl_info)
        layout.addWidget(lbl_time)
        if lbl_room:
            layout.addWidget(lbl_room)
        layout.addStretch()

        # Buttons (edit/delete)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_edit = QToolButton()
        btn_edit.setText("✏️")
        btn_edit.setToolTip("Modifier")
        btn_edit.setStyleSheet("QToolButton { background: transparent; color: white; font-size: 12px; border: none; }")
        btn_edit.clicked.connect(lambda: on_edit(slot_data))

        btn_del = QToolButton()
        btn_del.setText("🗑️")
        btn_del.setToolTip("Supprimer")
        btn_del.setStyleSheet("QToolButton { background: transparent; color: #ef5350; font-size: 12px; border: none; }")
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
        self.setWindowTitle("Ajouter une Heure" if slot_data is None else "Modifier l'Heure")
        self.setMinimumWidth(420)
        self.setStyleSheet(
            """
            QDialog { background: #1e2433; color: #e0e0e0; }
            QLabel  { color: #ccc; }
            QComboBox, QTimeEdit, QLineEdit {
                background: #252b3b; color: white; border: 1px solid #444;
                border-radius: 4px; padding: 5px 8px;
            }
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
        self.on_add = on_add_slot
        self.on_edit = on_edit_slot
        self.on_delete = on_delete_slot

        self.setWidgetResizable(True)
        self._container = QWidget()
        self.setWidget(self._container)
        self._grid_layout = QVBoxLayout(self._container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: #161b2e;")
        self._subject_color_map: dict[int, str] = {}
        self._color_idx = 0

    def _get_subject_color(self, subject_id: int) -> str:
        if subject_id not in self._subject_color_map:
            self._subject_color_map[subject_id] = SLOT_PALETTE[self._color_idx % len(SLOT_PALETTE)]
            self._color_idx += 1
        return self._subject_color_map[subject_id]

    def render(self, slots: list[dict]):
        """إعادة رسم الشبكة الكاملة."""
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
                QFrame {{ background: #1a1f30; border-radius: 8px;
                          border-left: 4px solid {DAY_COLORS[day_idx]}; margin-bottom: 4px; }}
            """
            )
            day_layout = QVBoxLayout(day_frame)
            day_layout.setContentsMargins(8, 6, 8, 6)
            day_layout.setSpacing(4)

            # Day header
            hdr = QHBoxLayout()
            lbl_day = QLabel(f"  {day}  /  {DAYS_AR[day_idx]}")
            lbl_day.setFont(QFont("Cairo", 12, QFont.Weight.Bold))
            lbl_day.setStyleSheet("color: white;")
            hdr.addWidget(lbl_day)
            hdr.addStretch()

            btn_add = QPushButton("+ Ajouter")
            btn_add.setStyleSheet(
                "QPushButton { background:#2962ff; color:white; border-radius:4px; "
                "padding:4px 10px; font-size:11px; } QPushButton:hover { background:#1565c0; }"
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
                empty.setStyleSheet("color: #555; font-style: italic; padding: 8px;")
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
        self._setup_ui()
        self._load_filters()

    # ── UI ────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: #161b2e; color: #e0e0e0;")
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("📅 Emploi du Temps / جدول الحصص")
        title.setFont(QFont("Cairo", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        hdr.addWidget(title)
        hdr.addStretch()

        hdr.addWidget(QLabel("Classe:"))
        self.cmb_class = QComboBox()
        self.cmb_class.setMinimumWidth(160)
        self.cmb_class.setStyleSheet(
            "QComboBox { background:#252b3b; color:white; border:1px solid #444; "
            "border-radius:4px; padding:5px 8px; } QComboBox::drop-down { border: none; }"
        )
        self.cmb_class.currentIndexChanged.connect(self._on_class_changed)
        hdr.addWidget(self.cmb_class)

        btn_print = QPushButton("🖨️ Imprimer")
        btn_print.setStyleSheet(
            "QPushButton { background:#37474f; color:white; border-radius:6px; padding:6px 14px; }"
            "QPushButton:hover { background:#263238; }"
        )
        btn_print.clicked.connect(self._print_timetable)
        hdr.addWidget(btn_print)

        root.addLayout(hdr)

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

        except Exception as e:
            AppLogger.error("Timetable", f"_load_filters error: {e}")

    def _on_class_changed(self):
        self._class_id = self.cmb_class.currentData()
        if self._class_id:
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

        except Exception as e:
            AppLogger.error("Timetable", f"_load_grid error: {e}")
            QMessageBox.warning(self, "Erreur", f"Chargement du planning: {e}")

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

    def _save_slot(self, values: dict):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
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
        if not self._class_id:
            QMessageBox.information(self, "Info", "Sélectionnez une classe avant d'imprimer.")
            return
        try:
            from fpdf import FPDF
        except ImportError:
            QMessageBox.warning(self, "Erreur", "fpdf2 non installé.")
            return

        class_name = self.cmb_class.currentText()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = TimetableRepository(conn).list_slots_for_print(self._class_id)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return

        pdf = FPDF(orientation="L", format="A4")
        pdf.add_page()

        # Polices Unicode (Cairo) pour supporter Arabe + Latin/accents
        import os as _os

        _font_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Fonts", "Cairo", "static")
        pdf.add_font("Cairo", "", _os.path.join(_font_dir, "Cairo-Regular.ttf"))
        pdf.add_font("Cairo", "B", _os.path.join(_font_dir, "Cairo-Bold.ttf"))

        pdf.set_font("Cairo", "B", 14)
        pdf.cell(0, 10, f"Emploi du Temps \u2014 {class_name}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Cairo", "", 10)
        pdf.ln(4)

        col_w = [30, 22, 22, 60, 60, 30]
        headers = ["Jour", "Début", "Fin", "Matière", "Enseignant", "Salle"]
        pdf.set_fill_color(41, 98, 255)
        pdf.set_text_color(255, 255, 255)
        for w, h in zip(col_w, headers):
            pdf.cell(w, 8, h, border=1, fill=True)
        pdf.ln()

        pdf.set_text_color(0, 0, 0)
        fill = False
        for row in rows:
            pdf.set_fill_color(230, 240, 255) if fill else pdf.set_fill_color(255, 255, 255)
            for w, val in zip(col_w, row):
                pdf.cell(w, 7, str(val or ""), border=1, fill=True)
            pdf.ln()
            fill = not fill

        import tempfile

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(tmp.name)
        tmp.close()
        _os.startfile(tmp.name)
        AppLogger.info("Timetable", f"Emploi du temps imprimé: {tmp.name}")

    # Called by main_dashbord refresh system
    def refresh_data(self):
        self._load_filters()
        if self._class_id:
            self._load_grid()
