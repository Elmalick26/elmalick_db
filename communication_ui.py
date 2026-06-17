import os
import smtplib
import sys
import time
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

import security_utils
from app_logger import AppLogger
from constants import PAGE_SIZE_DEFAULT, PASS_AVERAGE, STUDENT_CODE_PREFIX
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
from ui_components import (
    BaseWindow,
    create_card,
    style_table,
    styled_button,
    styled_combo,
    styled_date_edit,
    styled_input,
    styled_text_edit,
)
from ui_styles import (
    Colors,
    ModuleHeaderWidget,
    ThemeManager,
    apply_shadow_to_widget,
    get_card_style,
    get_module_caps,
    get_tabs_style,
)

COMMUNICATION_REPORT_OUTPUT_MODE = get_report_output_mode("communication_report_mode", "save")

# --- Thread for Sending Emails (يمنع تجمد البرنامج) ---


_EMAIL_MAX_RETRIES = 3  # Number of retry attempts per recipient


class EmailWorker(QThread):
    progress = pyqtSignal(int)
    log_signal = pyqtSignal(str, str, str)  # email, status, error
    stats_signal = pyqtSignal(int, int, int)  # total, sent, failed
    finished = pyqtSignal(int, int)  # sent_count, failed_count

    def __init__(self, smtp_config, recipients, subject, body, attachment):
        super().__init__()
        self.smtp_config = smtp_config
        self.recipients = recipients  # list of (id, name, email)
        self.subject = subject
        self.body = body
        self.attachment = attachment
        self._sent = 0
        self._failed = 0

    def _build_message(self, rname, remail):
        msg = MIMEMultipart()
        msg['From'] = self.smtp_config['email']
        msg['To'] = remail
        msg['Subject'] = self.subject
        personalized_body = self.body.replace("{NOM}", rname)
        msg.attach(MIMEText(personalized_body, 'plain'))
        if self.attachment and os.path.exists(self.attachment):
            with open(self.attachment, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(self.attachment))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(self.attachment)}"'
            msg.attach(part)
        return msg

    def _send_with_retry(self, server, rname, remail):
        last_err = None
        for attempt in range(1, _EMAIL_MAX_RETRIES + 1):
            try:
                msg = self._build_message(rname, remail)
                server.send_message(msg)
                return True, ""
            except Exception as e:
                last_err = str(e)
                if attempt < _EMAIL_MAX_RETRIES:
                    time.sleep(0.5 * attempt)
        return False, f"Échec après {_EMAIL_MAX_RETRIES} tentatives: {last_err}"

    def run(self):
        total = len(self.recipients)
        try:
            server = smtplib.SMTP(self.smtp_config['host'], int(self.smtp_config['port']))
            server.starttls()
            server.login(self.smtp_config['email'], self.smtp_config['password'])

            for i, (rid, rname, remail) in enumerate(self.recipients):
                if self.isInterruptionRequested():  # cooperative cancel (window closed)
                    break
                if not remail or "@" not in remail:
                    self._failed += 1
                    self.log_signal.emit(str(remail or rname), "Échec", "Email invalide")
                else:
                    ok, err = self._send_with_retry(server, rname, remail)
                    if ok:
                        self._sent += 1
                        self.log_signal.emit(remail, "Envoyé", "")
                    else:
                        self._failed += 1
                        self.log_signal.emit(remail, "Échec", err)

                self.progress.emit(int((i + 1) / total * 100))
                self.stats_signal.emit(total, self._sent, self._failed)

            server.quit()
        except Exception as e:
            self._failed += max(0, total - self._sent - self._failed)
            self.log_signal.emit("Connexion SMTP", "Erreur SMTP", str(e))

        self.finished.emit(self._sent, self._failed)


class CommunicationWindow(BaseWindow):
    def __init__(self):
        super().__init__("Communication & Emailing / التراسل الإلكتروني", 1100, 700)
        self.current_comm_report_rows = []
        self.current_comm_report_headers = []
        self.current_comm_report_title = ""
        self.attachment_path = None
        self.init_ui()
        self.load_settings()
        self.load_logs()

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return CommunicationRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "communication")
        self.btn_send.setEnabled(caps["can_write"])
        self.btn_send.setVisible(caps["can_write"])

    def init_ui(self):
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # Header
        header = ModuleHeaderWidget("📧", "CENTRE DE MESSAGERIE", "إرسال الإشعارات والبريد الإلكتروني")
        self._stat_total = header.add_stat("📨", "Messages", "0", "#3B82F6")
        self._stat_sent = header.add_stat("✅", "Envoyés", "0", "#22C55E")
        self._stat_failed = header.add_stat("❌", "Échecs", "0", "#EF4444")
        self.main_layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_compose_tab()
        self.setup_settings_tab()
        self.setup_history_tab()
        self.setup_reports_tab()

        self.main_layout.addWidget(self.tabs)

    def style_table(self, table):
        style_table(table)

    def setup_compose_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        target_card, tlay = create_card(layout_class=QHBoxLayout, with_shadow=True)

        self.combo_target_type = styled_combo()
        self.combo_target_type.addItems(
            ["Parents d'une Classe / أولياء فصل", "Tout le Personnel / كل الموظفين", "Profs Seulement / الأساتذة"]
        )
        self.combo_target_type.currentIndexChanged.connect(self.toggle_class_combo)

        self.combo_class = styled_combo()
        self.load_classes()

        tlay.addWidget(QLabel("Cible:"))
        tlay.addWidget(self.combo_target_type, 1)
        tlay.addWidget(QLabel("Classe:"))
        tlay.addWidget(self.combo_class, 1)

        layout.addWidget(target_card)

        msg_card, mlay = create_card(with_shadow=True)
        self.txt_subject = styled_input("Objet / الموضوع")
        self.txt_body = styled_text_edit("Message... (Utilisez {NOM} pour insérer le nom du destinataire)")

        att_layout = QHBoxLayout()
        self.lbl_attachment = QLabel("Aucun fichier joint")
        colors = ThemeManager.get_colors()
        self.lbl_attachment.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-style: italic;")

        btn_att = QPushButton("📎 Joindre un fichier")
        btn_att.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_att.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER}); color: white; border-radius: 8px; padding: 8px 12px; font-weight: bold; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
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

        self.btn_send = QPushButton("🚀 ENVOYER / إرسال")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setMinimumHeight(46)
        self.btn_send.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS}, stop:1 #16A34A); color: white; font-weight: bold; border-radius: 10px; font-size: 14px; border: none; }} QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
        self.btn_send.clicked.connect(self.send_email)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet(
            f"QProgressBar {{ border: 1px solid {colors.BORDER}; border-radius: 6px; text-align: center; color: {colors.TEXT_PRIMARY}; background: {colors.BG_MAIN}; }} QProgressBar::chunk {{ background-color: {colors.SUCCESS}; }}"
        )

        layout.addWidget(self.progress)
        layout.addWidget(self.btn_send)

        self.tabs.addTab(tab, "  📝 Nouveau Message  ")

    def setup_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        grp_card, form = create_card(with_shadow=True)

        form.addWidget(QLabel("Configuration SMTP (Gmail, Outlook...)"))

        self.txt_smtp_host = styled_input("smtp.gmail.com")
        self.txt_smtp_port = styled_input("587")
        self.txt_email = styled_input("votre_email@gmail.com")
        self.txt_password = styled_input("Mot de passe d'application")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.chk_save_password = QCheckBox("Enregistrer le mot de passe (non recommande)")

        btn_save = styled_button(
            "Sauvegarder Configuration",
            bg_color=ThemeManager.get_colors().WARNING,
            hover_color="#B45309",
            min_height=42,
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

        btn_refresh = styled_button(
            "Actualiser",
            bg_color=ThemeManager.get_colors().PRIMARY,
            hover_color=ThemeManager.get_colors().PRIMARY_HOVER,
            min_height=42,
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

        controls_card, controls = create_card(layout_class=QHBoxLayout, with_shadow=True)
        controls.setContentsMargins(15, 15, 15, 15)
        controls.setSpacing(10)

        self.combo_comm_report_type = styled_combo()
        self.combo_comm_report_type.addItem("Synthèse Livraison", "summary")
        self.combo_comm_report_type.addItem("Détail des Envois", "details")

        self.input_comm_from = styled_date_edit()
        self.input_comm_from.setDate(QDate.currentDate().addMonths(-1))

        self.input_comm_to = styled_date_edit()
        self.input_comm_to.setDate(QDate.currentDate())

        btn_generate = styled_button(
            "Générer",
            bg_color=ThemeManager.get_colors().PRIMARY,
            hover_color=ThemeManager.get_colors().PRIMARY_HOVER,
            min_height=38,
        )

        btn_export = styled_button(
            "Exporter PDF",
            bg_color=ThemeManager.get_colors().SUCCESS,
            hover_color=ThemeManager.get_colors().SUCCESS_HOVER,
            min_height=38,
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

        # FIX 4: COMMUNICATION_REPORT_OUTPUT_MODE is already the resolved value;
        # calling get_report_output_mode() again with it as its own default is redundant.
        mode = COMMUNICATION_REPORT_OUTPUT_MODE
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
            colors = ThemeManager.get_colors()
            self.lbl_attachment.setStyleSheet(f"color: {colors.SUCCESS}; font-weight: bold;")

    def save_settings(self):
        password_value = self.txt_password.text() if self.chk_save_password.isChecked() else ""
        try:
            encrypted_pwd = security_utils.encrypt_value(password_value) if password_value else ""
            db = DatabaseManager()
            with db.get_connection() as conn:
                CommunicationRepository(conn).upsert_email_settings(
                    self.txt_smtp_host.text(), self.txt_smtp_port.text(), self.txt_email.text(), encrypted_pwd
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
                stored_pwd = str(res[4] or "")
                if stored_pwd:
                    self.chk_save_password.setChecked(True)
                    self.txt_password.setText(security_utils.decrypt_value(stored_pwd))
                else:
                    self.chk_save_password.setChecked(False)
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

                    # FIX 3: Use the repo already in scope instead of calling
                    # self.get_active_year_id() which opens a second DB connection
                    # while one is already held by this with-block.
                    active_year = repo.get_active_year_id()

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

        # FIX 5: Validate port before handing to EmailWorker — int() inside
        # the thread raises ValueError which surfaces as a cryptic SMTP error.
        try:
            int(smtp_conf['port'])
        except (ValueError, TypeError):
            QMessageBox.warning(self, "Erreur", "Le port SMTP doit être un nombre entier (ex: 587).")
            self.tabs.setCurrentIndex(1)
            return

        if not smtp_conf['password']:
            QMessageBox.warning(
                self, "Erreur", "Mot de passe SMTP manquant (saisissez-le ou définissez SMTP_PASSWORD)."
            )
            self.tabs.setCurrentIndex(1)
            return

        # FIX 2: Stop any in-flight worker before starting a new one.
        # Without this, double-clicking Send spawns two concurrent SMTP sessions
        # and the old thread keeps inserting duplicate log rows after self.worker
        # is overwritten, with no way to stop it.
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_send.setEnabled(False)
        self._stat_total.set_value(str(len(recipients)))
        self._stat_sent.set_value("0")
        self._stat_failed.set_value("0")

        self.worker = EmailWorker(
            smtp_conf, recipients, self.txt_subject.text(), self.txt_body.toPlainText(), self.attachment_path
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log_result)
        self.worker.stats_signal.connect(self._update_send_stats)
        self.worker.finished.connect(self.on_send_finished)
        self.worker.start()

    def stop_background_workers(self) -> None:
        """Stop a running email worker before the shared DB pool is closed.

        This window is embedded in the main dashboard, so its own closeEvent
        never fires — the main window calls this on application shutdown.
        """
        worker = getattr(self, "worker", None)
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            worker.quit()
            worker.wait(3000)

    def log_result(self, email, status, error):
        try:
            db = DatabaseManager()
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with db.get_connection() as conn:
                CommunicationRepository(conn).insert_notification_log(email, self.txt_subject.text(), status, error, dt)
                conn.commit()
        except Exception as e:
            AppLogger.error("CommunicationUI", f"Error logging email: {e}")

    def _update_send_stats(self, total, sent, failed):
        self._stat_total.set_value(str(total))
        self._stat_sent.set_value(str(sent))
        self._stat_failed.set_value(str(failed))

    def on_send_finished(self, sent_count, failed_count):
        self.progress.setVisible(False)
        self.btn_send.setEnabled(True)
        total = sent_count + failed_count
        summary = (
            f"Envoi terminé\n\n"
            f"  Total destinataires : {total}\n"
            f"  ✅ Envoyés          : {sent_count}\n"
            f"  ❌ Échecs           : {failed_count}\n"
        )
        if failed_count > 0:
            summary += "\nConsultez l'historique pour le détail des erreurs."
        AppLogger.info("CommunicationUI", f"Email batch finished: {sent_count} sent, {failed_count} failed")
        QMessageBox.information(self, "Envoi terminé / اكتمل الإرسال", summary)
        self.load_logs()

    def load_logs(self):
        self.table_logs.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = CommunicationRepository(conn).list_notification_logs(limit=PAGE_SIZE_DEFAULT)

            for r in rows:
                idx = self.table_logs.rowCount()
                self.table_logs.insertRow(idx)
                for c, val in enumerate(r):
                    item = QTableWidgetItem(str(val if val is not None else "-"))
                    if c == 3:
                        colors = ThemeManager.get_colors()
                        item.setForeground(QColor(colors.SUCCESS) if val == "Envoyé" else QColor(colors.DANGER))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.table_logs.setItem(idx, c, item)

            # Update stat chips
            total = len(rows)
            sent = sum(1 for r in rows if r[3] == "Envoyé") if rows else 0
            self._stat_total.set_value(str(total))
            self._stat_sent.set_value(str(sent))
            self._stat_failed.set_value(str(total - sent))
        except Exception as e:
            AppLogger.error("CommunicationUI", f"Error loading logs: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommunicationWindow()
    window.show()
    sys.exit(app.exec())
