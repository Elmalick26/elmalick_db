import os
import sys
from datetime import date, datetime

from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt, QTime, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from print_export_service import get_report_output_mode, output_pdf
from repositories.discipline_repo import DisciplineRepository
from ui_styles import ModuleHeaderWidget, ThemeManager, friendly_db_error, get_module_caps, get_tabs_style

DISCIPLINE_OUTPUT_MODE = get_report_output_mode("student_discipline_mode", "print")

from pdf_helpers import ARABIC_SUPPORT
from pdf_helpers import prepare_pdf_text as _prepare_pdf_text
from pdf_helpers import setup_pdf_arabic_font
from ui_components import (
    BaseDialog,
    card_frame,
    dialog_button_row,
    dialog_error_label,
    section_label,
    style_table,
    styled_button,
    styled_combo,
    styled_date_edit,
    styled_input,
    styled_time_edit,
)


def fix_text(text):
    return _prepare_pdf_text(text)


# --- فئة تقارير الانضباط ---


class DisciplinePDF(FPDF):
    def __init__(self, school_info):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.school_info = school_info

        self.font_family = 'Arial'
        if ARABIC_SUPPORT:
            setup_pdf_arabic_font(self)
            self.font_family = 'ArabicFont'

    def sanitize(self, text):
        return fix_text(text)

    def header(self):
        left_x, left_y = 10, 5
        self.set_xy(left_x, left_y)
        self.set_font(self.font_family, '', 8)

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

        right_x = 175
        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None

        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=20, h=22)
            except Exception:
                pass
        self.set_xy(right_x, left_y + 22)
        self.set_y(self.get_y() + 2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, '', 8)
        self.cell(0, 10, fix_text('Document généré par le système - وثيقة مستخرجة من النظام'), 0, 0, 'C')

    def create_convocation(self, data):
        self.add_page()

        self.set_font(self.font_family, 'B', 18)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 15, fix_text("CONVOCATION / استدعاء ولي أمر"), 1, 1, 'C', True)
        self.ln(15)

        self.set_font(self.font_family, '', 14)

        self.cell(0, 10, fix_text("A l'attention du Tuteur de l'élève :"), 0, 1, 'L')
        self.set_font(self.font_family, 'B', 16)
        self.cell(0, 10, fix_text(f"   {data['name']}"), 0, 1, 'L')
        self.set_font(self.font_family, '', 14)
        self.cell(0, 10, fix_text(f"   Classe: {data['class']}"), 0, 1, 'L')
        if data.get('session'):
            self.cell(0, 10, fix_text(f"   Séance: {data['session']}"), 0, 1, 'L')

        self.ln(10)
        self.multi_cell(
            0,
            10,
            fix_text(
                "Monsieur/Madame,\n\n"
                "Vous êtes prié(e) de bien vouloir vous présenter à la direction de l'école "
                "le plus tôt possible (ou à la date indiquée ci-dessous) pour une affaire concernant votre enfant.\n"
            ),
        )

        self.ln(5)
        self.set_font(self.font_family, 'B', 14)
        self.cell(0, 10, fix_text("Motif de la convocation / سبب الاستدعاء :"), 0, 1, 'L')

        self.set_font(self.font_family, '', 12)
        self.set_fill_color(255, 245, 245)
        self.multi_cell(
            0, 10, fix_text(f"\n{data['inc']} (Date: {data['date']})\n\nDétails: {data['obs']}\n"), 1, 'L', True
        )

        self.ln(20)

        self.set_font(self.font_family, 'B', 12)
        self.cell(95, 10, fix_text("Signature du Tuteur"), 0, 0, 'C')
        self.cell(95, 10, fix_text("Le Directeur / Administration"), 0, 1, 'C')

    def create_sanction_notice(self, data):
        self.add_page()

        self.set_font(self.font_family, 'B', 20)
        self.set_text_color(200, 0, 0)
        self.cell(0, 15, fix_text("NOTIFICATION DE SANCTION / إشعار بعقوبة"), 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(10)

        self.set_font(self.font_family, 'B', 14)
        self.cell(0, 10, fix_text(f"Élève : {data['name']}   -   Classe : {data['class']}"), 0, 1, 'C')
        if data.get('session'):
            self.set_font(self.font_family, '', 12)
            self.cell(0, 8, fix_text(f"Séance : {data['session']}"), 0, 1, 'C')
            self.set_font(self.font_family, 'B', 14)
        self.line(40, self.get_y(), 170, self.get_y())
        self.ln(15)

        self.set_font(self.font_family, '', 14)
        self.multi_cell(
            0, 10, fix_text("Suite aux faits relevés, le Conseil de Discipline a décidé de la sanction suivante :\n")
        )

        self.ln(5)
        self.set_font(self.font_family, 'B', 24)
        self.set_fill_color(230, 230, 230)
        self.multi_cell(0, 20, fix_text(data['sanction']), 1, 'C', True)

        self.ln(10)
        if float(data['pts'] or 0) > 0:
            self.set_text_color(200, 0, 0)
            self.set_font(self.font_family, 'B', 16)
            self.cell(0, 10, fix_text(f"DÉDUCTION DE POINTS (Conduite) : -{data['pts']}"), 0, 1, 'C')
            self.set_text_color(0, 0, 0)
            self.ln(10)

        self.set_font(self.font_family, 'B', 12)
        self.cell(0, 10, fix_text("Détails de l'infraction :"), 0, 1, 'L')
        self.set_font(self.font_family, '', 12)
        self.multi_cell(
            0,
            8,
            fix_text(
                f"Type: {data['inc']}\nDate: {data['date']}\nSéance: {data.get('session', 'Hors séance')}\nObservation: {data['obs']}"
            ),
        )

    def create_history_report(self, rows, meta):
        self.add_page()
        self.set_font(self.font_family, 'B', 14)
        self.cell(0, 10, fix_text("RAPPORT HISTORIQUE DISCIPLINE"), 0, 1, 'C')
        self.set_font(self.font_family, '', 10)
        self.cell(0, 8, fix_text(f"Période: {meta.get('date_from', '')} -> {meta.get('date_to', '')}"), 0, 1, 'C')
        self.cell(0, 8, fix_text(f"Filtres: {meta.get('filters', 'Tous')}"), 0, 1, 'C')
        self.ln(2)

        self.set_font(self.font_family, 'B', 9)
        self.cell(25, 8, "Date", 1, 0, 'C')
        self.cell(45, 8, "Eleve", 1, 0, 'C')
        self.cell(50, 8, "Seance", 1, 0, 'C')
        self.cell(35, 8, "Incident", 1, 0, 'C')
        self.cell(35, 8, "Sanction", 1, 1, 'C')

        self.set_font(self.font_family, '', 8)
        for row in rows:
            self.cell(25, 7, fix_text(str(row.get('date', ''))), 1, 0, 'L')
            self.cell(45, 7, fix_text(str(row.get('name', ''))), 1, 0, 'L')
            self.cell(50, 7, fix_text(str(row.get('session', 'Hors séance'))), 1, 0, 'L')
            self.cell(35, 7, fix_text(str(row.get('incident', ''))), 1, 0, 'L')
            self.cell(35, 7, fix_text(str(row.get('sanction', ''))), 1, 1, 'L')

        self.ln(30)
        self.set_font(self.font_family, 'B', 12)
        self.cell(0, 10, fix_text("Le Directeur / Le Surveillant Général"), 0, 1, 'R')


class DisciplineEntryDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__("➕ Discipline Entry / تسجيل مخالفة", parent)
        self.setModal(True)
        self.setMinimumWidth(720)
        self.setMinimumHeight(640)
        self._build_ui()
        self.load_classes()

    def _build_ui(self):
        colors = ThemeManager.get_colors()

        header = QLabel('Nouveau Signalement / تسجيل مخالفة')
        header.setStyleSheet(f'font-size:16px; font-weight:bold; color:{colors.DANGER};')
        self.dialog_layout.addWidget(header)

        self._err_lbl = dialog_error_label()
        self.dialog_layout.addWidget(self._err_lbl)

        # ── Tab widget ────────────────────────────────────────────────────────
        self._inner_tabs = QTabWidget()
        self._inner_tabs.setStyleSheet(get_tabs_style())

        # ════════════════════ TAB 1 : Date & Élève ═══════════════════════════
        tab1 = QWidget()
        t1 = QVBoxLayout(tab1)
        t1.setContentsMargins(12, 14, 12, 8)
        t1.setSpacing(10)

        t1.addWidget(section_label('📅', 'Date & Contexte / التاريخ والسياق'))

        self.combo_class_entry = styled_combo(min_height=40)
        self.combo_class_entry.currentIndexChanged.connect(self.on_class_entry_changed)

        self.date_incident = styled_date_edit()
        self.date_incident.setCalendarPopup(True)
        self.date_incident.setDate(QDate.currentDate())
        self.date_incident.dateChanged.connect(self.refresh_entry_slot_options)
        self.date_incident.dateChanged.connect(self.load_students_entry)

        self.time_incident = styled_time_edit()
        self.time_incident.setTime(QTime.currentTime())
        self.time_incident.timeChanged.connect(self.on_incident_time_changed)

        self.combo_slot_entry = styled_combo(min_height=40)
        self.combo_slot_entry.addItem('Hors séance / خارج الحصة', -1)
        self.combo_slot_entry.addItem('Auto selon l\'heure', None)
        self.combo_slot_entry.currentIndexChanged.connect(self.on_entry_slot_changed)

        self.lbl_slot_entry_auto = QLabel('Hors séance / خارج الحصة')
        self.lbl_slot_entry_auto.setStyleSheet(f'font-weight:600; color:{colors.TEXT_SECONDARY};')

        g1 = QGridLayout()
        g1.setSpacing(10)
        g1.setColumnStretch(1, 1)
        g1.setColumnStretch(3, 1)
        g1.addWidget(QLabel('Classe:'), 0, 0)
        g1.addWidget(self.combo_class_entry, 0, 1)
        g1.addWidget(QLabel('Date:'), 0, 2)
        g1.addWidget(self.date_incident, 0, 3)
        g1.addWidget(QLabel('Heure:'), 1, 0)
        g1.addWidget(self.time_incident, 1, 1)
        g1.addWidget(QLabel('Séance:'), 1, 2)
        g1.addWidget(self.combo_slot_entry, 1, 3)
        g1.addWidget(QLabel('Contexte:'), 2, 0)
        g1.addWidget(self.lbl_slot_entry_auto, 2, 1, 1, 3)
        t1.addLayout(g1)

        t1.addWidget(section_label('👤', 'Élève & Période / الطالب والفترة'))

        self.combo_student_entry = styled_combo(min_height=40)
        self.combo_student_entry.addItem('-', None)

        self.lbl_period_entry_auto = QLabel('Détectée automatiquement / تُحدَّد تلقائياً')
        self.lbl_period_entry_auto.setStyleSheet(f'font-weight:600; color:{colors.TEXT_SECONDARY};')

        g2 = QGridLayout()
        g2.setSpacing(10)
        g2.setColumnStretch(1, 1)
        g2.setColumnStretch(3, 1)
        g2.addWidget(QLabel('Élève:'), 0, 0)
        g2.addWidget(self.combo_student_entry, 0, 1)
        g2.addWidget(QLabel('Période:'), 0, 2)
        g2.addWidget(self.lbl_period_entry_auto, 0, 3)
        t1.addLayout(g2)
        t1.addStretch()

        # ════════════════════ TAB 2 : Infraction & Sanction ══════════════════
        tab2 = QWidget()
        t2 = QVBoxLayout(tab2)
        t2.setContentsMargins(12, 14, 12, 8)
        t2.setSpacing(10)

        t2.addWidget(section_label('⚖️', 'Infraction & Sanction / المخالفة والعقوبة'))

        self.combo_type = styled_combo(min_height=40)
        self.combo_type.addItems(
            [
                'Bavardage / ثرثرة',
                'Retard / تأخر',
                'Absence injustifiée / غياب غير مبرر',
                'Non port de la tenue / عدم ارتداء الزي',
                'Insolence / وقاحة',
                'Bagarre / شجار',
                'Tricherie / غش',
                'Dégradation de matériel / تخريب',
            ]
        )

        self.txt_sanction = styled_input('Sanction (ex: Avertissement)', min_height=40)

        self.lbl_points_title = QLabel('Points à déduire (Conduite / 20):')
        self.lbl_points_title.setStyleSheet(f'color:{colors.TEXT_PRIMARY};')
        self.spin_points = QDoubleSpinBox()
        self.spin_points.setRange(0, 20)
        self.spin_points.setPrefix('Déduction: -')
        self.spin_points.setMinimumHeight(42)
        self.spin_points.setStyleSheet(
            f'QDoubleSpinBox {{ padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER};'
            f' border-radius: 8px; background-color: {colors.BG_MAIN}; color: {colors.DANGER}; font-weight: bold; }}'
        )

        self.txt_obs = QTextEdit()
        self.txt_obs.setPlaceholderText('Détails de l\'incident...')
        self.txt_obs.setMinimumHeight(90)
        self.txt_obs.setStyleSheet(
            f'QTextEdit {{ padding: 9px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px;'
            f' background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}'
            f'QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; }}'
        )

        g3 = QGridLayout()
        g3.setSpacing(10)
        g3.setColumnStretch(1, 1)
        g3.setColumnStretch(3, 1)
        g3.addWidget(QLabel('Type:'), 0, 0)
        g3.addWidget(self.combo_type, 0, 1)
        g3.addWidget(QLabel('Sanction:'), 0, 2)
        g3.addWidget(self.txt_sanction, 0, 3)
        g3.addWidget(self.lbl_points_title, 1, 0)
        g3.addWidget(self.spin_points, 1, 1, 1, 3)
        g3.addWidget(QLabel('Observation:'), 2, 0, Qt.AlignmentFlag.AlignTop)
        g3.addWidget(self.txt_obs, 2, 1, 1, 3)
        t2.addLayout(g3)
        t2.addStretch()

        self._inner_tabs.addTab(tab1, '  📅 Date & Élève  ')
        self._inner_tabs.addTab(tab2, '  ⚖️ Infraction & Sanction  ')
        self.dialog_layout.addWidget(self._inner_tabs)

        # ── Connexion changement de tab ───────────────────────────────────────
        self._inner_tabs.currentChanged.connect(self._on_tab_changed)

        # ── Barre de navigation (identique à StudentDialog) ───────────────────
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self._btn_prev = styled_button(
            '← Précédent',
            bg_color='transparent',
            text_color=colors.TEXT_SECONDARY,
            hover_color=colors.BG_MAIN,
            min_height=38,
        )
        self._btn_prev.setEnabled(False)
        self._btn_prev.setStyleSheet(
            self._btn_prev.styleSheet()
            + f'QPushButton:disabled {{ color:{colors.BORDER}; border:1.5px solid {colors.BORDER}; }}'
        )
        self._btn_prev.clicked.connect(self._go_prev)

        self._btn_next = styled_button('Suivant →', min_height=38)
        self._btn_next.clicked.connect(self._go_next)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f'color:{colors.BORDER};')

        self.btn_save_new = QPushButton('💾+  Enregistrer & Nouveau')
        self.btn_save_new.setMinimumHeight(38)
        self.btn_save_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_new.setStyleSheet(
            f'QPushButton {{ background:transparent; color:{colors.PRIMARY};'
            f' font-weight:700; font-size:12px; border-radius:7px;'
            f' border:2px solid {colors.PRIMARY}; padding:6px 16px; }}'
            f'QPushButton:hover {{ background:{colors.PRIMARY_LIGHT}; }}'
        )
        self.btn_save_new.clicked.connect(lambda: self._save_incident(save_and_new=True))
        self.btn_save_new.setVisible(False)

        self.btn_save = styled_button(
            '💾  Enregistrer', bg_color=colors.SUCCESS, hover_color=colors.SUCCESS_HOVER, min_height=38
        )
        self.btn_save.clicked.connect(lambda: self._save_incident(save_and_new=False))
        self.btn_save.setVisible(False)

        self.btn_cancel = styled_button(
            '✕  Annuler',
            bg_color='transparent',
            text_color=colors.TEXT_SECONDARY,
            hover_color=colors.BG_MAIN,
            min_height=38,
        )
        self.btn_cancel.clicked.connect(self.reject)

        nav_row.addWidget(self._btn_prev)
        nav_row.addWidget(self._btn_next)
        nav_row.addWidget(sep)
        nav_row.addStretch()
        nav_row.addWidget(self.btn_save_new)
        nav_row.addWidget(self.btn_save)
        nav_row.addWidget(self.btn_cancel)
        self.dialog_layout.addLayout(nav_row)

    # ── Navigation entre onglets ──────────────────────────────────────────────

    def _go_prev(self):
        self._inner_tabs.setCurrentIndex(0)

    def _go_next(self):
        """Valide l'onglet 1 avant de passer à l'onglet 2."""
        self._err_lbl.setVisible(False)
        if not self.combo_class_entry.currentData():
            self._err_lbl.setText('Veuillez sélectionner une classe.')
            self._err_lbl.setVisible(True)
            return
        if not self.combo_student_entry.currentData():
            self._err_lbl.setText('Veuillez sélectionner un élève.')
            self._err_lbl.setVisible(True)
            return
        period_txt = self.lbl_period_entry_auto.text().lower()
        if 'aucune' in period_txt or 'لا توجد' in period_txt or 'automatiquement' in period_txt:
            self._err_lbl.setText('Aucune période académique ne couvre cette date pour cette classe.')
            self._err_lbl.setVisible(True)
            return
        self._inner_tabs.setCurrentIndex(1)

    def _on_tab_changed(self, idx: int):
        count = self._inner_tabs.count()
        self._btn_prev.setEnabled(idx > 0)
        self._btn_next.setVisible(idx < count - 1)
        self.btn_save_new.setVisible(idx == count - 1)
        self.btn_save.setVisible(idx == count - 1)
        self._err_lbl.setVisible(False)

    def _format_slot_time_value(self, value):
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        text = str(value or "")
        return text[:5] if len(text) >= 5 else text

    def load_classes(self):
        self.combo_class_entry.clear()
        self.combo_class_entry.addItem("-", None)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                classes = DisciplineRepository(conn).list_classes()
            for cid, name in classes:
                self.combo_class_entry.addItem(name, cid)
        except Exception as e:
            AppLogger.error("DisciplineEntryDialog", f"Error loading classes: {e}")

    def refresh_entry_slot_options(self):
        cid = self.combo_class_entry.currentData()
        date_inc = self.date_incident.date().toString("yyyy-MM-dd")
        current_data = self.combo_slot_entry.currentData()

        self.combo_slot_entry.blockSignals(True)
        self.combo_slot_entry.clear()
        self.combo_slot_entry.addItem("Hors séance / خارج الحصة", -1)
        self.combo_slot_entry.addItem("Auto selon l'heure", None)

        if cid and date_inc:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    slots = DisciplineRepository(conn).list_timetable_slots_for_class_date(cid, date_inc)
                for slot_id, start_time, end_time, subject_name in slots:
                    start_txt = self._format_slot_time_value(start_time)
                    end_txt = self._format_slot_time_value(end_time)
                    self.combo_slot_entry.addItem(f"{start_txt}-{end_txt} | {subject_name or 'Séance'}", slot_id)
            except Exception:
                pass

        if current_data is not None:
            idx = self.combo_slot_entry.findData(current_data)
            self.combo_slot_entry.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.combo_slot_entry.setCurrentIndex(1)
        self.combo_slot_entry.blockSignals(False)

    def on_entry_slot_changed(self):
        slot_data = self.combo_slot_entry.currentData()
        if slot_data in (None, -1):
            self.load_students_entry()
            return
        label = self.combo_slot_entry.currentText()
        time_range = label.split("|", 1)[0].strip() if "|" in label else ""
        start_txt = time_range.split("-", 1)[0].strip() if "-" in time_range else ""
        start_time = QTime.fromString(start_txt, "HH:mm")
        if start_time.isValid():
            self.time_incident.blockSignals(True)
            self.time_incident.setTime(start_time)
            self.time_incident.blockSignals(False)
        self.load_students_entry()

    def on_incident_time_changed(self):
        cid = self.combo_class_entry.currentData()
        date_inc = self.date_incident.date().toString("yyyy-MM-dd")
        time_inc = self.time_incident.time().toString("HH:mm")
        slot_id, _ = self.parent().get_entry_slot_context(cid, date_inc, time_inc) if self.parent() else (None, None)
        if slot_id:
            self.combo_slot_entry.blockSignals(True)
            idx = self.combo_slot_entry.findData(slot_id)
            if idx >= 0:
                self.combo_slot_entry.setCurrentIndex(idx)
            self.combo_slot_entry.blockSignals(False)
        self.load_students_entry()

    def on_class_entry_changed(self):
        self.refresh_entry_slot_options()
        self.load_students_entry()

    def load_students_entry(self):
        cid = self.combo_class_entry.currentData()
        self.combo_student_entry.clear()
        self.combo_student_entry.addItem("-", None)
        self.lbl_period_entry_auto.setText("Détectée automatiquement")
        self.lbl_slot_entry_auto.setText("Contexte séance: Hors séance / سياق الحصة: خارج الحصة")
        if not cid:
            return

        active_year = self.parent().get_active_year_id() if self.parent() else -1
        if active_year == -1:
            self.lbl_period_entry_auto.setText("Aucune année active / لا توجد سنة نشطة")
            return

        try:
            date_inc = self.date_incident.date().toString("yyyy-MM-dd")
            resolved_period_id, resolved_period_name = self.parent().get_entry_period_context(
                cid, date_inc, active_year
            )
            self.lbl_period_entry_auto.setText(
                resolved_period_name or "Aucune période ne couvre cette date / لا توجد فترة تغطي هذا التاريخ"
            )
            if not resolved_period_id:
                return

            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = DisciplineRepository(conn)
                cycle_name = repo.get_cycle_name_for_class(cid)
                students = repo.list_active_students_fullname(cid, active_year)
            is_primary = bool(cycle_name and ("elem" in cycle_name or "prim" in cycle_name or "ibtida" in cycle_name))
            if is_primary:
                self.spin_points.setRange(0, 10)
                self.lbl_points_title.setText("Points à déduire (Note Conduite / 10):")
            else:
                self.spin_points.setRange(0, 20)
                self.lbl_points_title.setText("Points à déduire (Note Conduite / 20):")

            for s in students:
                self.combo_student_entry.addItem(s[1], s[0])

            slot_choice = self.combo_slot_entry.currentData()
            if slot_choice == -1:
                self.lbl_slot_entry_auto.setText("Hors séance / خارج الحصة")
            elif slot_choice is None:
                time_inc = self.time_incident.time().toString("HH:mm")
                slot_id, slot_label = self.parent().get_entry_slot_context(cid, date_inc, time_inc)
                self.lbl_slot_entry_auto.setText(slot_label or "Auto: aucune séance détectée / تلقائي: لا توجد حصة")
            else:
                self.lbl_slot_entry_auto.setText(self.combo_slot_entry.currentText())
        except Exception as e:
            AppLogger.error("DisciplineEntryDialog", f"Error loading students: {e}")

    def _save_incident(self, save_and_new=False):
        sid = self.combo_student_entry.currentData()
        cid = self.combo_class_entry.currentData()
        inc_type = self.combo_type.currentText()
        date_inc = self.date_incident.date().toString("yyyy-MM-dd")
        time_inc = self.time_incident.time().toString("HH:mm")
        sanction = self.txt_sanction.text()
        pts = self.spin_points.value()
        obs = self.txt_obs.toPlainText()

        if not sid:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève.")
            return

        active_year = self.parent().get_active_year_id() if self.parent() else -1
        if active_year == -1:
            return

        try:
            resolved_period_id, resolved_period_name = self.parent().get_entry_period_context(
                cid, date_inc, active_year
            )
            self.lbl_period_entry_auto.setText(resolved_period_name or "Aucune période pour cette date")
            if not resolved_period_id:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Aucune période académique ne couvre cette date pour cette classe. / لا توجد فترة أكاديمية تغطي هذا التاريخ لهذا الفصل.",
                )
                return

            slot_choice = self.combo_slot_entry.currentData()
            resolved_slot_id = None
            if slot_choice == -1:
                resolved_slot_id = None
                self.lbl_slot_entry_auto.setText("Hors séance / خارج الحصة")
            elif slot_choice is None:
                resolved_slot_id, resolved_slot_label = self.parent().get_entry_slot_context(cid, date_inc, time_inc)
                self.lbl_slot_entry_auto.setText(
                    resolved_slot_label or "Auto: aucune séance détectée / تلقائي: لا توجد حصة"
                )
            else:
                resolved_slot_id = slot_choice
                self.lbl_slot_entry_auto.setText(self.combo_slot_entry.currentText())

            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = DisciplineRepository(conn)
                repo.insert_incident(
                    sid,
                    date_inc,
                    inc_type,
                    sanction,
                    pts,
                    obs,
                    active_year,
                    resolved_period_id,
                    resolved_slot_id,
                )
                conn.commit()

            if self.parent():
                self.parent().load_recent()
                self.parent().load_history()

            self.txt_sanction.clear()
            self.txt_obs.clear()
            self.spin_points.setValue(0)

            if save_and_new:
                QMessageBox.information(
                    self, "Succès", "Incident enregistré. Vous pouvez saisir un nouveau signalement."
                )
            else:
                QMessageBox.information(self, "Succès", "Incident enregistré.")
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))


# ---------------------------------------------------------------------------
# Dialog : Modifier un incident existant
# ---------------------------------------------------------------------------


class DisciplineEditDialog(BaseDialog):
    def __init__(self, details: dict, parent=None):
        super().__init__("Modifier l'incident / تعديل المخالفة", parent)
        self.setMinimumWidth(520)
        self._details = details
        self._build_ui()

    def _format_slot_time(self, value):
        if hasattr(value, 'strftime'):
            return value.strftime('%H:%M')
        text = str(value or '')
        return text[:5] if len(text) >= 5 else text

    def _build_ui(self):
        colors = ThemeManager.get_colors()
        details = self._details

        lbl = QLabel(f"Modification: {details['student_name']}")
        lbl.setStyleSheet(f"font-size:14px; font-weight:bold; color:{colors.TEXT_PRIMARY};")
        self.add_widget(lbl)

        # Section 1 : Date & Séance
        self.dialog_layout.addWidget(section_label("📅", "Date & Séance"))

        self.date_edit = styled_date_edit()
        self.date_edit.setDate(QDate.fromString(details['date'], 'yyyy-MM-dd'))

        default_time = '08:00'
        if details.get('slot_start_time'):
            txt = self._format_slot_time(details['slot_start_time'])
            if txt:
                default_time = txt
        self.time_edit = styled_time_edit()
        parsed = QTime.fromString(default_time, 'HH:mm')
        self.time_edit.setTime(parsed if parsed.isValid() else QTime(8, 0))

        self.slot_combo = styled_combo()
        self._fill_slot_options(self.date_edit.date().toString('yyyy-MM-dd'))
        self.date_edit.dateChanged.connect(
            lambda: self._fill_slot_options(self.date_edit.date().toString('yyyy-MM-dd'))
        )
        self.time_edit.timeChanged.connect(self._sync_slot_from_time)

        form1 = QFormLayout()
        form1.setSpacing(10)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form1.addRow('Date:', self.date_edit)
        form1.addRow('Heure:', self.time_edit)
        form1.addRow('Séance:', self.slot_combo)
        self.dialog_layout.addLayout(form1)

        # Section 2 : Infraction & Sanction
        self.dialog_layout.addWidget(section_label("⚖️", "Infraction & Sanction / المخالفة والعقوبة"))

        self.type_combo = styled_combo()
        self.type_combo.addItems(
            [
                'Bavardage / ثرثرة',
                'Retard / تأخر',
                'Absence injustifiée / غياب غير مبرر',
                'Non port de la tenue / عدم ارتداء الزي',
                'Insolence / وقاحة',
                'Bagarre / شجار',
                'Tricherie / غش',
                'Dégradation de matériel / تخريب',
            ]
        )
        self.type_combo.setCurrentText(details['incident'])

        self.sanction_input = styled_input('Sanction')
        self.sanction_input.setText(details['sanction'] or '')

        max_pts = 10 if (self.parent() and self.parent().is_primary_class(details['class_id'])) else 20
        self.points_spin = QDoubleSpinBox()
        self.points_spin.setPrefix('Déduction: -')
        self.points_spin.setRange(0, max_pts)
        self.points_spin.setValue(float(details['points'] or 0))
        self.points_spin.setMinimumHeight(42)
        self.points_spin.setStyleSheet(
            f'QDoubleSpinBox {{ padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER};'
            f' border-radius: 8px; background-color: {colors.BG_MAIN}; color: {colors.DANGER}; font-weight: bold; }}'
        )

        self.obs_input = QTextEdit()
        self.obs_input.setMinimumHeight(80)
        self.obs_input.setText(details['observation'] or '')
        self.obs_input.setStyleSheet(
            f'QTextEdit {{ padding: 9px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px;'
            f' background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}'
            f'QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; }}'
        )

        form2 = QFormLayout()
        form2.setSpacing(10)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form2.addRow('Type:', self.type_combo)
        form2.addRow('Sanction:', self.sanction_input)
        form2.addRow(f'Points (/{max_pts}):', self.points_spin)
        form2.addRow('Observation:', self.obs_input)
        self.dialog_layout.addLayout(form2)

        self.dialog_layout.addLayout(dialog_button_row('✅ Enregistrer', self._on_save, self.reject))

    def _fill_slot_options(self, date_str: str):
        self.slot_combo.blockSignals(True)
        self.slot_combo.clear()
        self.slot_combo.addItem('Hors séance / خارج الحصة', -1)
        self.slot_combo.addItem('Auto selon l\'heure', None)
        class_id = self._details.get('class_id')
        if class_id:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    slots = DisciplineRepository(conn).list_timetable_slots_for_class_date(class_id, date_str)
                for slot_id, start_time, end_time, subject_name in slots:
                    s = self._format_slot_time(start_time)
                    e = self._format_slot_time(end_time)
                    self.slot_combo.addItem(f'{s}-{e} | {subject_name or "Séance"}', slot_id)
            except Exception:
                pass
        timetable_slot_id = self._details.get('timetable_slot_id')
        if timetable_slot_id:
            idx = self.slot_combo.findData(timetable_slot_id)
            self.slot_combo.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.slot_combo.setCurrentIndex(0)
        self.slot_combo.blockSignals(False)

    def _sync_slot_from_time(self):
        if self.slot_combo.currentData() == -1:
            return
        class_id = self._details.get('class_id')
        if not class_id:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                slot = DisciplineRepository(conn).resolve_timetable_slot_context_for_class_datetime(
                    class_id,
                    self.date_edit.date().toString('yyyy-MM-dd'),
                    self.time_edit.time().toString('HH:mm'),
                )
            if slot:
                idx = self.slot_combo.findData(slot[0])
                if idx >= 0:
                    self.slot_combo.blockSignals(True)
                    self.slot_combo.setCurrentIndex(idx)
                    self.slot_combo.blockSignals(False)
        except Exception:
            pass

    def _on_save(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = DisciplineRepository(conn)
                repo.update_incident(
                    self._details['id'],
                    self.date_edit.date().toString('yyyy-MM-dd'),
                    self.type_combo.currentText(),
                    self.sanction_input.text(),
                    self.points_spin.value(),
                    self.obs_input.toPlainText(),
                    None if self.slot_combo.currentData() in (-1, None) else self.slot_combo.currentData(),
                )
                conn.commit()
            if self.parent():
                self.parent().load_history()
                self.parent().load_recent()
            self.accept()
            QMessageBox.information(self, 'Succès', 'Modification enregistrée.')
        except Exception as e:
            QMessageBox.critical(self, 'Erreur', friendly_db_error(e))


class DisciplineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discipline & Sanctions / الانضباط والسلوك")
        self.setMinimumSize(1100, 700)

        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_classes()
        self.load_recent()
        self._load_kpi_stats()

        # Auto-refresh history to keep the register in sync with new incidents.
        self.history_refresh_timer = QTimer(self)
        self.history_refresh_timer.timeout.connect(self._auto_refresh_history)
        self.history_refresh_timer.start(12000)

    # ===== إضافة دالة جلب السنة النشطة لتأمين العمليات =====
    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return DisciplineRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def get_periods_for_class(self, class_id, year_id):
        if not class_id or year_id == -1:
            return []
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return DisciplineRepository(conn).list_periods_for_class(class_id, year_id)
        except Exception:
            return []

    def resolve_period_id_for_class_date(self, class_id, date_str, year_id):
        if not class_id or not date_str or year_id == -1:
            return None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return DisciplineRepository(conn).resolve_period_id_for_class_date(class_id, date_str, year_id)
        except Exception:
            return None

    def get_entry_period_context(self, class_id, date_inc, year_id):
        if not class_id or not date_inc or year_id == -1:
            return None, None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = DisciplineRepository(conn)
                period_id = repo.resolve_period_id_for_class_date(class_id, date_inc, year_id)
                if not period_id:
                    return None, None
                for current_period_id, period_name in repo.list_periods_for_class(class_id, year_id):
                    if current_period_id == period_id:
                        return period_id, period_name
                return period_id, None
        except Exception:
            return None, None

    def _format_slot_time_value(self, value):
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        text = str(value or "")
        return text[:5] if len(text) >= 5 else text

    def get_entry_slot_context(self, class_id, date_inc, time_inc):
        if not class_id or not date_inc or not time_inc:
            return None, None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = DisciplineRepository(conn)
                slot = repo.resolve_timetable_slot_context_for_class_datetime(class_id, date_inc, time_inc)
                if not slot:
                    return None, None
                slot_id, start_time, end_time, subject_name = slot
                label = f"{subject_name or 'Séance planifiée'} ({self._format_slot_time_value(start_time)}-{self._format_slot_time_value(end_time)})"
                return slot_id, label
        except Exception:
            return None, None

    def refresh_entry_slot_options(self):
        cid = self.combo_class_entry.currentData()
        date_inc = self.date_incident.date().toString("yyyy-MM-dd") if hasattr(self, "date_incident") else ""
        current_data = self.combo_slot_entry.currentData() if hasattr(self, "combo_slot_entry") else None

        self.combo_slot_entry.blockSignals(True)
        self.combo_slot_entry.clear()
        self.combo_slot_entry.addItem("Hors séance / خارج الحصة", -1)
        self.combo_slot_entry.addItem("Auto selon l'heure", None)

        if cid and date_inc:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    slots = DisciplineRepository(conn).list_timetable_slots_for_class_date(cid, date_inc)
                for slot_id, start_time, end_time, subject_name in slots:
                    start_txt = self._format_slot_time_value(start_time)
                    end_txt = self._format_slot_time_value(end_time)
                    self.combo_slot_entry.addItem(f"{start_txt}-{end_txt} | {subject_name or 'Séance'}", slot_id)
            except Exception:
                pass

        if current_data is not None:
            idx = self.combo_slot_entry.findData(current_data)
            self.combo_slot_entry.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.combo_slot_entry.setCurrentIndex(1)
        self.combo_slot_entry.blockSignals(False)

    def on_entry_slot_changed(self):
        slot_data = self.combo_slot_entry.currentData()
        if slot_data in (None, -1):
            self.load_students_entry()
            return
        label = self.combo_slot_entry.currentText()
        time_range = label.split("|", 1)[0].strip() if "|" in label else ""
        start_txt = time_range.split("-", 1)[0].strip() if "-" in time_range else ""
        start_time = QTime.fromString(start_txt, "HH:mm")
        if start_time.isValid():
            self.time_incident.blockSignals(True)
            self.time_incident.setTime(start_time)
            self.time_incident.blockSignals(False)
        self.load_students_entry()

    def on_incident_time_changed(self):
        cid = self.combo_class_entry.currentData()
        date_inc = self.date_incident.date().toString("yyyy-MM-dd") if hasattr(self, "date_incident") else ""
        time_inc = self.time_incident.time().toString("HH:mm") if hasattr(self, "time_incident") else ""
        slot_id, _ = self.get_entry_slot_context(cid, date_inc, time_inc)
        if slot_id:
            self.combo_slot_entry.blockSignals(True)
            idx = self.combo_slot_entry.findData(slot_id)
            if idx >= 0:
                self.combo_slot_entry.setCurrentIndex(idx)
            self.combo_slot_entry.blockSignals(False)
        self.load_students_entry()

    def on_class_entry_changed(self):
        self.refresh_entry_slot_options()
        self.load_students_entry()

    def on_class_hist_changed(self):
        cid = self.combo_class_hist.currentData()
        active_year = self.get_active_year_id()
        self.combo_period_hist.clear()
        self.combo_period_hist.addItem("Toutes les périodes", None)
        for period_id, period_name in self.get_periods_for_class(cid, active_year):
            self.combo_period_hist.addItem(period_name, period_id)
        self.load_subjects_for_history()
        self.load_slots_for_history()
        self.load_history()

    def on_subject_hist_changed(self):
        self.load_slots_for_history()
        self.load_history()

    def _format_history_slot_label(self, row):
        day_name = str(row[1] or "")
        start_txt = self._format_slot_time_value(row[2])
        end_txt = self._format_slot_time_value(row[3])
        subject_name = str(row[4] or "Séance")
        return f"{day_name} | {start_txt}-{end_txt} | {subject_name}"

    def load_subjects_for_history(self):
        cid = self.combo_class_hist.currentData() if hasattr(self, "combo_class_hist") else None
        self.combo_subject_hist.clear()
        self.combo_subject_hist.addItem("Toutes les matières", None)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = DisciplineRepository(conn).list_subjects_for_history(cid)
            for subject_id, subject_name in rows:
                self.combo_subject_hist.addItem(subject_name, subject_id)
        except Exception as e:
            AppLogger.error("StudentDiscipline", f"Error loading history subjects: {e}")

    def load_slots_for_history(self):
        cid = self.combo_class_hist.currentData() if hasattr(self, "combo_class_hist") else None
        subject_id = self.combo_subject_hist.currentData() if hasattr(self, "combo_subject_hist") else None
        self.combo_slot_hist.clear()
        self.combo_slot_hist.addItem("Toutes les séances", None)
        if not cid:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = DisciplineRepository(conn).list_slots_for_history(cid, subject_id)
            for row in rows:
                self.combo_slot_hist.addItem(self._format_history_slot_label(row), row[0])
        except Exception as e:
            AppLogger.error("StudentDiscipline", f"Error loading history slots: {e}")

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "student_discipline")
        self._rbac_can_write: bool = caps["can_write"]

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(16)

        # 1. En-tête unifié
        header = ModuleHeaderWidget(
            icon="⚖️",
            title="GESTION DE LA DISCIPLINE",
            subtitle="تسجيل المخالفات، العقوبات، واستدعاءات الأولياء",
        )
        self.layout.addWidget(header)
        self._stat_total = header.add_stat("📊", "Total Incidents", "—", "#3B82F6")
        self._stat_month = header.add_stat("📅", "Ce Mois", "—", "#F59E0B")
        self._stat_resolved = header.add_stat("✅", "Résolus", "—", "#22C55E")
        self._stat_serious = header.add_stat("🚨", "Graves", "—", "#EF4444")

        # 2. KPI Cards

        # 3. Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_entry_tab()
        self.setup_history_tab()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.layout.addWidget(self.tabs)

    def _on_tab_changed(self, index):
        if hasattr(self, "history_tab_index") and index == self.history_tab_index:
            self.load_history()

    def _auto_refresh_history(self):
        if hasattr(self, "history_tab_index") and self.tabs.currentIndex() == self.history_tab_index:
            self.load_history()

    def _load_kpi_stats(self):
        """Charge les statistiques de discipline dans les KPI Cards."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Resolve real table name across schema versions.
                cursor.execute(
                    "SELECT to_regclass('public.disciplineincidents'), to_regclass('public.studentdiscipline')"
                )
                reg_incidents, reg_legacy = cursor.fetchone()
                table_name = "DisciplineIncidents" if reg_incidents else ("StudentDiscipline" if reg_legacy else None)
                _ALLOWED_DISCIPLINE_TABLES = {"DisciplineIncidents", "StudentDiscipline"}
                if table_name not in _ALLOWED_DISCIPLINE_TABLES:
                    table_name = None
                if not table_name:
                    self._stat_total.set_value("0")
                    self._stat_month.set_value("0")
                    self._stat_resolved.set_value("0")
                    self._stat_serious.set_value("0")
                    return

                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                    (table_name.lower(),),
                )
                cols = {r[0].lower() for r in cursor.fetchall()}

                date_col = "incident_date" if "incident_date" in cols else ("date" if "date" in cols else None)
                status_col = "status" if "status" in cols else None
                severity_col = (
                    "severity" if "severity" in cols else ("severity_level" if "severity_level" in cols else None)
                )
                points_col = "points_deducted" if "points_deducted" in cols else None

                # Total incidents
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total = cursor.fetchone()[0] or 0

                # Ce mois
                today = date.today()
                if date_col:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE EXTRACT(MONTH FROM {date_col}) = %s AND EXTRACT(YEAR FROM {date_col}) = %s",
                        (today.month, today.year),
                    )
                    month_count = cursor.fetchone()[0] or 0
                else:
                    month_count = 0

                # Résolus
                if status_col:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE LOWER({status_col}) IN ('résolu', 'resolu', 'resolved', 'closed', 'cloture', 'clôturé')"
                    )
                    resolved = cursor.fetchone()[0] or 0
                else:
                    resolved = 0

                # Graves
                serious_filters = []
                if severity_col:
                    serious_filters.append(
                        f"LOWER({severity_col}) IN ('grave', 'sérieux', 'serieux', 'high', 'severe')"
                    )
                if points_col:
                    serious_filters.append(f"{points_col} >= 3")

                if serious_filters:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE " + " OR ".join(serious_filters))
                    serious = cursor.fetchone()[0] or 0
                else:
                    serious = 0

            self._stat_total.set_value(str(total))
            self._stat_month.set_value(str(month_count))
            self._stat_resolved.set_value(str(resolved))
            self._stat_serious.set_value(str(serious))
        except Exception as e:
            AppLogger.error("DisciplineWindow", f"Erreur KPI stats: {e}")
            self._stat_total.set_value("0")
            self._stat_month.set_value("0")
            self._stat_resolved.set_value("0")
            self._stat_serious.set_value("0")

    def setup_entry_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)
        colors = ThemeManager.get_colors()

        toolbar = QHBoxLayout()
        lbl_title = QLabel('Derniers Incidents / آخر المخالفات')
        lbl_title.setStyleSheet(f'font-weight:bold; color:{colors.TEXT_PRIMARY}; font-size:14px;')

        btn_open_entry = QPushButton('➕ Nouveau signalement / تسجيل مخالفة')
        btn_open_entry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_entry.setFixedHeight(32)
        btn_open_entry.setStyleSheet(
            f'QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,'
            f' stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER});'
            f' color:white; border:none; border-radius:7px; font-weight:700;'
            f' font-size:11px; padding:4px 14px; }}'
            f'QPushButton:hover {{ background:{colors.PRIMARY_DARK}; }}'
        )
        btn_open_entry.clicked.connect(self.open_entry_dialog)

        toolbar.addWidget(lbl_title)
        toolbar.addStretch()
        toolbar.addWidget(btn_open_entry)
        layout.addLayout(toolbar)

        self.table_recent = QTableWidget(0, 4)
        style_table(self.table_recent)
        self.table_recent.setHorizontalHeaderLabels(['Élève', 'Date', 'Type', 'Pts'])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_recent.setColumnWidth(3, 50)
        layout.addWidget(self.table_recent)

        self.tabs.addTab(tab, '  📝 Saisie Incident / تسجيل  ')

    def open_entry_dialog(self):
        if not getattr(self, "_rbac_can_write", True):
            QMessageBox.warning(self, "Accès refusé / وصول مرفوض", "ليس لديك صلاحية تسجيل الحوادث.")
            return

        dialog = DisciplineEntryDialog(self)
        dialog.exec()

    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Filter Card
        filter_card = card_frame()
        vlay_f = QVBoxLayout(filter_card)
        vlay_f.setContentsMargins(10, 8, 10, 8)
        vlay_f.setSpacing(6)

        self.combo_class_hist = styled_combo(min_height=32)
        self.combo_class_hist.currentIndexChanged.connect(self.on_class_hist_changed)

        self.combo_period_hist = styled_combo(min_height=32)
        self.combo_period_hist.currentIndexChanged.connect(self.load_history)

        self.combo_subject_hist = styled_combo(min_height=32)
        self.combo_subject_hist.currentIndexChanged.connect(self.on_subject_hist_changed)

        self.combo_slot_hist = styled_combo(min_height=32)
        self.combo_slot_hist.currentIndexChanged.connect(self.load_history)

        self.txt_search = styled_input("🔍 Chercher un élève...", min_height=32)
        self.txt_search.textChanged.connect(self.load_history)

        btn_export_hist = QPushButton("📄 Exporter PDF")
        btn_export_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_hist.setFixedHeight(32)
        colors = ThemeManager.get_colors()
        btn_export_hist.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER});"
            f" color: white; border: none; border-radius: 7px;"
            f" padding: 4px 10px; font-weight: bold; font-size:11px; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_export_hist.clicked.connect(self.export_history_pdf)

        row1_h = QHBoxLayout()
        row1_h.setSpacing(8)
        row1_h.addWidget(self.combo_class_hist, 1)
        row1_h.addWidget(self.combo_period_hist, 1)
        row1_h.addWidget(self.combo_subject_hist, 1)
        row1_h.addWidget(self.combo_slot_hist, 1)

        row2_h = QHBoxLayout()
        row2_h.setSpacing(8)
        row2_h.addWidget(self.txt_search, 1)
        row2_h.addWidget(btn_export_hist)

        vlay_f.addLayout(row1_h)
        vlay_f.addLayout(row2_h)
        layout.addWidget(filter_card)

        # Table
        self.table_history = QTableWidget(0, 8)
        style_table(self.table_history)
        self.table_history.setHorizontalHeaderLabels(
            ["Élève", "Classe", "Date", "Séance", "Incident", "Sanction", "Pts", "Action"]
        )
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_history.setColumnWidth(0, 50)
        self.table_history.setColumnWidth(6, 60)
        self.table_history.itemClicked.connect(self.on_history_item_clicked)
        layout.addWidget(self.table_history)

        self.history_tab_index = self.tabs.addTab(tab, "  📋 Historique & Rapports / السجل  ")

    # --- Logic ---
    def load_classes(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                classes = DisciplineRepository(conn).list_classes()

            if hasattr(self, "combo_class_entry"):
                self.combo_class_entry.clear()
            self.combo_class_hist.clear()
            self.combo_period_hist.clear()
            self.combo_subject_hist.clear()
            self.combo_slot_hist.clear()

            if hasattr(self, "combo_class_entry"):
                self.combo_class_entry.addItem("-", None)
            self.combo_class_hist.addItem("Toutes", None)
            self.combo_period_hist.addItem("Toutes les périodes", None)
            self.combo_subject_hist.addItem("Toutes les matières", None)
            self.combo_slot_hist.addItem("Toutes les séances", None)

            for c in classes:
                if hasattr(self, "combo_class_entry"):
                    self.combo_class_entry.addItem(c[1], c[0])
                self.combo_class_hist.addItem(c[1], c[0])
            self.load_subjects_for_history()
            self.load_slots_for_history()
        except Exception as e:
            AppLogger.error("StudentDiscipline", f"Error loading classes: {e}")

    # ===== تعديل مهم: جلب الطلاب من SCN بناءً على السنة النشطة =====
    def load_students_entry(self):
        cid = self.combo_class_entry.currentData()
        self.combo_student_entry.clear()
        self.lbl_period_entry_auto.setText("Détectée automatiquement")
        self.lbl_slot_entry_auto.setText("Contexte séance: Hors séance / سياق الحصة: خارج الحصة")
        if not cid:
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            self.lbl_period_entry_auto.setText("Aucune année active / لا توجد سنة نشطة")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = DisciplineRepository(conn)
                date_inc = self.date_incident.date().toString("yyyy-MM-dd")
                resolved_period_id, resolved_period_name = self.get_entry_period_context(cid, date_inc, active_year)
                self.lbl_period_entry_auto.setText(
                    resolved_period_name or "Aucune période ne couvre cette date / لا توجد فترة تغطي هذا التاريخ"
                )
                if not resolved_period_id:
                    return
                cycle_name = repo.get_cycle_name_for_class(cid)

                is_primary = bool(
                    cycle_name and ("elem" in cycle_name or "prim" in cycle_name or "ibtida" in cycle_name)
                )

                if is_primary:
                    self.spin_points.setRange(0, 10)
                    self.lbl_points_title.setText("Points à déduire (Note Conduite / 10):")
                else:
                    self.spin_points.setRange(0, 20)
                    self.lbl_points_title.setText("Points à déduire (Note Conduite / 20):")

                students = repo.list_active_students_fullname(cid, active_year)
                for s in students:
                    self.combo_student_entry.addItem(s[1], s[0])

                slot_choice = self.combo_slot_entry.currentData() if hasattr(self, "combo_slot_entry") else -1
                if slot_choice == -1:
                    self.lbl_slot_entry_auto.setText("Hors séance / خارج الحصة")
                elif slot_choice is None:
                    time_inc = self.time_incident.time().toString("HH:mm") if hasattr(self, "time_incident") else ""
                    slot_id, slot_label = self.get_entry_slot_context(cid, date_inc, time_inc)
                    self.lbl_slot_entry_auto.setText(slot_label or "Auto: aucune séance détectée / تلقائي: لا توجد حصة")
                else:
                    self.lbl_slot_entry_auto.setText(self.combo_slot_entry.currentText())
        except Exception as e:
            AppLogger.error("StudentDiscipline", f"Error loading students: {e}")

    def save_incident(self):
        if not getattr(self, "_rbac_can_write", True):
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Accès refusé / وصول مرفوض", "ليس لديك صلاحية تسجيل الحوادث.")
            return
        sid = self.combo_student_entry.currentData()
        cid = self.combo_class_entry.currentData()
        inc_type = self.combo_type.currentText()
        date_inc = self.date_incident.date().toString("yyyy-MM-dd")
        time_inc = self.time_incident.time().toString("HH:mm") if hasattr(self, "time_incident") else ""
        sanction = self.txt_sanction.text()
        pts = self.spin_points.value()
        obs = self.txt_obs.toPlainText()

        if not sid:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève.")
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = DisciplineRepository(conn)
                resolved_period_id, resolved_period_name = self.get_entry_period_context(cid, date_inc, active_year)
                self.lbl_period_entry_auto.setText(resolved_period_name or "Aucune période pour cette date")
                if not resolved_period_id:
                    QMessageBox.warning(
                        self,
                        "Erreur",
                        "Aucune période académique ne couvre cette date pour cette classe. / لا توجد فترة أكاديمية تغطي هذا التاريخ لهذا الفصل.",
                    )
                    return

                slot_choice = self.combo_slot_entry.currentData() if hasattr(self, "combo_slot_entry") else -1
                resolved_slot_id = None
                if slot_choice == -1:
                    resolved_slot_id = None
                    self.lbl_slot_entry_auto.setText("Hors séance / خارج الحصة")
                elif slot_choice is None:
                    resolved_slot_id, resolved_slot_label = self.get_entry_slot_context(cid, date_inc, time_inc)
                    self.lbl_slot_entry_auto.setText(
                        resolved_slot_label or "Auto: aucune séance détectée / تلقائي: لا توجد حصة"
                    )
                else:
                    resolved_slot_id = slot_choice
                    self.lbl_slot_entry_auto.setText(self.combo_slot_entry.currentText())

                repo.insert_incident(
                    sid,
                    date_inc,
                    inc_type,
                    sanction,
                    pts,
                    obs,
                    active_year,
                    resolved_period_id,
                    resolved_slot_id,
                )
                conn.commit()

            self.load_recent()
            self.load_history()
            self.txt_sanction.clear()
            self.txt_obs.clear()
            self.spin_points.setValue(0)
            QMessageBox.information(self, "Succès", "Incident enregistré.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    def load_recent(self):
        self.table_recent.setRowCount(0)
        active_year = self.get_active_year_id()
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = DisciplineRepository(conn).get_recent_incidents(active_year)
            for r in rows:
                idx = self.table_recent.rowCount()
                self.table_recent.insertRow(idx)
                self.table_recent.setItem(idx, 0, QTableWidgetItem(str(r[0]) if r[0] else "-"))
                self.table_recent.setItem(idx, 1, QTableWidgetItem(str(r[1]) if r[1] else ""))
                self.table_recent.setItem(idx, 2, QTableWidgetItem(str(r[2]) if r[2] else "-"))

                pts_item = QTableWidgetItem(f"-{r[3]}")
                pts_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                pts_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table_recent.setItem(idx, 3, pts_item)
        except Exception as e:
            AppLogger.error("StudentDiscipline", f"Error loading recent: {e}")

    # ===== تعديل مهم: جلب الفصول من SCN =====
    def get_incident_details(self, incident_id):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                result = DisciplineRepository(conn).get_incident_details(incident_id)
            if not result:
                return None
            return result
        except Exception as e:
            AppLogger.error("StudentDiscipline", f"Error fetching incident details: {e}")
            return None

    def is_primary_class(self, class_id):
        if not class_id:
            return False
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cycle_name = DisciplineRepository(conn).get_cycle_name_for_class(class_id)
            if not cycle_name:
                return False
            return "elem" in cycle_name or "prim" in cycle_name or "ibtida" in cycle_name
        except Exception:
            return False

    def load_history(self):
        self.table_history.setRowCount(0)
        cid = self.combo_class_hist.currentData()
        pid = self.combo_period_hist.currentData()
        subject_id = self.combo_subject_hist.currentData() if hasattr(self, "combo_subject_hist") else None
        slot_id = self.combo_slot_hist.currentData() if hasattr(self, "combo_slot_hist") else None
        search = self.txt_search.text()
        active_year = self.get_active_year_id()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = DisciplineRepository(conn).get_history(
                    active_year,
                    class_id=cid,
                    period_id=pid,
                    subject_id=subject_id,
                    timetable_slot_id=slot_id,
                    search=search,
                )

            self._history_rows = []

            for r in rows:
                idx = self.table_history.rowCount()
                self.table_history.insertRow(idx)

                # تخزين الـ ID في العنصر الأول
                name_item = QTableWidgetItem(str(r[1] or "-"))
                name_item.setData(Qt.ItemDataRole.UserRole, r[0])  # ID

                self.table_history.setItem(idx, 0, name_item)
                self.table_history.setItem(idx, 1, QTableWidgetItem(str(r[2] or "-")))
                self.table_history.setItem(idx, 2, QTableWidgetItem(str(r[3] or "-")))
                slot_text = (
                    f"{self._format_slot_time_value(r[8])}-{self._format_slot_time_value(r[9])} | {r[10]}"
                    if r[8] and r[9]
                    else "Hors séance"
                )
                self.table_history.setItem(idx, 3, QTableWidgetItem(slot_text))
                self.table_history.setItem(idx, 4, QTableWidgetItem(str(r[4] or "-")))
                self.table_history.setItem(idx, 5, QTableWidgetItem(str(r[5] or "-")))
                self.table_history.setItem(idx, 6, QTableWidgetItem(str(r[6] or "-")))

                btn_print = QPushButton("🖨️")
                btn_print.setToolTip("Imprimer Convocation / Notification")
                btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
                colors = ThemeManager.get_colors()
                btn_print.setStyleSheet(
                    f"""
                    QPushButton {{ background-color: {colors.PRIMARY}; color: white; border-radius: 4px; border: none; font-weight: bold; }}
                    QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
                """
                )
                data = {
                    'name': r[1],
                    'class': r[2] or "-",
                    'inc': r[4],
                    'date': r[3],
                    'obs': r[7],
                    'sanction': r[5],
                    'pts': r[6],
                    'session': slot_text,
                }
                self._history_rows.append(
                    {
                        'name': r[1],
                        'class': r[2] or "-",
                        'date': r[3],
                        'session': slot_text,
                        'incident': r[4],
                        'sanction': r[5],
                        'points': r[6],
                        'observation': r[7],
                    }
                )
                btn_print.clicked.connect(lambda ch, d=data: self.print_action(d))

                w = QWidget()
                l = QHBoxLayout(w)  # noqa: E741
                l.setContentsMargins(0, 0, 0, 0)
                l.addWidget(btn_print)
                self.table_history.setCellWidget(idx, 7, w)
        except Exception as e:
            AppLogger.error("StudentDiscipline", f"Error loading history: {e}")

    def export_history_pdf(self):
        rows = getattr(self, "_history_rows", [])
        if not rows:
            QMessageBox.information(self, "Information", "Aucune donnée filtrée à exporter.")
            return

        class_label = self.combo_class_hist.currentText() if hasattr(self, "combo_class_hist") else "Toutes"
        period_label = self.combo_period_hist.currentText() if hasattr(self, "combo_period_hist") else "Toutes"
        subject_label = self.combo_subject_hist.currentText() if hasattr(self, "combo_subject_hist") else "Toutes"
        slot_label = self.combo_slot_hist.currentText() if hasattr(self, "combo_slot_hist") else "Toutes"
        search_text = self.txt_search.text().strip() if hasattr(self, "txt_search") else ""

        filters = f"Classe={class_label}; Période={period_label}; Matière={subject_label}; Séance={slot_label}"
        if search_text:
            filters += f"; Recherche={search_text}"

        school_info = None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                school_info = DisciplineRepository(conn).get_school_info()
        except Exception:
            pass

        pdf = DisciplinePDF(school_info)
        pdf.create_history_report(
            rows,
            {
                'date_from': rows[-1].get('date', ''),
                'date_to': rows[0].get('date', ''),
                'filters': filters,
            },
        )
        output_pdf(
            pdf,
            self,
            "Historique_Discipline_Filtre.pdf",
            mode=DISCIPLINE_OUTPUT_MODE,
            dialog_title="Enregistrer PDF",
            success_save_message="Rapport PDF de l'historique généré.",
            success_print_message="Rapport d'historique envoyé à l'imprimante.",
        )

    def on_history_item_clicked(self, item):
        row = item.row()
        name_item = self.table_history.item(row, 0)
        if not name_item:
            return

        try:
            incident_id = name_item.data(Qt.ItemDataRole.UserRole)
            if not incident_id:
                return
        except Exception:
            return
        details = self.get_incident_details(incident_id)
        if not details:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Action")
        msg.setText("Choisir une action / اختر العملية:")
        btn_view = msg.addButton("Voir / عرض", QMessageBox.ButtonRole.ActionRole)
        btn_edit = msg.addButton("Modifier / تعديل", QMessageBox.ButtonRole.ActionRole)
        btn_delete = msg.addButton("Supprimer / حذف", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_view:
            self.show_incident_details(details)
        elif msg.clickedButton() == btn_edit:
            self.open_edit_dialog(details)
        elif msg.clickedButton() == btn_delete:
            self.delete_incident(details['id'], details['student_name'])

    def show_incident_details(self, details):
        info = (
            f"Elève: {details['student_name']}\n"
            f"Classe: {details['class_name']}\n"
            f"Date: {details['date']}\n"
            f"Séance: {(self._format_slot_time_value(details.get('slot_start_time')) + '-' + self._format_slot_time_value(details.get('slot_end_time')) + ' | ' + str(details.get('slot_subject') or '')) if details.get('slot_start_time') and details.get('slot_end_time') else 'Hors séance'}\n"
            f"Incident: {details['incident']}\n"
            f"Sanction: {details['sanction']}\n"
            f"Pts: -{details['points']}\n"
            f"Note: {details['observation']}"
        )
        QMessageBox.information(self, "Détails", info)

    def open_edit_dialog(self, details):
        DisciplineEditDialog(details, parent=self).exec()

    def delete_incident(self, incident_id, student_name):
        if (
            QMessageBox.question(
                self,
                "Confirmation",
                f"Supprimer l'incident de {student_name} ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    DisciplineRepository(conn).delete_incident(incident_id)
                    conn.commit()
                self.load_history()
                self.load_recent()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))

    def print_action(self, data):
        msg = QMessageBox()
        msg.setWindowTitle("Impression / طباعة")
        msg.setText("Choisir le document à imprimer:")
        btn_convoc = msg.addButton("Convocation Parents", QMessageBox.ButtonRole.ActionRole)
        btn_sanction = msg.addButton("Notification Sanction", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_cancel:
            return

        school_info = None
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                school_info = DisciplineRepository(conn).get_school_info()
        except Exception:
            pass
        pdf = DisciplinePDF(school_info)

        file_name = "Convocation.pdf" if msg.clickedButton() == btn_convoc else "Sanction.pdf"

        if msg.clickedButton() == btn_convoc:
            pdf.create_convocation(data)
        elif msg.clickedButton() == btn_sanction:
            pdf.create_sanction_notice(data)

        output_pdf(
            pdf,
            self,
            file_name,
            mode=DISCIPLINE_OUTPUT_MODE,
            dialog_title="Enregistrer PDF",
            success_save_message="Document PDF généré.",
            success_print_message="Document envoyé à l'imprimante.",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DisciplineWindow()
    window.show()
    sys.exit(app.exec())
