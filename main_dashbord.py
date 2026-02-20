import sys
from datetime import datetime

from database_setup import DatabaseManager

# --- إصلاح Unicode على Windows ---
if sys.platform == 'win32':
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                             QFrame, QGridLayout, QScrollArea, QSizePolicy, QDialog,
                             QGraphicsDropShadowEffect, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QAction

# Import database path manager
from db_path import DB_PATH

# --- استيراد الأنظمة الجديدة ---
try:
    from config_manager import ConfigManager
    from auto_backup import AutoBackupSystem
    from app_logger import AppLogger
    from ui_styles import ThemeManager, rgba
    ENHANCED_FEATURES = True
except ImportError:
    ENHANCED_FEATURES = False
    print("⚠️ بعض الميزات المحسنة غير متوفرة")

# --- استيراد جميع الوحدات ---
from student_management import ModernStudentManagement as StudentManagementWindow
from student_attendance import StudentAttendanceWindow
from student_grades import StudentGradesWindow
from bulletin_generation import BulletinGenerationWindow
from finance_dashboard import ModernFinanceDashboard as FinanceDashboard
from finance_fees_setup import FeesSetupWindow as FinanceFeesSetupWindow
from finance_payments import StudentPaymentWindow as FinancePaymentsWindow
from finance_expenses import ExpensesWindow as FinanceExpensesWindow
from staff_management import ModernStaffManagement as StaffManagementWindow
from staff_attendance import StaffAttendanceWindow
from staff_leaves import StaffLeaveWindow as StaffLeaveWindow
from academic_settings import AcademicSettingsWindow
from user_management import UserManagementWindow
from communication_ui import CommunicationWindow
from inventory_management import InventoryWindow as InventoryManagementWindow
from student_discipline import DisciplineWindow as StudentDisciplineWindow
from year_end_migration import MigrationWindow as YearEndMigrationWindow
from system_maintenance import SystemMaintenanceWindow
from admin_documents import AdminDocsWindow
from advanced_reports import AdvancedReportsWindow

class MainDashboard(QMainWindow):
    def __init__(self, user_role="Admin"):
        super().__init__()
        self.user_role = user_role
        self.nav_buttons = []  # لتخزين الأزرار مع الفهارس
        self.setWindowTitle("El Malick Gestion Scolaire")
        self.setMinimumSize(1358, 760)

        # أيقونة التطبيق
        import os
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # التأكد من إنشاء جميع الجداول
        self.ensure_database_structure()
        
        # تهيئة الأنظمة المحسنة
        if ENHANCED_FEATURES:
            self.config = ConfigManager()
            self.backup_system = AutoBackupSystem(
                db_path=self.config.db_path,
                backup_dir=self.config.backup_dir
            )
            AppLogger.info("MainDashboard", "تم تحميل الأنظمة المحسنة بنجاح")
            
            # نسخة احتياطية عند البدء
            if self.config.get_bool('BACKUP', 'backup_on_startup', True):
                try:
                    AppLogger.info("MainDashboard", "إنشاء نسخة احتياطية عند البدء...")
                    self.backup_system.backup_on_startup()
                except Exception as e:
                    AppLogger.error("Startup", f"Startup Backup Failed: {e}")
            
            # بدء النسخ الاحتياطي التلقائي
            try:
                if self.config.auto_backup_enabled:
                    self.backup_system.start_auto_backup(
                        interval_hours=self.config.backup_interval_hours
                    )
            except Exception as e:
                AppLogger.error("Startup", f"Auto Backup Init Failed: {e}")
            
            # ضبط الثيم الحالي (سيتم تطبيقه بعد بناء الواجهة)
            ThemeManager.set_theme("dark" if self.config.dark_mode_enabled else "light")
            AppLogger.info("MainDashboard", f"تم تفعيل الوضع: {ThemeManager._current_theme}")
        
        self.init_ui()
        # تطبيق الثيم بعد بناء الواجهة لضمان تحديث جميع العناصر
        if ENHANCED_FEATURES:
            self.apply_theme_to_all_windows()
        self.ensure_indexes()

    def ensure_database_structure(self):
        """التأكد من وجود جميع الجداول باستخدام المدير المركزي"""
        try:
            # استخدام المدير المركزي
            from database_setup import DatabaseManager
            db_manager = DatabaseManager()
            db_manager.initialize_database()
            AppLogger.info("Database", "تم التحقق من هيكلة قاعدة البيانات بنجاح")
        except Exception as e:
            QMessageBox.critical(self, "خطأ قاعدة البيانات", f"فشل في تهيئة قاعدة البيانات:\n{str(e)}")
            AppLogger.error("Database", f"Critical DB Init Error: {e}")
            
            
    def init_ui(self):
        colors = ThemeManager.get_colors()
        sidebar_bg = colors.BG_HEADER
        sidebar_hover = colors.BORDER
        sidebar_text = colors.TEXT_SECONDARY
        sidebar_text_active = colors.HEADER_TEXT if hasattr(colors, "HEADER_TEXT") else colors.TEXT_PRIMARY
        sidebar_logo_bg = colors.BG_HEADER
        user_frame_bg = colors.BG_HEADER
        user_frame_border = colors.BORDER

        # الحاوية الرئيسية
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. القائمة الجانبية (Deep Slate Sidebar) ---
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setFixedWidth(260)
        sidebar_scroll.setWidgetResizable(True)
        # لون الخلفية للقائمة الجانبية (Slate 900 - داكن جداً)
        sidebar_scroll.setStyleSheet(f"background-color: {sidebar_bg}; border: none;")

        sidebar_content = QWidget()
        sidebar_content.setStyleSheet(f"""
            QWidget {{
                background-color: {sidebar_bg}; 
                color: {sidebar_text_active};
            }}
            QPushButton {{
                text-align: left;
                padding: 12px 20px;
                border: none;
                color: {sidebar_text};
                font-size: 14px;
                font-family: 'Segoe UI', 'Cairo';
                border-radius: 6px;
                margin: 2px 10px;
            }}
            QPushButton:hover {{
                background-color: {sidebar_hover};
                color: {sidebar_text_active};
                font-weight: bold;
            }}
            /* العناوين الفرعية في القائمة */
            QLabel {{
                color: {sidebar_text};
                font-weight: bold;
                font-size: 11px;
                padding: 15px 20px 5px 20px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        
        side_layout = QVBoxLayout(sidebar_content)
        side_layout.setContentsMargins(0, 0, 0, 20)
        side_layout.setSpacing(4)

        # الشعار
        lbl_logo = QLabel("🏫 SCHOOL MASTER")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet(f"""
            font-size: 20px; 
            color: {sidebar_text_active}; 
            padding: 30px 0; 
            background-color: {sidebar_logo_bg};
            font-weight: 900;
            border-bottom: 1px solid {user_frame_border};
        """)
        side_layout.addWidget(lbl_logo)

        # القوائم
        self.nav_buttons = []

        self.add_nav_btn(side_layout, "🏠 Tableau de Bord / الرئيسية", 0)
        
        side_layout.addWidget(QLabel("SCOLARITÉ / الشؤون المدرسية"))
        self.add_nav_btn(side_layout, "👨‍🎓 Élèves / الطلاب", 1)
        self.add_nav_btn(side_layout, "📅 Assiduité / الغياب", 2)
        self.add_nav_btn(side_layout, "⚖️ Discipline / الانضباط", 3)
        self.add_nav_btn(side_layout, "🗂️ Documents & Cartes / وثائق", 4)
        
        side_layout.addWidget(QLabel("PÉDAGOGIE / البيداغوجيا"))
        self.add_nav_btn(side_layout, "📝 Notes / العلامات", 5)
        self.add_nav_btn(side_layout, "🖨️ Bulletins / الكشوف", 6)
        
        side_layout.addWidget(QLabel("FINANCES / المالية"))
        self.add_nav_btn(side_layout, "💰 Tableau Financier / الملخص", 7)
        self.add_nav_btn(side_layout, "⚙️ Configuration des Frais / إعداد الرسوم", 8)
        self.add_nav_btn(side_layout, "💸 Paiements / المدفوعات", 9)
        self.add_nav_btn(side_layout, "📉 Dépenses / المصاريف", 10)
        self.add_nav_btn(side_layout, "📦 Stock & Inventaire / المخزون", 11)
        self.add_nav_btn(side_layout, "📊 Rapports Avancés / التقارير المتقدمة", 20)
        
        side_layout.addWidget(QLabel("ADMINISTRATION / الإدارة"))
        self.add_nav_btn(side_layout, "👥 Staff / الموظفون", 12)
        self.add_nav_btn(side_layout, "⏰ Pointage / حضور الموظفين", 13)
        self.add_nav_btn(side_layout, "🏖️ Gestion des Congés / إدارة الإجازات", 14)
        self.add_nav_btn(side_layout, "📧 Communication / التراسل", 15)
        self.add_nav_btn(side_layout, "⚙️ Paramètres / الإعدادات", 16)
        self.add_nav_btn(side_layout, "🔄 Clôture Année / إغلاق", 17)
        self.add_nav_btn(side_layout, "🔐 Utilisateurs / المستخدمين", 18)
        self.add_nav_btn(side_layout, "🛡️ Maintenance / الصيانة", 19)

        side_layout.addStretch()
        
        # معلومات المستخدم
        user_frame = QFrame()
        user_frame.setStyleSheet(f"""
            background-color: {user_frame_bg}; 
            border-top: 1px solid {user_frame_border}; 
            margin-top: 10px;
        """)
        user_layout = QHBoxLayout(user_frame)
        lbl_user_icon = QLabel("👤")
        lbl_user_icon.setStyleSheet(f"color: {sidebar_text_active};")
        
        lbl_user_info = QLabel(f"{self.user_role} User")
        lbl_user_info.setStyleSheet(f"background: transparent; color: {sidebar_text_active};")
        
        user_layout.addWidget(lbl_user_icon)
        user_layout.addWidget(lbl_user_info)
        user_layout.addStretch()
        
        # زر تبديل Dark Mode
        self.btn_dark_mode = QPushButton("🌙" if ThemeManager._current_theme != "dark" else "☀️")
        self.btn_dark_mode.setMinimumHeight(32)
        self.btn_dark_mode.setToolTip("تبديل الوضع الداكن / Dark Mode")
        self.btn_dark_mode.setStyleSheet(f"""
            QPushButton {{
                background: {colors.BG_CARD};
                color: {colors.TEXT_PRIMARY};
                border-radius: 6px;
                padding: 0;
                font-size: 16px;
                border: 1px solid {colors.BORDER};
            }}
            QPushButton:hover {{
                background-color: {colors.BORDER};
            }}
        """)
        self.btn_dark_mode.clicked.connect(self.toggle_dark_mode)
        user_layout.addWidget(self.btn_dark_mode)
        
        # زر خروج
        btn_logout = QPushButton("🚪")
        btn_logout.setMinimumHeight(32)
        btn_logout.setToolTip("Déconnexion")
        btn_logout.setStyleSheet(f"""
            QPushButton {{
                background: {colors.BG_CARD};
                color: {colors.TEXT_PRIMARY};
                border-radius: 6px;
                padding: 0;
                border: 1px solid {colors.BORDER};
            }}
            QPushButton:hover {{
                background-color: {colors.DANGER};
                color: white;
            }}
        """)
        btn_logout.clicked.connect(self.close)
        user_layout.addWidget(btn_logout)

        side_layout.addWidget(user_frame)

        sidebar_scroll.setWidget(sidebar_content)
        main_layout.addWidget(sidebar_scroll)

        # --- 2. منطقة العمل (Content Area) ---
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(2, 2, 2, 2)
        
        # الترويسة العلوية (Header)
        header_layout = QHBoxLayout()
        lbl_page_title = QLabel(f"     Bienvenue, {self.user_role}")
        lbl_page_title.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {colors.TEXT_PRIMARY};")
        
        lbl_date = QLabel(datetime.now().strftime('%d %B %Y     '))
        lbl_date.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 14px; font-weight: 600;")
        
        header_layout.addWidget(lbl_page_title)
        header_layout.addStretch()
        header_layout.addWidget(lbl_date)
        
        content_layout.addLayout(header_layout)
        content_layout.addSpacing(15)

        # Stacked Widget
        self.stack = QStackedWidget()
        
        # الصفحة 0: اللوحة الرئيسية
        self.home_page = self.create_home_dashboard()
        self.stack.addWidget(self.home_page)

        # تحميل جميع الشاشات (20 شاشة)
        # تحميل جميع الشاشات (20 شاشة) مع معالجة الأخطاء لمنع توقف البرنامج
        page_constructors = [
            StudentManagementWindow, #1
            StudentAttendanceWindow, #2
            StudentDisciplineWindow, #3
            AdminDocsWindow, #4
            StudentGradesWindow, #5
            BulletinGenerationWindow, #6
            FinanceDashboard, #7
            FinanceFeesSetupWindow, #8
            FinancePaymentsWindow, #9
            FinanceExpensesWindow, #10
            InventoryManagementWindow, #11
            StaffManagementWindow, #12
            StaffAttendanceWindow, #13
            StaffLeaveWindow, #14
            CommunicationWindow, #15
            AcademicSettingsWindow, #16
            YearEndMigrationWindow, #17
            UserManagementWindow, #18
            SystemMaintenanceWindow, #19
            AdvancedReportsWindow #20
        ]

        for i, PageClass in enumerate(page_constructors):
            try:
                page_instance = PageClass()
                self.stack.addWidget(page_instance)
            except Exception as e:
                error_msg = f"Failed to load module {i+1} ({PageClass.__name__}):\n{str(e)}"
                print(error_msg)
                try:
                    AppLogger.error("Startup", error_msg)
                except:
                    pass
                
                # Show error placeholder widget so user knows what happened
                err_widget = QLabel(f"⚠️ {error_msg}")
                err_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                err_widget.setStyleSheet(
                    f"color: {colors.DANGER}; font-size: 14px; background: {colors.BG_CARD}; border: 1px solid {colors.DANGER};"
                )
                self.stack.addWidget(err_widget)

        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_area)
        
        # تطبيق الصلاحيات
        self.apply_permissions()

    def add_nav_btn(self, layout, text, index):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn.clicked.connect(lambda: self.stack.setCurrentIndex(index))
        layout.addWidget(btn)
        self.nav_buttons.append((index, btn))

    def apply_permissions(self):
        """تطبيق نظام الصلاحيات على الأزرار"""
        if self.user_role == "Admin":
            return

        if self.user_role == "Comptable":
            # المحاسب يرى: المالية كاملة + المخزون + التقارير المتقدمة
            # يخفي: بيداغوجيا، موظفين، إعدادات، صيانة، المستخدمين، انضباط، وثائق، الحضور، الطلاب
            hidden_indices = [7, 8, 9, 10, 11]
            for idx, btn in self.nav_buttons:
                if idx in hidden_indices: 
                    btn.setVisible(False)

        elif self.user_role == "Prof":
            # الأستاذ يرى: بيداغوجيا + طلاب + الحضور 
            # يخفي: مالية، مخزون، موظفين، إعدادات، صيانة
            hidden_indices = [2, 5]
            for idx, btn in self.nav_buttons:
                if idx in hidden_indices:
                    btn.setVisible(False)
        
        elif self.user_role == "Pédagogique":
            # البيداغوجي يرى: بيداغوجيا + طلاب + وثائق + انضباط
            # يخفي: مالية، مخزون، موظفين، إعدادات، صيانة
            hidden_indices = [2, 3, 5, 6]
            for idx, btn in self.nav_buttons:
                if idx in hidden_indices:
                    btn.setVisible(False)
        
        elif self.user_role == "Secretaire":
            # السكرتير يرى: الطلاب، الحضور، الوثائق، الموظفين، التراسل
            # يخفي: الدرجات، الكشوف، المالية، الصيانة، الإعدادات
            hidden_indices = [1, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            for idx, btn in self.nav_buttons:
                if idx in hidden_indices:
                    btn.setVisible(False)

    def create_home_dashboard(self):
        colors = ThemeManager.get_colors()
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(25)
        
        try:
            db_manager = DatabaseManager()
            with db_manager.get_connection() as conn:
                # تنبيه المخزون المنخفض (فقط للمدير والمحاسب)
                if self.user_role in ["Admin", "Comptable"]:
                    try:
                        low_stock = self.get_low_stock_items(conn)
                        if low_stock > 0:
                            alert_frame = QFrame()
                            alert_frame.setStyleSheet(f"""
                                QFrame {{
                                    background-color: {colors.BG_CARD};
                                    border-left: 4px solid {colors.WARNING};
                                    border-radius: 8px;
                                    padding: 12px;
                                }}
                            """)
                            
                            alert_layout = QHBoxLayout(alert_frame)
                            alert_layout.setContentsMargins(15, 10, 15, 10)
                            
                            icon_lbl = QLabel("⚠️")
                            icon_lbl.setStyleSheet("font-size: 24px;")
                            
                            text_lbl = QLabel(f"<b>{low_stock} article(s)</b> en stock faible! / <b>مواد منخفضة</b>")
                            text_lbl.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
                            
                            btn_view = QPushButton("📦 Voir Stock")
                            btn_view.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: {colors.WARNING};
                                    color: white;
                                    padding: 8px 16px;
                                    border-radius: 6px;
                                    font-weight: bold;
                                    border: none;
                                }}
                                QPushButton:hover {{
                                    background-color: {colors.WARNING};
                                }}
                            """)
                            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
                            btn_view.clicked.connect(lambda: self.stack.setCurrentIndex(11))  # Index du stock
                            
                            alert_layout.addWidget(icon_lbl)
                            alert_layout.addWidget(text_lbl)
                            alert_layout.addStretch()
                            alert_layout.addWidget(btn_view)
                            
                            layout.addWidget(alert_frame)
                    except Exception as e:
                        print(f"Error checking stock: {e}")

                grid = QGridLayout()
                grid.setSpacing(25)

                # 1. بطاقة الطلاب
                try:
                    card_students = self.create_summary_card("Étudiants / الطلاب", self.get_student_count(conn), "Inscrits actifs", colors.PRIMARY, "👨‍🎓") # Blue Accent
                    grid.addWidget(card_students, 0, 0)
                except Exception as e:
                    print(f"Error creating student card: {e}")
                    grid.addWidget(QLabel("Error loading student card"), 0, 0)

                # 2. بطاقة الموظفين
                try:
                    card_staff = self.create_summary_card("Personnel / الموظفون", self.get_staff_count(conn), "Enseignants & Admin", colors.WARNING, "👥") # Amber Accent
                    grid.addWidget(card_staff, 0, 1)
                except Exception as e:
                    print(f"Error creating staff card: {e}")
                    grid.addWidget(QLabel("Error loading staff card"), 0, 1)

                # 3. بطاقة الحضور
                try:
                    card_attendance = self.create_summary_card("Présence / الحضور", self.get_attendance_count(conn), "Aujourd'hui", colors.SUCCESS, "✅") # Emerald Accent
                    grid.addWidget(card_attendance, 0, 2)
                except Exception as e:
                    print(f"Error creating attendance card: {e}")
                    grid.addWidget(QLabel("Error loading attendance card"), 0, 2)

                # البطاقات المالية (للمدير والمحاسب فقط)
                if self.user_role in ["Admin", "Comptable"]:
                    try:
                        total_income = self.get_total_income(conn)
                        card_income = self.create_summary_card("Total Recettes / الإيرادات", f"{total_income:,.0f} FCFA", "Cumul Total", colors.SUCCESS, "💰")
                        grid.addWidget(card_income, 1, 0)
                        
                        total_expenses = self.get_total_expenses(conn)
                        card_expenses = self.create_summary_card("Total Dépenses / المصاريف", f"{total_expenses:,.0f} FCFA", "Cumul Total", colors.DANGER, "📉")
                        grid.addWidget(card_expenses, 1, 1)

                        total_balance = total_income - total_expenses
                        color = colors.SUCCESS if total_balance >= 0 else colors.DANGER
                        # أيقونة الميزان
                        card_balance = self.create_summary_card("Solde Global / الرصيد العام", f"{total_balance:,.0f} FCFA", "Net Total", color, "⚖️")
                        grid.addWidget(card_balance, 1, 2)
                    except Exception as e:
                        print(f"Error loading finance data: {e}")

                layout.addLayout(grid)
                layout.addStretch()
                
        except Exception as e:
            error_label = QLabel(f"Critical Dashboard Error: {str(e)}")
            error_label.setStyleSheet(f"color: {colors.DANGER}; font-size: 16px; padding: 20px;")
            layout.addWidget(error_label)
            AppLogger.error("Dashboard", f"Home Dashboard Creation Failed: {e}")

        return page

    def create_summary_card(self, title, value, subtitle, color, icon):
        colors = ThemeManager.get_colors()
        frame = QFrame()
        # تصميم البطاقة بنمط Deep Slate: حدود رمادية فاتحة، خلفية بيضاء نقية
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors.BG_CARD}; 
                border-radius: 12px; 
                border: 1px solid {colors.BORDER};
            }}
        """)
        frame.setMinimumHeight(150)
        
        # ظل أنيق وناعم
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(15, 23, 42, 20)) # Slate Dark Shadow
        shadow.setOffset(0, 4)
        frame.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(25, 25, 25, 25)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 14px; font-weight: 700; text-transform: uppercase;")
        
        lbl_value = QLabel(str(value))
        lbl_value.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-size: 28px; font-weight: 800;")
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_value)
        text_layout.addWidget(lbl_sub)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # الأيقونة (دائرة ملونة)
        icon_cont = QLabel(icon)
        icon_cont.setFixedSize(54, 54)
        icon_cont.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # خلفية الأيقونة شفافة قليلاً
        icon_cont.setStyleSheet(f"""
            background-color: {rgba(color, 21)}; 
            color: {color};
            font-size: 26px;
            border-radius: 27px;
        """)
        layout.addWidget(icon_cont)
        
        return frame

    # --- Helper Functions (Database) ---
    def get_student_count(self, conn=None):
        return self._safe_db_query("SELECT COUNT(*) FROM Students WHERE status='Active'", conn=conn)

    def get_staff_count(self, conn=None):
        return self._safe_db_query("SELECT COUNT(*) FROM Staff WHERE status='Actif'", conn=conn)

    def get_attendance_count(self, conn=None):
        today = datetime.now().strftime("%Y-%m-%d")
        return self._safe_db_query("SELECT COUNT(*) FROM StudentAttendance WHERE date=? AND status='Présent'", (today,), conn=conn)

    def get_total_income(self, conn=None):
        val = self._safe_db_query("SELECT SUM(amount_paid) FROM Payments", conn=conn)
        return float(val) if val != "0" and val is not None else 0.0

    def get_total_expenses(self, conn=None):
        val = self._safe_db_query("SELECT SUM(amount) FROM Expenses", conn=conn)
        return float(val) if val != "0" and val is not None else 0.0
    
    def get_low_stock_items(self, conn=None):
        """عدد الأصناف التي كميتها أقل من أو تساوي الحد الأدنى"""
        val = self._safe_db_query("SELECT COUNT(*) FROM InventoryItems WHERE quantity <= min_quantity", conn=conn)
        try:
            return int(val) if val is not None else 0
        except (TypeError, ValueError):
            return 0

    def _safe_db_query(self, query, params=(), conn=None):
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                result = cur.fetchone()
                return result[0] if result and result[0] is not None else "0"
            except Exception:
                return "0"
        else:
            try:
                with DatabaseManager() as db:
                    conn = db.get_connection()
                    cur = conn.cursor()
                    cur.execute(query, params)
                    result = cur.fetchone()
                    return result[0] if result and result[0] is not None else "0"
            except Exception:
                return "0"

    def ensure_indexes(self):
        """إنشاء الفهارس الأساسية لتحسين الأداء (آمن عند غياب الجداول)."""
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            index_statements = [
                "CREATE INDEX IF NOT EXISTS idx_students_status ON Students(status)",
                "CREATE INDEX IF NOT EXISTS idx_students_class ON Students(class_id)",
                "CREATE INDEX IF NOT EXISTS idx_attendance_date_status ON StudentAttendance(date, status)",
                "CREATE INDEX IF NOT EXISTS idx_attendance_student_date ON StudentAttendance(student_id, date)",
                "CREATE INDEX IF NOT EXISTS idx_payments_student ON Payments(student_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_date ON Payments(transaction_date)",
                "CREATE INDEX IF NOT EXISTS idx_expenses_date ON Expenses(expense_date)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_item ON InventoryLog(item_id)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_date ON InventoryLog(transaction_date)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_low ON InventoryItems(quantity, min_quantity)",
                "CREATE INDEX IF NOT EXISTS idx_grades_student_subject ON Grades(student_id, subject_id)",
                "CREATE INDEX IF NOT EXISTS idx_grades_assessment ON Grades(assessment_id)",
                "CREATE INDEX IF NOT EXISTS idx_assessments_period ON AssessmentTypes(period_id)",
                "CREATE INDEX IF NOT EXISTS idx_periods_cycle_year ON AcademicPeriods(cycle_id, year_id)",
                "CREATE INDEX IF NOT EXISTS idx_staff_attendance_staff_date ON StaffAttendance(staff_id, attendance_date)",
                "CREATE INDEX IF NOT EXISTS idx_staff_attendance_date ON StaffAttendance(attendance_date)",
                "CREATE INDEX IF NOT EXISTS idx_discipline_student_date ON StudentDiscipline(student_id, incident_date)",
                "CREATE INDEX IF NOT EXISTS idx_salary_slips_staff_month ON SalarySlips(staff_id, month_str)",
                "CREATE INDEX IF NOT EXISTS idx_auditlogs_timestamp ON AuditLogs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_notifications_sent ON NotificationLogs(sent_at)",
            ]
            for stmt in index_statements:
                try:
                    cursor.execute(stmt)
                except Exception:
                    continue
            conn.commit()
    
    def toggle_dark_mode(self):
        """تبديل الوضع الداكن"""
        is_dark = (ThemeManager._current_theme == "dark")
        new_theme = "light" if is_dark else "dark"
        
        # تحديث ThemeManager
        ThemeManager.apply_theme(QApplication.instance(), new_theme)
        
        # حفظ الإعداد في config.ini
        if ENHANCED_FEATURES:
            self.config.set('UI', 'enable_dark_mode', str(not is_dark))
            AppLogger.info("MainDashboard", f"تم تغيير المظهر إلى: {new_theme}")
        
        # تحديث رمز الزر
        self.btn_dark_mode.setText("☀️" if new_theme == "dark" else "🌙")
        
        # تطبيق المظهر على جميع النوافذ المفتوحة
        self.apply_theme_to_all_windows()
    
    def apply_theme_to_all_windows(self):
        """تطبيق المظهر على جميع النوافذ"""
        # تطبيق على النافذة الرئيسية والتطبيق
        ThemeManager.apply_theme(QApplication.instance(), ThemeManager._current_theme)


def excepthook(type, value, traceback):
    error_msg = f"Critical Error: {value}"
    print(error_msg)
    try:
        from app_logger import AppLogger
        AppLogger.error("System", f"Uncaught Exception: {value}")
    except:
        pass
    
    QMessageBox.critical(None, "Application Crash", 
                         f"An unexpected error occurred:\n{value}\n\nThe application will close.")
    sys.exit(1)

if __name__ == "__main__":
    sys.excepthook = excepthook
    app = QApplication(sys.argv)
    
    # 1. Initialize Database Structure First
    try:
        from database_setup import DatabaseManager
        db_mgr = DatabaseManager()
        db_mgr.initialize_database()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database Initialization Failed: {e}")
        # MessageBox could be shown here if critical, but proceed to try login
    
    try:
        from login_window import LoginWindow
        has_login = True
    except ImportError:
        has_login = False
        print("LoginWindow file not found, running Dashboard directly.")

    if has_login:
        try:
            login = LoginWindow()
            if login.exec():
                try:
                    main_win = MainDashboard(user_role=login.user_role)
                    main_win.show()
                    sys.exit(app.exec())
                except Exception as e:
                    QMessageBox.critical(None, "Dashboard Error", f"Failed to start dashboard:\n{str(e)}")
                    print(f"Dashboard init failed: {e}")
            else:
                sys.exit(0)
        except Exception as e:
            QMessageBox.critical(None, "Login Error", f"Failed to start login window:\n{str(e)}")
            print(f"Login window failed: {e}")
            
    else:
        main_win = MainDashboard(user_role="Admin")
        main_win.show()
        sys.exit(app.exec())