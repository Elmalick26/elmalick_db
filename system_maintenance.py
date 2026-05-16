import sys
import os
import shutil
import datetime
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QMessageBox, QHeaderView,
                             QGroupBox, QFileDialog, QProgressBar, QFrame,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon

from ui_styles import ThemeManager, Colors, get_table_style
from config_manager import ConfigManager
from database_setup import DatabaseManager
from db_path import find_pg_tool
from app_logger import AppLogger

THEME_AVAILABLE = True


class SystemMaintenanceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maintenance & Sauvegarde / الصيانة والنسخ الاحتياطي")
        self.setMinimumSize(1100, 700)
        self.config = ConfigManager()

        # Apply theme
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
            """)

        # استخدام مسار النسخ الاحتياطي الموحد من ConfigManager
        self.backup_dir = self.config.backup_dir

        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except Exception as e:
            AppLogger.warning("SystemMaintenance", f"Warning: Could not create backup directory at {self.backup_dir}: {e}")

        self.init_ui()
        self.load_backups()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # 1. Header Frame
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

        icon_lbl = QLabel("🛡️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_layout = QVBoxLayout()
        header_lbl = QLabel("MAINTENANCE & SAUVEGARDE")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("مركز النسخ الاحتياطي واستعادة البيانات (PostgreSQL)")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")

        title_layout.addWidget(header_lbl)
        title_layout.addWidget(sub_lbl)

        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_layout)
        hl.addStretch()

        self.main_layout.addWidget(header_frame)

        # 2. Actions Group
        action_group = QGroupBox("Actions Rapides / إجراءات سريعة")
        action_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {colors.BG_CARD}; border-radius: 12px; padding: 15px;
                border: 1px solid {colors.BORDER}; font-weight: bold; color: {colors.TEXT_SECONDARY}; margin-top: 10px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }}
        """)

        # Shadow for card
        shadow_card = QGraphicsDropShadowEffect()
        shadow_card.setBlurRadius(20)
        shadow_card.setColor(QColor(15, 23, 42, 15))
        shadow_card.setOffset(0, 4)
        action_group.setGraphicsEffect(shadow_card)

        h_layout = QHBoxLayout(action_group)
        h_layout.setSpacing(20)
        h_layout.setContentsMargins(20, 30, 20, 20)

        # Create Backup Button
        btn_backup = QPushButton(" Créer une Sauvegarde Maintenant")
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup.setMinimumHeight(50)
        btn_backup.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.SUCCESS}; color: white; font-weight: bold;
                font-size: 14px; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
        """)
        btn_backup.clicked.connect(self.create_backup)

        # Export Button
        btn_export = QPushButton(" Exporter vers USB/Disque")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(50)
        btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.PRIMARY}; color: white; font-weight: bold;
                font-size: 14px; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_export.clicked.connect(self.export_backup)

        # Import Button
        btn_import = QPushButton(" Importer depuis USB/Disque")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setMinimumHeight(50)
        btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.SECONDARY}; color: white; font-weight: bold;
                font-size: 14px; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_import.clicked.connect(self.import_backup)

        h_layout.addWidget(btn_backup)
        h_layout.addWidget(btn_export)
        h_layout.addWidget(btn_import)
        self.main_layout.addWidget(action_group)

        # 3. Backups List
        lbl_list = QLabel("Historique des Sauvegardes / سجل النسخ الاحتياطية:")
        lbl_list.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; margin-top: 10px;")
        self.main_layout.addWidget(lbl_list)

        self.table_backups = QTableWidget()
        self.style_table(self.table_backups)
        self.table_backups.setColumnCount(4)
        self.table_backups.setHorizontalHeaderLabels(["Nom du Fichier", "Date de Création", "Taille", "Actions"])
        self.table_backups.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.main_layout.addWidget(self.table_backups)

        # Footer Note
        footer_frame = QFrame()
        footer_frame.setStyleSheet(f"background-color: {colors.BG_MAIN}; border: 1px dashed {colors.DANGER}; border-radius: 6px;")
        fl = QHBoxLayout(footer_frame)
        lbl_note = QLabel("⚠️ Note: La restauration d'une ancienne sauvegarde écrasera les données actuelles. Assurez-vous qu'aucun autre utilisateur n'est connecté.")
        lbl_note.setStyleSheet(f"color: {colors.DANGER}; font-style: italic; background: transparent;")
        fl.addWidget(lbl_note)
        self.main_layout.addWidget(footer_frame)

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER};
                border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY};
            }}
            QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {colors.BG_MAIN}; color: {colors.TEXT_PRIMARY}; }}
            QTableWidget::item:alternate {{ background-color: {colors.BG_MAIN}; }}
            QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
            QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
        """)

    def load_backups(self):
        self.table_backups.setRowCount(0)
        if not os.path.exists(self.backup_dir):
            return

        try:
            # البحث عن ملفات .sql أو .backup الخاصة بـ PostgreSQL
            files = [f for f in os.listdir(self.backup_dir) if f.endswith('.sql') or f.endswith('.backup')]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.backup_dir, x)), reverse=True)

            colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

            for f in files:
                full_path = os.path.join(self.backup_dir, f)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                date_time = datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S')

                row = self.table_backups.rowCount()
                self.table_backups.insertRow(row)

                self.table_backups.setItem(row, 0, QTableWidgetItem(f))
                self.table_backups.setItem(row, 1, QTableWidgetItem(date_time))
                self.table_backups.setItem(row, 2, QTableWidgetItem(f"{size_mb:.2f} MB"))

                # Action Buttons Widget
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(5, 2, 5, 2)
                btn_layout.setSpacing(10)

                btn_restore = QPushButton("Restaurer")
                btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_restore.setStyleSheet(f"""
                    QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 4px; padding: 5px; border: none; }}
                    QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
                """)
                btn_restore.clicked.connect(lambda ch, fname=f: self.restore_backup(fname))

                btn_delete = QPushButton("Supprimer")
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setStyleSheet(f"""
                    QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; border-radius: 4px; padding: 5px; border: none; }}
                    QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
                """)
                btn_delete.clicked.connect(lambda ch, fname=f: self.delete_backup(fname))

                btn_layout.addWidget(btn_restore)
                btn_layout.addWidget(btn_delete)
                self.table_backups.setCellWidget(row, 3, btn_widget)
        except Exception as e:
            AppLogger.error("SystemMaintenance", f"Error loading backups: {e}")

    def _is_custom_backup_file(self, file_path):
        """Detect PostgreSQL custom-format dump by file signature (PGDMP)."""
        try:
            with open(file_path, "rb") as f:
                return f.read(5) == b"PGDMP"
        except Exception:
            return False

    def create_backup(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f"backup_postgres_{timestamp}.sql"  # صيغة SQL نقية للتوافقية العالية
            backup_path = os.path.join(self.backup_dir, backup_name)

            # جلب بيانات الاتصال من ConfigManager
            db_host = self.config.db_host
            db_port = str(self.config.db_port)
            db_name = self.config.db_name
            db_user = self.config.db_user
            db_password = self.config.db_password

            # إعداد البيئة لتمرير كلمة المرور لـ pg_dump دون أن يطلبها
            env = os.environ.copy()
            env["PGPASSWORD"] = db_password

            # بناء أمر pg_dump — صيغة SQL نقية (ليست Custom format)
            pg_dump_exe = find_pg_tool("pg_dump")
            dump_command = [
                pg_dump_exe,
                "-h", db_host,
                "-p", db_port,
                "-U", db_user,
                "-f", backup_path,
                db_name
            ]

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            # تنفيذ الأمر
            result = subprocess.run(dump_command, env=env, capture_output=True, text=True)

            QApplication.restoreOverrideCursor()

            if result.returncode == 0:
                self.load_backups()
                QMessageBox.information(self, "Succès", "Sauvegarde créée avec succès (PostgreSQL) !")
            else:
                raise Exception(f"Erreur pg_dump: {result.stderr}")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Erreur", f"Échec de la sauvegarde:\nAssurez-vous que les outils PostgreSQL (pg_dump) sont installés et dans le PATH.\nDetails: {str(e)}")

    def export_backup(self):
        selected_row = self.table_backups.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une sauvegarde dans la liste pour l'exporter.")
            return

        filename = self.table_backups.item(selected_row, 0).text()
        source_path = os.path.join(self.backup_dir, filename)

        if not os.path.exists(source_path):
            QMessageBox.warning(self, "Erreur", "Le fichier de sauvegarde est introuvable.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter la sauvegarde", filename, "PostgreSQL Backup Files (*.sql *.backup)")
        if file_path:
            try:
                shutil.copy2(source_path, file_path)
                QMessageBox.information(self, "Succès", "Sauvegarde exportée avec succès !")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur d'exportation: {str(e)}")

    def import_backup(self):
        """استيراد نسخة احتياطية من ملف خارجي إلى مجلد النسخ الاحتياطية الخاص بالبرنامج"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Importer une base de données", "", "PostgreSQL Backup Files (*.sql *.backup)")
        if file_path:
            try:
                # ننسخ الملف إلى مجلد الـ backups ليظهر في القائمة
                filename = os.path.basename(file_path)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                # نضيف Timestamp لتجنب تكرار الأسماء
                new_filename = f"import_{timestamp}_{filename}"
                dest_path = os.path.join(self.backup_dir, new_filename)

                shutil.copy2(file_path, dest_path)

                self.load_backups()
                QMessageBox.information(self, "Succès", "Fichier importé avec succès. Vous pouvez maintenant le restaurer depuis la liste.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'importation: {str(e)}")

    def restore_backup(self, filename):
        reply = QMessageBox.question(self, "Danger - Restauration",
                                     f"Voulez-vous vraiment restaurer la version '{filename}' ?\n\n"
                                     "⚠️ ATTENTION : Toutes les données actuelles seront effacées et remplacées par cette sauvegarde.\n"
                                     "Assurez-vous que l'application est la seule connectée à la base de données.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. Safety backup of current state just in case
                self.create_backup()

                # 2. Restore selected backup
                source = os.path.join(self.backup_dir, filename)

                # جلب بيانات الاتصال من ConfigManager
                db_host = self.config.db_host
                db_port = str(self.config.db_port)
                db_name = self.config.db_name
                db_user = self.config.db_user
                db_password = self.config.db_password

                env = os.environ.copy()
                env["PGPASSWORD"] = db_password

                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

                # تنظيف قاعدة البيانات الحالية قبل الاستعادة (اختياري ولكنه ينصح به مع pg_restore لتجنب التعارض)
                # ملاحظة: أوامر الاستعادة تختلف إذا كان الملف .sql نقي أو .backup مخصص.

                is_custom = self._is_custom_backup_file(source)

                if not is_custom:
                    # إذا كان الملف نصي عادي
                    restore_command = [
                        find_pg_tool("psql"),
                        "-h", db_host,
                        "-p", db_port,
                        "-U", db_user,
                        "-d", db_name,
                        "-f", source
                    ]
                else:
                    # إذا كان الملف بصيغة Custom (c) وهو الأرجح من الدالة السابقة
                    restore_command = [
                        find_pg_tool("pg_restore"),
                        "-h", db_host,
                        "-p", db_port,
                        "-U", db_user,
                        "-d", db_name,
                        "--clean",  # إسقاط الكائنات الموجودة
                        "--if-exists",
                        "-1",  # تنفيذ في معاملة واحدة (Transaction)
                        source
                    ]

                result = subprocess.run(restore_command, env=env, capture_output=True, text=True)

                QApplication.restoreOverrideCursor()

                if result.returncode == 0:
                    QMessageBox.information(self, "Succès", "Restauration terminée avec succès. L'application va se fermer pour rafraîchir les données.")
                    sys.exit(0)  # الخروج ليقوم المستخدم بإعادة تشغيل البرنامج
                else:
                    error_msg = result.stderr if result.stderr else result.stdout
                    raise Exception(f"pg_restore/psql أرجع رمز الخطأ {result.returncode}:\n{error_msg}")

            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Erreur", f"Échec de la restauration:\n{str(e)}")

    def delete_backup(self, filename):
        reply = QMessageBox.question(self, "Confirmation", "Supprimer cette sauvegarde ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(os.path.join(self.backup_dir, filename))
                self.load_backups()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemMaintenanceWindow()
    window.show()
    sys.exit(app.exec())
