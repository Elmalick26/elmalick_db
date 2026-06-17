import os
import shutil
import sys
from contextlib import suppress
from datetime import datetime

import psycopg2
from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from print_export_service import get_report_output_mode, output_pdf
from repositories.admin_documents_repo import AdminDocumentsRepository
from ui_components import BaseWindow, create_card, styled_button, styled_combo, styled_date_edit, styled_text_edit

# FIX 1: Added friendly_db_error to the import — was missing, caused NameError on photo upload error
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

ADMIN_DOCS_OUTPUT_MODE = get_report_output_mode("admin_documents_mode", "print")

# FIX 7: Anchor photo storage to the application directory, not the CWD
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PHOTOS_DIR = os.path.join(_APP_DIR, "school_data", "photos")

from pdf_helpers import ARABIC_SUPPORT
from pdf_helpers import contains_arabic as _contains_arabic
from pdf_helpers import find_arabic_font_path as _get_arabic_font_path
from pdf_helpers import get_pdf_font_name, is_arabic_font_ready
from pdf_helpers import latin_fallback as _latin_fallback_text
from pdf_helpers import prepare_pdf_text as _prepare_pdf_text
from pdf_helpers import sanitize_latin as _sanitize_latin
from pdf_helpers import setup_pdf_arabic_font


def _register_arabic_font(pdf):
    font_path = _get_arabic_font_path()
    if not font_path:
        return False
    try:
        pdf.add_font("ArabicFont", "", font_path, uni=True)
        pdf.add_font("ArabicFont", "B", font_path, uni=True)
        pdf.add_font("ArabicFont", "I", font_path, uni=True)
        pdf.add_font("ArabicFont", "BI", font_path, uni=True)
        return True
    except Exception:
        return False


# --- بطاقة الطالب المزدوجة (Recto/Verso) ---


class IDCardPDF(FPDF):
    def __init__(self, school_info, year_label):
        super().__init__(orientation='P', unit='mm', format=(85, 55))
        self.school_info = school_info
        self.year_label = year_label
        self.set_auto_page_break(False)
        self.set_margins(2, 2, 2)

        self.font_name = "Helvetica"
        self.arabic_font_ready = False
        if _register_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def header(self):
        pass

    def footer(self):
        pass

    def generate_senegal_id_card(self, student):
        # ==========================================
        # RECTO - هوية المدرسة
        # ==========================================
        self.add_page()

        self.set_line_width(0.3)
        self.set_draw_color(100, 100, 100)
        self.rect(1, 1, 83, 53, style='D')

        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        if logo_path and os.path.exists(logo_path):
            with suppress(Exception):
                self.image(logo_path, x=32.5, y=3, w=20, h=22)

        self.set_fill_color(15, 23, 42)
        self.rect(1, 26, 83, 18, style='F')

        self.set_text_color(255, 255, 255)
        self.set_font(self.font_name, '', 5)

        self.set_xy(1, 28)
        republic = self.sanitize(self.school_info[1]) if self.school_info else "République du Sénégal"
        self.cell(83, 3, republic, 0, 1, 'C')

        ia_ief = ""
        if self.school_info:
            ia = self.sanitize(self.school_info[2])
            ief = self.sanitize(self.school_info[3])
            ia_ief = f"{ia} / {ief}"
        self.cell(83, 3, ia_ief, 0, 1, 'C')

        self.set_font(self.font_name, 'B', 8)
        school_name = self.sanitize(self.school_info[4]) if self.school_info else "NOM DE L'ETABLISSEMENT"
        self.cell(83, 4, school_name.upper(), 0, 1, 'C')

        self.set_font(self.font_name, '', 5)
        auth = self.sanitize(self.school_info[5]) if self.school_info else "N/A"
        self.cell(83, 3, f"Aut: {auth}", 0, 1, 'C')

        self.set_text_color(0, 0, 0)
        self.set_xy(1, 46)
        addr = self.sanitize(self.school_info[6]) if self.school_info else "Adresse"
        phone = self.sanitize(self.school_info[7]) if self.school_info else "Tel"

        self.cell(83, 3, f"Adresse: {addr}", 0, 1, 'C')
        self.cell(83, 3, f"Tel: {phone}", 0, 1, 'C')

        # ==========================================
        # VERSO - بيانات الطالب والرسوم
        # ==========================================
        self.add_page()

        self.rect(1, 1, 83, 53, style='D')

        photo_x, photo_y, photo_w, photo_h = 3, 3, 16, 18
        self.rect(photo_x, photo_y, photo_w, photo_h)
        if student.get('photo') and os.path.exists(student['photo']):
            try:
                self.image(student['photo'], photo_x, photo_y, photo_w, photo_h)
            except Exception:
                pass

        self.set_xy(21, 6)
        self.set_font(self.font_name, 'B', 7)
        self.cell(20, 4, "Matricule:", 0, 1, 'L')
        self.set_xy(21, 10)
        self.set_font(self.font_name, '', 8)
        self.cell(20, 4, str(student['id']), 0, 1, 'C')

        self.set_font(self.font_name, 'B', 5)
        y_pos = 23
        line_h = 3.8

        dob_str = str(student.get('dob') or "")
        birth_place_str = self.sanitize(student.get('birth_place') or "")

        lines = [
            ("P. et Nom :", self.sanitize(student['name']).upper()),
            ("Né(e) le:", dob_str + " à " + birth_place_str),
            ("Adresse :", self.sanitize(student.get('address') or "")),
            ("N° tel :", str(student.get('phone') or "")),
            ("Classe :", self.sanitize(student.get('class') or "-")),
            ("Code Accès :", str(student.get('student_code') or student.get('class_number') or student['id'])),
            ("Année scolaire :", self.year_label),
            ("Date d'inscription :", str(student.get('reg_date') or "")),
        ]

        for lbl, val in lines:
            self.set_xy(3, y_pos)
            self.cell(16, line_h, lbl, 0, 0, 'L')
            self.set_font(self.font_name, '', 5)
            self.cell(22, line_h, str(val), 'B', 1, 'L')
            self.set_font(self.font_name, 'B', 5)
            y_pos += line_h

        self.line(42, 2, 42, 53)

        self.set_xy(43, 3)
        self.set_font(self.font_name, 'B', 6)
        self.cell(40, 4, "Les frais de scolarité", 0, 1, 'C')

        self.set_xy(43, 8)
        self.set_fill_color(15, 23, 42)
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_name, '', 5)
        self.cell(15, 4, "Description", 1, 0, 'C', True)
        self.cell(10, 4, "Montant", 1, 0, 'C', True)
        self.cell(8, 4, "Date", 1, 0, 'C', True)
        self.cell(7, 4, "Sign", 1, 1, 'C', True)

        self.set_text_color(0, 0, 0)
        months = [
            "Inscription",
            "Octobre",
            "Novembre",
            "Décembre",
            "Janvier",
            "Février",
            "Mars",
            "Avril",
            "Mai",
            "Juin",
        ]
        dues_map = student.get('dues_map', {}) if isinstance(student, dict) else {}

        for m in months:
            due_entry = dues_map.get(m, {})
            amount_txt = due_entry.get('amount', "")
            due_date_txt = due_entry.get('date', "")
            sign_txt = "✓" if due_entry.get('paid') else ""
            self.set_x(43)
            self.cell(15, 4.1, m, 1, 0, 'L')
            self.cell(10, 4.1, amount_txt, 1, 0, 'C')
            self.cell(8, 4.1, due_date_txt, 1, 0, 'C')
            self.cell(7, 4.1, sign_txt, 1, 1, 'C')


# --- وثائق A4 العادية ---
class DocumentPDF(FPDF):
    def __init__(self, school_info, year_label, page_format=None):
        if page_format:
            super().__init__(orientation='P', unit='mm', format=page_format)
        else:
            super().__init__()
        self.school_info = school_info
        self.year_label = year_label
        self.font_name = "Arial"
        self.arabic_font_ready = False
        if _register_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def draw_header_official(self):
        left_x, left_y = 10, 10
        self.set_xy(left_x, left_y)
        self.set_font(self.font_name, '', 8)

        if self.school_info:
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

        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None

        if logo_path and os.path.exists(logo_path):
            with suppress(Exception):
                self.image(logo_path, x=175, y=left_y, w=20, h=22)

        line_y = max(self.get_y(), left_y + 26)
        self.set_y(line_y)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def generate_certificat_scolarite(self, student):
        self.add_page()
        self.draw_header_official()

        self.set_font(self.font_name, 'B', 24)
        self.cell(0, 20, "CERTIFICAT DE SCOLARITE", 0, 1, 'C')
        self.ln(10)

        self.set_font(self.font_name, '', 14)
        txt = (
            f"Je soussigné, Directeur de l'établissement, certifie que l'élève :\n\n"
            f"Prénom et Nom : {self.sanitize(student['name']).upper()}\n"
            f"Date de Naissance  : {student['dob']}"
            f"  à  {self.sanitize(student['birth_place'])}\n"
            f"Matricule : {student['id']}\n\n"
            f"Est régulièrement inscrit(e) dans notre établissement en classe de :"
            f"{self.sanitize(student['class']).upper()}\n\n"
            f"Pour l'année scolaire {self.year_label}.\n\n"
            f"Ce certificat est délivré pour servir et valoir ce que de droit."
        )

        self.multi_cell(0, 10, txt)

        self.ln(30)
        self.set_font(self.font_name, 'I', 12)
        date_str = datetime.now().strftime("%d/%m/%Y")
        city = self.sanitize(self.school_info[6].split(' ')[0]) if self.school_info and self.school_info[6] else "Ville"
        self.cell(0, 10, f"Fait à {city}, le {date_str}", 0, 1, 'R')
        self.ln(5)
        self.set_font(self.font_name, 'B', 12)
        self.cell(0, 10, "Le Directeur (Cachet et Signature)", 0, 1, 'R')

    # FIX 8: generate_id_card() removed — it was dead code, never called anywhere.
    # Card generation is handled exclusively by IDCardPDF.generate_senegal_id_card().

    def generate_convocation(self, student, motif, date_conv):
        self.add_page()
        self.draw_header_official()

        self.set_font(self.font_name, 'B', 20)
        self.cell(0, 15, "CONVOCATION", 0, 1, 'C')
        self.ln(10)

        self.set_font(self.font_name, '', 12)
        parent = self.sanitize(student['parent']) if student['parent'] else "Le Tuteur"

        txt = (
            f"M./Mme {parent},\n\n"
            f"Vous êtes prié(e) de bien vouloir vous présenter à la direction de l'école "
            f"le {date_conv} pour une affaire concernant votre enfant :\n\n"
            f"Nom : {self.sanitize(student['name']).upper()}\n"
            f"Classe : {self.sanitize(student['class'])}\n\n"
            f"Motif : {self.sanitize(motif)}\n\n"
            "Nous comptons sur votre présence."
        )

        self.multi_cell(0, 10, txt)

        self.ln(30)
        self.set_font(self.font_name, 'B', 12)
        self.cell(0, 10, "Le Directeur", 0, 1, 'R')


class AdminDocsWindow(BaseWindow):
    def __init__(self):
        super().__init__("Générateur de Documents Administratifs / الوثائق الإدارية", 1100, 700)
        # FIX 3: Cache active year at instance level — avoids one extra DB call per student
        self._active_year_id: int = -1
        self.init_ui()
        self.load_classes()
        self._refresh_active_year()
        self._load_kpi_stats()

    def _refresh_active_year(self):
        """Fetch and cache the active academic year ID — call once on init and after year changes."""
        self._active_year_id = self._fetch_active_year_id()

    def _fetch_active_year_id(self) -> int:
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return AdminDocumentsRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def get_active_year_id(self) -> int:
        """Return cached active year ID. Use _refresh_active_year() to update."""
        return self._active_year_id

    def apply_rbac(self, role: str) -> None:
        caps = get_module_caps(role, "admin_docs")
        self.btn_upload_photo.setEnabled(caps["can_write"])
        self.btn_upload_photo.setVisible(caps["can_write"])

    def init_ui(self):
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        header = ModuleHeaderWidget(
            icon="🗂️",
            title="DOCUMENTS & CARTES",
            subtitle="إصدار الوثائق الرسمية والبطاقات",
        )
        self.main_layout.addWidget(header)
        self._stat_students = header.add_stat("👥", "Élèves Inscrits", "—", "#3B82F6")
        self._stat_certs = header.add_stat("📄", "Certificats Générés", "—", "#22C55E")
        self._stat_cards = header.add_stat("🧧", "Cartes Élèves", "—", "#8B5CF6")
        self._stat_convocs = header.add_stat("📬", "Convocations", "—", "#F59E0B")

        self.setup_combined_view()

    def setup_combined_view(self):
        colors = ThemeManager.get_colors()

        doc_card, doc_cl = create_card()

        main_hlay = QHBoxLayout()
        main_hlay.setContentsMargins(20, 20, 20, 20)
        main_hlay.setSpacing(24)

        # Left panel: selection
        left_panel = QWidget()
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(16)

        title_left = QLabel("📌 التحديد الأساسي (Sélection)")
        title_left.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; font-size: 14px;")
        left_lay.addWidget(title_left)

        self.combo_class_shared = styled_combo()
        self.combo_class_shared.currentIndexChanged.connect(
            lambda: self.load_students(self.combo_class_shared, self.combo_student_shared)
        )
        self.combo_student_shared = styled_combo()
        self.combo_student_shared.currentIndexChanged.connect(self.check_photo_status)

        self.combo_class_cert = self.combo_class_shared
        self.combo_class_card = self.combo_class_shared
        self.combo_class_conv = self.combo_class_shared
        self.combo_student_cert = self.combo_student_shared
        self.combo_student_card = self.combo_student_shared
        self.combo_student_conv = self.combo_student_shared

        self.combo_doc_type = styled_combo()
        self.combo_doc_type.addItem("📜  Certificat de Scolarité")
        self.combo_doc_type.addItem("💳  Carte d'Étudiant")
        self.combo_doc_type.addItem("⚠️  Convocation des Parents")
        self.combo_doc_type.currentIndexChanged.connect(self._on_doc_type_changed)

        left_lay.addWidget(QLabel("الفصل (Classe) :"))
        left_lay.addWidget(self.combo_class_shared)
        left_lay.addWidget(QLabel("الطالب (Élève) :"))
        left_lay.addWidget(self.combo_student_shared)
        left_lay.addWidget(QLabel("نوع الوثيقة (Type de document) :"))
        left_lay.addWidget(self.combo_doc_type)
        left_lay.addStretch()

        # Right panel: document-specific settings
        right_panel = QFrame()
        right_panel.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border-radius: 8px; border: 1px solid #E2E8F0; }"
        )
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(20, 20, 20, 20)

        title_right = QLabel("⚙️ إعدادات الوثيقة (Paramètres)")
        title_right.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; font-size: 14px; border: none;")
        right_lay.addWidget(title_right)

        from PyQt6.QtWidgets import QStackedWidget

        self.stacked_config = QStackedWidget()

        # Page 0: Certificate
        page_cert = QWidget()
        page_cert_lay = QVBoxLayout(page_cert)
        lbl_cert = QLabel("لا توجد إعدادات إضافية مطلوبة.\nالشهادة المدرسية جاهزة للطباعة.")
        lbl_cert.setStyleSheet("color: #64748B; border: none; font-size: 12px;")
        lbl_cert.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_cert_lay.addWidget(lbl_cert)
        self.stacked_config.addWidget(page_cert)

        # Page 1: Student card (photo upload)
        page_card = QWidget()
        page_card.setStyleSheet("border: none;")
        card_lay = QVBoxLayout(page_card)
        card_lay.setSpacing(12)

        self.btn_upload_photo = QPushButton("📷 Ajouter Photo / إضافة صورة")
        self.btn_upload_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload_photo.setStyleSheet(
            f"QPushButton {{ background: white; color: {colors.PRIMARY}; border-radius: 6px;"
            f" padding: 8px 16px; border: 1.5px solid {colors.PRIMARY}; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #EFF6FF; }}"
        )
        self.btn_upload_photo.clicked.connect(self.upload_student_photo)

        self.lbl_photo_status = QLabel("...")
        self.lbl_photo_status.setStyleSheet("color: #64748B;")
        self.lbl_photo_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_lay.addWidget(self.btn_upload_photo)
        card_lay.addWidget(self.lbl_photo_status)
        card_lay.addStretch()
        self.stacked_config.addWidget(page_card)

        # Page 2: Parent convocation
        page_conv = QWidget()
        page_conv.setStyleSheet("border: none;")
        conv_lay = QVBoxLayout(page_conv)
        conv_lay.setSpacing(10)

        conv_lay.addWidget(QLabel("📅 Date du rendez-vous / تاريخ الموعد:"))
        self.date_conv = styled_date_edit()
        self.date_conv.setDate(QDate.currentDate().addDays(1))
        conv_lay.addWidget(self.date_conv)

        conv_lay.addWidget(QLabel("📝 Motif / سبب الاستدعاء:"))
        self.txt_motif = styled_text_edit("Motif de la convocation (ex: Absence prolongée...)")
        self.txt_motif.setMaximumHeight(70)
        conv_lay.addWidget(self.txt_motif)
        self.stacked_config.addWidget(page_conv)

        right_lay.addWidget(self.stacked_config)

        main_hlay.addWidget(left_panel, 1)
        main_hlay.addWidget(right_panel, 1)

        # Action buttons
        action_row = QHBoxLayout()
        action_row.setContentsMargins(20, 0, 20, 10)
        action_row.setSpacing(15)

        self._btn_batch = styled_button(
            "🖨️  Toute la Classe (طباعة للفصل كاملاً)",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=45,
        )
        self._btn_batch.clicked.connect(lambda: self.print_card(mode='batch'))
        self._btn_batch.setVisible(False)

        self._btn_action = styled_button(
            "🖨️  Imprimer Certificat", bg_color=colors.PRIMARY, hover_color=colors.PRIMARY_HOVER, min_height=45
        )
        self._btn_action.clicked.connect(self._on_action_clicked)

        action_row.addStretch()
        action_row.addWidget(self._btn_batch)
        action_row.addWidget(self._btn_action)

        doc_cl.addLayout(main_hlay)
        doc_cl.addLayout(action_row)

        self.main_layout.addWidget(doc_card)
        self.main_layout.addStretch()

    def _on_doc_type_changed(self, idx):
        colors = ThemeManager.get_colors()

        self.stacked_config.setCurrentIndex(idx)
        self._btn_batch.setVisible(idx == 1)

        btn_style_template = (
            "QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {0}, stop:1 {1}); "
            "color: white; font-weight: bold; border-radius: 8px; border: none; padding: 10px 24px; font-size: 13px; }}"
            "QPushButton:hover {{ background: {2}; }}"
        )

        if idx == 0:
            self._btn_action.setText("🖨️  Imprimer Certificat (طباعة شهادة)")
            self._btn_action.setStyleSheet(
                btn_style_template.format(colors.PRIMARY, colors.PRIMARY_HOVER, colors.PRIMARY_DARK)
            )
        elif idx == 1:
            self._btn_action.setText("🖨️  Imprimer Carte (طباعة بطاقة)")
            self._btn_action.setStyleSheet(
                btn_style_template.format(colors.PRIMARY, colors.PRIMARY_HOVER, colors.PRIMARY_DARK)
            )
        else:
            self._btn_action.setText("⚠️  Générer Convocation (إصدار استدعاء)")
            self._btn_action.setStyleSheet(
                btn_style_template.format(colors.DANGER, colors.DANGER_HOVER, colors.DANGER_HOVER)
            )

    def _on_action_clicked(self):
        idx = self.combo_doc_type.currentIndex()
        if idx == 0:
            self.print_certificate()
        elif idx == 1:
            self.print_card(mode='single')
        else:
            self.print_convocation()

    # --- KPI Stats ---

    def _load_kpi_stats(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM Students WHERE is_active = TRUE")
                students = cursor.fetchone()[0] or 0
                self._stat_students.set_value(str(students))

                # FIX 4: DocumentsLog may not exist — query each stat independently
                # so a missing table doesn't suppress the student count above
                for stat_widget, doc_type in [
                    (self._stat_certs, "Certificat de Scolarité"),
                    (self._stat_cards, "Carte Étudiant"),
                    (self._stat_convocs, "Convocation"),
                ]:
                    try:
                        cursor.execute("SELECT COUNT(*) FROM DocumentsLog WHERE doc_type=%s", (doc_type,))
                        stat_widget.set_value(str(cursor.fetchone()[0] or 0))
                    except Exception:
                        stat_widget.set_value("0")
        except Exception as e:
            AppLogger.error("AdminDocsWindow", f"Erreur KPI stats: {e}")

    def load_classes(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                classes = AdminDocumentsRepository(conn).list_classes()

            self.combo_class_shared.clear()
            self.combo_class_shared.addItem("-", None)
            for c in classes:
                self.combo_class_shared.addItem(c[1], c[0])
        except Exception as e:
            AppLogger.error("AdminDocuments", f"Error loading classes: {e}")

    def load_students(self, class_combo=None, student_combo=None):
        if class_combo is None or student_combo is None:
            return
        class_id = class_combo.currentData()
        student_combo.clear()
        if not class_id:
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            # FIX 10: Inform the user instead of silently leaving the combo empty
            AppLogger.warning("AdminDocuments", "Aucune année scolaire active trouvée.")
            student_combo.addItem("⚠️ Aucune année active", None)
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = AdminDocumentsRepository(conn).list_active_students_in_class(class_id, active_year)
            for s in rows:
                student_combo.addItem(s[1], s[0])
        except Exception as e:
            AppLogger.error("AdminDocuments", f"Error loading students: {e}")

    def check_photo_status(self):
        sid = self.combo_student_card.currentData()
        colors = ThemeManager.get_colors()

        if not sid:
            self.lbl_photo_status.setText("...")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                path = AdminDocumentsRepository(conn).get_student_photo_path(sid)
            if path and os.path.exists(path):
                self.lbl_photo_status.setText("✅ Photo disponible")
                self.lbl_photo_status.setStyleSheet(f"color: {colors.SUCCESS}; font-weight: bold; margin-left: 10px;")
            else:
                self.lbl_photo_status.setText("❌ Pas de photo")
                self.lbl_photo_status.setStyleSheet(f"color: {colors.DANGER}; font-weight: bold; margin-left: 10px;")
        except Exception:
            self.lbl_photo_status.setText("❌ Erreur DB")

    def upload_student_photo(self):
        sid = self.combo_student_card.currentData()
        if not sid:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un élève d'abord.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Photo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            # FIX 7: Use absolute path anchored to the application directory
            if not os.path.exists(_PHOTOS_DIR):
                os.makedirs(_PHOTOS_DIR)
            ext = os.path.splitext(file_path)[1]
            new_path = os.path.join(_PHOTOS_DIR, f"std_{sid}{ext}")

            try:
                shutil.copy(file_path, new_path)

                db = DatabaseManager()
                with db.get_connection() as conn:
                    AdminDocumentsRepository(conn).update_student_photo_path(sid, new_path)
                    conn.commit()
                self.check_photo_status()
                QMessageBox.information(self, "Succès", "Photo enregistrée avec succès.")
            except Exception as e:
                # FIX 1: friendly_db_error is now imported — this no longer raises NameError
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    def get_common_data(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AdminDocumentsRepository(conn)
                info = repo.get_school_info()
                yr_label = repo.get_active_year_label()
            year = yr_label or "202X"
            return info, year
        except Exception:
            return None, "202X"

    def get_student_data(self, sid):
        # FIX 3: Use cached _active_year_id instead of opening a second DB connection
        active_year = self._active_year_id
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = AdminDocumentsRepository(conn)
                res = repo.get_student_full_data(sid, active_year)
                due_rows = repo.get_student_dues(sid, active_year)

                dues_map = {}
                month_names = {
                    10: "Octobre",
                    11: "Novembre",
                    12: "Décembre",
                    1: "Janvier",
                    2: "Février",
                    3: "Mars",
                    4: "Avril",
                    5: "Mai",
                    6: "Juin",
                }

                for fee_type, fee_description, net_amount, due_date, is_paid in due_rows:
                    key = None
                    fee_type_str = str(fee_type or "")
                    fee_desc = str(fee_description or "")
                    fee_desc_low = fee_desc.lower()

                    if fee_type_str == "Registration" or "inscription" in fee_desc_low:
                        key = "Inscription"
                    else:
                        try:
                            due_month = int(str(due_date or "").split("-")[1])
                            key = month_names.get(due_month)
                        except Exception:
                            key = None

                    if not key:
                        continue

                    amount_val = float(net_amount or 0)
                    existing = dues_map.get(key)
                    if existing:
                        try:
                            prev_amount = float(existing.get('amount', '0').replace(' ', '').replace(',', ''))
                        except Exception:
                            prev_amount = 0.0
                        amount_val = prev_amount + amount_val

                    date_txt = ""
                    try:
                        date_txt = datetime.strptime(str(due_date), "%Y-%m-%d").strftime("%d/%m") if due_date else ""
                    except Exception:
                        date_txt = ""

                    # FIX 9 (dues_map): OR the paid status — any payment for this month marks it paid
                    prev_paid = existing.get('paid', False) if existing else False
                    dues_map[key] = {
                        'amount': f"{amount_val:,.0f}".replace(",", " "),
                        'date': date_txt,
                        'paid': bool(is_paid) or prev_paid,
                    }

            if res:
                return {
                    'id': res[0],
                    'name': res[1],
                    'dob': res[2].strftime("%d/%m/%Y") if res[2] else "",
                    'birth_place': res[3] or "",
                    'class': res[4] or "-",
                    'parent': res[5],
                    'photo': res[6],
                    'address': res[7] or "",
                    'phone': res[8] or "",
                    'reg_date': res[9] or "",
                    'class_number': res[10] if len(res) > 10 else None,
                    'student_code': res[11] if len(res) > 11 else None,
                    'dues_map': dues_map,
                }
            return None
        except Exception as e:
            AppLogger.error("AdminDocuments", f"Error fetching student data: {e}")
            return None

    def print_certificate(self):
        sid = self.combo_student_cert.currentData()
        if not sid:
            return

        info, year = self.get_common_data()
        std = self.get_student_data(sid)

        # FIX 2: Guard against None student data before accessing dict keys
        if std is None:
            QMessageBox.warning(self, "Erreur", "Données de l'élève introuvables. Veuillez réessayer.")
            return

        pdf = DocumentPDF(info, year)
        pdf.generate_certificat_scolarite(std)
        output_pdf(
            pdf,
            self,
            f"Certificat_{sid}.pdf",
            mode=ADMIN_DOCS_OUTPUT_MODE,
            dialog_title="Save PDF",
            file_filter="PDF (*.pdf)",
            success_save_message="Certificat généré.",
            success_print_message="Certificat envoyé à l'imprimante.",
        )

    def print_convocation(self):
        sid = self.combo_student_conv.currentData()
        motif = self.txt_motif.toPlainText()
        # FIX 9: Renamed 'date' → 'conv_date_str' to avoid shadowing Python's date type
        conv_date_str = self.date_conv.date().toString("dd/MM/yyyy")
        if not sid or not motif:
            return

        info, year = self.get_common_data()
        std = self.get_student_data(sid)

        # FIX 2: Guard against None student data
        if std is None:
            QMessageBox.warning(self, "Erreur", "Données de l'élève introuvables. Veuillez réessayer.")
            return

        pdf = DocumentPDF(info, year)
        pdf.generate_convocation(std, motif, conv_date_str)
        output_pdf(
            pdf,
            self,
            f"Convocation_{sid}.pdf",
            mode=ADMIN_DOCS_OUTPUT_MODE,
            dialog_title="Save PDF",
            file_filter="PDF (*.pdf)",
            success_save_message="Convocation générée.",
            success_print_message="Convocation envoyée à l'imprimante.",
        )

    def print_card(self, mode='single'):
        info, year = self.get_common_data()
        pdf = IDCardPDF(info, year)
        pages_generated = 0

        if mode == 'single':
            sid = self.combo_student_card.currentData()
            if not sid:
                return
            std = self.get_student_data(sid)
            # FIX 2: Guard against None student data
            if std is None:
                QMessageBox.warning(self, "Erreur", "Données de l'élève introuvables.")
                return
            pdf.generate_senegal_id_card(std)
            pages_generated = 1
        else:
            cid = self.combo_class_card.currentData()
            if not cid:
                return
            active_year = self.get_active_year_id()
            if active_year == -1:
                QMessageBox.warning(self, "Erreur", "Aucune année scolaire active.")
                return

            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    ids = AdminDocumentsRepository(conn).list_student_ids_in_class(cid, active_year)

                for sid in ids:
                    std = self.get_student_data(sid)
                    if std:
                        pdf.generate_senegal_id_card(std)
                        pages_generated += 1
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération: {e}")
                return

        # FIX 5: Do not call output_pdf on an empty PDF — fpdf2 would crash
        if pages_generated == 0:
            QMessageBox.warning(self, "Attention", "Aucune carte générée. Vérifiez les données des élèves.")
            return

        output_pdf(
            pdf,
            self,
            "Cartes_Etudiant_Senegal.pdf",
            mode=ADMIN_DOCS_OUTPUT_MODE,
            dialog_title="Save PDF",
            file_filter="PDF (*.pdf)",
            success_save_message="Carte(s) générée(s) avec succès.",
            success_print_message="Carte(s) envoyée(s) à l'imprimante.",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminDocsWindow()
    window.show()
    sys.exit(app.exec())
