import sys
import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QMessageBox, QHeaderView, 
                             QGroupBox, QTableWidget, QTableWidgetItem, QFileDialog, 
                             QTabWidget, QProgressBar, QFrame, QGridLayout, 
                             QGraphicsDropShadowEffect, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from database_setup import DatabaseManager

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, Colors, get_table_style, get_tabs_style

THEME_AVAILABLE = True

# --- Thread for Sending Emails (يمنع تجمد البرنامج) ---
class EmailWorker(QThread):
    progress = pyqtSignal(int)
    log_signal = pyqtSignal(str, str, str) # email, status, error
    finished = pyqtSignal()

    def __init__(self, smtp_config, recipients, subject, body, attachment):
        super().__init__()
        self.smtp_config = smtp_config
        self.recipients = recipients # list of (id, name, email)
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
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            # تطبيق نمط Deep Slate
            self.setStyleSheet(f"""
                QMainWindow {
                    background-color: {colors.BG_MAIN};
                }
                QLabel {
                    font-family: 'Segoe UI', 'Cairo', sans-serif;
                    color: {colors.TEXT_PRIMARY};
                }
                QGroupBox {
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    margin-top: 10px;
                    background-color: {colors.BG_CARD};
                    font-weight: bold;
                    color: {colors.TEXT_SECONDARY};
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                    left: 10px;
                }
            """)
        
        self.attachment_path = None
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # Header Frame
        header_frame = QFrame()
        bg_header = colors.BG_HEADER

        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_header};
                border-radius: 10px;
            }}
        """)
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
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("إرسال الإشعارات والبريد الإلكتروني")
        sub_lbl.setFont(QFont("Cairo", 11))
        if THEME_AVAILABLE:
            sub_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        else:
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
            colors = Colors()
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 12px; margin-top: 15px; }}
                QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 12px 30px; margin-right: 6px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-family: 'Segoe UI', 'Cairo'; }}
                QTabBar::tab:selected {{ background: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; }}
                QTabBar::tab:hover {{ background: {colors.BORDER}; }}
            """)
        
        self.setup_compose_tab()
        self.setup_settings_tab()
        self.setup_history_tab()
        
        self.layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_CARD}; 
                    border-radius: 12px; 
                    border: 1px solid {colors.BORDER};
                }}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20); shadow.setColor(QColor(15, 23, 42, 15)); shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            le.setStyleSheet(f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        else:
            colors = Colors()
            le.setStyleSheet(f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        combo = QComboBox()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        else:
            colors = Colors()
            combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        combo.setMinimumHeight(38)
        return combo

    def styled_text_edit(self, placeholder=""):
        text_edit = QTextEdit()
        if placeholder:
            text_edit.setPlaceholderText(placeholder)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            text_edit.setStyleSheet(
                f"QTextEdit {{ padding: 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} "
                f"QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
            )
        else:
            colors = Colors()
            text_edit.setStyleSheet(
                f"QTextEdit {{ padding: 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} "
                f"QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}"
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
            table.setStyleSheet(f"""
                QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 8px; border: none; font-weight: bold; }}
            """)

    def setup_compose_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Target Card
        target_card = self.create_card()
        tlay = QHBoxLayout(target_card)
        tlay.setContentsMargins(15, 15, 15, 15)
        
        self.combo_target_type = self.styled_combo()
        self.combo_target_type.addItems(["Parents d'une Classe / أولياء فصل", "Tout le Personnel / كل الموظفين", "Profs Seulement / الأساتذة"])
        self.combo_target_type.currentIndexChanged.connect(self.toggle_class_combo)
        
        self.combo_class = self.styled_combo()
        self.load_classes()
        
        tlay.addWidget(QLabel("Cible:"))
        tlay.addWidget(self.combo_target_type, 1)
        tlay.addWidget(QLabel("Classe:"))
        tlay.addWidget(self.combo_class, 1)
        
        layout.addWidget(target_card)

        # Message Card
        msg_card = self.create_card()
        mlay = QVBoxLayout(msg_card)
        mlay.setContentsMargins(15, 15, 15, 15)
        
        self.txt_subject = self.styled_input("Objet / الموضوع")
        
        self.txt_body = self.styled_text_edit(
            "Message... (Utilisez {NOM} pour insérer le nom du destinataire)"
        )
        
        att_layout = QHBoxLayout()
        self.lbl_attachment = QLabel("Aucun fichier joint")
        if THEME_AVAILABLE:
            self.lbl_attachment.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; font-style: italic;")
        else:
            self.lbl_attachment.setStyleSheet(f"color: {Colors().TEXT_SECONDARY}; font-style: italic;")
        btn_att = QPushButton("📎 Joindre un fichier")
        btn_att.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_att.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
        else:
            colors = Colors()
            btn_att.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; border-radius: 6px; padding: 8px; font-weight: bold;")
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

        # Actions
        btn_send = QPushButton("🚀 ENVOYER / إرسال")
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_send.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; font-size: 14px; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_send.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; font-size: 14px; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_send.clicked.connect(self.send_email)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.progress.setStyleSheet(f"QProgressBar {{ border: 1px solid {colors.BORDER}; border-radius: 6px; text-align: center; color: {colors.TEXT_PRIMARY}; background: {colors.BG_MAIN}; }} QProgressBar::chunk {{ background-color: {colors.SUCCESS}; }}")
        else:
            colors = Colors()
            self.progress.setStyleSheet(f"QProgressBar {{ border: 1px solid {colors.BORDER}; border-radius: 6px; text-align: center; color: {colors.TEXT_PRIMARY}; background: {colors.BG_MAIN}; }} QProgressBar::chunk {{ background-color: {colors.SUCCESS}; }}")
        
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
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_save.setStyleSheet(f"background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px;")
        else:
            colors = Colors()
            btn_save.setStyleSheet(f"background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px;")
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
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_refresh.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 8px;")
        else:
            colors = Colors()
            btn_refresh.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 8px;")
        btn_refresh.clicked.connect(self.load_logs)
        
        layout.addWidget(btn_refresh)
        layout.addWidget(self.table_logs)
        self.tabs.addTab(tab, "  📜 Historique  ")

    # --- Logic ---
    def load_classes(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, class_name_fr FROM Classes")
            rows = cursor.fetchall()
        for c in rows:
            self.combo_class.addItem(c[1], c[0])

    def toggle_class_combo(self):
        # تفعيل قائمة الفصول فقط إذا كان الاختيار "أولياء فصل"
        is_class = (self.combo_target_type.currentIndex() == 0)
        self.combo_class.setEnabled(is_class)

    def attach_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Joindre un fichier")
        if f:
            self.attachment_path = f
            self.lbl_attachment.setText(os.path.basename(f))
            if THEME_AVAILABLE:
                self.lbl_attachment.setStyleSheet(f"color: {ThemeManager.get_colors().SUCCESS}; font-weight: bold;")
            else:
                self.lbl_attachment.setStyleSheet(f"color: {Colors().SUCCESS}; font-weight: bold;")

    def save_settings(self):
        password_value = self.txt_password.text() if self.chk_save_password.isChecked() else ""
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM EmailSettings")
            cursor.execute("INSERT INTO EmailSettings (smtp_server, smtp_port, email_address, email_password) VALUES (?,?,?,?)",
                        (self.txt_smtp_host.text(), self.txt_smtp_port.text(), self.txt_email.text(), password_value))
            conn.commit()
        QMessageBox.information(self, "Succès", "Paramètres sauvegardés.")

    def load_settings(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM EmailSettings LIMIT 1")
            res = cursor.fetchone()
        
        if res:
            self.txt_smtp_host.setText(res[1])
            self.txt_smtp_port.setText(res[2])
            self.txt_email.setText(res[3])
            self.chk_save_password.setChecked(bool(res[4]))
            self.txt_password.clear()

    def get_recipients(self):
        target_idx = self.combo_target_type.currentIndex()
        db = DatabaseManager()
        recipients = []
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if target_idx == 0: # Parents of Class
                cid = self.combo_class.currentData()
                if not cid: return []
                # استخدام parent_email
                cursor.execute("SELECT id, parent_name, parent_email FROM Students WHERE class_id=? AND status='Active'", (cid,))
                for r in cursor.fetchall():
                    recipients.append((r[0], r[1], r[2]))
                    
            elif target_idx == 1: # All Staff
                # استخدام email للموظفين
                cursor.execute("SELECT id, first_name || ' ' || last_name, email FROM Staff WHERE status='Actif'")
                for r in cursor.fetchall():
                    recipients.append((r[0], r[1], r[2]))
                    
            elif target_idx == 2: # Teachers Only
                cursor.execute("SELECT id, first_name || ' ' || last_name, email FROM Staff WHERE status='Actif' AND role LIKE '%Prof%'")
                for r in cursor.fetchall():
                    recipients.append((r[0], r[1], r[2]))
                
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
            'password': self.txt_password.text()
        }

        if not smtp_conf['password']:
            smtp_conf['password'] = os.environ.get("SMTP_PASSWORD", "")

        if not smtp_conf['host'] or not smtp_conf['email']:
            QMessageBox.warning(self, "Erreur", "Veuillez configurer le SMTP d'abord.")
            self.tabs.setCurrentIndex(1)
            return

        if not smtp_conf['password']:
            QMessageBox.warning(self, "Erreur", "Mot de passe SMTP manquant (saisissez-le ou définissez SMTP_PASSWORD).")
            self.tabs.setCurrentIndex(1)
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.worker = EmailWorker(smtp_conf, recipients, self.txt_subject.text(), self.txt_body.toPlainText(), self.attachment_path)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log_result)
        self.worker.finished.connect(self.on_send_finished)
        self.worker.start()

    def log_result(self, email, status, error):
        db = DatabaseManager()
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with db.get_connection() as conn:
            conn.execute("INSERT INTO NotificationLogs (recipient_contact, subject, status, error_msg, sent_at) VALUES (?,?,?,?,?)",
                        (email, self.txt_subject.text(), status, error, dt))
            conn.commit()

    def on_send_finished(self):
        self.progress.setVisible(False)
        QMessageBox.information(self, "Terminé", "Processus d'envoi terminé. Vérifiez l'historique.")
        self.load_logs()

    def load_logs(self):
        self.table_logs.setRowCount(0)
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sent_at, recipient_contact, subject, status FROM NotificationLogs ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()
            
        for r in rows:
            idx = self.table_logs.rowCount()
            self.table_logs.insertRow(idx)
            for c, val in enumerate(r):
                item = QTableWidgetItem(str(val))
                if c == 3:
                    if THEME_AVAILABLE:
                        colors = ThemeManager.get_colors()
                        item.setForeground(QColor(colors.SUCCESS) if val == "Envoyé" else QColor(colors.DANGER))
                    else:
                        colors = Colors()
                        item.setForeground(QColor(colors.SUCCESS) if val == "Envoyé" else QColor(colors.DANGER))
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table_logs.setItem(idx, c, item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommunicationWindow()
    window.show()
    sys.exit(app.exec())