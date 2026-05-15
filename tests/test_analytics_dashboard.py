"""
tests/test_analytics_dashboard.py
اختبارات وحدة analytics_dashboard.py (Phase 6.1).

تغطي:
  - AnalyticsWorker: _load_grades, _load_attendance, _load_finance
  - KpiCard: set_value
  - GradesBarChart / AttendanceLineChart / FinancePieChart: update_data (empty + data)
  - AnalyticsDashboardWindow: _on_grades, _on_attendance, _on_finance
"""

from __future__ import annotations

import sys
import os
import types
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ── Stubs للمكتبات الثقيلة ──────────────────────────────────
# نُنشئ stubs قبل أي import حقيقي


def _make_qt_stubs():
    """إنشاء stubs لـ PyQt6 و Matplotlib لتجنب حاجة الشاشة."""
    # Matplotlib backend stub
    mpl_stub = types.ModuleType("matplotlib")
    mpl_stub.use = lambda *a, **kw: None
    sys.modules.setdefault("matplotlib", mpl_stub)

    for sub in ["matplotlib.pyplot", "matplotlib.figure", "matplotlib.backends", "matplotlib.backends.backend_qt5agg"]:
        m = types.ModuleType(sub)
        sys.modules.setdefault(sub, m)

    fig_mod = sys.modules["matplotlib.figure"]
    fig_mod.Figure = MagicMock

    canvas_mod = sys.modules["matplotlib.backends.backend_qt5agg"]
    canvas_mod.FigureCanvasQTAgg = MagicMock

    plt_mod = sys.modules["matplotlib.pyplot"]
    plt_mod.cm = MagicMock()
    plt_mod.cm.RdYlGn = MagicMock(return_value=["#aaa"])

    # PyQt6 stubs
    for mod_name in [
        "PyQt6",
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    def _make_class(name, *bases):
        return type(
            name,
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
            },
        )

    widgets = sys.modules["PyQt6.QtWidgets"]
    for cls_name in [
        "QMainWindow",
        "QWidget",
        "QVBoxLayout",
        "QHBoxLayout",
        "QLabel",
        "QComboBox",
        "QPushButton",
        "QTabWidget",
        "QScrollArea",
        "QSizePolicy",
        "QFrame",
        "QGridLayout",
        "QSplitter",
        "QTableWidget",
        "QTableWidgetItem",
        "QHeaderView",
        "QDialog",
        "QFormLayout",
        "QTimeEdit",
        "QLineEdit",
        "QDialogButtonBox",
        "QMessageBox",
        "QToolButton",
        "QMenu",
        "QScrollArea",
        "QApplication",
    ]:
        setattr(widgets, cls_name, _make_class(cls_name))

    # pytest-qt needs QApplication.instance() to be callable
    widgets.QApplication.instance = staticmethod(lambda: None)
    widgets.QApplication.setQuitOnLastWindowClosed = staticmethod(lambda *a: None)
    # QFrame.Shape used in analytics_dashboard.py
    widgets.QFrame.Shape = MagicMock()
    widgets.QFrame.Shape.StyledPanel = 1

    core = sys.modules["PyQt6.QtCore"]
    core.Qt = MagicMock()
    core.QThread = type(
        "QThread",
        (object,),
        {
            "__init__": lambda self, *a, **kw: None,
            "start": lambda self: None,
            "quit": lambda self: None,
            "isRunning": lambda self: False,
        },
    )
    core.pyqtSignal = lambda *a: MagicMock()
    core.QSize = MagicMock()
    core.QTime = MagicMock()

    gui = sys.modules["PyQt6.QtGui"]
    gui.QFont = MagicMock()
    gui.QColor = MagicMock()
    gui.QBrush = MagicMock()
    gui.QAction = MagicMock()


_make_qt_stubs()

# ── Stubs للوحدات الداخلية ───────────────────────────────────
db_stub = types.ModuleType("database_setup")
db_stub.DatabaseManager = MagicMock()
sys.modules["database_setup"] = db_stub

logger_stub = types.ModuleType("app_logger")
logger_stub.AppLogger = MagicMock()
sys.modules["app_logger"] = logger_stub

ui_stub = types.ModuleType("ui_styles")
ui_stub.ThemeManager = MagicMock()
ui_stub.Colors = MagicMock()
sys.modules["ui_styles"] = ui_stub

svc_stub = types.ModuleType("services.grade_service")


class _FakeGradeService:
    def calculate_period_average(self, pairs):
        if not pairs:
            return 0.0
        total_w = sum(c for _, c in pairs)
        if total_w == 0:
            return 0.0
        return sum(g * c for g, c in pairs) / total_w

    def get_honor_mention(self, avg):
        if avg >= 16:
            return "Très Bien"
        if avg >= 14:
            return "Bien"
        if avg >= 12:
            return "Assez Bien"
        if avg >= 10:
            return "Passable"
        return "Insuffisant"


svc_stub.GradeService = _FakeGradeService
# Note: we don't override sys.modules["services.grade_service"] here to avoid
# breaking test_grade_service.py. Handler tests inject _FakeGradeService directly.

# ── Import du module sous test ────────────────────────────────
from analytics_dashboard import (
    AnalyticsWorker,
    KpiCard,
    GradesBarChart,
    AttendanceLineChart,
    FinancePieChart,
    AnalyticsDashboardWindow,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _make_cursor(rows):
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = rows[0] if rows else None
    return cur


# ═══════════════════════════════════════════════════════════════
# AnalyticsWorker — pure-logic tests (no real DB)
# ═══════════════════════════════════════════════════════════════
class TestAnalyticsWorkerGrades:
    def _worker(self, year_id=1, class_id=None):
        w = AnalyticsWorker.__new__(AnalyticsWorker)
        w.year_id = year_id
        w.class_id = class_id
        w.grades_ready = MagicMock()
        w.grades_ready.emit = MagicMock()
        return w

    def test_grades_empty(self):
        w = self._worker()
        repo = MagicMock()
        repo.get_grades_by_subject.return_value = []
        w._load_grades(repo)
        w.grades_ready.emit.assert_called_once_with([], [], [])

    def test_grades_normalizes_to_20(self):
        """Doit normaliser avg_score / max_score * 20."""
        w = self._worker()
        # (subject_name_fr, avg_score, coefficient, max_score)
        rows = [("Maths", 16.0, 3.0, 20.0), ("Science", 8.0, 2.0, 10.0)]
        repo = MagicMock()
        repo.get_grades_by_subject.return_value = rows
        w._load_grades(repo)
        args = w.grades_ready.emit.call_args[0]
        names, averages, coefficients = args
        assert names == ["Maths", "Science"]
        assert abs(averages[0] - 16.0) < 0.01  # 16/20*20
        assert abs(averages[1] - 16.0) < 0.01  # 8/10*20
        assert coefficients == [3.0, 2.0]

    def test_grades_none_score_treated_as_zero(self):
        w = self._worker()
        rows = [("Arabe", None, 4.0, 20.0)]
        repo = MagicMock()
        repo.get_grades_by_subject.return_value = rows
        w._load_grades(repo)
        _, averages, _ = w.grades_ready.emit.call_args[0]
        assert averages[0] == 0.0

    def test_grades_max_score_zero_gives_zero(self):
        w = self._worker()
        rows = [("Gym", 5.0, 1.0, 0.0)]
        repo = MagicMock()
        repo.get_grades_by_subject.return_value = rows
        w._load_grades(repo)
        _, averages, _ = w.grades_ready.emit.call_args[0]
        assert averages[0] == 0.0

    def test_grades_with_class_filter(self):
        """Si class_id défini, le repo est appelé avec class_id."""
        w = self._worker(class_id=5)
        repo = MagicMock()
        repo.get_grades_by_subject.return_value = []
        w._load_grades(repo)
        repo.get_grades_by_subject.assert_called_once_with(w.year_id, 5)

    def test_grades_without_class_filter(self):
        w = self._worker(class_id=None)
        repo = MagicMock()
        repo.get_grades_by_subject.return_value = []
        w._load_grades(repo)
        repo.get_grades_by_subject.assert_called_once_with(w.year_id, None)


class TestAnalyticsWorkerAttendance:
    def _worker(self, year_id=1, class_id=None):
        w = AnalyticsWorker.__new__(AnalyticsWorker)
        w.year_id = year_id
        w.class_id = class_id
        w.attendance_ready = MagicMock()
        w.attendance_ready.emit = MagicMock()
        return w

    def test_attendance_empty(self):
        w = self._worker()
        repo = MagicMock()
        repo.get_monthly_attendance_rate.return_value = []
        w._load_attendance(repo)
        w.attendance_ready.emit.assert_called_once_with({})

    def test_attendance_calculates_rate(self):
        rows = [("2026-01", 100, 85), ("2026-02", 80, 72)]
        w = self._worker()
        repo = MagicMock()
        repo.get_monthly_attendance_rate.return_value = rows
        w._load_attendance(repo)
        monthly = w.attendance_ready.emit.call_args[0][0]
        assert monthly["2026-01"] == 85.0
        assert abs(monthly["2026-02"] - 90.0) < 0.1

    def test_attendance_skips_zero_total(self):
        rows = [("2026-03", 0, 0)]
        w = self._worker()
        repo = MagicMock()
        repo.get_monthly_attendance_rate.return_value = rows
        w._load_attendance(repo)
        monthly = w.attendance_ready.emit.call_args[0][0]
        assert "2026-03" not in monthly

    def test_attendance_with_class_filter(self):
        w = self._worker(class_id=3)
        repo = MagicMock()
        repo.get_monthly_attendance_rate.return_value = []
        w._load_attendance(repo)
        repo.get_monthly_attendance_rate.assert_called_once_with(w.year_id, 3)


class TestAnalyticsWorkerFinance:
    def _worker(self, year_id=1, class_id=None):
        w = AnalyticsWorker.__new__(AnalyticsWorker)
        w.year_id = year_id
        w.class_id = class_id
        w.finance_ready = MagicMock()
        w.finance_ready.emit = MagicMock()
        return w

    def _cursor_sequence(self, due_val, paid_val):
        cur = MagicMock()
        cur.fetchone.side_effect = [(due_val,), (paid_val,)]
        return cur

    def test_finance_emits_paid_and_due(self):
        w = self._worker()
        repo = MagicMock()
        repo.get_finance_summary.return_value = (35000.0, 50000.0)
        w._load_finance(repo)
        w.finance_ready.emit.assert_called_once_with(35000.0, 50000.0)

    def test_finance_handles_none_values(self):
        w = self._worker()
        repo = MagicMock()
        repo.get_finance_summary.return_value = (0.0, 0.0)
        w._load_finance(repo)
        paid, due = w.finance_ready.emit.call_args[0]
        assert due == 0.0
        assert paid == 0.0

    def test_finance_with_class_filter(self):
        w = self._worker(class_id=7)
        repo = MagicMock()
        repo.get_finance_summary.return_value = (0.0, 0.0)
        w._load_finance(repo)
        repo.get_finance_summary.assert_called_once_with(w.year_id, 7)


# ═══════════════════════════════════════════════════════════════
# KpiCard
# ═══════════════════════════════════════════════════════════════
class TestKpiCard:
    def test_set_value_updates_label(self):
        card = KpiCard("Test", "—")
        recorded = []
        card.lbl_value = MagicMock()
        card.lbl_value.setText = lambda v: recorded.append(v)
        card.set_value("42%")
        assert recorded == ["42%"]

    def test_initial_value(self):
        card = KpiCard("Ma Carte", "init_val")
        assert card.lbl_value is not None  # objet créé


# ═══════════════════════════════════════════════════════════════
# GradesBarChart
# ═══════════════════════════════════════════════════════════════
class TestGradesBarChart:
    def _chart(self):
        c = GradesBarChart.__new__(GradesBarChart)
        c.fig = MagicMock()
        c.ax = MagicMock()
        c.canvas = MagicMock()
        return c

    def test_update_empty_draws_empty(self):
        c = self._chart()
        c.update_data([], [], [])
        c.ax.clear.assert_called()

    def test_update_with_data_calls_barh(self):
        c = self._chart()
        bar_mock = MagicMock()
        bar_mock.get_width.return_value = 15.0
        bar_mock.get_y.return_value = 0.0
        bar_mock.get_height.return_value = 1.0
        c.ax.barh.return_value = [bar_mock]

        import sys

        plt_mod = sys.modules["matplotlib.pyplot"]
        plt_mod.cm.RdYlGn.return_value = ["#aaa"]

        c.update_data(["Maths", "Physique"], [15.0, 12.0], [3.0, 2.0])
        c.ax.barh.assert_called_once()
        c.canvas.draw.assert_called()

    def test_update_sets_xlim_to_20(self):
        c = self._chart()
        c.ax.barh.return_value = []
        c.update_data(["X"], [10.0], [1.0])
        c.ax.set_xlim.assert_called_with(0, 20)


# ═══════════════════════════════════════════════════════════════
# AttendanceLineChart
# ═══════════════════════════════════════════════════════════════
class TestAttendanceLineChart:
    def _chart(self):
        c = AttendanceLineChart.__new__(AttendanceLineChart)
        c.fig = MagicMock()
        c.ax = MagicMock()
        c.canvas = MagicMock()
        return c

    def test_empty_monthly_shows_no_line(self):
        c = self._chart()
        c.update_data({})
        c.ax.plot.assert_not_called()
        c.canvas.draw.assert_called()

    def test_monthly_data_plots_correctly(self):
        c = self._chart()
        data = {"2026-01": 88.0, "2026-02": 92.5, "2026-03": 79.0}
        c.update_data(data)
        c.ax.plot.assert_called_once()
        args = c.ax.plot.call_args[0]
        assert args[0] == ["01", "02", "03"]
        assert args[1] == [88.0, 92.5, 79.0]

    def test_threshold_line_drawn_at_80(self):
        c = self._chart()
        c.update_data({"2026-01": 75.0})
        c.ax.axhline.assert_called_once_with(80, linestyle="--", color="#ef5350", linewidth=1, label="Seuil 80%")

    def test_fill_between_called(self):
        c = self._chart()
        c.update_data({"2026-01": 90.0})
        c.ax.fill_between.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# FinancePieChart
# ═══════════════════════════════════════════════════════════════
class TestFinancePieChart:
    def _chart(self):
        c = FinancePieChart.__new__(FinancePieChart)
        c.fig = MagicMock()
        c.ax = MagicMock()
        c.canvas = MagicMock()
        return c

    def test_zero_due_skips_pie(self):
        c = self._chart()
        c.update_data(0.0, 0.0)
        c.ax.pie.assert_not_called()
        c.canvas.draw.assert_called()

    def test_paid_exceeds_due_remaining_zero(self):
        """Si paid > due, remaining = 0."""
        c = self._chart()
        mock_wedge = MagicMock()
        mock_text = MagicMock()
        mock_text.set_fontsize = lambda *a: None
        mock_text.set_color = lambda *a: None
        c.ax.pie.return_value = ([mock_wedge], [mock_text], [mock_text])
        c.update_data(120000.0, 100000.0)
        sizes = c.ax.pie.call_args[0][0]
        assert sizes[1] == 0  # remaining clampé à 0

    def test_normal_finance(self):
        c = self._chart()
        mock_text = MagicMock()
        mock_text.set_fontsize = lambda *a: None
        mock_text.set_color = lambda *a: None
        c.ax.pie.return_value = ([], [], [mock_text])
        c.update_data(75000.0, 100000.0)
        sizes = c.ax.pie.call_args[0][0]
        assert sizes[0] == 75000.0
        assert sizes[1] == 25000.0


# ═══════════════════════════════════════════════════════════════
# AnalyticsDashboardWindow — signal handlers
# ═══════════════════════════════════════════════════════════════
class TestAnalyticsDashboardHandlers:
    def _window(self):
        w = AnalyticsDashboardWindow.__new__(AnalyticsDashboardWindow)
        w._svc = _FakeGradeService()
        w.grades_chart = MagicMock()
        w.att_chart = MagicMock()
        w.fin_chart = MagicMock()
        w.kpi_avg = MagicMock()
        w.kpi_att = MagicMock()
        w.kpi_paid = MagicMock()
        w.kpi_risk = MagicMock()
        return w

    def test_on_grades_updates_chart(self):
        w = self._window()
        w._on_grades(["Maths", "Sci"], [14.0, 8.0], [3.0, 2.0])
        w.grades_chart.update_data.assert_called_once_with(["Maths", "Sci"], [14.0, 8.0], [3.0, 2.0])

    def test_on_grades_risk_count(self):
        w = self._window()
        # Élèves avec average < 10 → 1 élève en difficulté
        w._on_grades(["Maths", "Hist"], [14.0, 8.0], [3.0, 2.0])
        w.kpi_risk.set_value.assert_called_with("1")

    def test_on_grades_empty(self):
        """Pas d'appels sur kpi si pas de données."""
        w = self._window()
        w._on_grades([], [], [])
        w.kpi_avg.set_value.assert_not_called()

    def test_on_attendance_updates_chart(self):
        w = self._window()
        data = {"2026-01": 88.0, "2026-02": 92.0}
        w._on_attendance(data)
        w.att_chart.update_data.assert_called_once_with(data)

    def test_on_attendance_calculates_overall(self):
        w = self._window()
        w._on_attendance({"2026-01": 80.0, "2026-02": 90.0})
        w.kpi_att.set_value.assert_called_with("85.0%")

    def test_on_attendance_empty(self):
        w = self._window()
        w._on_attendance({})
        w.kpi_att.set_value.assert_not_called()

    def test_on_finance_calculates_percentage(self):
        w = self._window()
        w._on_finance(75000.0, 100000.0)
        w.fin_chart.update_data.assert_called_once_with(75000.0, 100000.0)
        w.kpi_paid.set_value.assert_called_with("75.0%")

    def test_on_finance_zero_due(self):
        w = self._window()
        w._on_finance(0.0, 0.0)
        w.kpi_paid.set_value.assert_called_with("—")

    def test_on_finance_full_payment(self):
        w = self._window()
        w._on_finance(50000.0, 50000.0)
        w.kpi_paid.set_value.assert_called_with("100.0%")


# ═══════════════════════════════════════════════════════════════
# AnalyticsWorker.run()
# ═══════════════════════════════════════════════════════════════
class TestAnalyticsWorkerRun:
    def _worker(self):
        w = AnalyticsWorker.__new__(AnalyticsWorker)
        w.year_id = 1
        w.class_id = None
        w.error_signal = MagicMock()
        w.error_signal.emit = MagicMock()
        w._load_grades = MagicMock()
        w._load_attendance = MagicMock()
        w._load_finance = MagicMock()
        return w

    def _mock_db_ctx(self):
        cur = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__ = lambda self: self
        conn.__exit__ = MagicMock(return_value=False)
        db = MagicMock()
        db.get_connection.return_value = conn
        return db, conn, cur

    def test_run_calls_all_loaders(self):
        w = self._worker()
        db, conn, cur = self._mock_db_ctx()
        with patch("analytics_dashboard.DatabaseManager", return_value=db):
            with patch("analytics_dashboard.AnalyticsRepository") as MockRepo:
                w.run()
        assert w._load_grades.call_count == 1
        assert w._load_attendance.call_count == 1
        assert w._load_finance.call_count == 1
        w.error_signal.emit.assert_not_called()

    def test_run_emits_error_on_exception(self):
        w = self._worker()
        with patch("analytics_dashboard.DatabaseManager") as MockDB:
            MockDB.return_value.get_connection.side_effect = Exception("DB down")
            w.run()
        w.error_signal.emit.assert_called_once()
        assert "DB down" in w.error_signal.emit.call_args[0][0]

    def test_run_loaders_receive_cursor(self):
        """run() passe bien le même repo aux 3 loaders."""
        w = self._worker()
        db, conn, cur = self._mock_db_ctx()
        with patch("analytics_dashboard.DatabaseManager", return_value=db):
            with patch("analytics_dashboard.AnalyticsRepository") as MockRepo:
                repo_instance = MagicMock()
                MockRepo.return_value = repo_instance
                w.run()
        assert w._load_grades.call_args[0][0] is repo_instance
        assert w._load_finance.call_args[0][0] is repo_instance


# ═══════════════════════════════════════════════════════════════
# AnalyticsDashboardWindow — _load_filters, _refresh, refresh_data
# ═══════════════════════════════════════════════════════════════
class TestAnalyticsDashboardFilters:
    def _window(self):
        w = AnalyticsDashboardWindow.__new__(AnalyticsDashboardWindow)
        w._year_id = None
        w._class_id = None
        w._worker = None
        w._svc = _FakeGradeService()
        w.cmb_year = MagicMock()
        w.cmb_year.currentData.return_value = 1
        w.cmb_class = MagicMock()
        w.cmb_class.currentData.return_value = None
        w.grades_chart = MagicMock()
        w.att_chart = MagicMock()
        w.fin_chart = MagicMock()
        w.kpi_avg = MagicMock()
        w.kpi_att = MagicMock()
        w.kpi_paid = MagicMock()
        w.kpi_risk = MagicMock()
        return w

    def _mock_db(self, year_rows, class_rows):
        cur = MagicMock()
        cur.fetchall.side_effect = [year_rows, class_rows]
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__ = lambda self: self
        conn.__exit__ = MagicMock(return_value=False)
        db = MagicMock()
        db.get_connection.return_value = conn
        return db, cur

    def test_load_filters_populates_year_combo(self):
        w = self._window()
        years = [(1, "2025-2026", True), (2, "2024-2025", False)]
        classes = [(10, "6ème A")]
        db, cur = self._mock_db(years, classes)
        with patch("analytics_dashboard.DatabaseManager", return_value=db), patch.object(w, "_load_classes"):
            w._load_filters()
        # addItem appelé pour chaque année
        assert w.cmb_year.addItem.call_count == len(years)

    def test_load_filters_sets_active_year(self):
        w = self._window()
        years = [(1, "2025-2026", False), (2, "2024-2025", True)]
        classes = []
        db, cur = self._mock_db(years, classes)
        with patch("analytics_dashboard.DatabaseManager", return_value=db), patch.object(w, "_load_classes"):
            w._load_filters()
        # L'année active est l'index 1 → setCurrentIndex(1)
        w.cmb_year.setCurrentIndex.assert_called_with(1)

    def test_load_filters_error_handled(self):
        w = self._window()
        with patch("analytics_dashboard.DatabaseManager") as MockDB:
            MockDB.return_value.get_connection.side_effect = Exception("conn fail")
            w._load_filters()  # ne doit pas lever d'exception

    def test_load_classes_populates_combo(self):
        w = self._window()
        cur = MagicMock()
        cur.fetchall.return_value = [(10, "6ème A"), (11, "5ème B")]
        conn = MagicMock()
        conn.cursor.return_value = cur
        w._load_classes(conn, 1)
        # "Toutes les classes" + 2 classes = 3 addItem calls
        assert w.cmb_class.addItem.call_count == 3

    def test_load_classes_error_handled(self):
        w = self._window()
        conn = MagicMock()
        conn.cursor.side_effect = Exception("cursor fail")
        w._load_classes(conn, 1)  # ne doit pas lever d'exception

    def test_refresh_no_year_skips_worker(self):
        w = self._window()
        w.cmb_year.currentData.return_value = None
        w.cmb_class.currentData.return_value = None
        w._refresh()
        assert w._worker is None

    def test_refresh_starts_worker(self):
        w = self._window()
        w.cmb_year.currentData.return_value = 1
        w.cmb_class.currentData.return_value = None
        with patch("analytics_dashboard.AnalyticsWorker") as MockWorker:
            mock_instance = MagicMock()
            MockWorker.return_value = mock_instance
            w._refresh()
        mock_instance.start.assert_called_once()

    def test_refresh_stops_running_worker(self):
        w = self._window()
        old_worker = MagicMock()
        old_worker.isRunning.return_value = True
        w._worker = old_worker
        w.cmb_year.currentData.return_value = 1
        w.cmb_class.currentData.return_value = None
        with patch("analytics_dashboard.AnalyticsWorker") as MockWorker:
            MockWorker.return_value = MagicMock()
            w._refresh()
        old_worker.quit.assert_called_once()

    def test_on_year_changed_calls_refresh(self):
        w = self._window()
        w.cmb_year.currentData.return_value = 1
        with (
            patch("analytics_dashboard.DatabaseManager") as MockDB,
            patch.object(w, "_load_classes"),
            patch.object(w, "_refresh") as mock_refresh,
        ):
            conn = MagicMock()
            conn.__enter__ = lambda self: self
            conn.__exit__ = MagicMock(return_value=False)
            MockDB.return_value.get_connection.return_value = conn
            w._on_year_changed()
        mock_refresh.assert_called_once()

    def test_refresh_data_calls_both(self):
        w = self._window()
        with patch.object(w, "_load_filters") as mock_lf, patch.object(w, "_refresh") as mock_rf:
            w.refresh_data()
        mock_lf.assert_called_once()
        mock_rf.assert_called_once()
