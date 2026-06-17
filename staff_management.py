import os
import shutil
import sys
from datetime import datetime

from fpdf import FPDF
from PyQt6.QtCore import QDate, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager, log_audit
from print_export_service import get_report_output_mode, output_pdf
from repositories.finance_repo import FinanceRepository
from repositories.staff_repo import StaffRepository
from ui_components import (
    card_frame,
    compact_icon_btn,
    horizontal_separator,
    section_label,
    style_table,
    styled_button,
    styled_combo,
    styled_date_edit,
    styled_input,
)
from ui_styles import ModuleHeaderWidget, ThemeManager, friendly_db_error, get_module_caps, get_tabs_style
from validators import format_errors, validate_staff

STAFF_LIST_OUTPUT_MODE = get_report_output_mode("staff_list_mode", "save")

from pdf_helpers import (
    prepare_pdf_text as _prepare_pdf_text,  # FIX 1: alias was `sanitize` but StaffReportPDF.sanitize() called `_sanitize_latin(text)` —; NameError on every non-Arabic cell, crashing all staff list PDF exports.
)
from pdf_helpers import sanitize_latin as _sanitize_latin
from pdf_helpers import setup_pdf_arabic_font


class StaffReportPDF(FPDF):
    def __init__(self, school_info, report_title, orientation='L'):
        super().__init__(orientation=orientation, unit='mm', format='A4')
        self.school_info = school_info
        self.report_title = report_title
        self.set_auto_page_break(True, margin=12)
        self.font_name = "Helvetica"
        self.arabic_font_ready = False
        if setup_pdf_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def header(self):
        left_x, left_y = 10, 5
        page_w = self.w
        self.set_xy(left_x, left_y)
        self.set_font(self.font_name, '', 8)

        # FIX 3: Added len > 7 guard — indices 1–7 raised IndexError on partial tuples.
        if self.school_info and len(self.school_info) > 7:
            republic = self.sanitize(self.school_info[1])
            self.cell(80, 3, republic, 0, 1, 'L')
            ia_text = self.sanitize(self.school_info[2])
            self.cell(80, 3, ia_text, 0, 1, 'L')
            ief_text = self.sanitize(self.school_info[3])
            self.cell(80, 3, ief_text, 0, 1, 'L')
            school_name = self.sanitize(self.school_info[4])
            self.cell(80, 3, school_name, 0, 1, 'L')
            auth_text = self.sanitize(self.school_info[5])
            self.cell(80, 3, f"Auto N: {auth_text}", 0, 1, 'L')
            addr_text = self.sanitize(self.school_info[6])
            self.cell(80, 3, f"Lieu: {addr_text}", 0, 1, 'L')
            phone_text = self.sanitize(self.school_info[7])
            self.cell(80, 3, f"Tel: {phone_text}", 0, 1, 'L')

        right_x = page_w - 30
        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=20, h=22)
            except Exception:
                pass

        body_bottom_y = self.get_y()
        line_y = max(body_bottom_y + 2, left_y + 24)
        self.line(10, line_y, page_w - 10, line_y)
        self.set_y(line_y + 4)

        title_style = '' if self.arabic_font_ready else 'B'
        self.set_font(self.font_name, title_style, 12)
        self.set_text_color(44, 62, 80)
        self.cell(0, 8, self.sanitize(self.report_title), 0, 1, 'C')
        self.set_font(self.font_name, '', 9)
        self.set_text_color(100, 116, 139)
        if "LISTE DU PERSONNEL" in self.report_title:
            self.cell(0, 5, self.sanitize("Gestion des ressources humaines"), 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font(self.font_name, 'I', 7)
        date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        page_w = self.w - self.l_margin - self.r_margin
        self.cell(page_w / 2, 4, f"Imprimé le {date_str}", 0, 0, 'L')
        self.cell(page_w / 2, 4, f"Page {self.page_no()}", 0, 0, 'R')


class StaffDialog(QDialog):
    """Fenêtre modale pour ajouter / modifier un employé."""

    RESULT_SAVE_AND_NEW = 10

    def __init__(self, parent=None, staff_id: int | None = None):
        super().__init__(parent)
        self._staff_id = staff_id
        self._photo_path: str = ""
        is_edit = staff_id is not None
        self.setWindowTitle("✏️ Modifier l'employé" if is_edit else "➕ Nouvel Employé")
        self.setMinimumWidth(720)
        self.setModal(True)
        ThemeManager.apply_theme(self)
        self._build_ui(is_edit)

    # ─────────────────────────── Construction UI ───────────────────────────

    def _build_ui(self, is_edit: bool) -> None:
        colors = ThemeManager.get_colors()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())
        self._build_tab_profile()
        self._build_tab_contract()
        main_layout.addWidget(self.tabs)

        # ─── Pied de navigation ───
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self._btn_prev = styled_button(
            "← Précédent",
            bg_color="transparent",
            text_color=colors.TEXT_SECONDARY,
            hover_color=colors.BG_MAIN,
            min_height=36,
        )
        self._btn_prev.setEnabled(False)
        self._btn_prev.setStyleSheet(
            self._btn_prev.styleSheet()
            + f"QPushButton:disabled {{ color:{colors.BORDER}; border:1.5px solid {colors.BORDER}; }}"
        )
        self._btn_prev.clicked.connect(self._go_prev)

        self._btn_next = styled_button("Suivant →", min_height=36)
        self._btn_next.clicked.connect(self._go_next)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(28)
        sep.setStyleSheet(f"color:{colors.BORDER};")

        if not is_edit:
            self._btn_save_new = QPushButton("💾+ Enregistrer & Nouveau")
            self._btn_save_new.setMinimumHeight(36)
            self._btn_save_new.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_save_new.setVisible(False)
            self._btn_save_new.setStyleSheet(
                f"QPushButton {{ background:transparent; color:{colors.PRIMARY};"
                f" font-weight:700; font-size:12px; border-radius:7px;"
                f" border:2px solid {colors.PRIMARY}; padding:6px 16px; }}"
                f"QPushButton:hover {{ background:{colors.PRIMARY_LIGHT}; }}"
            )
            self._btn_save_new.clicked.connect(self._on_accept_and_new)
        else:
            self._btn_save_new = None

        save_label = "✏️ Modifier" if is_edit else "💾 Enregistrer"
        self._btn_save = styled_button(
            save_label, bg_color=colors.SUCCESS, hover_color=colors.SUCCESS_HOVER, min_height=36
        )
        self._btn_save.setVisible(False)
        self._btn_save.clicked.connect(self._on_accept)

        btn_cancel = styled_button(
            "✕ Annuler",
            bg_color="transparent",
            text_color=colors.TEXT_SECONDARY,
            hover_color=colors.BG_MAIN,
            min_height=36,
        )
        btn_cancel.clicked.connect(self.reject)

        nav_row.addWidget(self._btn_prev)
        nav_row.addWidget(self._btn_next)
        nav_row.addWidget(sep)
        nav_row.addStretch()
        if self._btn_save_new:
            nav_row.addWidget(self._btn_save_new)
        nav_row.addWidget(self._btn_save)
        nav_row.addWidget(btn_cancel)
        main_layout.addLayout(nav_row)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._on_tab_changed(0)

    def _styled_input(self, placeholder: str) -> QLineEdit:
        return styled_input(placeholder, min_height=40)

    def _styled_combo(self) -> QComboBox:
        return styled_combo(min_height=40)

    def _section_label(self, icon: str, text: str) -> QLabel:
        return section_label(icon, text)

    def _build_tab_profile(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        colors = ThemeManager.get_colors()

        # صورة الموظف — مطابق لنمط StudentDialog
        top_photo_row = QHBoxLayout()
        top_photo_row.setSpacing(16)

        photo_col = QVBoxLayout()
        photo_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.lbl_photo = QLabel()
        self.lbl_photo.setFixedSize(90, 90)
        self.lbl_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo.setText("📷")
        self.lbl_photo.setStyleSheet(
            f"QLabel {{ background:{colors.PRIMARY_LIGHT}; border-radius:45px;"
            f"border:3px solid {colors.PRIMARY}; color:{colors.TEXT_SECONDARY};"
            f"font-size:24px; }}"
        )
        btn_upload = QPushButton("Changer")
        btn_upload.setMinimumHeight(28)
        btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{colors.PRIMARY};"
            f"font-size:11px; font-weight:600; border:1px solid {colors.PRIMARY};"
            f"border-radius:5px; padding:3px 8px; }}"
            f"QPushButton:hover {{ background:{colors.PRIMARY_LIGHT}; }}"
        )
        btn_upload.clicked.connect(self._upload_photo)
        photo_col.addWidget(self.lbl_photo, 0, Qt.AlignmentFlag.AlignHCenter)
        photo_col.addWidget(btn_upload, 0, Qt.AlignmentFlag.AlignHCenter)
        top_photo_row.addLayout(photo_col)
        top_photo_row.addStretch(1)
        layout.addLayout(top_photo_row)

        # Identité
        layout.addWidget(self._section_label("👤", "Identité"))
        grid1 = QGridLayout()
        grid1.setSpacing(10)
        grid1.setColumnStretch(1, 1)
        grid1.setColumnStretch(3, 1)

        self.txt_fname = self._styled_input("Prénom / الاسم")
        self.txt_lname = self._styled_input("Nom / اللقب")
        self.combo_role = self._styled_combo()
        self.combo_role.addItems(["Professeur", "Administration", "Comptabilité", "Agent", "Sécurité"])
        self.txt_spec = self._styled_input("Spécialité (Ex: Math)")

        grid1.addWidget(QLabel("Prénom:"), 0, 0)
        grid1.addWidget(self.txt_fname, 0, 1)
        grid1.addWidget(QLabel("Nom:"), 0, 2)
        grid1.addWidget(self.txt_lname, 0, 3)
        grid1.addWidget(QLabel("Fonction:"), 1, 0)
        grid1.addWidget(self.combo_role, 1, 1)
        grid1.addWidget(QLabel("Spécialité:"), 1, 2)
        grid1.addWidget(self.txt_spec, 1, 3)
        layout.addLayout(grid1)

        # Coordonnées
        layout.addWidget(self._section_label("📞", "Coordonnées & Statut"))
        grid2 = QGridLayout()
        grid2.setSpacing(10)
        grid2.setColumnStretch(1, 1)
        grid2.setColumnStretch(3, 1)

        self.txt_phone = self._styled_input("Téléphone / الهاتف")
        self.txt_email = self._styled_input("Email / البريد")
        self.txt_address = self._styled_input("Adresse / العنوان")
        self.combo_status = self._styled_combo()
        self.combo_status.addItems(
            [
                "Actif / نشط",
                "Congé / إجازة",
                "Suspendu / موقوف",
                "Démission / استقالة",
                "Licencié / مفصول",
                "Retraité / متقاعد",
            ]
        )

        grid2.addWidget(QLabel("Téléphone:"), 0, 0)
        grid2.addWidget(self.txt_phone, 0, 1)
        grid2.addWidget(QLabel("Email:"), 0, 2)
        grid2.addWidget(self.txt_email, 0, 3)
        grid2.addWidget(QLabel("Adresse:"), 1, 0)
        grid2.addWidget(self.txt_address, 1, 1)
        grid2.addWidget(QLabel("Statut:"), 1, 2)
        grid2.addWidget(self.combo_status, 1, 3)
        layout.addLayout(grid2)

        layout.addStretch()

        self.txt_fname.textChanged.connect(self._refresh_tab_indicators)
        self.txt_lname.textChanged.connect(self._refresh_tab_indicators)
        self.tabs.addTab(tab, "○ Profil")

    def _build_tab_contract(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        colors = ThemeManager.get_colors()

        layout.addWidget(self._section_label("💼", "Contrat & Salaire / العقد والراتب"))
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.date_hire = QDateEdit()
        self.date_hire.setCalendarPopup(True)
        self.date_hire.setDate(QDate.currentDate())
        self.date_hire.setMinimumHeight(40)
        self.date_hire.setStyleSheet(
            f"QDateEdit {{padding:8px 12px;border:1.5px solid {colors.INPUT_BORDER};"
            f"border-radius:8px;background:{colors.INPUT_BG};color:{colors.TEXT_PRIMARY};font-size:13px;}}"
            f"QDateEdit:focus{{border:2px solid {colors.BORDER_FOCUS};}}"
        )

        self.combo_contract = self._styled_combo()
        self.combo_contract.addItems(["Salaire Mensuel (راتب شهري)", "Vacataire/Horaire (بالساعة)"])
        self.combo_contract.currentIndexChanged.connect(self._toggle_salary_fields)

        spin_style = (
            f"QDoubleSpinBox {{padding:8px 12px;border:1.5px solid {colors.INPUT_BORDER};"
            f"border-radius:8px;background:{colors.INPUT_BG};color:{colors.TEXT_PRIMARY};font-size:13px;}}"
            f"QDoubleSpinBox:focus{{border:2px solid {colors.BORDER_FOCUS};}}"
        )

        self.spin_salary = QDoubleSpinBox()
        self.spin_salary.setRange(0, 5000000)
        self.spin_salary.setPrefix("FCFA ")
        self.spin_salary.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_salary.setMinimumHeight(40)
        self.spin_salary.setStyleSheet(spin_style)

        self.spin_hourly = QDoubleSpinBox()
        self.spin_hourly.setRange(0, 100000)
        self.spin_hourly.setPrefix("FCFA ")
        self.spin_hourly.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_hourly.setMinimumHeight(40)
        self.spin_hourly.setStyleSheet(spin_style)

        self.lbl_salary = QLabel("Salaire de base:")
        self.lbl_hourly = QLabel("Taux horaire:")

        grid.addWidget(QLabel("Date d'embauche:"), 0, 0)
        grid.addWidget(self.date_hire, 0, 1)
        grid.addWidget(QLabel("Type de contrat:"), 0, 2)
        grid.addWidget(self.combo_contract, 0, 3)
        grid.addWidget(self.lbl_salary, 1, 0)
        grid.addWidget(self.spin_salary, 1, 1)
        grid.addWidget(self.lbl_hourly, 1, 2)
        grid.addWidget(self.spin_hourly, 1, 3)
        layout.addLayout(grid)
        layout.addStretch()

        self._toggle_salary_fields()
        self.tabs.addTab(tab, "✓ Contrat")

    # ─────────────────────────── Navigation ───────────────────────────

    def _go_prev(self) -> None:
        self.tabs.setCurrentIndex(self.tabs.currentIndex() - 1)

    def _go_next(self) -> None:
        self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)

    def _on_tab_changed(self, idx: int) -> None:
        count = self.tabs.count()
        self._btn_prev.setEnabled(idx > 0)
        self._btn_next.setVisible(idx < count - 1)
        if self._btn_save_new:
            self._btn_save_new.setVisible(idx == count - 1)
        self._btn_save.setVisible(idx == count - 1)

    def _refresh_tab_indicators(self) -> None:
        has_id = bool(self.txt_fname.text().strip() and self.txt_lname.text().strip())
        self.tabs.setTabText(0, ("✓ " if has_id else "○ ") + "Profil")
        self.tabs.setTabText(1, "✓  Contrat")

    # ─────────────────────────── Actions ───────────────────────────

    def _toggle_salary_fields(self) -> None:
        is_monthly = self.combo_contract.currentIndex() == 0
        self.lbl_salary.setVisible(is_monthly)
        self.spin_salary.setVisible(is_monthly)
        self.lbl_hourly.setVisible(not is_monthly)
        self.spin_hourly.setVisible(not is_monthly)

    def _upload_photo(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir une photo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self._photo_path = file_path
            pixmap = QPixmap(file_path)
            self.lbl_photo.setPixmap(
                pixmap.scaled(
                    84, 84, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
                )
            )
            self.lbl_photo.setText("")

    def _validate(self) -> bool:
        if not self.txt_fname.text().strip() or not self.txt_lname.text().strip():
            QMessageBox.warning(self, "Champs obligatoires", "Prénom et Nom sont obligatoires.")
            self.tabs.setCurrentIndex(0)
            self.txt_fname.setFocus()
            return False
        return True

    def _on_accept(self) -> None:
        if self._validate():
            self.accept()

    def _on_accept_and_new(self) -> None:
        if self._validate():
            self.done(self.RESULT_SAVE_AND_NEW)

    # ─────────────────────────── Données ───────────────────────────

    def populate(self, data: tuple) -> None:
        """Remplir depuis get_staff_details() tuple:
        (first_name, last_name, role, specialty, phone, email, address,
         hire_date, contract_type, salary_base, hourly_rate, photo_path, status)
        """
        self.txt_fname.setText(data[0] or "")
        self.txt_lname.setText(data[1] or "")
        self.combo_role.setCurrentText(data[2] or "")
        self.txt_spec.setText(data[3] or "")
        self.txt_phone.setText(data[4] or "")
        self.txt_email.setText(data[5] or "")
        self.txt_address.setText(data[6] or "")
        try:
            if data[7]:
                self.date_hire.setDate(QDate.fromString(str(data[7]), "yyyy-MM-dd"))
        except Exception:
            pass
        self.combo_contract.setCurrentIndex(0 if data[8] == "Monthly" else 1)
        self.spin_salary.setValue(float(data[9]) if data[9] else 0.0)
        self.spin_hourly.setValue(float(data[10]) if data[10] else 0.0)
        if data[11] and os.path.exists(data[11]):
            self._photo_path = data[11]
            pixmap = QPixmap(data[11])
            self.lbl_photo.setPixmap(
                pixmap.scaled(
                    84, 84, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
                )
            )
            self.lbl_photo.setText("")
        status_map = {"Actif": 0, "Congé": 1, "Suspendu": 2, "Démission": 3, "Licencié": 4, "Retraité": 5}
        self.combo_status.setCurrentIndex(status_map.get(data[12] or "Actif", 0))
        self._refresh_tab_indicators()

    def get_values(self) -> dict:
        """Retourner un dict prêt pour StaffRepository.add_staff / update_staff."""
        status_text = self.combo_status.currentText()
        status = status_text.split(" / ")[0]
        is_monthly = self.combo_contract.currentIndex() == 0
        return {
            "first_name": self.txt_fname.text().strip(),
            "last_name": self.txt_lname.text().strip(),
            "role": self.combo_role.currentText(),
            "specialty": self.txt_spec.text().strip(),
            "phone": self.txt_phone.text().strip(),
            "email": self.txt_email.text().strip(),
            "address": self.txt_address.text().strip(),
            "hire_date": self.date_hire.date().toString("yyyy-MM-dd"),
            "contract_type": "Monthly" if is_monthly else "Hourly",
            "salary_base": self.spin_salary.value() if is_monthly else 0.0,
            "hourly_rate": 0.0 if is_monthly else self.spin_hourly.value(),
            "status": status,
            "photo_path": "",  # will be set by caller after copying the file
        }

    def get_new_photo_path(self) -> str:
        """Chemin local de la nouvelle photo sélectionnée, ou chaîne vide."""
        return self._photo_path


class ModernStaffManagement(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des RH / إدارة الموارد البشرية")
        self.setMinimumSize(1100, 700)

        ThemeManager.apply_theme(self)

        self.init_ui()
        self.load_staff_list()
        self._load_kpi_stats()

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "staff_management")
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
            icon="👥",
            title="RESSOURCES HUMAINES",
            subtitle="إدارة الموظفين، الرواتب، والجدول الزمني",
        )
        self.main_layout.addWidget(header)
        self._stat_total = header.add_stat("👥", "Total Personnel", "—", "#3B82F6")
        self._stat_profs = header.add_stat("👨‍🏫", "Professeurs", "—", "#8B5CF6")
        self._stat_admin = header.add_stat("🏢", "Administration", "—", "#F59E0B")
        self._stat_actifs = header.add_stat("✅", "Actifs", "—", "#22C55E")

        # 2. KPI

        # 3. Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_staff_tab()

        self.main_layout.addWidget(self.tabs)

    def setup_staff_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        colors = ThemeManager.get_colors()

        # ─── Barre d'outils ───
        toolbar_card = card_frame()
        tlay = QHBoxLayout(toolbar_card)
        tlay.setContentsMargins(10, 6, 10, 6)
        tlay.setSpacing(8)

        self.btn_add = QPushButton("➕  Nouvel Employé")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setFixedHeight(32)
        self.btn_add.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {colors.SUCCESS}, stop:1 #16A34A); color:white; font-weight:700;"
            f"font-size:12px; border-radius:7px; border:none; padding:4px 14px; }}"
            f"QPushButton:hover {{ background:{colors.SUCCESS_HOVER}; }}"
            f"QPushButton:disabled {{ background:{colors.BORDER}; color:{colors.TEXT_SECONDARY}; }}"
        )
        self.btn_add.clicked.connect(lambda: self.open_staff_dialog())

        self.txt_search = styled_input("🔍 Rechercher un employé...", min_height=32)
        self.txt_search.setMaximumWidth(380)
        self.txt_search.textChanged.connect(self.load_staff_list)

        btn_print = QPushButton("🖨 Liste")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setFixedHeight(32)
        btn_print.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{colors.PRIMARY};"
            f" font-weight:600; border:1.5px solid {colors.PRIMARY};"
            f" border-radius:7px; font-size:11px; padding:4px 12px; }}"
            f"QPushButton:hover {{ background:{colors.PRIMARY_LIGHT}; }}"
        )
        btn_print.clicked.connect(self.print_staff_list)

        tlay.addWidget(self.btn_add)
        tlay.addStretch()
        tlay.addWidget(self.txt_search)
        tlay.addStretch()
        tlay.addWidget(btn_print)
        layout.addWidget(toolbar_card)

        # ─── Tableau ───
        self.table_staff = QTableWidget()
        style_table(self.table_staff)
        self.table_staff.setColumnCount(9)
        self.table_staff.setHorizontalHeaderLabels(
            ["ID", "Nom & Prénom", "Fonction", "Spécialité", "Tél", "Contrat", "Montant", "Statut", "⚙️"]
        )
        self.table_staff.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_staff.setColumnWidth(0, 50)
        self.table_staff.setColumnWidth(7, 90)
        self.table_staff.setColumnWidth(8, 80)
        self.table_staff.setIconSize(QSize(32, 32))
        layout.addWidget(self.table_staff)

        self.tabs.addTab(tab, "  👨‍💼 Personnel / الموظفون  ")

    def load_staff_list(self):
        self.table_staff.setRowCount(0)
        search_txt = self.txt_search.text()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                rows = repo.list_staff(search_txt)

            for row in rows:
                r_idx = self.table_staff.rowCount()
                self.table_staff.insertRow(r_idx)

                self.table_staff.setItem(r_idx, 0, QTableWidgetItem(str(row[0])))

                name_item = QTableWidgetItem(row[1] or "")
                if row[8] and os.path.exists(row[8]):
                    icon = QIcon(row[8])
                    name_item.setIcon(icon)
                self.table_staff.setItem(r_idx, 1, name_item)

                self.table_staff.setItem(r_idx, 2, QTableWidgetItem(row[2] or ""))
                self.table_staff.setItem(r_idx, 3, QTableWidgetItem(row[3] or ""))
                self.table_staff.setItem(r_idx, 4, QTableWidgetItem(row[4] or ""))

                ctype = "Mensuel" if row[5] == "Monthly" else "Horaire"
                amount = f"{row[6]:,.0f}" if row[5] == "Monthly" else f"{row[7]:,.0f}/h"

                self.table_staff.setItem(r_idx, 5, QTableWidgetItem(ctype))
                self.table_staff.setItem(r_idx, 6, QTableWidgetItem(amount))

                status = row[9] or "Actif"
                status_item = QTableWidgetItem(status)
                if status == "Actif":
                    status_item.setForeground(QColor(16, 185, 129))
                elif status in ["Congé", "Suspendu"]:
                    status_item.setForeground(QColor(245, 158, 11))
                else:
                    status_item.setForeground(QColor(239, 68, 68))
                self.table_staff.setItem(r_idx, 7, status_item)

                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(5)

                _c = ThemeManager.get_colors()
                btn_edit = QPushButton("✎ Modifier")
                btn_edit.setFixedHeight(28)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet(
                    f"QPushButton {{ background:{_c.PRIMARY}; color:white; border-radius:6px;"
                    f"border:none; font-weight:600; font-size:11px; padding:3px 8px; }}"
                    f"QPushButton:hover {{ background:{_c.PRIMARY_HOVER}; }}"
                )
                btn_edit.clicked.connect(lambda ch, pid=row[0]: self.open_staff_dialog(pid))

                btn_del = QPushButton("✕ Archiver")
                btn_del.setFixedHeight(28)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet(
                    f"QPushButton {{ background:{_c.DANGER}; color:white; border-radius:6px;"
                    f"border:none; font-weight:600; font-size:11px; padding:3px 8px; }}"
                    f"QPushButton:hover {{ background:#B91C1C; }}"
                )
                btn_del.clicked.connect(lambda ch, pid=row[0]: self.delete_staff_from_table(pid))

                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_del)
                self.table_staff.setCellWidget(r_idx, 8, btn_widget)
        except Exception as e:
            AppLogger.error("StaffManagement", f"Error loading staff list: {e}")

    # ───────────────────────────── KPI ─────────────────────────────

    def _load_kpi_stats(self):
        """Charge les compteurs pour les cartes KPI."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM Staff")
                total = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM Staff WHERE role = 'Professeur'")
                profs = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM Staff WHERE role = 'Administration'")
                admin = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM Staff WHERE status ILIKE '%Actif%'")
                actifs = cursor.fetchone()[0]
            self._stat_total.set_value(str(total))
            self._stat_profs.set_value(str(profs))
            self._stat_admin.set_value(str(admin))
            self._stat_actifs.set_value(str(actifs))
        except Exception as e:
            AppLogger.error("StaffManagement", f"KPI load error: {e}")

    def open_staff_dialog(self, staff_id: int | None = None) -> None:
        """Ouvrir la boîte de dialogue pour ajouter ou modifier un employé."""
        dialog = StaffDialog(self, staff_id=staff_id)
        if staff_id is not None:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    repo = StaffRepository(conn)
                    data = repo.get_staff_details(staff_id)
                if data:
                    dialog.populate(data)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))
                return

        result = dialog.exec()
        if result in (QDialog.DialogCode.Accepted, StaffDialog.RESULT_SAVE_AND_NEW):
            values = dialog.get_values()
            self._save_staff_from_dialog(dialog, values, staff_id)
            if result == StaffDialog.RESULT_SAVE_AND_NEW:
                self.open_staff_dialog()

    def _save_staff_from_dialog(self, dialog: "StaffDialog", values: dict, staff_id: int | None) -> None:
        """Copier la photo et enregistrer les données via le repository."""
        errors = validate_staff(values)
        if errors:
            QMessageBox.warning(self, "بيانات غير صالحة / Données invalides", format_errors(errors))
            return
        try:
            db = DatabaseManager()
            new_photo = dialog.get_new_photo_path()
            if new_photo:
                save_dir = "staff_photos"
                os.makedirs(save_dir, exist_ok=True)
                ext = os.path.splitext(new_photo)[1]
                filename = f"staff_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                saved_path = os.path.join(save_dir, filename)
                try:
                    shutil.copy(new_photo, saved_path)
                    values["photo_path"] = saved_path
                except Exception as e:
                    AppLogger.error("StaffManagement", f"Photo copy failed: {e}")
            elif staff_id is not None:
                with db.get_connection() as conn:
                    repo = StaffRepository(conn)
                    values["photo_path"] = repo.get_photo_path(staff_id) or ""

            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                if staff_id is not None:
                    repo.update_staff(staff_id, values)
                    log_audit(
                        conn,
                        getattr(self, "current_user", "system"),
                        "EDIT_STAFF",
                        f"{values['first_name']} {values['last_name']} (id={staff_id})",
                    )
                    QMessageBox.information(self, "Succès", "Mise à jour réussie.")
                else:
                    repo.add_staff(values)
                    log_audit(
                        conn,
                        getattr(self, "current_user", "system"),
                        "ADD_STAFF",
                        f"{values['first_name']} {values['last_name']}",
                    )
                    QMessageBox.information(self, "Succès", "Employé ajouté avec succès.")
                conn.commit()
            self.load_staff_list()
            self._load_kpi_stats()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    def delete_staff_from_table(self, pid):
        reply = QMessageBox.question(
            self,
            'Confirmation',
            "Voulez-vous archiver cet employé ?\n(Cela masquera l'employé des listes actives)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    repo = StaffRepository(conn)
                    repo.archive_staff(pid)
                    log_audit(conn, getattr(self, "current_user", "system"), "ARCHIVE_STAFF", f"id={pid}")
                    conn.commit()
                self.load_staff_list()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    def print_staff_list(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = StaffRepository(conn)
                school_info = FinanceRepository(conn).get_school_info()
                rows = repo.list_staff_for_report()

            pdf = StaffReportPDF(school_info, "LISTE DU PERSONNEL")
            pdf.add_page()

            pdf.set_fill_color(30, 41, 59)
            pdf.set_text_color(255, 255, 255)
            font_to_use = "ArabicFont" if pdf.arabic_font_ready else "Helvetica"
            pdf.set_font(font_to_use, 'B', 8)

            col_widths = [10, 35, 25, 28, 32, 36, 36, 18, 15, 13, 13, 18]
            headers = [
                "ID",
                "Nom Complet",
                "Fonction",
                "Spécialité",
                "Téléphone",
                "Email",
                "Adresse",
                "Embauche",
                "Contrat",
                "Salaire",
                "Heure",
                "Statut",
            ]
            for i, header in enumerate(headers):
                ln_val = 1 if i == len(headers) - 1 else 0
                pdf.cell(col_widths[i], 7, pdf.sanitize(header), 1, ln_val, 'C', True)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font(font_to_use, '', 7)

            for i, row in enumerate(rows):
                fill = i % 2 == 0
                if fill:
                    pdf.set_fill_color(248, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.cell(col_widths[0], 6, str(row[0]), 1, 0, 'C', fill)
                pdf.cell(col_widths[1], 6, pdf.sanitize(row[1]), 1, 0, 'L', fill)
                pdf.cell(col_widths[2], 6, pdf.sanitize(row[2]), 1, 0, 'L', fill)
                pdf.cell(col_widths[3], 6, pdf.sanitize(row[3]), 1, 0, 'L', fill)
                pdf.cell(col_widths[4], 6, pdf.sanitize(row[4]), 1, 0, 'L', fill)
                pdf.cell(col_widths[5], 6, pdf.sanitize(row[5]), 1, 0, 'L', fill)
                pdf.cell(col_widths[6], 6, pdf.sanitize(row[6]), 1, 0, 'L', fill)
                pdf.cell(col_widths[7], 6, pdf.sanitize(row[7]), 1, 0, 'C', fill)
                pdf.cell(
                    col_widths[8], 6, pdf.sanitize("Mensuel" if row[8] == "Monthly" else "Horaire"), 1, 0, 'L', fill
                )
                pdf.cell(col_widths[9], 6, pdf.sanitize(f"{row[9]:.0f}" if row[9] is not None else ""), 1, 0, 'R', fill)
                pdf.cell(
                    col_widths[10], 6, pdf.sanitize(f"{row[10]:.0f}" if row[10] is not None else ""), 1, 0, 'R', fill
                )
                pdf.cell(col_widths[11], 6, pdf.sanitize(row[11]), 1, 1, 'C', fill)

            output_pdf(
                pdf,
                self,
                f"Liste_Personnel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mode=STAFF_LIST_OUTPUT_MODE,
                dialog_title="Sauvegarder PDF",
                success_save_message="Rapport généré en PDF.",
                success_print_message="Rapport envoyé à l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération du PDF: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernStaffManagement()
    window.show()
    sys.exit(app.exec())
