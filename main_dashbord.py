import os
import sys
import traceback
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from auto_backup import AutoBackupSystem
from config_manager import ConfigManager

# --- استيراد أنظمة الدعم الأساسية ---
from database_setup import DatabaseManager
from db_path import configure_qt_font_environment
from repositories.attendance_repo import AttendanceRepository
from repositories.finance_repo import FinanceRepository
from repositories.grades_repo import GradesRepository
from repositories.staff_repo import StaffRepository
from repositories.student_repo import StudentRepository
from ui_styles import Colors, DarkColors, KpiCard, ThemeManager, ToastNotification


def _resolve_app_icon_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "icon.ico"),
        os.path.join(base_dir, "assets", "icon.ico"),
        os.path.join(base_dir, "..", "icon.ico"),
        os.path.join(base_dir, "..", "assets", "icon.ico"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return ""


# --- استيراد شاشة تسجيل الدخول ---
from login_window import LoginWindow

# --- استيراد جميع وحدات النظام (الشاشات) ---
try:
    from academic_settings import AcademicSettingsWindow
    from admin_documents import AdminDocsWindow
    from analytics_dashboard import AnalyticsDashboardWindow
    from bulletin_generation import BulletinGenerationWindow
    from communication_ui import CommunicationWindow
    from finance_dashboard import ModernFinanceDashboard
    from finance_expenses import ExpensesWindow
    from finance_fees_setup import FeesSetupWindow
    from finance_payments import StudentPaymentWindow
    from inventory_management import InventoryWindow
    from payment_management import StudentDuesWindow
    from staff_attendance import StaffAttendanceWindow
    from staff_leaves import StaffLeaveWindow
    from staff_management import ModernStaffManagement
    from student_attendance import StudentAttendanceWindow
    from student_discipline import DisciplineWindow
    from student_grades import StudentGradesWindow
    from student_management import ModernStudentManagement
    from system_maintenance import SystemMaintenanceWindow
    from timetable_manager import TimetableWindow
    from user_management import UserManagementWindow
    from year_end_migration import MigrationWindow

    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    AppLogger.error("MainDashboard", f"Erreur d'importation des modules: {e}")


class MainWindow(QMainWindow):
    def __init__(self, username, role):
        super().__init__()
        self.username = username
        self.user_role = role
        self.config = ConfigManager()
        self.setWindowTitle(f"{self.config.app_name} - {self.user_role}")
        icon_path = _resolve_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1280, 800)
        self.showMaximized()

        # تطبيق الثيم المحفوظ
        if self.config.dark_mode_enabled:
            ThemeManager.set_theme("dark")
        else:
            ThemeManager.set_theme("light")
        ThemeManager.apply_theme(self)

        # تهيئة النسخ الاحتياطي التلقائي
        if self.config.auto_backup_enabled:
            self.backup_system = AutoBackupSystem()
            self.backup_system.start_auto_backup(interval_hours=self.config.backup_interval_hours)

        # حاويات النوافذ الفرعية والأزرار (الصلاحيات تُحسب في setup_modules_and_permissions)
        self.module_widgets = {}
        self.module_factories = {}
        self.nav_buttons = {}
        self.allowed_modules = []  # يُملأ في setup_modules_and_permissions

        self.init_ui()
        self.load_dashboard_data()

        # تحديث لوحة التحكم تلقائياً كل 5 دقائق
        self._kpi_timer = QTimer(self)
        self._kpi_timer.timeout.connect(self._auto_refresh_dashboard)
        self._kpi_timer.start(5 * 60 * 1000)

        AppLogger.info("Main", f"Session démarrée pour: {self.username} ({self.user_role})")

        # اختصار البحث العالمي Ctrl+K
        self._search_dlg = None
        sc = QShortcut(QKeySequence("Ctrl+K"), self)
        sc.activated.connect(self.open_global_search)

        # F5 — تحديث الوحدة الحالية
        sc_f5 = QShortcut(QKeySequence("F5"), self)
        sc_f5.activated.connect(self._refresh_current_module)

        # Escape — العودة إلى لوحة التحكم الرئيسية
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._go_to_dashboard)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ================= 1. القائمة الجانبية (Sidebar) =================
        self.setup_sidebar()

        # ================= 2. منطقة العرض الرئيسية (Right Content) =================
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        # أ. الشريط العلوي (Topbar)
        self.setup_topbar()

        # ب. منطقة النوافذ (Stacked Widget)
        self.content_area = QStackedWidget()
        colors = ThemeManager.get_colors()
        self.content_area.setStyleSheet(f"background-color: {colors.BG_MAIN};")

        # إضافة لوحة التحكم (Dashboard) كشاشة أولى
        self.dashboard_screen = self.create_dashboard_screen()
        self.dashboard_idx = self.content_area.addWidget(self.dashboard_screen)

        self.right_layout.addWidget(self.content_area, 1)
        self.main_layout.addWidget(self.right_widget, 1)

        # إعداد الوحدات بناءً على الصلاحيات
        if MODULES_AVAILABLE:
            self.setup_modules_and_permissions()
        else:
            err_lbl = QLabel("Certains modules sont manquants. Vérifiez les fichiers.")
            err_lbl.setStyleSheet(f"color: {colors.DANGER}; font-size: 18px;")
            err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_area.addWidget(err_lbl)

    def setup_sidebar(self):
        colors = ThemeManager.get_colors()
        self._sidebar_expanded = True
        self._cat_labels = []  # category header labels
        self._btn_icon_map = {}  # mod_id → icon str

        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet(
            f"""
            QFrame {{ background-color: {colors.BG_HEADER}; border-right: 2px solid {colors.BORDER}; }}
        """
        )

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(5)

        # شعار البرنامج + زر طي الشريط الجانبي
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)
        self.app_title = QLabel("🏫 El Malick Gest")
        self.app_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.app_title.setStyleSheet(f"color: {colors.HEADER_TEXT}; padding: 6px 4px;")
        self.app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_toggle_sidebar = QPushButton("❮")
        self.btn_toggle_sidebar.setFixedSize(28, 28)
        self.btn_toggle_sidebar.setToolTip("Réduire la barre latérale")
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{colors.HEADER_TEXT}; border:1px solid {colors.BORDER}; "
            "border-radius:4px; font-size:14px; font-weight:bold; }} "
            f"QPushButton:hover {{ background:{colors.PRIMARY}; border-color:{colors.PRIMARY}; }}"
        )
        self.btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        title_row.addWidget(self.app_title, 1)
        title_row.addWidget(self.btn_toggle_sidebar)
        self.sidebar_layout.addLayout(title_row)

        # زر الرئيسية (Dashboard)
        self.btn_dashboard = QPushButton("🏠 Tableau de Bord / الرئيسية")
        self.btn_dashboard.setToolTip("Tableau de Bord / الرئيسية")
        self.style_nav_button(self.btn_dashboard)
        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.clicked.connect(lambda: self.switch_module(self.dashboard_idx, self.btn_dashboard))
        self.sidebar_layout.addWidget(self.btn_dashboard)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {colors.BORDER}; opacity: 0.2; margin: 10px 0;")
        self.sidebar_layout.addWidget(line)

        # Scroll Area للأزرار
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.nav_container = QWidget()
        self.nav_container.setStyleSheet("background: transparent;")
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(2)
        scroll.setWidget(self.nav_container)
        self.sidebar_layout.addWidget(scroll, 1)

        self.sidebar_layout.addStretch()

        # زر الخروج
        self.btn_logout = QPushButton("🚪 Déconnexion / خروج")
        self.btn_logout.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left; padding: 12px 15px; border: none; border-radius: 6px;
                color: {colors.DANGER}; font-size: 14px; font-weight: bold; background-color: transparent;
            }}
            QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; color: white; }}
        """
        )
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.clicked.connect(self.logout)
        self.sidebar_layout.addWidget(self.btn_logout)

        self.main_layout.addWidget(self.sidebar)

    def setup_topbar(self):
        colors = ThemeManager.get_colors()
        self.topbar = QFrame()
        self.topbar.setFixedHeight(60)
        self.topbar.setStyleSheet(
            f"""
            QFrame {{ background-color: {colors.BG_CARD}; border-bottom: 2px solid {colors.BORDER}; }}
        """
        )

        tlay = QHBoxLayout(self.topbar)
        tlay.setContentsMargins(20, 0, 20, 0)

        self.lbl_module_title = QLabel("Tableau de Bord / اللوحة الرئيسية")
        self.lbl_module_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_module_title.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; border: none;")
        tlay.addWidget(self.lbl_module_title)

        tlay.addStretch()

        # الوقت والتاريخ
        self.lbl_datetime = QLabel()
        self.lbl_datetime.setStyleSheet(
            f"color: {colors.TEXT_SECONDARY}; font-weight: bold; margin-right: 20px; border: none;"
        )
        self.update_time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        tlay.addWidget(self.lbl_datetime)

        # زر الثيم ☀️/🌙
        self.btn_theme = QPushButton()
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setFixedSize(40, 40)

        # التعديل هنا: إجبار استخدام خط الإيموجي وضبط الـ padding ليظهر الرمز
        self.btn_theme.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {colors.INPUT_BG};
                border-radius: 20px;
                font-size: 20px;
                border: 1px solid {colors.BORDER};
                font-family: "Segoe UI Emoji";
                padding: 0px;
                padding-bottom: 4px;
            }}
            QPushButton:hover {{ background-color: {colors.BORDER}; }}
        """
        )
        self.update_theme_icon()  # استدعاء التحديث بعد ضبط الستايل
        self.btn_theme.clicked.connect(self.toggle_theme)
        tlay.addWidget(self.btn_theme)

        # المستخدم
        lbl_user = QLabel(f"👤 {self.username} ({self.user_role})")
        lbl_user.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; margin-left: 15px; border: none;")
        tlay.addWidget(lbl_user)

        self.right_layout.addWidget(self.topbar)

    def update_time(self):
        self.lbl_datetime.setText(datetime.now().strftime("%d %b %Y - %H:%M:%S"))

    def toggle_theme(self):
        is_dark = ThemeManager.is_dark_mode()
        new_theme = "light" if is_dark else "dark"

        ThemeManager.set_theme(new_theme)
        self.config.set('UI', 'enable_dark_mode', str(not is_dark))
        self.config.set('APPLICATION', 'theme', new_theme)

        # إعادة تطبيق الاستايلات على النوافذ المفتوحة
        ThemeManager.apply_theme(QApplication.instance())
        self.update_theme_icon()
        self.apply_runtime_theme_updates()

        # إعادة رسم الرسم البياني في لوحة التحكم إذا كان موجوداً
        if hasattr(self, 'ax'):
            colors = ThemeManager.get_colors()
            self.figure.patch.set_facecolor(colors.BG_CARD)
            self.ax.set_facecolor(colors.BG_CARD)
            self.ax.tick_params(colors=colors.TEXT_SECONDARY)
            for spine in self.ax.spines.values():
                spine.set_color(colors.BORDER)
            self.canvas.draw()

    def update_theme_icon(self):
        if ThemeManager.is_dark_mode():
            self.btn_theme.setText("☀️")
            self.btn_theme.setToolTip("Passer au mode clair / تفعيل الوضع الفاتح")
        else:
            self.btn_theme.setText("🌙")
            self.btn_theme.setToolTip("Passer au mode sombre / تفعيل الوضع الداكن")

    def apply_runtime_theme_updates(self):
        colors = ThemeManager.get_colors()

        self.sidebar.setStyleSheet(
            f"QFrame {{ background-color: {colors.BG_HEADER}; border-right: 1px solid {colors.BORDER}; }}"
        )
        self.topbar.setStyleSheet(
            f"QFrame {{ background-color: {colors.BG_CARD}; border-bottom: 1px solid {colors.BORDER}; }}"
        )
        self.content_area.setStyleSheet(f"background-color: {colors.BG_MAIN};")

        if hasattr(self, 'app_title'):
            self.app_title.setStyleSheet(f"color: {colors.HEADER_TEXT}; padding: 10px; margin-bottom: 10px;")

        self.lbl_module_title.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; border: none;")
        self.lbl_datetime.setStyleSheet(
            f"color: {colors.TEXT_SECONDARY}; font-weight: bold; margin-right: 20px; border: none;"
        )
        if hasattr(self, 'lbl_user'):
            self.lbl_user.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; margin-left: 15px; border: none;")

        self.btn_theme.setStyleSheet(
            f"""
            QPushButton {{ background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; border-radius: 20px; font-size: 16px; border: 1px solid {colors.BORDER}; font-weight: 800; }}
            QPushButton:hover {{ background-color: {colors.BORDER}; }}
            """
        )

        self.style_nav_button(self.btn_dashboard)
        for btn in self.nav_buttons.values():
            self.style_nav_button(btn)

        if hasattr(self, 'btn_logout'):
            self.btn_logout.setStyleSheet(
                f"""
                QPushButton {{
                    text-align: left; padding: 12px 15px; border: none; border-radius: 6px;
                    color: {colors.DANGER}; font-size: 14px; font-weight: bold; background-color: transparent;
                }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; color: white; }}
                """
            )

    def create_dashboard_screen(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- 1. KPI Cards (الإحصائيات) ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(20)

        colors = ThemeManager.get_colors()

        self.kpi_students = KpiCard("👨‍🎓", "Total Élèves", "0", colors.PRIMARY, theme_mode="default")
        self.kpi_staff = KpiCard("👥", "Total Personnel", "0", colors.SECONDARY, theme_mode="default")
        self.kpi_classes = KpiCard("🏫", "Classes Actives", "0", colors.WARNING, theme_mode="default")
        self.kpi_revenue = KpiCard("💰", "Revenu (Année)", "0 FCFA", colors.SUCCESS, theme_mode="default")

        kpi_layout.addWidget(self.kpi_students)
        kpi_layout.addWidget(self.kpi_staff)
        kpi_layout.addWidget(self.kpi_classes)
        kpi_layout.addWidget(self.kpi_revenue)

        if self.user_role not in ("Admin", "Comptable"):
            self.kpi_revenue.hide()
        layout.addLayout(kpi_layout)

        # --- 2. Middle Section (Charts & Quick Actions) ---
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(20)

        # Chart
        chart_card = QFrame()
        chart_card.setStyleSheet(
            f"background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER};"
        )
        chart_layout = QVBoxLayout(chart_card)
        lbl_chart = QLabel("Répartition des Élèves par Cycle / توزيع الطلاب")
        lbl_chart.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {colors.TEXT_PRIMARY}; border: none;")
        chart_layout.addWidget(lbl_chart)

        self.figure = Figure(figsize=(5, 3))
        self.figure.patch.set_facecolor(colors.BG_CARD)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        mid_layout.addWidget(chart_card, 2)

        # Quick Actions
        qa_card = QFrame()
        qa_card.setStyleSheet(
            f"background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER};"
        )
        qa_layout = QVBoxLayout(qa_card)
        lbl_qa = QLabel("⚡ Actions Rapides / إجراءات سريعة")
        lbl_qa.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {colors.TEXT_PRIMARY}; border: none;")
        qa_layout.addWidget(lbl_qa)

        qa_grid = QGridLayout()
        qa_grid.setSpacing(10)

        self.btn_qa_add_student = self.create_qa_button("Nouvel Élève", "➕", colors.PRIMARY)
        self.btn_qa_add_student.clicked.connect(lambda: self.trigger_module("student_management"))

        self.btn_qa_pay = self.create_qa_button("Encaisser", "💳", colors.SUCCESS)
        self.btn_qa_pay.clicked.connect(lambda: self.trigger_module("finance_payments"))

        self.btn_qa_att = self.create_qa_button("Faire l'Appel", "📅", colors.WARNING)
        self.btn_qa_att.clicked.connect(lambda: self.trigger_module("student_attendance"))

        self.btn_qa_grades = self.create_qa_button("Saisir Notes", "📝", colors.SECONDARY)
        self.btn_qa_grades.clicked.connect(lambda: self.trigger_module("student_grades"))

        qa_grid.addWidget(self.btn_qa_add_student, 0, 0)
        qa_grid.addWidget(self.btn_qa_pay, 0, 1)
        qa_grid.addWidget(self.btn_qa_att, 1, 0)
        qa_grid.addWidget(self.btn_qa_grades, 1, 1)

        qa_layout.addLayout(qa_grid)
        qa_layout.addStretch()
        mid_layout.addWidget(qa_card, 1)

        layout.addLayout(mid_layout)

        # --- 3. مركز التنبيهات الذكي ---
        alerts_frame = QFrame()
        alerts_frame.setStyleSheet(
            f"""
            QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}
        """
        )
        alerts_vlay = QVBoxLayout(alerts_frame)
        alerts_vlay.setContentsMargins(15, 12, 15, 15)
        alerts_vlay.setSpacing(10)

        lbl_alerts_hdr = QLabel("🔔  Centre d'Alertes / مركز التنبيهات")
        lbl_alerts_hdr.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {colors.TEXT_PRIMARY}; border: none;")
        alerts_vlay.addWidget(lbl_alerts_hdr)

        alerts_cards_row = QHBoxLayout()
        alerts_cards_row.setSpacing(15)

        self.alert_absent = self.create_alert_card("Absences > 20%", "⚠️", colors.WARNING)
        self.alert_late = self.create_alert_card("Retards de paiement", "💸", colors.DANGER)
        self.alert_grades = self.create_alert_card("Moyennes < 8 / 20", "📉", colors.SECONDARY)
        self.alert_leaves = self.create_alert_card("Congés en attente", "🏖️", colors.PRIMARY)

        alerts_cards_row.addWidget(self.alert_absent)
        alerts_cards_row.addWidget(self.alert_late)
        alerts_cards_row.addWidget(self.alert_grades)
        alerts_cards_row.addWidget(self.alert_leaves)
        alerts_vlay.addLayout(alerts_cards_row)

        layout.addWidget(alerts_frame)

        # تحديث كل 5 دقائق
        self.alerts_refresh_timer = QTimer(self)
        self.alerts_refresh_timer.timeout.connect(self.load_alerts_data)
        self.alerts_refresh_timer.start(5 * 60 * 1000)

        return widget

    def create_alert_card(self, title, icon, color):
        """إنشاء بطاقة تنبيه قابلة للتحديث لمركز التنبيهات"""
        colors = ThemeManager.get_colors()
        card = QFrame()
        card.setMinimumHeight(140)
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {colors.BG_MAIN}; border-radius: 10px;
                border: 1px solid {colors.BORDER}; border-top: 4px solid {color};
            }}
        """
        )

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        # رأس البطاقة: عنوان + شارة العدد
        header_row = QHBoxLayout()
        lbl_title = QLabel(f"{icon}  {title}")
        lbl_title.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-weight: bold; font-size: 12px; border: none;")
        header_row.addWidget(lbl_title)
        header_row.addStretch()

        lbl_badge = QLabel("0")
        lbl_badge.setObjectName("badge")
        lbl_badge.setMinimumWidth(24)
        lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_badge.setStyleSheet(
            f"""
            QLabel {{ background-color: {color}; color: white; border-radius: 10px;
                      padding: 1px 7px; font-weight: bold; font-size: 11px; border: none; }}
        """
        )
        header_row.addWidget(lbl_badge)
        lay.addLayout(header_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {colors.BORDER}; border: none; max-height: 1px;")
        lay.addWidget(sep)

        # حاوية العناصر
        items_widget = QWidget()
        items_widget.setStyleSheet("background: transparent;")
        items_lay = QVBoxLayout(items_widget)
        items_lay.setContentsMargins(0, 0, 0, 0)
        items_lay.setSpacing(2)
        lbl_ok = QLabel("✅  Aucune alerte")
        lbl_ok.setStyleSheet(f"color: {colors.SUCCESS}; font-size: 11px; border: none;")
        items_lay.addWidget(lbl_ok)
        items_lay.addStretch()
        lay.addWidget(items_widget, 1)

        # حفظ المراجع كخصائص للبطاقة لتسهيل التحديث
        card._badge = lbl_badge
        card._items_lay = items_lay
        card._accent = color

        return card

    def _update_alert_card(self, card, rows, format_fn):
        """تحديث محتوى بطاقة تنبيه بالبيانات الجديدة"""
        colors = ThemeManager.get_colors()
        lay = card._items_lay

        # إزالة العناصر القديمة
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        count = len(rows)
        card._badge.setText(str(count))

        if count == 0:
            lbl = QLabel("✅  Aucune alerte")
            lbl.setStyleSheet(f"color: {colors.SUCCESS}; font-size: 11px; border: none;")
            lay.addWidget(lbl)
        else:
            for r in rows[:5]:
                lbl = QLabel(f"• {format_fn(r)}")
                lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 11px; border: none;")
                lbl.setWordWrap(True)
                lay.addWidget(lbl)
            if count > 5:
                more = QLabel(f"... +{count - 5} autres")
                more.setStyleSheet(f"color: {card._accent}; font-size: 11px; font-weight: bold; border: none;")
                lay.addWidget(more)
        lay.addStretch()

    def load_alerts_data(self):
        """تحميل بيانات التنبيهات الأربعة من قاعدة البيانات"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                active_year = FinanceRepository(conn).get_active_year_id()
                if active_year == -1:
                    return
                absent_rows = AttendanceRepository(conn).get_high_absence_students(active_year)
                late_rows = FinanceRepository(conn).get_late_dues_students(active_year)
                low_grade_rows = GradesRepository(conn).get_low_average_students(active_year)
                leave_rows = StaffRepository(conn).list_pending_leaves()

            self._update_alert_card(self.alert_absent, absent_rows, lambda r: f"{r[0]}  ({int(r[1])}%)")
            self._update_alert_card(self.alert_late, late_rows, lambda r: f"{r[0]}  ({r[1]:,.0f} F)")
            self._update_alert_card(self.alert_grades, low_grade_rows, lambda r: f"{r[0]}  ({r[1]}/20)")
            self._update_alert_card(self.alert_leaves, leave_rows, lambda r: f"{r[0]}  — {r[1]}")

        except Exception as e:
            AppLogger.error("MainDashboard", f"Alerts load error: {e}")

    def create_qa_button(self, text, icon, color):
        btn = QPushButton(f"{icon} {text}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(60)
        colors = ThemeManager.get_colors()
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};
                border: 1px solid {colors.BORDER}; border-radius: 8px; font-weight: bold; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {color}; color: white; border: none; }}
        """
        )
        return btn

    def load_dashboard_data(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                fin_repo = FinanceRepository(conn)
                stu_repo = StudentRepository(conn)
                sta_repo = StaffRepository(conn)

                active_year = fin_repo.get_active_year_id()

                st_count = stu_repo.count_active_students(active_year)
                self.kpi_students.set_value(str(st_count))

                self.kpi_staff.set_value(str(sta_repo.get_active_staff_count()))

                self.kpi_classes.set_value(str(stu_repo.count_classes()))

                rev = fin_repo.get_total_revenue(active_year) or 0
                self.kpi_revenue.set_value(f"{rev:,.0f}")

                data = stu_repo.get_students_by_cycle(active_year)

            self.ax = self.figure.add_subplot(111)
            self.ax.clear()

            colors = ThemeManager.get_colors()
            if data:
                labels = [r[0] for r in data]
                sizes = [r[1] for r in data]
                self.ax.pie(
                    sizes,
                    labels=labels,
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=[colors.PRIMARY, colors.SUCCESS, colors.WARNING, colors.SECONDARY],
                    textprops={'color': colors.TEXT_PRIMARY, 'fontweight': 'bold'},
                )
            else:
                self.ax.text(0.5, 0.5, "Pas de données", ha='center', va='center', color=colors.TEXT_SECONDARY)
                self.ax.axis('off')

            self.canvas.draw()

        except Exception as e:
            AppLogger.error("MainDashboard", f"Dashboard Data Error: {e}")

        # تحميل بيانات التنبيهات
        self.load_alerts_data()

    def style_nav_button(self, btn):
        colors = ThemeManager.get_colors()
        btn.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left; padding: 12px 15px; border: none; border-radius: 6px;
                color: {colors.HEADER_TEXT}; font-size: 14px; font-weight: bold; background-color: transparent;
            }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            QPushButton:checked {{ background-color: {colors.PRIMARY}; border-left: 4px solid white; }}
        """
        )
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

    def setup_modules_and_permissions(self):
        self.module_windows = {}
        all_modules = [
            ("academic_settings", "Configuration Scolaire", "⚙️", AcademicSettingsWindow, "Paramètres"),
            ("user_management", "Utilisateurs & Droits", "🔐", UserManagementWindow, "Paramètres"),
            ("system_maintenance", "Sauvegarde & Système", "🛡️", SystemMaintenanceWindow, "Paramètres"),
            ("migration_tool", "Clôture & Migration", "🔄", MigrationWindow, "Paramètres"),
            ("student_management", "Gestion des Élèves", "👨‍🎓", ModernStudentManagement, "Scolarité & Pédagogie"),
            ("staff_management", "Ressources Humaines", "👥", ModernStaffManagement, "Scolarité & Pédagogie"),
            ("staff_attendance", "Présence du Personnel", "🕘", StaffAttendanceWindow, "Scolarité & Pédagogie"),
            ("staff_leaves", "Congés du Personnel", "🏖️", StaffLeaveWindow, "Scolarité & Pédagogie"),
            ("student_attendance", "Assiduité (Présence)", "📅", StudentAttendanceWindow, "Scolarité & Pédagogie"),
            ("student_discipline", "Discipline & Comportement", "⚖️", DisciplineWindow, "Scolarité & Pédagogie"),
            ("student_grades", "Saisie des Notes", "📝", StudentGradesWindow, "Scolarité & Pédagogie"),
            ("bulletin_generation", "Génération Bulletins", "🖨️", BulletinGenerationWindow, "Scolarité & Pédagogie"),
            ("finance_dashboard", "Tableau de Bord Financier", "📈", ModernFinanceDashboard, "Finance"),
            ("fees_setup", "Configuration des Frais", "💰", FeesSetupWindow, "Finance"),
            ("student_dues", "Factures & Engagements", "🧾", StudentDuesWindow, "Finance"),
            ("finance_payments", "Caisse & Paiements", "💵", StudentPaymentWindow, "Finance"),
            ("expenses_payroll", "Dépenses & Salaires", "💸", ExpensesWindow, "Finance"),
            ("inventory", "Gestion de Stock", "📦", InventoryWindow, "Finance"),
            ("admin_docs", "Documents Administratifs", "🗂️", AdminDocsWindow, "Outils & Rapports"),
            ("communication", "Centre de Messagerie", "📧", CommunicationWindow, "Outils & Rapports"),
            ("analytics_dashboard", "Analytics & Rapports", "📊", AnalyticsDashboardWindow, "Outils & Rapports"),
            ("timetable", "Emploi du Temps", "📅", TimetableWindow, "Scolarité & Pédagogie"),
        ]

        role_permissions = {
            "Admin": ["all"],
            "Comptable": [
                "finance_dashboard",
                "fees_setup",
                "student_dues",
                "finance_payments",
                "expenses_payroll",
                "inventory",
            ],
            "Secretaire": [
                "student_management",
                "staff_management",
                "staff_attendance",
                "staff_leaves",
                "student_attendance",
                "admin_docs",
                "communication",
            ],
            "Pédagogique": [
                "academic_settings",
                "student_management",
                "student_attendance",
                "student_discipline",
                "student_grades",
                "bulletin_generation",
            ],
            "Prof": ["student_attendance", "student_discipline", "student_grades"],
        }

        self.allowed_modules = role_permissions.get(self.user_role, [])
        is_admin = "all" in self.allowed_modules

        colors = ThemeManager.get_colors()
        current_category = ""

        for mod_id, title, icon, window_class, category in all_modules:
            if is_admin or mod_id in self.allowed_modules:

                # Category Header
                if category != current_category:
                    lbl_cat = QLabel(category.upper())
                    lbl_cat.setStyleSheet(
                        f"color: {colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; margin-top: 10px; margin-left: 5px;"
                    )
                    self.nav_layout.addWidget(lbl_cat)
                    self._cat_labels.append(lbl_cat)
                    current_category = category

                # Navigation Button
                btn = QPushButton(f" {icon}   {title}")
                self.style_nav_button(btn)
                btn.setToolTip(title)

                self.module_factories[mod_id] = window_class
                self.module_widgets[mod_id] = None
                btn.clicked.connect(lambda checked, mid=mod_id, b=btn, t=title: self.open_module(mid, b, t))

                self.nav_layout.addWidget(btn)
                self.nav_buttons[mod_id] = btn
                self._btn_icon_map[mod_id] = icon

        # تطبيق RBAC على الأزرار السريعة بعد تعبئة allowed_modules
        self.apply_rbac_to_quick_actions()

    def open_module(self, mod_id, active_button, title):
        widget_idx = self.module_widgets.get(mod_id)

        if widget_idx is None:
            window_class = self.module_factories.get(mod_id)
            if not window_class:
                AppLogger.error("Main", f"Module introuvable: {mod_id}")
                return

            try:
                module_instance = window_class()
                # تطبيق RBAC على مستوى الأزرار داخل الوحدة
                if hasattr(module_instance, "apply_rbac"):
                    module_instance.apply_rbac(self.user_role)
                self.module_windows[mod_id] = module_instance

                if isinstance(module_instance, QMainWindow):
                    widget_to_add = module_instance.takeCentralWidget()
                    if widget_to_add is None:
                        widget_to_add = QWidget()
                else:
                    widget_to_add = module_instance

                widget_idx = self.content_area.addWidget(widget_to_add)
                self.module_widgets[mod_id] = widget_idx
            except Exception as e:
                AppLogger.error("Main", f"Erreur de chargement du module {mod_id}: {e}")
                QMessageBox.warning(self, "Module", f"Impossible d'ouvrir le module: {title}")
                return

        self.refresh_module_data(mod_id)
        self.switch_module(widget_idx, active_button, title)

    def refresh_module_data(self, mod_id):
        module_instance = self.module_windows.get(mod_id)
        if not module_instance:
            return

        refresh_calls = [
            "refresh_all_data",
            "refresh_data",
            "load_filters",
            "load_classes",
            "load_students",
            "load_inventory",
            "load_logs",
            "load_users",
        ]

        for method_name in refresh_calls:
            method = getattr(module_instance, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception as e:
                    AppLogger.warning("Main", f"Refresh {mod_id}.{method_name} ignoré: {e}")

    def apply_rbac_to_quick_actions(self):
        """إخفاء الأزرار السريعة التي لا يملك المستخدم صلاحية عليها"""
        is_admin = "all" in self.allowed_modules

        if not is_admin and "student_management" not in self.allowed_modules:
            self.btn_qa_add_student.hide()

        if not is_admin and "finance_payments" not in self.allowed_modules:
            self.btn_qa_pay.hide()

        if not is_admin and "student_attendance" not in self.allowed_modules:
            self.btn_qa_att.hide()

        if not is_admin and "student_grades" not in self.allowed_modules:
            self.btn_qa_grades.hide()

    def trigger_module(self, mod_id):
        """تشغيل وحدة من خلال الأزرار السريعة (Quick Actions)"""
        if mod_id in self.nav_buttons:
            self.nav_buttons[mod_id].click()

    def _toggle_sidebar(self):
        """Toggle sidebar between expanded (260px) and compact icon-only (64px) modes."""
        self._sidebar_expanded = not self._sidebar_expanded
        if self._sidebar_expanded:
            self.sidebar.setFixedWidth(260)
            self.btn_toggle_sidebar.setText("❮")
            self.btn_toggle_sidebar.setToolTip("Réduire la barre latérale")
            self.app_title.setText("🏫 El Malick Gest")
            self.btn_dashboard.setText("🏠 Tableau de Bord / الرئيسية")
            for mod_id, btn in self.nav_buttons.items():
                icon = self._btn_icon_map.get(mod_id, "")
                # Restore full label from button's tooltip
                btn.setText(f" {icon}   {btn.toolTip()}")
                btn.setStyleSheet("")
                self.style_nav_button(btn)
            for lbl in self._cat_labels:
                lbl.setVisible(True)
            if hasattr(self, 'btn_logout'):
                self.btn_logout.setText("🚪 Déconnexion / خروج")
        else:
            self.sidebar.setFixedWidth(64)
            self.btn_toggle_sidebar.setText("❯")
            self.btn_toggle_sidebar.setToolTip("Agrandir la barre latérale")
            self.app_title.setText("🏫")
            self.btn_dashboard.setText("🏠")
            for mod_id, btn in self.nav_buttons.items():
                icon = self._btn_icon_map.get(mod_id, "•")
                btn.setText(icon)
                btn.setStyleSheet(
                    "QPushButton { text-align:center; padding:10px 0; font-size:20px; "
                    "border:none; border-radius:6px; background:transparent; color:#94A3B8; } "
                    "QPushButton:hover { background:#334155; color:white; } "
                    "QPushButton:checked { background:#3B82F6; color:white; }"
                )
            for lbl in self._cat_labels:
                lbl.setVisible(False)
            if hasattr(self, 'btn_logout'):
                self.btn_logout.setText("🚪")

    def switch_module(self, index, active_button, title="Tableau de Bord / اللوحة الرئيسية"):
        """التبديل الفوري بين الوحدات — بدون QGraphicsOpacityEffect لتجنّب تعارض الـ painters."""
        self.content_area.setCurrentIndex(index)
        self.lbl_module_title.setText(title)

        # تحديث حالة الأزرار في القائمة الجانبية
        self.btn_dashboard.setChecked(False)
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        active_button.setChecked(True)

        # إذا عدنا للوحة الرئيسية، قم بتحديث البيانات
        if index == self.dashboard_idx:
            self.load_dashboard_data()

    def _auto_refresh_dashboard(self):
        """تحديث تلقائي للـ KPI وبطاقات التنبيه كل 5 دقائق"""
        if self.content_area.currentIndex() == self.dashboard_idx:
            self.load_dashboard_data()
        else:
            # حتى لو الشاشة الأخرى مفتوحة — حدّث فقط التنبيهات بصمت
            self.load_alerts_data()

    def open_global_search(self):
        """فتح نافذة البحث العالمي (Ctrl+K)"""
        from global_search_dialog import GlobalSearchDialog

        if self._search_dlg is None:
            self._search_dlg = GlobalSearchDialog(parent=self)
            self._search_dlg.navigate_to.connect(self._on_search_navigate)
        self._search_dlg.show()
        self._search_dlg.raise_()
        self._search_dlg.activateWindow()

    def _refresh_current_module(self):
        """F5 — تحديث بيانات الوحدة الحالية المعروضة"""
        current_idx = self.content_area.currentIndex()
        if current_idx == self.dashboard_idx:
            self.load_dashboard_data()
            return
        # إيجاد mod_id المقابل للـ index الحالي
        for mod_id, idx in self.module_widgets.items():
            if idx == current_idx:
                self.refresh_module_data(mod_id)
                return

    def _go_to_dashboard(self):
        """Escape — العودة إلى لوحة التحكم الرئيسية"""
        self.switch_module(self.dashboard_idx, self.btn_dashboard)

    def _on_search_navigate(self, module_id: str, record_id: int):
        """التنقل إلى الوحدة المطلوبة عند اختيار نتيجة من البحث"""
        if module_id in self.nav_buttons:
            self.nav_buttons[module_id].click()
        else:
            AppLogger.warning("Main", f"Module '{module_id}' introuvable dans la nav")

    def logout(self):
        reply = QMessageBox.question(
            self,
            'Déconnexion',
            "Voulez-vous vraiment vous déconnecter ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            AppLogger.info("Main", f"Utilisateur déconnecté: {self.username}")
            self.close()
            # إعادة تشغيل نافذة تسجيل الدخول
            self.login_window = LoginWindow()
            if self.login_window.exec():
                self.new_main = MainWindow(self.login_window.txt_user.text(), self.login_window.user_role)
                self.new_main.show()

    def closeEvent(self, event):
        """تنظيف الموارد عند إغلاق البرنامج نهائياً"""
        if hasattr(self, 'backup_system'):
            self.backup_system.stop_auto_backup()
        DatabaseManager.close_pool()
        AppLogger.info("Main", "Fermeture de l'application.")
        event.accept()


def main():
    configure_qt_font_environment()

    # 1. إعداد النظام وقاعدة البيانات
    db = DatabaseManager()
    db.initialize_database()

    # 2. بدء التطبيق
    app = QApplication(sys.argv)
    icon_path = _resolve_app_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    # تحميل خط مخصص (اختياري لتحسين المظهر)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # 3. شاشة تسجيل الدخول
    # 2.5 معالج الإعداد الأول (يعمل فقط عند أول تشغيل أو عدم وجود إعدادات)
    try:
        from PyQt6.QtWidgets import QDialog

        from first_run_wizard import FirstRunWizard, should_run_wizard

        if should_run_wizard():
            wizard = FirstRunWizard()
            if wizard.exec() != QDialog.DialogCode.Accepted:
                # المستخدم أغلق المعالج دون إكمال الإعداد
                AppLogger.warning("Main", "Fermeture de l'assistant de configuration — arrêt de l'application")
                sys.exit(0)
    except Exception as _wiz_err:
        AppLogger.error("Main", f"Erreur lors du lancement de l'assistant: {_wiz_err}")

    # 3. شاشة تسجيل الدخول
    login = LoginWindow()
    if login.exec():
        user = login.txt_user.text()
        role = login.user_role

        try:
            # 4. الواجهة الرئيسية
            app.main_window = MainWindow(user, role)
            app.main_window.show()
            sys.exit(app.exec())
        except Exception as e:
            error_details = traceback.format_exc()
            AppLogger.error("Main", f"Crash au démarrage de la fenêtre principale: {e}\n{error_details}")
            QMessageBox.critical(
                None, "Erreur Critique", "Échec d'ouverture de l'interface principale. Consultez le fichier de logs."
            )


if __name__ == "__main__":
    main()
