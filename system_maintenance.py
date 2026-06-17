import datetime
import os
import shutil
import subprocess
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from config_manager import ConfigManager
from database_setup import DatabaseManager
from db_path import find_pg_tool
from ui_components import style_table
from ui_styles import ModuleHeaderWidget, ThemeManager, friendly_db_error, get_module_caps


class SystemMaintenanceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maintenance & Sauvegarde / الصيانة والنسخ الاحتياطي")
        self.setMinimumSize(1100, 700)
        self.config = ConfigManager()

        # Apply theme
        ThemeManager.apply_theme(self)
        # استخدام مسار النسخ الاحتياطي الموحد من ConfigManager
        self.backup_dir = self.config.backup_dir

        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except Exception as e:
            AppLogger.warning(
                "SystemMaintenance", f"Warning: Could not create backup directory at {self.backup_dir}: {e}"
            )

        self.init_ui()
        self.load_backups()

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "system_maintenance")
        self.btn_backup.setEnabled(caps["can_write"])
        self.btn_backup.setVisible(caps["can_write"])
        self.btn_export.setEnabled(caps["can_write"])
        self.btn_export.setVisible(caps["can_write"])
        self.btn_import.setEnabled(caps["can_write"])
        self.btn_import.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. Header
        header = ModuleHeaderWidget(
            "🛡️", "MAINTENANCE & SAUVEGARDE", "مركز النسخ الاحتياطي واستعادة البيانات (PostgreSQL)"
        )
        self._stat_backups = header.add_stat("💾", "Sauvegardes", "0", "#3B82F6")
        self._stat_last = header.add_stat("📅", "Dernière", "—", "#22C55E")
        self._stat_size = header.add_stat("📊", "Taille Totale", "—", "#8B5CF6")
        self.main_layout.addWidget(header)

        colors = ThemeManager.get_colors()

        # 2. Actions Group
        action_group = QGroupBox("Actions Rapides / إجراءات سريعة")
        action_group.setStyleSheet(
            f"""
            QGroupBox {{
                background-color: {colors.BG_CARD}; border-radius: 16px; padding: 15px;
                border: 1px solid {colors.BORDER}; font-weight: bold; color: {colors.TEXT_SECONDARY}; margin-top: 10px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }}
        """
        )

        h_layout = QHBoxLayout(action_group)
        h_layout.setSpacing(20)
        h_layout.setContentsMargins(20, 30, 20, 20)

        # Create Backup Button
        self.btn_backup = QPushButton(" Créer une Sauvegarde Maintenant")
        self.btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_backup.setMinimumHeight(50)
        self.btn_backup.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS}, stop:1 #16A34A); color: white; font-weight: bold; font-size: 14px; border-radius: 10px; border: none; }} QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
        self.btn_backup.clicked.connect(self.create_backup)

        # Export Button
        self.btn_export = QPushButton(" Exporter vers USB/Disque")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setMinimumHeight(50)
        self.btn_export.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER}); color: white; font-weight: bold; font-size: 14px; border-radius: 10px; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        self.btn_export.clicked.connect(self.export_backup)

        # Import Button
        self.btn_import = QPushButton(" Importer depuis USB/Disque")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.setMinimumHeight(50)
        self.btn_import.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SECONDARY}, stop:1 #0284C7); color: white; font-weight: bold; font-size: 14px; border-radius: 10px; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_HOVER}; }}"
        )
        self.btn_import.clicked.connect(self.import_backup)

        h_layout.addWidget(self.btn_backup)
        h_layout.addWidget(self.btn_export)
        h_layout.addWidget(self.btn_import)
        self.main_layout.addWidget(action_group)

        # 3. Backups List
        lbl_list = QLabel("Historique des Sauvegardes / سجل النسخ الاحتياطية:")
        lbl_list.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; margin-top: 10px;")
        self.main_layout.addWidget(lbl_list)

        self.table_backups = QTableWidget()
        style_table(self.table_backups)
        self.table_backups.setColumnCount(4)
        self.table_backups.setHorizontalHeaderLabels(["Nom du Fichier", "Date de Création", "Taille", "Actions"])
        self.table_backups.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.main_layout.addWidget(self.table_backups)

        # Footer Note
        footer_frame = QFrame()
        footer_frame.setStyleSheet(
            f"background-color: {colors.BG_MAIN}; border: 1px dashed {colors.DANGER}; border-radius: 6px;"
        )
        fl = QHBoxLayout(footer_frame)
        lbl_note = QLabel(
            "⚠️ Note: La restauration d'une ancienne sauvegarde écrasera les données actuelles. Assurez-vous qu'aucun autre utilisateur n'est connecté."
        )
        lbl_note.setStyleSheet(f"color: {colors.DANGER}; font-style: italic; background: transparent;")
        fl.addWidget(lbl_note)
        self.main_layout.addWidget(footer_frame)

    def load_backups(self):
        self.table_backups.setRowCount(0)
        if not os.path.exists(self.backup_dir):
            return

        try:
            # البحث عن ملفات .sql أو .backup الخاصة بـ PostgreSQL
            files = [f for f in os.listdir(self.backup_dir) if f.endswith('.sql') or f.endswith('.backup')]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.backup_dir, x)), reverse=True)

            # Update stat chips
            self._stat_backups.set_value(str(len(files)))
            if files:
                mtime = os.path.getmtime(os.path.join(self.backup_dir, files[0]))
                self._stat_last.set_value(datetime.datetime.fromtimestamp(mtime).strftime('%d/%m/%Y'))
                total_bytes = sum(os.path.getsize(os.path.join(self.backup_dir, f)) for f in files)
                self._stat_size.set_value(f"{total_bytes / (1024*1024):.1f} MB")
            else:
                self._stat_last.set_value("—")
                self._stat_size.set_value("—")

            colors = ThemeManager.get_colors()

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
                btn_restore.setStyleSheet(
                    f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.WARNING}, stop:1 #D97706); color: white; font-weight: bold; border-radius: 6px; padding: 5px 10px; border: none; }} QPushButton:hover {{ background: #B45309; }}"
                )
                btn_restore.clicked.connect(lambda ch, fname=f: self.restore_backup(fname))

                btn_delete = QPushButton("Supprimer")
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setStyleSheet(
                    f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.DANGER}, stop:1 #EF4444); color: white; font-weight: bold; border-radius: 6px; padding: 5px 10px; border: none; }} QPushButton:hover {{ background: {colors.DANGER_HOVER}; }}"
                )
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
            dump_command = [pg_dump_exe, "-h", db_host, "-p", db_port, "-U", db_user, "-f", backup_path, db_name]

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            # تنفيذ الأمر
            result = subprocess.run(dump_command, env=env, capture_output=True, text=True)

            QApplication.restoreOverrideCursor()

            if result.returncode == 0:
                self.load_backups()
                QMessageBox.information(self, "Succès", "Sauvegarde créée avec succès (PostgreSQL) !")
            else:
                raise RuntimeError(f"Erreur pg_dump: {result.stderr}")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de la sauvegarde:\nAssurez-vous que les outils PostgreSQL (pg_dump) sont installés et dans le PATH.\nDetails: {str(e)}",
            )

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

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter la sauvegarde", filename, "PostgreSQL Backup Files (*.sql *.backup)"
        )
        if file_path:
            try:
                shutil.copy2(source_path, file_path)
                QMessageBox.information(self, "Succès", "Sauvegarde exportée avec succès !")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur d'exportation: {str(e)}")

    def import_backup(self):
        """استيراد نسخة احتياطية من ملف خارجي إلى مجلد النسخ الاحتياطية الخاص بالبرنامج"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importer une base de données", "", "PostgreSQL Backup Files (*.sql *.backup)"
        )
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
                QMessageBox.information(
                    self, "Succès", "Fichier importé avec succès. Vous pouvez maintenant le restaurer depuis la liste."
                )
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'importation: {str(e)}")

    def restore_backup(self, filename):
        reply = QMessageBox.question(
            self,
            "Danger - Restauration",
            f"Voulez-vous vraiment restaurer la version '{filename}' ?\n\n"
            "⚠️ ATTENTION : Toutes les données actuelles seront effacées et remplacées par cette sauvegarde.\n"
            "Assurez-vous que l'application est la seule connectée à la base de données.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

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
                        "-h",
                        db_host,
                        "-p",
                        db_port,
                        "-U",
                        db_user,
                        "-d",
                        db_name,
                        "-f",
                        source,
                    ]
                else:
                    # إذا كان الملف بصيغة Custom (c) وهو الأرجح من الدالة السابقة
                    restore_command = [
                        find_pg_tool("pg_restore"),
                        "-h",
                        db_host,
                        "-p",
                        db_port,
                        "-U",
                        db_user,
                        "-d",
                        db_name,
                        "--clean",  # إسقاط الكائنات الموجودة
                        "--if-exists",
                        "-1",  # تنفيذ في معاملة واحدة (Transaction)
                        source,
                    ]

                result = subprocess.run(restore_command, env=env, capture_output=True, text=True)

                QApplication.restoreOverrideCursor()

                if result.returncode == 0:
                    QMessageBox.information(
                        self,
                        "Succès",
                        "Restauration terminée avec succès. L'application va se fermer pour rafraîchir les données.",
                    )
                    sys.exit(0)  # الخروج ليقوم المستخدم بإعادة تشغيل البرنامج
                else:
                    error_msg = result.stderr or result.stdout
                    raise RuntimeError(f"pg_restore/psql أرجع رمز الخطأ {result.returncode}:\n{error_msg}")

            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Erreur", f"Échec de la restauration:\n{str(e)}")

    def delete_backup(self, filename):
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Supprimer cette sauvegarde ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(os.path.join(self.backup_dir, filename))
                self.load_backups()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", friendly_db_error(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemMaintenanceWindow()
    window.show()
    sys.exit(app.exec())
