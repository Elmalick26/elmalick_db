import os
import sys
from datetime import datetime

import psycopg2  # تغيير المكتبة
from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import security_utils
from app_logger import AppLogger
from database_setup import DatabaseManager, log_audit
from pdf_helpers import ARABIC_SUPPORT
from pdf_helpers import find_arabic_font_path as _get_arabic_font_path
from pdf_helpers import prepare_pdf_text as _prepare_pdf_text
from pdf_helpers import setup_pdf_arabic_font
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    get_school_info_row,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.user_repo import UserRepository
from ui_components import (
    BaseDialog,
    card_frame,
    dialog_button_row,
    dialog_error_label,
    style_table,
    styled_button,
    styled_combo,
    styled_input,
)
from ui_styles import Colors, ModuleHeaderWidget, ThemeManager, get_module_caps, get_table_style, get_tabs_style

USER_AUDIT_REPORT_OUTPUT_MODE = get_report_output_mode("user_audit_report_mode", "save")


class UserDialog(BaseDialog):
    """Dialog for adding/editing users"""

    def __init__(self, staff_list=None, data=None, parent=None):
        super().__init__("Éditer Utilisateur" if data else "Ajouter Utilisateur", parent)
        self.staff_list = staff_list or []
        self.data = data
        self.setMinimumWidth(500)
        self.setModal(True)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        form = QFormLayout()
        form.setSpacing(12)

        self.cmb_staff = styled_combo()
        self.cmb_staff.addItem("Lier à un employé...", None)
        for staff_id, staff_name in self.staff_list:
            self.cmb_staff.addItem(staff_name, staff_id)
        form.addRow("Employé:", self.cmb_staff)

        self.cmb_role = styled_combo()
        self.cmb_role.addItems(["Admin", "Comptable", "Prof", "Secretaire", "Pédagogique"])
        form.addRow("Rôle:", self.cmb_role)

        self.txt_username = styled_input("Nom d'utilisateur")
        form.addRow("Utilisateur:", self.txt_username)

        self.txt_email = styled_input("Email")
        form.addRow("Email:", self.txt_email)

        self.txt_password = styled_input("Mot de passe")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mot de passe:", self.txt_password)

        if data:
            self.cmb_staff.setCurrentIndex(self.cmb_staff.findData(data.get("staff_id")))
            self.cmb_role.setCurrentText(data.get("role", "Prof"))
            self.txt_username.setText(data.get("username", ""))
            self.txt_email.setText(data.get("email", ""))
            if data.get("password"):
                self.txt_password.setText(data.get("password", ""))

        self.dialog_layout.addLayout(form)
        self.dialog_layout.addLayout(dialog_button_row("Valider" if data else "Créer", self.accept, self.reject))

    def get_values(self):
        return {
            "staff_id": self.cmb_staff.currentData(),
            "role": self.cmb_role.currentText(),
            "username": self.txt_username.text().strip(),
            "email": self.txt_email.text().strip(),
            "password": self.txt_password.text().strip(),
        }

    def _validate(self):
        vals = self.get_values()
        if not vals["username"]:
            self._err_lbl.setText("Le nom d'utilisateur est requis.")
            self._err_lbl.setVisible(True)
            return False
        if not vals["password"]:
            self._err_lbl.setText("Le mot de passe est requis.")
            self._err_lbl.setVisible(True)
            return False
        self._err_lbl.setVisible(False)
        return True

    def accept(self):
        if self._validate():
            super().accept()


class UserEditDialog(BaseDialog):
    """Dialog for editing user password and deleting account"""

    def __init__(self, user_data, parent=None):
        super().__init__(f"Gérer: {user_data.get('username', 'N/A')}", parent)
        self.user_data = user_data
        self.setMinimumWidth(450)
        self.setModal(True)
        colors = ThemeManager.get_colors()

        info_lbl = QLabel(f"Utilisateur: {user_data.get('username')} | Email: {user_data.get('email')}")
        info_lbl.setStyleSheet(f"font-weight: 600; color: {colors.TEXT_PRIMARY};")
        self.dialog_layout.addWidget(info_lbl)

        # Password reset section
        pwd_lbl = QLabel("Réinitialiser le mot de passe:")
        pwd_lbl.setStyleSheet(f"font-weight: 600; color: {colors.TEXT_SECONDARY};")
        self.dialog_layout.addWidget(pwd_lbl)

        self._pwd_err = dialog_error_label()
        self.dialog_layout.addWidget(self._pwd_err)

        self.txt_new_password = styled_input("Nouveau mot de passe")
        self.txt_new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.dialog_layout.addWidget(self.txt_new_password)

        btn_reset = styled_button("💾 Valider Mot de Passe", min_height=38)
        btn_reset.clicked.connect(self.on_reset_password)
        self.dialog_layout.addWidget(btn_reset)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {colors.BORDER};")
        sep.setFixedHeight(1)
        self.dialog_layout.addWidget(sep)

        del_lbl = QLabel("Zone Danger: Supprimer ce compte")
        del_lbl.setStyleSheet(f"font-weight: 600; color: {colors.DANGER};")
        self.dialog_layout.addWidget(del_lbl)

        btn_delete = styled_button(
            "🗑️ Supprimer Définitivement", bg_color=colors.DANGER, hover_color=colors.DANGER_HOVER, min_height=38
        )
        btn_delete.clicked.connect(self.on_delete_account)
        self.dialog_layout.addWidget(btn_delete)

        self.dialog_layout.addStretch()

        close_row = QHBoxLayout()
        close_row.addStretch()
        colors2 = ThemeManager.get_colors()
        btn_close = QPushButton("Fermer")
        btn_close.setMinimumHeight(36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1.5px solid {colors2.BORDER};"
            f" color:{colors2.TEXT_SECONDARY}; font-weight:700; border-radius:8px; padding:6px 18px; }}"
            f"QPushButton:hover {{ background:{colors2.BG_MAIN}; color:{colors2.TEXT_PRIMARY}; }}"
        )
        btn_close.clicked.connect(self.reject)
        close_row.addWidget(btn_close)
        self.dialog_layout.addLayout(close_row)

        self.password_changed = False
        self.account_deleted = False

    def on_reset_password(self):
        new_pass = self.txt_new_password.text().strip()
        if not new_pass:
            self._pwd_err.setText("Veuillez entrer un nouveau mot de passe.")
            self._pwd_err.setVisible(True)
            return
        self._pwd_err.setVisible(False)
        reply = QMessageBox.question(
            self, "Confirmation", f"Êtes-vous sûr de vouloir changer le mot de passe de {self.user_data['username']} ?"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.user_data["new_password"] = new_pass
        self.password_changed = True
        QMessageBox.information(self, "Succès", "Mot de passe mis à jour.")
        self.txt_new_password.clear()

    def on_delete_account(self):
        reply = QMessageBox.warning(
            self,
            "Confirmation Définitive",
            f"⚠️ Êtes-vous ABSOLUMENT sûr de vouloir supprimer {self.user_data['username']} ?\n\nCette action est IRRÉVERSIBLE.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.account_deleted = True
            self.accept()


class UserManagementWindow(QMainWindow):
    def __init__(self, current_user="Admin"):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Gestion des Utilisateurs / إدارة المستخدمين")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر
        ThemeManager.apply_theme(self)
        self.selected_user_id = None
        self.selected_username = ""
        self.current_audit_report_rows = []
        self.current_audit_report_headers = ["Date/Heure", "Acteur", "Action", "Cible"]
        self.current_audit_report_title = "Rapport Journal d'Audit"
        self.current_audit_period_label = "30 derniers jours"

        self.staff_list_cache = []
        self.ensure_admin_exists()
        self.init_ui()
        self.load_users()
        self.load_audit_logs()
        self._load_kpi_stats()

    def ensure_admin_exists(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = UserRepository(conn)
                if repo.count_users() == 0:
                    default_pass = security_utils.hash_password("admin")
                    repo.create_user("admin", "admin@school.local", default_pass, "Admin")
                    log_audit(conn, "System", "Auto-Create", "admin")
                    conn.commit()
        except Exception as e:
            AppLogger.error("UserManagement", f"Error ensuring admin exists: {e}")

    def log_action(self, action, target):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                log_audit(conn, self.current_user, action, target)
                conn.commit()
            self.load_audit_logs()
        except Exception as e:
            AppLogger.error("UserManagement", f"Audit Error: {e}")

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "user_management")
        if hasattr(self, "btn_add"):
            self.btn_add.setEnabled(caps["can_write"])
            self.btn_add.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. En-tête unifié
        header = ModuleHeaderWidget(
            icon="🔐",
            title="GESTION DES UTILISATEURS",
            subtitle="إدارة الصلاحيات، الحسابات، وسجل العمليات",
        )
        self.main_layout.addWidget(header)
        self._stat_users = header.add_stat("👥", "Utilisateurs", "—", "#3B82F6")
        self._stat_active = header.add_stat("✅", "Actifs", "—", "#22C55E")
        self._stat_admins = header.add_stat("🔑", "Admins", "—", "#8B5CF6")
        self._stat_audit = header.add_stat("📝", "Logs Audit", "—", "#F59E0B")

        # 2. KPI Cards

        # 3. Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_users_tab()
        self.setup_audit_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        return card_frame()

    def styled_input(self, placeholder):
        return styled_input(placeholder)

    def styled_combo(self):
        return styled_combo()

    def style_table(self, table):
        style_table(table)

    def _load_kpi_stats(self):
        """Charge les statistiques des utilisateurs."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Total utilisateurs
                cursor.execute("SELECT COUNT(*) FROM Users")
                total = cursor.fetchone()[0] or 0
                # Actifs
                cursor.execute("SELECT COUNT(*) FROM Users WHERE is_active = TRUE")
                active = cursor.fetchone()[0] or 0
                # Admins
                cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'Admin'")
                admins = cursor.fetchone()[0] or 0
                # Logs audit (30 derniers jours)
                cursor.execute("SELECT COUNT(*) FROM AuditLogs WHERE timestamp >= NOW() - INTERVAL '30 days'")
                audit_count = cursor.fetchone()[0] or 0

            self._stat_users.set_value(str(total))
            self._stat_active.set_value(str(active))
            self._stat_admins.set_value(str(admins))
            self._stat_audit.set_value(str(audit_count))
        except Exception as e:
            AppLogger.error("UserManagementWindow", f"Erreur KPI stats: {e}")

    def setup_users_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        colors = ThemeManager.get_colors()

        # Toolbar: Title + Add button
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(12)

        lbl_title = QLabel("👥 Utilisateurs / المستخدمون")
        lbl_title.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {colors.TEXT_PRIMARY};")
        toolbar.addWidget(lbl_title)
        toolbar.addStretch()

        self.btn_add = QPushButton("➕ Ajouter Utilisateur")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setMinimumHeight(38)
        self.btn_add.setMaximumWidth(200)
        self.btn_add.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS} stop:1 #16A34A); color: white; font-weight: 700; padding: 8px 16px; border-radius: 8px; border: none; }} QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }} QPushButton:disabled {{ background:{colors.BORDER}; color:{colors.TEXT_SECONDARY}; }}"
        )
        self.btn_add.clicked.connect(lambda: self.open_user_dialog())
        toolbar.addWidget(self.btn_add)
        layout.addLayout(toolbar)

        # Users Table with Action column
        self.table = QTableWidget()
        self.style_table(self.table)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "👤 Employé", "📝 Utilisateur", "📧 Email", "🔐 Rôle", "⚙️ Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Employé
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Utilisateur
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Email
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Rôle
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Action
        self.table.horizontalHeader().resizeSection(5, 110)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.tabs.addTab(tab, "  👥 Utilisateurs  ")
        self.load_users()

    def setup_audit_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        filter_card = self.create_card()
        flay = QHBoxLayout(filter_card)
        flay.setContentsMargins(10, 10, 10, 10)

        self.txt_audit_search = self.styled_input("🔍 Rechercher dans l'historique (Nom, Action, Date)...")
        self.txt_audit_search.textChanged.connect(self.load_audit_logs)
        flay.addWidget(self.txt_audit_search)

        self.combo_audit_period = self.styled_combo()
        self.combo_audit_period.addItems(
            ["7 derniers jours", "30 derniers jours", "90 derniers jours", "Période personnalisée", "Tout"]
        )
        self.combo_audit_period.setCurrentText("30 derniers jours")
        self.combo_audit_period.currentIndexChanged.connect(self.on_audit_period_changed)
        flay.addWidget(self.combo_audit_period)

        self.date_audit_from = QDateEdit()
        self.date_audit_from.setCalendarPopup(True)
        self.date_audit_from.setDisplayFormat("yyyy-MM-dd")
        self.date_audit_from.setDate(QDate.currentDate().addDays(-29))
        self.date_audit_from.setEnabled(False)
        self.date_audit_from.dateChanged.connect(self.load_audit_logs)
        colors = ThemeManager.get_colors()
        self.date_audit_from.setStyleSheet(
            f"QDateEdit {{ padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
        )
        flay.addWidget(self.date_audit_from)

        self.date_audit_to = QDateEdit()
        self.date_audit_to.setCalendarPopup(True)
        self.date_audit_to.setDisplayFormat("yyyy-MM-dd")
        self.date_audit_to.setDate(QDate.currentDate())
        self.date_audit_to.setEnabled(False)
        self.date_audit_to.dateChanged.connect(self.load_audit_logs)
        self.date_audit_to.setStyleSheet(
            f"QDateEdit {{ padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
        )
        flay.addWidget(self.date_audit_to)

        self.combo_audit_limit = self.styled_combo()
        self.combo_audit_limit.addItems(["100", "300", "500", "1000"])
        self.combo_audit_limit.setCurrentText("300")
        self.combo_audit_limit.currentIndexChanged.connect(self.load_audit_logs)
        flay.addWidget(self.combo_audit_limit)

        btn_export_audit = QPushButton("📄 Exporter Rapport PDF")
        btn_export_audit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_audit.setMinimumHeight(42)
        btn_export_audit.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.PRIMARY} stop:1 {colors.PRIMARY_HOVER}); color: white; font-weight: bold; padding: 8px 14px; border-radius: 8px; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_export_audit.clicked.connect(self.export_audit_report_pdf)
        flay.addWidget(btn_export_audit)

        layout.addWidget(filter_card)

        self.table_audit = QTableWidget()
        self.style_table(self.table_audit)
        self.table_audit.setColumnCount(4)
        self.table_audit.setHorizontalHeaderLabels(["Date/Heure", "Acteur (من)", "Action (ماذا)", "Cible (على من)"])
        self.table_audit.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_audit)

        self.tabs.addTab(tab, "  📜 Journal d'Audit / السجل  ")

    def on_audit_period_changed(self):
        is_custom = self.combo_audit_period.currentText() == "Période personnalisée"
        self.date_audit_from.setEnabled(is_custom)
        self.date_audit_to.setEnabled(is_custom)
        self.load_audit_logs()

    def get_audit_date_range(self):
        period = self.combo_audit_period.currentText()
        today = QDate.currentDate()

        if period == "7 derniers jours":
            self.current_audit_period_label = "7 derniers jours"
            start = today.addDays(-6).toString("yyyy-MM-dd") + " 00:00:00"
            end = today.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        if period == "30 derniers jours":
            self.current_audit_period_label = "30 derniers jours"
            start = today.addDays(-29).toString("yyyy-MM-dd") + " 00:00:00"
            end = today.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        if period == "90 derniers jours":
            self.current_audit_period_label = "90 derniers jours"
            start = today.addDays(-89).toString("yyyy-MM-dd") + " 00:00:00"
            end = today.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        if period == "Période personnalisée":
            start_date = self.date_audit_from.date()
            end_date = self.date_audit_to.date()
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            self.current_audit_period_label = (
                f"{start_date.toString('yyyy-MM-dd')} -> {end_date.toString('yyyy-MM-dd')}"
            )
            start = start_date.toString("yyyy-MM-dd") + " 00:00:00"
            end = end_date.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        self.current_audit_period_label = "Tout"
        return None, None

    # --- Logic ---
    def open_user_dialog(self, user_id=None):
        """Open UserDialog for adding or editing a user."""
        staff_list = [(s[0], f"{s[1]} {s[2]}") for s in self.staff_list_cache]
        dialog = UserDialog(
            staff_list=staff_list, data=None if user_id is None else self._get_user_data(user_id), parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            try:
                hashed_pwd = security_utils.hash_password(values['password'])
                db = DatabaseManager()
                with db.get_connection() as conn:
                    if user_id is None:
                        UserRepository(conn).create_user(
                            values['username'], values['email'], hashed_pwd, values['role'], staff_id=values['staff_id']
                        )
                        log_audit(conn, getattr(self, "current_user", "admin"), "CREATE_USER", values['username'])
                    else:
                        UserRepository(conn).update_user(user_id, values['email'], values['role'])
                        log_audit(conn, getattr(self, "current_user", "admin"), "UPDATE_USER", values['username'])
                    conn.commit()
                self.load_users()
                QMessageBox.information(self, "Succès", "Utilisateur sauvegardé.")
            except psycopg2.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Nom d'utilisateur déjà pris.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def open_edit_dialog(self, user_id):
        """Open UserEditDialog for password reset or account deletion."""
        user_data = self._get_user_data(user_id)
        if not user_data:
            QMessageBox.warning(self, "Erreur", "Utilisateur introuvable.")
            return
        dialog = UserEditDialog(user_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    if dialog.password_changed:
                        hashed_pwd = security_utils.hash_password(dialog.user_data.get("new_password", ""))
                        UserRepository(conn).update_password(user_id, hashed_pwd)
                        log_audit(conn, getattr(self, "current_user", "admin"), "RESET_PASSWORD", user_data["username"])
                    if dialog.account_deleted:
                        if user_id == 1 or user_data["username"] == 'admin':
                            QMessageBox.warning(self, "Interdit", "Impossible de supprimer l'administrateur.")
                            return
                        UserRepository(conn).delete_user(user_id)
                        log_audit(conn, getattr(self, "current_user", "admin"), "DELETE_USER", user_data["username"])
                    conn.commit()
                self.load_users()
                if dialog.account_deleted:
                    QMessageBox.information(self, "Succès", "Compte supprimé.")
                else:
                    QMessageBox.information(self, "Succès", "Mot de passe mis à jour.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _get_user_data(self, user_id):
        """Retrieve user data by ID as a dict."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT u.id, u.staff_id,
                           COALESCE(s.first_name || ' ' || s.last_name, '---') AS staff_name,
                           u.username, u.email, u.role
                    FROM Users u
                    LEFT JOIN Staff s ON u.staff_id = s.id
                    WHERE u.id = %s
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "staff_id": row[1],
                    "staff_name": row[2],
                    "username": row[3],
                    "email": row[4],
                    "role": row[5],
                }
            return None
        except Exception as e:
            AppLogger.error("UserManagement", f"Error fetching user data: {e}")
            return None

    def load_users(self):
        self.table.setRowCount(0)
        self.staff_list_cache = []  # Populate cache for dialogs
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                # Populate staff cache for UserDialog
                staff_rows = UserRepository(conn).list_active_staff()
                self.staff_list_cache = [(s[0], s[1], s[2]) for s in staff_rows]  # (staff_id, first_name, last_name)

                # Load users
                rows = UserRepository(conn).list_users()

            colors = ThemeManager.get_colors()
            for row in rows:
                idx = self.table.rowCount()
                self.table.insertRow(idx)
                user_id, staff_id, staff_name, username, email, role = row
                self.table.setItem(idx, 0, QTableWidgetItem(str(user_id)))
                self.table.setItem(idx, 1, QTableWidgetItem(str(staff_name or "---")))
                self.table.setItem(idx, 2, QTableWidgetItem(str(username or "")))
                self.table.setItem(idx, 3, QTableWidgetItem(str(email or "")))
                self.table.setItem(idx, 4, QTableWidgetItem(str(role or "")))

                # Action column: Edit + Delete buttons
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 2, 4, 2)
                action_layout.setSpacing(6)
                action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                btn_edit = QPushButton("✎ Éditer")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setFixedHeight(28)
                btn_edit.setStyleSheet(
                    f"QPushButton {{ background: {colors.PRIMARY}; color: white; font-size: 11px; font-weight: 600; border-radius: 6px; border: none; padding: 3px 8px; }} "
                    f"QPushButton:hover {{ background: {colors.PRIMARY_HOVER}; }}"
                )
                btn_edit.clicked.connect(lambda checked, uid=user_id: self.open_edit_dialog(uid))
                action_layout.addWidget(btn_edit)

                btn_delete = QPushButton("✕ Suppr")
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setFixedHeight(28)
                btn_delete.setStyleSheet(
                    f"QPushButton {{ background: {colors.DANGER}; color: white; font-size: 11px; font-weight: 600; border-radius: 6px; border: none; padding: 3px 8px; }} "
                    f"QPushButton:hover {{ background: {colors.DANGER_HOVER}; }}"
                )
                btn_delete.clicked.connect(lambda checked, uid=user_id: self._confirm_delete_user(uid))
                action_layout.addWidget(btn_delete)

                self.table.setCellWidget(idx, 5, action_widget)
                self.table.setRowHeight(idx, 38)
        except Exception as e:
            AppLogger.error("UserManagement", f"Error loading users: {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur de chargement: {e}")

    def _confirm_delete_user(self, user_id):
        """Confirm and delete a user."""
        user_data = self._get_user_data(user_id)
        if not user_data:
            return
        if user_id == 1 or user_data["username"] == 'admin':
            QMessageBox.warning(self, "Interdit", "Impossible de supprimer l'administrateur.")
            return
        if (
            QMessageBox.question(
                self,
                "Confirmer la suppression",
                f"Supprimer l'utilisateur '{user_data['username']}' ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    UserRepository(conn).delete_user(user_id)
                    log_audit(conn, getattr(self, "current_user", "admin"), "DELETE_USER", user_data["username"])
                    conn.commit()
                self.load_users()
                QMessageBox.information(self, "Succès", "Compte supprimé.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def load_audit_logs(self):
        self.table_audit.setRowCount(0)
        search = self.txt_audit_search.text()
        max_rows = int(self.combo_audit_limit.currentText()) if hasattr(self, "combo_audit_limit") else 300
        date_start, date_end = self.get_audit_date_range() if hasattr(self, "combo_audit_period") else (None, None)

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = UserRepository(conn).list_audit_logs(search, date_start, date_end, max_rows)

            self.current_audit_report_rows = [[r[0], r[1], r[2], r[3]] for r in rows]

            colors = ThemeManager.get_colors()

            for row in rows:
                idx = self.table_audit.rowCount()
                self.table_audit.insertRow(idx)
                timestamp = str(row[0] or "-")
                actor = str(row[1] or "-")
                action = str(row[2] or "-")
                target = str(row[3] or "-")

                self.table_audit.setItem(idx, 0, QTableWidgetItem(timestamp))
                self.table_audit.setItem(idx, 1, QTableWidgetItem(actor))

                action_item = QTableWidgetItem(action)
                if "Delete" in action:
                    action_item.setForeground(QColor(colors.DANGER))
                elif "Add" in action or "Create" in action:
                    action_item.setForeground(QColor(colors.SUCCESS))
                self.table_audit.setItem(idx, 2, action_item)
                self.table_audit.setItem(idx, 3, QTableWidgetItem(target))
        except Exception as e:
            AppLogger.error("UserManagement", f"Error loading logs: {e}")

    def export_audit_report_pdf(self):
        if not self.current_audit_report_rows:
            QMessageBox.warning(self, "Attention", "Aucune donnée à exporter dans le journal.")
            return

        pdf = FPDF(orientation='L')
        pdf.add_page()
        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, self.current_audit_report_title)

        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 7, f"Genere le: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
        pdf.ln(2)

        headers = self.current_audit_report_headers
        col_widths = [48, 45, 88, 88]

        apply_table_header_style(pdf, "Arial", 9)
        for index, header in enumerate(headers):
            text = str(header).encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(col_widths[index], 8, text, 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, "Arial", 8)
        for row_idx, row_values in enumerate(self.current_audit_report_rows):
            set_zebra_row_fill(pdf, row_idx)
            for col_idx, value in enumerate(row_values):
                text = str(value).encode('latin-1', 'ignore').decode('latin-1')
                align = 'L' if col_idx == 3 else 'C'
                pdf.cell(col_widths[col_idx], 7, text, 1, 0, align, True)
            pdf.ln()

        mode = get_report_output_mode("user_audit_report_mode", USER_AUDIT_REPORT_OUTPUT_MODE)
        output_pdf(
            pdf,
            self,
            default_name=f"Rapport_Audit_Utilisateurs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=mode,
            dialog_title="Exporter Rapport Journal d'Audit",
            success_save_message=f"Rapport du journal d'audit exporte ({self.current_audit_period_label}, max {len(self.current_audit_report_rows)} lignes).",
            success_print_message="Rapport du journal d'audit envoye a l'imprimante.",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserManagementWindow()
    window.show()
    sys.exit(app.exec())
