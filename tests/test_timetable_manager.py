"""
tests/test_timetable_manager.py
اختبارات وحدة timetable_manager.py (Phase 6.2).

تغطي:
  - SlotDialog: get_values, _validate_and_accept (وقت خاطئ)
  - TimetableGrid: render (empty + slots), _get_subject_color
  - TimetableWindow: _load_grid, _save_slot, _update_slot, _delete_slot,
                     _add_slot_for_day, _confirm_delete_slot, _edit_slot
"""

from __future__ import annotations

import sys
import os
import types
from unittest.mock import MagicMock, patch, call

import pytest


# ── Stubs PyQt6 ──────────────────────────────────────────────
def _make_qt_stubs():
    for mod_name in ["PyQt6", "PyQt6.QtWidgets", "PyQt6.QtCore", "PyQt6.QtGui"]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    widgets = sys.modules["PyQt6.QtWidgets"]
    for cls_name in [
        "QMainWindow",
        "QWidget",
        "QVBoxLayout",
        "QHBoxLayout",
        "QLabel",
        "QComboBox",
        "QPushButton",
        "QTableWidget",
        "QTableWidgetItem",
        "QHeaderView",
        "QDialog",
        "QFormLayout",
        "QTimeEdit",
        "QLineEdit",
        "QDialogButtonBox",
        "QMessageBox",
        "QFrame",
        "QSizePolicy",
        "QToolButton",
        "QMenu",
        "QScrollArea",
        "QApplication",
    ]:
        setattr(
            widgets,
            cls_name,
            type(
                cls_name,
                (object,),
                {
                    "__init__": lambda self, *a, **kw: None,
                    "setStyleSheet": lambda self, *a: None,
                    "addWidget": lambda self, *a: None,
                    "addLayout": lambda self, *a: None,
                    "addStretch": lambda self, *a: None,
                    "setContentsMargins": lambda self, *a: None,
                    "setSpacing": lambda self, *a: None,
                    "blockSignals": lambda self, *a: None,
                    "clear": lambda self, *a: None,
                    "addItem": lambda self, *a: None,
                    "currentData": lambda self: None,
                    "currentIndex": lambda self: 0,
                    "setCurrentIndex": lambda self, *a: None,
                    "setMinimumWidth": lambda self, *a: None,
                    "setMinimumHeight": lambda self, *a: None,
                    "setSizePolicy": lambda self, *a: None,
                    "setFrameShape": lambda self, *a: None,
                    "setWordWrap": lambda self, *a: None,
                    "setFont": lambda self, *a: None,
                    "setText": lambda self, t: None,
                    "setToolTip": lambda self, *a: None,
                    "setCheckable": lambda self, *a: None,
                    "setCursor": lambda self, *a: None,
                    "setWidgetResizable": lambda self, *a: None,
                    "setWidget": lambda self, *a: None,
                    "clicked": MagicMock(),
                    "connect": lambda self, *a: None,
                    "currentIndexChanged": MagicMock(),
                    "exec": lambda self: 1,  # QDialog.exec → accepted
                    "accept": lambda self: None,
                    "reject": lambda self: None,
                    "findData": lambda self, v: 0,
                    "show": lambda self: None,
                },
            ),
        )

    # pytest-qt requires QApplication.instance() as a static/class method
    widgets.QApplication.instance = staticmethod(lambda: None)
    widgets.QApplication.setQuitOnLastWindowClosed = staticmethod(lambda *a: None)
    # QFrame.Shape used in timetable_manager.py
    widgets.QFrame.Shape = MagicMock()
    widgets.QFrame.Shape.StyledPanel = 1

    core = sys.modules["PyQt6.QtCore"]
    core.Qt = MagicMock()
    core.QSize = MagicMock()

    # QTime mock
    class FakeQTime:
        def __init__(self, h=0, m=0):
            self._h = h
            self._m = m

        @classmethod
        def fromString(cls, s, fmt):
            parts = s.split(":")
            return cls(int(parts[0]), int(parts[1]))

        def toString(self, fmt):
            return f"{self._h:02d}:{self._m:02d}"

        def __le__(self, other):
            return (self._h, self._m) <= (other._h, other._m)

    core.QTime = FakeQTime

    gui = sys.modules["PyQt6.QtGui"]
    gui.QFont = MagicMock()
    gui.QColor = MagicMock()
    gui.QBrush = MagicMock()
    gui.QAction = MagicMock()


_make_qt_stubs()

# ── Stubs internes ───────────────────────────────────────────
# Save any real modules already loaded so we can restore them afterwards.
_saved_internal = {
    mod: sys.modules[mod]
    for mod in ("database_setup", "app_logger", "ui_styles")
    if mod in sys.modules
}

for mod_name, attrs in [
    ("database_setup", {"DatabaseManager": MagicMock()}),
    ("app_logger", {"AppLogger": MagicMock()}),
    ("ui_styles", {"ThemeManager": MagicMock(), "Colors": MagicMock()}),
]:
    m = types.ModuleType(mod_name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[mod_name] = m

# ── Import module ────────────────────────────────────────────
from timetable_manager import (
    TimetableGrid,
    TimetableWindow,
    SlotDialog,
    DAYS_FR,
    SLOT_PALETTE,
)

# Restore original modules (or remove stubs if nothing was saved).
for _stub_mod in ("database_setup", "app_logger", "ui_styles"):
    if _stub_mod in _saved_internal:
        sys.modules[_stub_mod] = _saved_internal[_stub_mod]
    else:
        sys.modules.pop(_stub_mod, None)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _make_conn(rows=None):
    """Mock connection + cursor."""
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = rows[0] if rows else None
    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = lambda self: self
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cur


def _make_db_ctx(rows=None):
    """Patch DatabaseManager().get_connection()."""
    conn, cur = _make_conn(rows)
    db = MagicMock()
    db.get_connection.return_value = conn
    return db, conn, cur


# ═══════════════════════════════════════════════════════════════
# TimetableGrid
# ═══════════════════════════════════════════════════════════════
class TestTimetableGrid:
    def _grid(self):
        g = TimetableGrid.__new__(TimetableGrid)
        g.on_add = MagicMock()
        g.on_edit = MagicMock()
        g.on_delete = MagicMock()
        g._subject_color_map = {}
        g._color_idx = 0
        # Layout stub
        layout = MagicMock()
        layout.count.return_value = 0
        g._grid_layout = layout
        g._container = MagicMock()
        return g

    def test_get_subject_color_consistent(self):
        g = self._grid()
        color1 = g._get_subject_color(10)
        color2 = g._get_subject_color(10)
        assert color1 == color2

    def test_different_subjects_get_different_colors(self):
        g = self._grid()
        c1 = g._get_subject_color(1)
        c2 = g._get_subject_color(2)
        assert c1 != c2

    def test_colors_cycle_through_palette(self):
        g = self._grid()
        colors = [g._get_subject_color(i) for i in range(len(SLOT_PALETTE))]
        assert set(colors) == set(SLOT_PALETTE)

    def test_render_empty_slots(self):
        """render([]) ne doit pas lever d'exception."""
        g = self._grid()
        # render nécessite des widgets QFrame, on le teste via mock
        with (
            patch("timetable_manager.QFrame") as MockFrame,
            patch("timetable_manager.QVBoxLayout") as MockVLayout,
            patch("timetable_manager.QHBoxLayout") as MockHLayout,
            patch("timetable_manager.QLabel") as MockLabel,
            patch("timetable_manager.QPushButton") as MockBtn,
        ):
            MockFrame.return_value = MagicMock()
            MockVLayout.return_value = MagicMock()
            MockHLayout.return_value = MagicMock()
            g._grid_layout = MagicMock()
            g._grid_layout.count.return_value = 0
            g.render([])
            # 6 jours doivent être ajoutés
            assert g._grid_layout.addWidget.call_count == len(DAYS_FR)

    def test_render_assigns_colors_to_subjects(self):
        g = self._grid()
        with (
            patch("timetable_manager.QFrame") as MockFrame,
            patch("timetable_manager.QVBoxLayout") as MockVLayout,
            patch("timetable_manager.QHBoxLayout") as MockHLayout,
            patch("timetable_manager.QLabel") as MockLabel,
            patch("timetable_manager.QPushButton") as MockBtn,
            patch("timetable_manager.SlotCell") as MockCell,
        ):
            MockFrame.return_value = MagicMock()
            MockVLayout.return_value = MagicMock()
            MockHLayout.return_value = MagicMock()
            g._grid_layout = MagicMock()
            g._grid_layout.count.return_value = 0

            slots = [
                {
                    "id": 1,
                    "day_of_week": "Lundi",
                    "start_time": "08:00",
                    "end_time": "09:00",
                    "subject_id": 5,
                    "teacher_id": 1,
                    "room": "S01",
                    "subject_name_fr": "Maths",
                    "teacher_name": "M. Diallo",
                },
            ]
            g.render(slots)
            MockCell.assert_called_once()
            # Premier arg = slot_data
            assert MockCell.call_args[0][0]["subject_id"] == 5


# ═══════════════════════════════════════════════════════════════
# SlotDialog — get_values
# ═══════════════════════════════════════════════════════════════
class TestSlotDialog:
    def _dialog(self, slot_data=None):
        from PyQt6.QtCore import QTime

        d = SlotDialog.__new__(SlotDialog)
        d.cmb_day = MagicMock()
        d.cmb_day.currentData.return_value = "Lundi"
        d.cmb_day.findData = MagicMock(return_value=0)
        d.time_start = MagicMock()
        d.time_start.time.return_value = QTime(8, 0)
        d.time_end = MagicMock()
        d.time_end.time.return_value = QTime(9, 0)
        d.cmb_subject = MagicMock()
        d.cmb_subject.currentData.return_value = 3
        d.cmb_teacher = MagicMock()
        d.cmb_teacher.currentData.return_value = 2
        d.txt_room = MagicMock()
        d.txt_room.text.return_value = "Salle 01"
        return d

    def test_get_values_returns_dict(self):
        d = self._dialog()
        vals = d.get_values()
        assert vals["day_of_week"] == "Lundi"
        assert vals["start_time"] == "08:00"
        assert vals["end_time"] == "09:00"
        assert vals["subject_id"] == 3
        assert vals["teacher_id"] == 2
        assert vals["room"] == "Salle 01"

    def test_get_values_empty_room(self):
        d = self._dialog()
        d.txt_room.text.return_value = "   "
        vals = d.get_values()
        assert vals["room"] == ""

    def test_validate_rejects_end_before_start(self):
        from PyQt6.QtCore import QTime

        d = self._dialog()
        d.time_start.time.return_value = QTime(10, 0)
        d.time_end.time.return_value = QTime(9, 0)
        with patch("timetable_manager.QMessageBox") as MockMsgBox:
            MockMsgBox.warning = MagicMock()
            d.accept = MagicMock()
            d._validate_and_accept()
            MockMsgBox.warning.assert_called_once()
            d.accept.assert_not_called()

    def test_validate_accepts_valid_times(self):
        from PyQt6.QtCore import QTime

        d = self._dialog()
        d.time_start.time.return_value = QTime(8, 0)
        d.time_end.time.return_value = QTime(9, 0)
        with patch("timetable_manager.QMessageBox") as MockMsgBox:
            d.accept = MagicMock()
            d._validate_and_accept()
            MockMsgBox.warning.assert_not_called()
            d.accept.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# TimetableWindow — CRUD
# ═══════════════════════════════════════════════════════════════
class TestTimetableWindowCrud:
    def _window(self):
        w = TimetableWindow.__new__(TimetableWindow)
        w._class_id = 1
        w._classes = [(1, "6ème A"), (2, "5ème B")]
        w._subjects = [(1, "Maths"), (2, "Physique")]
        w._staff = [(1, "M. Diallo"), (2, "Mme Sow")]
        w.cmb_class = MagicMock()
        w.cmb_class.currentText.return_value = "6ème A"
        w.grid = MagicMock()
        return w

    def _patch_db(self, w, rows=None):
        db, conn, cur = _make_db_ctx(rows or [])
        patcher = patch("timetable_manager.DatabaseManager", return_value=db)
        return patcher, db, conn, cur

    # ── _load_grid ──────────────────────────────────────────
    def test_load_grid_calls_render(self):
        w = self._window()
        row = (1, "Lundi", "08:00", "09:00", 1, 1, "S01", "Maths", "M. Diallo")
        p, db, conn, cur = self._patch_db(w, [row])
        cur.fetchall.return_value = [row]
        with p:
            w._load_grid()
        w.grid.render.assert_called_once()
        slots = w.grid.render.call_args[0][0]
        assert len(slots) == 1
        assert slots[0]["subject_name_fr"] == "Maths"

    def test_load_grid_skips_if_no_class(self):
        w = self._window()
        w._class_id = None
        w._load_grid()
        w.grid.render.assert_not_called()

    def test_load_grid_empty_renders_empty(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w, [])
        with p:
            w._load_grid()
        w.grid.render.assert_called_once_with([])

    # ── _save_slot ──────────────────────────────────────────
    def test_save_slot_inserts_record(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w)
        values = {
            "day_of_week": "Mardi",
            "start_time": "10:00",
            "end_time": "11:00",
            "subject_id": 1,
            "teacher_id": 1,
            "room": "S02",
        }
        with p:
            w._save_slot(values)
        # First call is INSERT, second is SELECT (from _load_grid)
        sql = cur.execute.call_args_list[0][0][0]
        assert "INSERT INTO Timetable" in sql
        conn.commit.assert_called_once()

    def test_save_slot_reloads_grid(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w)
        with p:
            w._save_slot(
                {
                    "day_of_week": "Lundi",
                    "start_time": "08:00",
                    "end_time": "09:00",
                    "subject_id": 1,
                    "teacher_id": None,
                    "room": "",
                }
            )
        w.grid.render.assert_called()

    def test_save_slot_empty_room_stored_as_none(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w)
        with p:
            w._save_slot(
                {
                    "day_of_week": "Lundi",
                    "start_time": "08:00",
                    "end_time": "09:00",
                    "subject_id": 1,
                    "teacher_id": None,
                    "room": "",
                }
            )
        # First call is INSERT
        params = cur.execute.call_args_list[0][0][1]
        assert params[6] is None  # room → None si vide

    # ── _update_slot ─────────────────────────────────────────
    def test_update_slot_executes_update(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w)
        values = {
            "day_of_week": "Mercredi",
            "start_time": "11:00",
            "end_time": "12:00",
            "subject_id": 2,
            "teacher_id": 2,
            "room": "S03",
        }
        with p:
            w._update_slot(42, values)
        # First call is UPDATE, second is SELECT (from _load_grid)
        sql = cur.execute.call_args_list[0][0][0]
        assert "UPDATE Timetable" in sql
        params = cur.execute.call_args_list[0][0][1]
        assert params[-1] == 42  # WHERE id = 42
        conn.commit.assert_called_once()

    def test_update_slot_reloads_grid(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w)
        with p:
            w._update_slot(
                1,
                {
                    "day_of_week": "Jeudi",
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "subject_id": 1,
                    "teacher_id": 1,
                    "room": "S01",
                },
            )
        w.grid.render.assert_called()

    # ── _delete_slot ─────────────────────────────────────────
    def test_delete_slot_executes_delete(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w)
        with p:
            w._delete_slot(7)
        # First call is DELETE, second is SELECT (from _load_grid)
        sql = cur.execute.call_args_list[0][0][0]
        assert "DELETE FROM Timetable" in sql
        params = cur.execute.call_args_list[0][0][1]
        assert params == (7,)
        conn.commit.assert_called_once()

    def test_delete_slot_reloads_grid(self):
        w = self._window()
        p, db, conn, cur = self._patch_db(w)
        with p:
            w._delete_slot(5)
        w.grid.render.assert_called()

    # ── _add_slot_for_day ────────────────────────────────────
    def test_add_slot_no_class_shows_info(self):
        w = self._window()
        w._class_id = None
        with patch("timetable_manager.QMessageBox") as MockMsg:
            MockMsg.information = MagicMock()
            w._add_slot_for_day("Lundi")
            MockMsg.information.assert_called_once()

    def test_add_slot_dialog_accepted_saves(self):
        w = self._window()
        fake_vals = {
            "day_of_week": "Lundi",
            "start_time": "08:00",
            "end_time": "09:00",
            "subject_id": 1,
            "teacher_id": 1,
            "room": "S01",
        }
        with patch("timetable_manager.SlotDialog") as MockDlg:
            dlg_inst = MagicMock()
            dlg_inst.exec.return_value = 1
            dlg_inst.get_values.return_value = fake_vals
            dlg_inst.cmb_day.findData.return_value = 0  # int so idx >= 0 works
            MockDlg.return_value = dlg_inst
            with patch.object(w, "_save_slot") as mock_save:
                w._add_slot_for_day("Lundi")
                mock_save.assert_called_once_with(fake_vals)

    def test_add_slot_dialog_cancelled_no_save(self):
        w = self._window()
        with patch("timetable_manager.SlotDialog") as MockDlg:
            dlg_inst = MagicMock()
            dlg_inst.exec.return_value = 0
            dlg_inst.cmb_day.findData.return_value = 0
            MockDlg.return_value = dlg_inst
            with patch.object(w, "_save_slot") as mock_save:
                w._add_slot_for_day("Lundi")
                mock_save.assert_not_called()

    # ── _edit_slot ───────────────────────────────────────────
    def test_edit_slot_dialog_accepted_updates(self):
        w = self._window()
        slot = {
            "id": 10,
            "day_of_week": "Lundi",
            "start_time": "08:00",
            "end_time": "09:00",
            "subject_id": 1,
            "teacher_id": 1,
            "room": "",
        }
        new_vals = {**slot, "room": "S02"}
        with patch("timetable_manager.SlotDialog") as MockDlg:
            dlg_inst = MagicMock()
            dlg_inst.exec.return_value = 1
            dlg_inst.get_values.return_value = new_vals
            MockDlg.return_value = dlg_inst
            with patch.object(w, "_update_slot") as mock_update:
                w._edit_slot(slot)
                mock_update.assert_called_once_with(10, new_vals)

    # ── _confirm_delete_slot ─────────────────────────────────
    def test_confirm_delete_accepted_deletes(self):
        w = self._window()
        slot = {"id": 99, "subject_name_fr": "Maths", "day_of_week": "Mardi"}
        with patch("timetable_manager.QMessageBox") as MockMsg:
            MockMsg.StandardButton = MagicMock()
            MockMsg.question.return_value = MockMsg.StandardButton.Yes
            with patch.object(w, "_delete_slot") as mock_del:
                w._confirm_delete_slot(slot)
                mock_del.assert_called_once_with(99)

    def test_confirm_delete_rejected_no_delete(self):
        w = self._window()
        slot = {"id": 99, "subject_name_fr": "Hist", "day_of_week": "Lundi"}
        with patch("timetable_manager.QMessageBox") as MockMsg:
            MockMsg.StandardButton = MagicMock()
            MockMsg.question.return_value = MockMsg.StandardButton.No
            with patch.object(w, "_delete_slot") as mock_del:
                w._confirm_delete_slot(slot)
                mock_del.assert_not_called()

    # ── refresh_data ─────────────────────────────────────────
    def test_refresh_data_calls_load_filters(self):
        w = self._window()
        with patch.object(w, "_load_filters") as mock_lf, patch.object(w, "_load_grid") as mock_lg:
            w.refresh_data()
            mock_lf.assert_called_once()
            mock_lg.assert_called_once()

    def test_refresh_data_skips_grid_if_no_class(self):
        w = self._window()
        w._class_id = None
        with patch.object(w, "_load_filters"), patch.object(w, "_load_grid") as mock_lg:
            w.refresh_data()
            mock_lg.assert_not_called()


# ═══════════════════════════════════════════════════════════════
# TimetableWindow — _load_filters, _on_class_changed, error paths
# ═══════════════════════════════════════════════════════════════
class TestTimetableWindowFilters:
    def _window(self):
        w = TimetableWindow.__new__(TimetableWindow)
        w._class_id = None
        w._classes = []
        w._subjects = []
        w._staff = []
        w.cmb_class = MagicMock()
        w.cmb_class.currentData.return_value = None
        w.cmb_class.currentText.return_value = "6ème A"
        w.grid = MagicMock()
        return w

    def _mock_db(self, *fetchall_returns):
        cur = MagicMock()
        cur.fetchall.side_effect = list(fetchall_returns)
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__ = lambda self: self
        conn.__exit__ = MagicMock(return_value=False)
        db = MagicMock()
        db.get_connection.return_value = conn
        return db, cur

    def test_load_filters_populates_class_combo(self):
        w = self._window()
        classes = [(1, "6ème A"), (2, "5ème B")]
        subjects = [(10, "Maths"), (11, "Arabe")]
        staff = [(20, "M. Diop")]
        db, cur = self._mock_db(classes, subjects, staff)
        with patch("timetable_manager.DatabaseManager", return_value=db):
            w._load_filters()
        # "— Sélectionner —" + 2 classes = 3 addItem calls au minimum
        assert w.cmb_class.addItem.call_count >= len(classes) + 1
        assert w._classes == classes
        assert w._subjects == subjects
        assert w._staff == staff

    def test_load_filters_sets_index_when_classes_exist(self):
        w = self._window()
        db, cur = self._mock_db([(1, "6ème A")], [], [])
        with patch("timetable_manager.DatabaseManager", return_value=db):
            w._load_filters()
        w.cmb_class.setCurrentIndex.assert_called_with(1)

    def test_load_filters_error_handled(self):
        w = self._window()
        with patch("timetable_manager.DatabaseManager") as MockDB:
            MockDB.return_value.get_connection.side_effect = Exception("conn fail")
            w._load_filters()  # ne doit pas lever d'exception

    def test_on_class_changed_sets_class_id_and_loads_grid(self):
        w = self._window()
        w.cmb_class.currentData.return_value = 5
        with patch.object(w, "_load_grid") as mock_lg:
            w._on_class_changed()
        assert w._class_id == 5
        mock_lg.assert_called_once()

    def test_on_class_changed_no_class_skips_grid(self):
        w = self._window()
        w.cmb_class.currentData.return_value = None
        with patch.object(w, "_load_grid") as mock_lg:
            w._on_class_changed()
        mock_lg.assert_not_called()

    def test_load_grid_error_shows_warning(self):
        w = self._window()
        w._class_id = 1
        with patch("timetable_manager.DatabaseManager") as MockDB, patch("timetable_manager.QMessageBox") as MockMsg:
            MockDB.return_value.get_connection.side_effect = Exception("grid fail")
            MockMsg.warning = MagicMock()
            w._load_grid()
        MockMsg.warning.assert_called_once()

    def test_save_slot_error_shows_critical(self):
        w = self._window()
        w._class_id = 1
        with patch("timetable_manager.DatabaseManager") as MockDB, patch("timetable_manager.QMessageBox") as MockMsg:
            MockDB.return_value.get_connection.side_effect = Exception("save fail")
            MockMsg.critical = MagicMock()
            w._save_slot(
                {
                    "day_of_week": "Lundi",
                    "start_time": "08:00",
                    "end_time": "09:00",
                    "subject_id": 1,
                    "teacher_id": 1,
                    "room": "",
                }
            )
        MockMsg.critical.assert_called_once()

    def test_update_slot_error_shows_critical(self):
        w = self._window()
        w._class_id = 1
        with patch("timetable_manager.DatabaseManager") as MockDB, patch("timetable_manager.QMessageBox") as MockMsg:
            MockDB.return_value.get_connection.side_effect = Exception("upd fail")
            MockMsg.critical = MagicMock()
            w._update_slot(
                42,
                {
                    "day_of_week": "Lundi",
                    "start_time": "08:00",
                    "end_time": "09:00",
                    "subject_id": 1,
                    "teacher_id": 1,
                    "room": "",
                },
            )
        MockMsg.critical.assert_called_once()

    def test_delete_slot_error_shows_critical(self):
        w = self._window()
        w._class_id = 1
        with patch("timetable_manager.DatabaseManager") as MockDB, patch("timetable_manager.QMessageBox") as MockMsg:
            MockDB.return_value.get_connection.side_effect = Exception("del fail")
            MockMsg.critical = MagicMock()
            w._delete_slot(7)
        MockMsg.critical.assert_called_once()

    def test_print_no_class_shows_info(self):
        w = self._window()
        w._class_id = None
        with patch("timetable_manager.QMessageBox") as MockMsg:
            MockMsg.information = MagicMock()
            w._print_timetable()
        MockMsg.information.assert_called_once()

    def test_print_fpdf_missing_shows_warning(self):
        w = self._window()
        w._class_id = 1
        # Remove fpdf from sys.modules to simulate ImportError
        with patch.dict(sys.modules, {"fpdf": None}), patch("timetable_manager.QMessageBox") as MockMsg:
            MockMsg.warning = MagicMock()
            w._print_timetable()
        MockMsg.warning.assert_called_once()

    def test_edit_slot_cancelled_no_update(self):
        w = self._window()
        slot = {
            "id": 10,
            "day_of_week": "Lundi",
            "start_time": "08:00",
            "end_time": "09:00",
            "subject_id": 1,
            "teacher_id": 1,
            "room": "",
        }
        with patch("timetable_manager.SlotDialog") as MockDlg:
            dlg_inst = MagicMock()
            dlg_inst.exec.return_value = 0
            MockDlg.return_value = dlg_inst
            with patch.object(w, "_update_slot") as mock_upd:
                w._edit_slot(slot)
                mock_upd.assert_not_called()
