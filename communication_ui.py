import os
import smtplib
import sys
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psycopg2
from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
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
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    get_school_info_row,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.communication_repo import CommunicationRepository
from ui_styles import Colors, ThemeManager, apply_shadow_to_widget, get_card_style, get_table_style, get_tabs_style

THEME_AVAILABLE = True
COMMUNICATION_REPORT_OUTPUT_MODE = get_report_output_mode("communication_report_mode", "save")

# --- Thread for Sending Emails (يمنع تجمد البرنامج) ---


class EmailWorker(QThread):
    progress = pyqtSignal(int)
    log_signal = pyqtSignal(str, str, str)  # email, status, error
    finished = pyqtSignal()

    def __init__(self, smtp_config, recipients, subject, body, attachment):
        super().__init__()
        self.smtp_config = smtp_config
        self.recipients = recipients  # list of (id, name, email)
        self.subject = subject
        self.body = body
        self.attachment = attachment

    def run(self):
        try:
            server = smtplib.SMTP(self.smtp_config['host'], int(self.smtp_config['port']))
            server.starttls()
            server.login(self.smtp_config['email'], self.smtp_config['password'])

            total = len(self.recipients)
            for i, (rid, rname, remail) in enumerate(self.recipients):
                if not remail or "@" not in remail:
                    self.log_signal.emit(rname, "Échec", "Email invalide")
                    continue

                try:
                    msg = MIMEMultipart()
                    msg['From'] = self.smtp_config['email']
                    msg['To'] = remail
                    msg['Subject'] = self.subject

                    # تخصيص نص الرسالة
                    personalized_body = self.body.replace("{NOM}", rname)
                    msg.attach(MIMEText(personalized_body, 'plain'))

                    if self.attachment:
                        with open(self.attachment, "rb") as f:
                            part = MIMEApplication(f.read(), Name=os.path.basename(self.attachment))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(self.attachment)}"'
                        msg.attach(part)

                    server.send_message(msg)
                    self.log_signal.emit(remail, "Envoyé", "")
                except Exception as e:
                    self.log_signal.emit(remail, "Échec", str(e))

                self.progress.emit(int((i + 1) / total * 100))

            server.quit()
        except Exception as e:
            self.log_signal.emit("Connection", "Erreur SMTP", str(e))

        self.finished.emit()


class CommunicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Communication & Emailing / التراسل الإلكتروني")
        self.setMinimumSize(1100, 700)
        self.current_comm_report_rows = []
        self.current_comm_report_headers = []
        self.current_comm_report_title = ""

        # تطبيق المظهر
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(
                f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER}; border-radius: 8px; margin-top: 10px;
                    background-color: {colors.BG_CARD}; font-weight: bold; color: {colors.TEXT_SECONDARY};
                }}
            """
            )

        self.attachment_path = None
        self.init_ui()
        self.load_settings()

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return CommunicationRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # Header Frame
        header_frame = QFrame()
        header_frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 10px; }}")
        header_frame.setMaximumHeight(80)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)

        icon_lbl = QLabel("📧")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_layout = QVBoxLayout()
        header_lbl = QLabel("CENTRE DE MESSAGERIE")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("إرسال الإشعارات والبريد الإلكتروني")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")

        title_layout.addWidget(header_lbl)
        title_layout.addWidget(sub_lbl)

        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_layout)
        hl.addStretch()

        self.layout.addWidget(header_frame)

        self.tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.tabs.setStyleSheet(get_tabs_style())
        else:
            self.tabs.setStyleSheet(
                f"""
                QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 12px; margin-top: 15px; }}
                QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 12px 30px; margin-right: 6px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-family: 'Segoe UI', 'Cairo'; }}
                QTabBar::tab:selected {{ background: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; }}
                QTabBar::tab:hover {{ background: {colors.BORDER}; }}
            """
            )

        self.setup_compose_tab()
        self.setup_settings_tab()
        self.setup_history_tab()
        self.setup_reports_tab()

        self.layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(
                f"QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}"
            )
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        le.setStyleSheet(
            f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(
            f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        combo.setMinimumHeight(38)
        return combo

    def styled_date(self):
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setMinimumHeight(38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        date_edit.setStyleSheet(
            f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        return date_edit

    def styled_text_edit(self, placeholder=""):
        text_edit = QTextEdit()
        if placeholder:
            text_edit.setPlaceholderText(placeholder)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        text_edit.setStyleSheet(
            f"QTextEdit {{ padding: 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
        )
        return text_edit

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())
        else:
            colors = Colors()
            table.setStyleSheet(
                f"""
                QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 8px; border: none; font-weight: bold; }}
            """
            )

    def setup_compose_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        target_card = self.create_card()
        tlay = QHBoxLayout(target_card)
        tlay.setContentsMargins(15, 15, 15, 15)

        self.combo_target_type = self.styled_combo()
        self.combo_target_type.addItems(
            ["Parents d'une Classe / أولياء فصل", "Tout le Personnel / كل الموظفين", "Profs Seulement / الأساتذة"]
        )
        self.combo_target_type.currentIndexChanged.connect(self.toggle_class_combo)

        self.combo_class = self.styled_combo()
        self.load_classes()

        tlay.addWidget(QLabel("Cible:"))
        tlay.addWidget(self.combo_target_type, 1)
        tlay.addWidget(QLabel("Classe:"))
        tlay.addWidget(self.combo_class, 1)

        layout.addWidget(target_card)

        msg_card = self.create_card()
        mlay = QVBoxLayout(msg_card)
        mlay.setContentsMargins(15, 15, 15, 15)

        self.txt_subject = self.styled_input("Objet / الموضوع")
        self.txt_body = self.styled_text_edit("Message... (Utilisez {NOM} pour insérer le nom du destinataire)")

        att_layout = QHBoxLayout()
        self.lbl_attachment = QLabel("Aucun fichier joint")
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        self.lbl_attachment.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-style: italic;")

        btn_att = QPushButton("📎 Joindre un fichier")
        btn_att.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_att.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;"
        )
        btn_att.clicked.connect(self.attach_file)

        att_layout.addWidget(btn_att)
        att_layout.addWidget(self.lbl_attachment)
        att_layout.addStretch()

        mlay.addWidget(QLabel("Objet:"))
        mlay.addWidget(self.txt_subject)
        mlay.addWidget(QLabel("Message:"))
        mlay.addWidget(self.txt_body)
        mlay.addLayout(att_layout)

        layout.addWidget(msg_card)

        btn_send = QPushButton("🚀 ENVOYER / إرسال")
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.setMinimumHeight(45)
        btn_send.setStyleSheet(
            f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; font-size: 14px; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}"
        )
        btn_send.clicked.connect(self.send_email)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet(
            f"QProgressBar {{ border: 1px solid {colors.BORDER}; border-radius: 6px; text-align: center; color: {colors.TEXT_PRIMARY}; background: {colors.BG_MAIN}; }} QProgressBar::chunk {{ background-color: {colors.SUCCESS}; }}"
        )

        layout.addWidget(self.progress)
        layout.addWidget(btn_send)

        self.tabs.addTab(tab, "  📝 Nouveau Message  ")

    def setup_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        grp_card = self.create_card()
        form = QVBoxLayout(grp_card)
        form.setContentsMargins(20, 20, 20, 20)

        form.addWidget(QLabel("Configuration SMTP (Gmail, Outlook...)"))

        self.txt_smtp_host = self.styled_input("smtp.gmail.com")
        self.txt_smtp_port = self.styled_input("587")
        self.txt_email = self.styled_input("votre_email@gmail.com")
        self.txt_password = self.styled_input("Mot de passe d'application")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.chk_save_password = QCheckBox("Enregistrer le mot de passe (non recommande)")

        btn_save = QPushButton("Sauvegarder Configuration")
        btn_save.setMinimumHeight(40)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_save.setStyleSheet(
            f"background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px; border: none;"
        )
        btn_save.clicked.connect(self.save_settings)

        form.addWidget(QLabel("Serveur SMTP:"))
        form.addWidget(self.txt_smtp_host)
        form.addWidget(QLabel("Port:"))
        form.addWidget(self.txt_smtp_port)
        form.addWidget(QLabel("Email:"))
        form.addWidget(self.txt_email)
        form.addWidget(QLabel("Mot de passe:"))
        form.addWidget(self.txt_password)
        form.addWidget(self.chk_save_password)
        form.addSpacing(10)
        form.addWidget(btn_save)

        layout.addWidget(grp_card)
        layout.addStretch()
        self.tabs.addTab(tab, "  ⚙️ Paramètres SMTP  ")

    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        self.table_logs = QTableWidget(0, 4)
        self.style_table(self.table_logs)
        self.table_logs.setHorizontalHeaderLabels(["Date", "Destinataire", "Sujet", "Statut"])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        btn_refresh = QPushButton("Actualiser")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 8px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}"
        )
        btn_refresh.clicked.connect(self.load_logs)

        layout.addWidget(btn_refresh)
        layout.addWidget(self.table_logs)
        self.tabs.addTab(tab, "  📜 Historique  ")

    def setup_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        controls_card = self.create_card()
        controls = QHBoxLayout(controls_card)
        controls.setContentsMargins(15, 15, 15, 15)
        controls.setSpacing(10)

        self.combo_comm_report_type = self.styled_combo()
        self.combo_comm_report_type.addItem("Synthèse Livraison", "summary")
        self.combo_comm_report_type.addItem("Détail des Envois", "details")

        self.input_comm_from = self.styled_date()
        self.input_comm_from.setDate(QDate.currentDate().addMonths(-1))

        self.input_comm_to = self.styled_date()
        self.input_comm_to.setDate(QDate.currentDate())

        btn_generate = QPushButton("Générer")
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generate.setMinimumHeight(38)

        btn_export = QPushButton("Exporter PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(38)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_generate.setStyleSheet(
            f"background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; border: none;"
        )
        btn_export.setStyleSheet(
            f"background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 6px; border: none;"
        )

        btn_generate.clicked.connect(self.run_communication_report)
        btn_export.clicked.connect(self.export_communication_report_pdf)

        controls.addWidget(QLabel("Rapport:"))
        controls.addWidget(self.combo_comm_report_type)
        controls.addWidget(QLabel("Du:"))
        controls.addWidget(self.input_comm_from)
        controls.addWidget(QLabel("Au:"))
        controls.addWidget(self.input_comm_to)
        controls.addWidget(btn_generate)
        controls.addWidget(btn_export)

        self.table_comm_report = QTableWidget(0, 1)
        self.style_table(self.table_comm_report)
        self.table_comm_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(controls_card)
        layout.addWidget(self.table_comm_report)
        self.tabs.addTab(tab, "  📊 Rapports Livraison  ")

    def run_communication_report(self):
        report_kind = self.combo_comm_report_type.currentData() or "summary"
        date_from = self.input_comm_from.date().toString("yyyy-MM-dd")
        date_to = self.input_comm_to.date().toString("yyyy-MM-dd")
        date_to_full = f"{date_to} 23:59:59"

        headers, rows, title = [], [], ""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = CommunicationRepository(conn)

                if report_kind == "summary":
                    title = "Rapport Synthèse Livraison Emails"
                    headers = ["Statut", "Nombre", "Taux %"]
                    summary = repo.get_notification_log_summary(date_from, date_to_full)
                    total = sum(int(count or 0) for _, count in summary)
                    for status, count in summary:
                        count_int = int(count or 0)
                        rate = (count_int * 100.0 / total) if total else 0.0
                        rows.append([status or "-", count_int, f"{rate:.1f}%"])
                else:
                    title = "Rapport Détail des Envois Emails"
                    headers = ["Date", "Destinataire", "Sujet", "Statut", "Erreur"]
                    for sent_at, recipient, subject, status, error_msg in repo.get_notification_log_detail(
                        date_from, date_to_full
                    ):
                        rows.append(
                            [
                                sent_at or "-",
                                recipient or "-",
                                subject or "-",
                                status or "-",
                                error_msg or "",
                            ]
                        )

            self.current_comm_report_title = title
            self.current_comm_report_headers = headers
            self.current_comm_report_rows = rows

            self.table_comm_report.setColumnCount(len(headers) if headers else 1)
            self.table_comm_report.setHorizontalHeaderLabels(headers or ["Données"])
            self.table_comm_report.setRowCount(0)

            for row_vals in rows:
                idx = self.table_comm_report.rowCount()
                self.table_comm_report.insertRow(idx)
                for col, val in enumerate(row_vals):
                    self.table_comm_report.setItem(idx, col, QTableWidgetItem(str(val)))

            if not rows:
                QMessageBox.information(self, "Information", "Aucune donnée trouvée pour cette période.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de rapport: {e}")

    def export_communication_report_pdf(self):
        if not self.current_comm_report_rows:
            QMessageBox.warning(self, "Attention", "Générez d'abord un rapport avec des données.")
            return

        orientation = 'L' if len(self.current_comm_report_headers) >= 5 else 'P'
        pdf = FPDF(orientation=orientation)
        pdf.add_page()

        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, self.current_comm_report_title)

        period_line = f"Période: {self.input_comm_from.date().toString('dd/MM/yyyy')} - {self.input_comm_to.date().toString('dd/MM/yyyy')}"
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 7, period_line.encode('latin-1', 'ignore').decode('latin-1'), 0, 1, 'C')
        pdf.ln(2)

        table_width = pdf.w - 20
        col_width = table_width / max(1, len(self.current_comm_report_headers))

        apply_table_header_style(pdf, "Arial", 9)
        for header in self.current_comm_report_headers:
            text = str(header).encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(col_width, 8, text, 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, "Arial", 8)
        for row_idx, row_vals in enumerate(self.current_comm_report_rows):
            set_zebra_row_fill(pdf, row_idx)
            for val in row_vals:
                text = str(val).encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(col_width, 7, text, 1, 0, 'C', True)
            pdf.ln()

        mode = get_report_output_mode("communication_report_mode", COMMUNICATION_REPORT_OUTPUT_MODE)
        output_pdf(
            pdf,
            self,
            default_name=f"Rapport_Communication_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=mode,
            dialog_title="Exporter Rapport Communication",
            success_save_message="Rapport communication exporté.",
            success_print_message="Rapport communication envoyé à l'imprimante.",
        )

    # --- Logic ---
    def load_classes(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = CommunicationRepository(conn).list_classes()
            self.combo_class.clear()
            for c in rows:
                self.combo_class.addItem(str(c[1] or "-"), c[0])
        except Exception as e:
            AppLogger.error("CommunicationUI", f"Error loading classes: {e}")

    def toggle_class_combo(self):
        is_class = self.combo_target_type.currentIndex() == 0
        self.combo_class.setEnabled(is_class)

    def attach_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Joindre un fichier")
        if f:
            self.attachment_path = f
            self.lbl_attachment.setText(os.path.basename(f))
            colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
            self.lbl_attachment.setStyleSheet(f"color: {colors.SUCCESS}; font-weight: bold;")

    def save_settings(self):
        password_value = self.txt_password.text() if self.chk_save_password.isChecked() else ""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                CommunicationRepository(conn).upsert_email_settings(
                    self.txt_smtp_host.text(), self.txt_smtp_port.text(), self.txt_email.text(), password_value
                )
                conn.commit()
            QMessageBox.information(self, "Succès", "Paramètres sauvegardés.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de sauvegarde: {e}")

    def load_settings(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                res = CommunicationRepository(conn).get_email_settings()

            if res:
                self.txt_smtp_host.setText(str(res[1] or ""))
                self.txt_smtp_port.setText(str(res[2] or ""))
                self.txt_email.setText(str(res[3] or ""))
                self.chk_save_password.setChecked(bool(res[4]))
                self.txt_password.clear()
        except Exception:
            pass

    def get_recipients(self):
        target_idx = self.combo_target_type.currentIndex()
        recipients = []

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = CommunicationRepository(conn)

                if target_idx == 0:  # Parents of Class
                    cid = self.combo_class.currentData()
                    if not cid:
                        return []

                    active_year = self.get_active_year_id()

                    for r in repo.get_recipients_parents_of_class(cid, active_year):
                        recipients.append((r[0], str(r[1] or "[Parent]"), str(r[2] or "")))

                elif target_idx == 1:  # All Staff
                    for r in repo.get_recipients_all_staff():
                        display_name = str(r[1] or "").strip() or "[Staff]"
                        recipients.append((r[0], display_name, str(r[2] or "")))

                elif target_idx == 2:  # Teachers Only
                    for r in repo.get_recipients_teachers():
                        display_name = str(r[1] or "").strip() or "[Prof]"
                        recipients.append((r[0], display_name, str(r[2] or "")))
        except Exception as e:
            AppLogger.error("CommunicationUI", f"Error fetching recipients: {e}")

        return recipients

    def send_email(self):
        recipients = self.get_recipients()
        if not recipients:
            QMessageBox.warning(self, "Erreur", "Aucun destinataire trouvé (Vérifiez les emails dans les fiches).")
            return

        smtp_conf = {
            'host': self.txt_smtp_host.text(),
            'port': self.txt_smtp_port.text(),
            'email': self.txt_email.text(),
            'password': self.txt_password.text(),
        }

        if not smtp_conf['password']:
            smtp_conf['password'] = os.environ.get("SMTP_PASSWORD", "")

        if not smtp_conf['host'] or not smtp_conf['email']:
            QMessageBox.warning(self, "Erreur", "Veuillez configurer le SMTP d'abord.")
            self.tabs.setCurrentIndex(1)
            return

        if not smtp_conf['password']:
            QMessageBox.warning(
                self, "Erreur", "Mot de passe SMTP manquant (saisissez-le ou définissez SMTP_PASSWORD)."
            )
            self.tabs.setCurrentIndex(1)
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)

        self.worker = EmailWorker(
            smtp_conf, recipients, self.txt_subject.text(), self.txt_body.toPlainText(), self.attachment_path
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log_result)
        self.worker.finished.connect(self.on_send_finished)
        self.worker.start()

    def log_result(self, email, status, error):
        try:
            db = DatabaseManager()
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with db.get_connection() as conn:
                CommunicationRepository(conn).insert_notification_log(email, self.txt_subject.text(), status, error, dt)
                conn.commit()
        except Exception as e:
            AppLogger.error("CommunicationUI", f"Error logging email: {e}")

    def on_send_finished(self):
        self.progress.setVisible(False)
        QMessageBox.information(self, "Terminé", "Processus d'envoi terminé. Vérifiez l'historique.")
        self.load_logs()

    def load_logs(self):
        self.table_logs.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = CommunicationRepository(conn).list_notification_logs(limit=50)

            for r in rows:
                idx = self.table_logs.rowCount()
                self.table_logs.insertRow(idx)
                for c, val in enumerate(r):
                    item = QTableWidgetItem(str(val if val is not None else "-"))
                    if c == 3:
                        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                        item.setForeground(QColor(colors.SUCCESS) if val == "Envoyé" else QColor(colors.DANGER))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.table_logs.setItem(idx, c, item)
        except Exception as e:
            AppLogger.error("CommunicationUI", f"Error loading logs: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommunicationWindow()
    window.show()
    sys.exit(app.exec())
