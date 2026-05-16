"""
analytics_dashboard.py — Phase 6.1
لوحة تحليلات متقدمة: إحصاءات الدرجات والحضور والمالية بمخططات Matplotlib.

• مخطط توزيع المعدلات للفصل (histogram)
• مقارنة المواد (bar chart)
• تطور الحضور الشهري (line chart)
• نسب المستحقات (pie chart)
"""

from __future__ import annotations

import sys
from datetime import date

import matplotlib
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from app_logger import AppLogger  # noqa: E402
from database_setup import DatabaseManager  # noqa: E402
from repositories.analytics_repo import AnalyticsRepository  # noqa: E402
from services.grade_service import GradeService  # noqa: E402
from ui_styles import Colors, ThemeManager  # noqa: E402


# ──────────────────────────────────────────────────────────────
# Worker: تحميل البيانات في thread منفصل
# ──────────────────────────────────────────────────────────────
class AnalyticsWorker(QThread):
    grades_ready = pyqtSignal(list, list, list)  # (names, averages, coefficients)
    attendance_ready = pyqtSignal(dict)  # {"YYYY-MM": rate_pct}
    finance_ready = pyqtSignal(float, float)  # (total_paid, total_due)
    error_signal = pyqtSignal(str)

    def __init__(self, year_id: int, class_id: int | None = None):
        super().__init__()
        self.year_id = year_id
        self.class_id = class_id

    def run(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AnalyticsRepository(conn)
                self._load_grades(repo)
                self._load_attendance(repo)
                self._load_finance(repo)
        except Exception as e:
            AppLogger.error("AnalyticsDashboard", f"Worker error: {e}")
            self.error_signal.emit(str(e))

    def _load_grades(self, repo: AnalyticsRepository):
        rows = repo.get_grades_by_subject(self.year_id, self.class_id)

        names = [r[0] for r in rows]
        averages = [float(r[1]) if r[1] is not None else 0.0 for r in rows]
        max_scores = [float(r[3]) for r in rows]
        normalized = [avg / mx * 20 if mx else 0 for avg, mx in zip(averages, max_scores)]

        self.grades_ready.emit(names, normalized, [float(r[2]) for r in rows])

    def _load_attendance(self, repo: AnalyticsRepository):
        rows = repo.get_monthly_attendance_rate(self.year_id, self.class_id)

        monthly = {}
        for row in rows:
            month, total, present = row
            if total and total > 0:
                monthly[month] = round((present / total) * 100, 1)

        self.attendance_ready.emit(monthly)

    def _load_finance(self, repo: AnalyticsRepository):
        total_paid, total_due = repo.get_finance_summary(self.year_id, self.class_id)
        self.finance_ready.emit(total_paid, total_due)


# ──────────────────────────────────────────────────────────────
# Chart Widgets
# ──────────────────────────────────────────────────────────────
def _make_figure(figsize=(6, 4)):
    fig = Figure(figsize=figsize, tight_layout=True, facecolor="#1e2433")
    return fig


class GradesBarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = _make_figure((7, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._draw_empty()

    def _draw_empty(self):
        self.ax.clear()
        self.ax.set_facecolor("#1e2433")
        self.ax.text(
            0.5,
            0.5,
            "En attente de données…",
            ha="center",
            va="center",
            color="#aaaaaa",
            fontsize=12,
            transform=self.ax.transAxes,
        )
        self.ax.axis("off")
        self.canvas.draw()

    def update_data(self, names: list, averages: list, coefficients: list):
        self.ax.clear()
        if not names:
            self._draw_empty()
            return

        colors = plt.cm.RdYlGn([a / 20 for a in averages])  # type: ignore[attr-defined]
        bars = self.ax.barh(names, averages, color=colors, edgecolor="#444")
        self.ax.set_xlim(0, 20)
        self.ax.set_xlabel("Moyenne /20", color="#cccccc")
        self.ax.set_title("Moyennes par Matière", color="white", fontsize=13, pad=10)
        self.ax.tick_params(colors="#cccccc")
        self.ax.set_facecolor("#252b3b")
        self.fig.set_facecolor("#1e2433")
        for spine in self.ax.spines.values():
            spine.set_edgecolor("#444")

        # أضف القيمة على كل شريط
        for bar, avg in zip(bars, averages):
            self.ax.text(
                bar.get_width() + 0.2,
                bar.get_y() + bar.get_height() / 2,
                f"{avg:.1f}",
                va="center",
                color="white",
                fontsize=9,
            )

        self.canvas.draw()


class AttendanceLineChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = _make_figure((7, 3.5))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._draw_empty()

    def _draw_empty(self):
        self.ax.clear()
        self.ax.set_facecolor("#1e2433")
        self.ax.text(
            0.5, 0.5, "Chargement…", ha="center", va="center", color="#aaaaaa", fontsize=12, transform=self.ax.transAxes
        )
        self.ax.axis("off")
        self.canvas.draw()

    def update_data(self, monthly: dict):
        self.ax.clear()
        if not monthly:
            self.ax.text(
                0.5,
                0.5,
                "Aucune donnée de présence",
                ha="center",
                va="center",
                color="#aaaaaa",
                fontsize=11,
                transform=self.ax.transAxes,
            )
            self.ax.axis("off")
            self.canvas.draw()
            return

        months = list(monthly.keys())
        rates = list(monthly.values())
        short_labels = [m[5:] for m in months]  # MM only

        self.ax.plot(short_labels, rates, marker="o", linewidth=2, color="#4fc3f7", markersize=6)
        self.ax.fill_between(range(len(rates)), rates, alpha=0.15, color="#4fc3f7")
        self.ax.axhline(80, linestyle="--", color="#ef5350", linewidth=1, label="Seuil 80%")
        self.ax.set_ylim(0, 105)
        self.ax.set_ylabel("Taux de présence (%)", color="#cccccc")
        self.ax.set_title("Évolution de la Présence Mensuelle", color="white", fontsize=13, pad=10)
        self.ax.tick_params(colors="#cccccc")
        self.ax.set_facecolor("#252b3b")
        self.fig.set_facecolor("#1e2433")
        for spine in self.ax.spines.values():
            spine.set_edgecolor("#444")
        self.ax.legend(facecolor="#1e2433", labelcolor="#cccccc")
        self.canvas.draw()


class FinancePieChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = _make_figure((5, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._draw_empty()

    def _draw_empty(self):
        self.ax.clear()
        self.ax.set_facecolor("#1e2433")
        self.ax.text(
            0.5, 0.5, "Chargement…", ha="center", va="center", color="#aaaaaa", fontsize=12, transform=self.ax.transAxes
        )
        self.ax.axis("off")
        self.canvas.draw()

    def update_data(self, paid: float, total_due: float):
        self.ax.clear()
        remaining = max(0, total_due - paid)

        if total_due <= 0:
            self.ax.text(
                0.5,
                0.5,
                "Aucune donnée financière",
                ha="center",
                va="center",
                color="#aaaaaa",
                fontsize=11,
                transform=self.ax.transAxes,
            )
            self.ax.axis("off")
            self.canvas.draw()
            return

        sizes = [paid, remaining]
        labels = [f"Payé\n{paid:,.0f} FCFA", f"Restant\n{remaining:,.0f} FCFA"]
        explode = (0.05, 0)
        colors_pie = ["#66bb6a", "#ef5350"]

        wedges, texts, autotexts = self.ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            colors=colors_pie,
            explode=explode,
            startangle=90,
            textprops={"color": "white", "fontsize": 9},
        )
        for at in autotexts:
            at.set_fontsize(10)
            at.set_color("white")

        self.ax.set_title("Recouvrement des Frais", color="white", fontsize=13, pad=10)
        self.fig.set_facecolor("#1e2433")
        self.canvas.draw()


# ──────────────────────────────────────────────────────────────
# KPI Card
# ──────────────────────────────────────────────────────────────
class KpiCard(QFrame):
    def __init__(self, title: str, value: str = "—", icon: str = "📊", color: str = "#4fc3f7", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(80)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: #1e2433; border: 1px solid #333;
                border-radius: 10px; border-left: 4px solid {color};
            }}
        """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        top = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setFont(QFont("Segoe UI Emoji", 20))
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        top.addWidget(lbl_icon)
        top.addWidget(lbl_title)
        top.addStretch()

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")

        layout.addLayout(top)
        layout.addWidget(self.lbl_value)

    def set_value(self, value: str):
        self.lbl_value.setText(value)


# ──────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────
class AnalyticsDashboardWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analytics — Tableau de Bord Analytique")
        self._year_id = None
        self._class_id = None
        self._worker = None
        self._svc = GradeService()
        self._setup_ui()
        self._load_filters()

    # ── UI Setup ──────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("📊 Tableau de Bord Analytique")
        title.setFont(QFont("Cairo", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        header.addWidget(title)
        header.addStretch()

        # Filtres
        header.addWidget(QLabel("Année:"))
        self.cmb_year = QComboBox()
        self.cmb_year.setMinimumWidth(140)
        self.cmb_year.currentIndexChanged.connect(self._on_year_changed)
        header.addWidget(self.cmb_year)

        header.addWidget(QLabel("Classe:"))
        self.cmb_class = QComboBox()
        self.cmb_class.setMinimumWidth(130)
        self.cmb_class.addItem("Toutes les classes", None)
        self.cmb_class.currentIndexChanged.connect(self._refresh)
        header.addWidget(self.cmb_class)

        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.setStyleSheet(
            "QPushButton { background:#2962ff; color:white; border-radius:6px; "
            "padding:6px 14px; font-weight:bold; } QPushButton:hover { background:#1565c0; }"
        )
        btn_refresh.clicked.connect(self._refresh)
        header.addWidget(btn_refresh)
        root.addLayout(header)

        # KPI Cards
        kpi_row = QHBoxLayout()
        self.kpi_avg = KpiCard("Moyenne Générale", "—", "🎓", "#66bb6a")
        self.kpi_att = KpiCard("Taux de Présence", "—", "📅", "#4fc3f7")
        self.kpi_paid = KpiCard("Taux de Recouvrement", "—", "💰", "#ffa726")
        self.kpi_risk = KpiCard("Élèves en Difficulté", "—", "⚠️", "#ef5350")
        for card in (self.kpi_avg, self.kpi_att, self.kpi_paid, self.kpi_risk):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # Charts (tabs)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane { border: 1px solid #333; background: #1e2433; border-radius: 8px; }
            QTabBar::tab { background: #252b3b; color: #aaa; padding: 8px 16px; border-radius: 4px 4px 0 0; }
            QTabBar::tab:selected { background: #1e2433; color: white; border-bottom: 2px solid #4fc3f7; }
        """
        )

        # Tab 1: Grades
        grades_tab = QWidget()
        grades_layout = QVBoxLayout(grades_tab)
        self.grades_chart = GradesBarChart()
        grades_layout.addWidget(self.grades_chart)
        self.tabs.addTab(grades_tab, "📚 Notes par Matière")

        # Tab 2: Attendance
        att_tab = QWidget()
        att_layout = QVBoxLayout(att_tab)
        self.att_chart = AttendanceLineChart()
        att_layout.addWidget(self.att_chart)
        self.tabs.addTab(att_tab, "📅 Présences Mensuelles")

        # Tab 3: Finance
        fin_tab = QWidget()
        fin_layout = QVBoxLayout(fin_tab)
        self.fin_chart = FinancePieChart()
        fin_layout.addWidget(self.fin_chart)
        self.tabs.addTab(fin_tab, "💰 Recouvrement Financier")

        root.addWidget(self.tabs)

        # Global stylesheet
        central.setStyleSheet("background: #161b2e; color: #e0e0e0;")
        self.cmb_year.setStyleSheet(
            "QComboBox { background:#252b3b; color:white; border:1px solid #444; "
            "border-radius:4px; padding:4px 8px; } QComboBox::drop-down { border: none; }"
        )
        self.cmb_class.setStyleSheet(self.cmb_year.styleSheet())

    # ── Data Loading ──────────────────────────────────────────
    def _load_filters(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                # Academic years
                years = AnalyticsRepository(conn).get_academic_years()
                self.cmb_year.blockSignals(True)
                self.cmb_year.clear()
                active_idx = 0
                for i, (yid, label, is_active) in enumerate(years):
                    self.cmb_year.addItem(label, yid)
                    if is_active:
                        active_idx = i
                self.cmb_year.setCurrentIndex(active_idx)
                self.cmb_year.blockSignals(False)

                if years:
                    self._year_id = years[active_idx][0]
                    self._load_classes(conn, self._year_id)

        except Exception as e:
            AppLogger.error("AnalyticsDashboard", f"_load_filters error: {e}")

    def _load_classes(self, conn, year_id: int):
        self.cmb_class.blockSignals(True)
        self.cmb_class.clear()
        self.cmb_class.addItem("Toutes les classes", None)
        try:
            for cid, name in AnalyticsRepository(conn).get_classes_for_year(year_id):
                self.cmb_class.addItem(name, cid)
        except Exception as e:
            AppLogger.error("AnalyticsDashboard", f"_load_classes error: {e}")
        finally:
            self.cmb_class.blockSignals(False)

    def _on_year_changed(self):
        self._year_id = self.cmb_year.currentData()
        if self._year_id:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    self._load_classes(conn, self._year_id)
            except Exception as e:
                AppLogger.error("AnalyticsDashboard", f"year_changed error: {e}")
        self._refresh()

    def _refresh(self):
        self._year_id = self.cmb_year.currentData()
        self._class_id = self.cmb_class.currentData()

        if not self._year_id:
            return

        if self._worker and self._worker.isRunning():
            self._worker.quit()

        self._worker = AnalyticsWorker(self._year_id, self._class_id)
        self._worker.grades_ready.connect(self._on_grades)
        self._worker.attendance_ready.connect(self._on_attendance)
        self._worker.finance_ready.connect(self._on_finance)
        self._worker.error_signal.connect(lambda e: AppLogger.error("Analytics", e))
        self._worker.start()

    # ── Signal Handlers ───────────────────────────────────────
    def _on_grades(self, names: list, averages: list, coefficients: list):
        self.grades_chart.update_data(names, averages, coefficients)
        if averages:
            pairs = list(zip(averages, coefficients))
            gen_avg = self._svc.calculate_period_average(pairs)
            self.kpi_avg.set_value(f"{gen_avg:.2f}/20")
            mention = self._svc.get_honor_mention(gen_avg)
            self.kpi_avg.set_value(f"{gen_avg:.2f}/20\n{mention}")

            # Count students at risk (avg < 10)
            at_risk = sum(a < 10 for a in averages)
            self.kpi_risk.set_value(str(at_risk))

    def _on_attendance(self, monthly: dict):
        self.att_chart.update_data(monthly)
        if monthly:
            overall = sum(monthly.values()) / len(monthly)
            self.kpi_att.set_value(f"{overall:.1f}%")

    def _on_finance(self, paid: float, total_due: float):
        self.fin_chart.update_data(paid, total_due)
        if total_due > 0:
            pct = (paid / total_due) * 100
            self.kpi_paid.set_value(f"{pct:.1f}%")
        else:
            self.kpi_paid.set_value("—")

    # Called by main_dashbord.py on each show
    def refresh_data(self):
        self._load_filters()
        self._refresh()
