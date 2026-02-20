import sys
import os
import shutil
import datetime
from db_path import DB_PATH
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QMessageBox, QHeaderView, 
                             QGroupBox, QFileDialog, QProgressBar, QFrame,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon

from ui_styles import ThemeManager, Colors, get_table_style

THEME_AVAILABLE = True


class SystemMaintenanceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maintenance & Sauvegarde / الصيانة والنسخ الاحتياطي")
        self.setMinimumSize(1100, 700)

        # Apply theme
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)

        self.db_name = DB_PATH
        self.backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

        self.init_ui()
        self.load_backups()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame
        header_frame = QFrame()
        if THEME_AVAILABLE:
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {ThemeManager.get_colors().BG_HEADER};
                    border-radius: 10px;
                }}
            """)
        else:
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors().BG_HEADER};
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
        
        icon_lbl = QLabel("🛡️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("MAINTENANCE & SAUVEGARDE")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {Colors().HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("مركز النسخ الاحتياطي واستعادة البيانات")
        sub_lbl.setFont(QFont("Cairo", 11))
        if THEME_AVAILABLE:
            sub_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        else:
            sub_lbl.setStyleSheet(f"color: {Colors().TEXT_SECONDARY}; background: transparent;")
        
        title_layout.addWidget(header_lbl)
        title_layout.addWidget(sub_lbl)
        
        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_layout)
        hl.addStretch()
        
        self.main_layout.addWidget(header_frame)

        # 2. Actions Group
        action_group = QGroupBox("Actions Rapides / إجراءات سريعة")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            action_group.setStyleSheet(
                f"background-color: {colors.BG_CARD}; border-radius: 12px; padding: 15px; border: 1px solid {colors.BORDER};"
            )
        else:
            colors = Colors()
            action_group.setStyleSheet(
                f"background-color: {colors.BG_CARD}; border-radius: 12px; padding: 15px; border: 1px solid {colors.BORDER};"
            )
        
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
        btn_backup.setIcon(QIcon()) # Add icon if available, unicode used in text
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup.setMinimumHeight(50)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_backup.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.SUCCESS}; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 14px;
                    border-radius: 8px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_backup.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.SUCCESS}; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 14px;
                    border-radius: 8px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_backup.clicked.connect(self.create_backup)
        
        # Export Button
        btn_export = QPushButton(" Exporter vers USB/Disque")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setMinimumHeight(50)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_export.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 14px;
                    border-radius: 8px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_export.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 14px;
                    border-radius: 8px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_export.clicked.connect(self.export_backup)

        h_layout.addWidget(btn_backup)
        h_layout.addWidget(btn_export)
        self.main_layout.addWidget(action_group)

        # 3. Backups List
        lbl_list = QLabel("Historique des Sauvegardes / سجل النسخ الاحتياطية:")
        if THEME_AVAILABLE:
            lbl_list.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; margin-top: 10px;")
        else:
            lbl_list.setStyleSheet(f"font-weight: bold; color: {Colors().TEXT_PRIMARY}; margin-top: 10px;")
        self.main_layout.addWidget(lbl_list)
        
        self.table_backups = QTableWidget()
        self.style_table(self.table_backups)
        self.table_backups.setColumnCount(4)
        self.table_backups.setHorizontalHeaderLabels(["Nom du Fichier", "Date de Création", "Taille", "Actions"])
        self.table_backups.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.main_layout.addWidget(self.table_backups)

        # Footer Note
        footer_frame = QFrame()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            footer_frame.setStyleSheet(f"background-color: {colors.BG_MAIN}; border: 1px dashed {colors.DANGER}; border-radius: 6px;")
        else:
            colors = Colors()
            footer_frame.setStyleSheet(f"background-color: {colors.BG_MAIN}; border: 1px dashed {colors.DANGER}; border-radius: 6px;")
        fl = QHBoxLayout(footer_frame)
        lbl_note = QLabel("⚠️ Note: La restauration d'une ancienne sauvegarde écrasera les données actuelles. Soyez prudent.")
        if THEME_AVAILABLE:
            lbl_note.setStyleSheet(f"color: {ThemeManager.get_colors().DANGER}; font-style: italic; background: transparent;")
        else:
            lbl_note.setStyleSheet(f"color: {Colors().DANGER_HOVER}; font-style: italic; background: transparent;")
        fl.addWidget(lbl_note)
        self.main_layout.addWidget(footer_frame)

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {colors.BG_CARD};
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    gridline-color: {colors.BORDER};
                    font-size: 13px;
                    color: {colors.TEXT_PRIMARY};
                }}
                QTableWidget::item {{
                    padding: 8px;
                    border-bottom: 1px solid {colors.BG_MAIN};
                    color: {colors.TEXT_PRIMARY};
                }}
                QTableWidget::item:alternate {{
                    background-color: {colors.BG_MAIN};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors.PRIMARY};
                    color: white;
                }}
                QHeaderView::section {{
                    background-color: {colors.BG_HEADER};
                    color: {colors.HEADER_TEXT};
                    padding: 10px;
                    border: none;
                    font-weight: bold;
                }}
            """)
        else:
            colors = Colors()
            table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {colors.BG_CARD};
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    gridline-color: {colors.BORDER};
                    font-size: 13px;
                    color: {colors.TEXT_PRIMARY};
                }}
                QTableWidget::item {{
                    padding: 8px;
                    border-bottom: 1px solid {colors.BG_MAIN};
                }}
                QTableWidget::item:alternate {{
                    background-color: {colors.BG_MAIN};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors.PRIMARY};
                    color: {colors.HEADER_TEXT};
                }}
                QHeaderView::section {{
                    background-color: {colors.BG_HEADER};
                    color: {colors.HEADER_TEXT};
                    padding: 10px;
                    border: none;
                    font-weight: bold;
                }}
            """)

    def load_backups(self):
        self.table_backups.setRowCount(0)
        try:
            files = [f for f in os.listdir(self.backup_dir) if f.endswith('.db') or f.endswith('.bak')]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.backup_dir, x)), reverse=True)
            
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
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    btn_restore.setStyleSheet(f"""
                        QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 4px; padding: 5px; border: none; }}
                        QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
                    """)
                else:
                    colors = Colors()
                    btn_restore.setStyleSheet(f"""
                        QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 4px; padding: 5px; border: none; }}
                        QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
                    """)
                btn_restore.clicked.connect(lambda ch, fname=f: self.restore_backup(fname))
                
                btn_delete = QPushButton("Supprimer")
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    btn_delete.setStyleSheet(f"""
                        QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; border-radius: 4px; padding: 5px; border: none; }}
                        QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
                    """)
                else:
                    colors = Colors()
                    btn_delete.setStyleSheet(f"""
                        QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; border-radius: 4px; padding: 5px; border: none; }}
                        QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
                    """)
                btn_delete.clicked.connect(lambda ch, fname=f: self.delete_backup(fname))
                
                btn_layout.addWidget(btn_restore)
                btn_layout.addWidget(btn_delete)
                self.table_backups.setCellWidget(row, 3, btn_widget)
        except Exception as e:
            # استخدام logging or AppLogger if imported
            pass

    def create_backup(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f"backup_auto_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            shutil.copy2(self.db_name, backup_path)
            
            self.load_backups()
            QMessageBox.information(self, "Succès", "Sauvegarde créée avec succès !")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la sauvegarde: {str(e)}")

    def export_backup(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        default_name = f"School_DB_{timestamp}.db"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter la base de données", default_name, "Database Files (*.db)")
        if file_path:
            try:
                shutil.copy2(self.db_name, file_path)
                QMessageBox.information(self, "Succès", "Base de données exportée !")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur d'exportation: {str(e)}")

    def restore_backup(self, filename):
        reply = QMessageBox.question(self, "Danger - Restauration", 
                                     f"Voulez-vous vraiment restaurer la version '{filename}' ?\n\n"
                                     "⚠️ ATTENTION : Toutes les données actuelles seront remplacées.\n"
                                     "Le programme devra redémarrer.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. Safety backup
                self.create_backup()
                
                source = os.path.join(self.backup_dir, filename)
                shutil.copy2(source, self.db_name)
                
                QMessageBox.information(self, "Succès", "Restauration terminée. L'application va se fermer.")
                sys.exit(0) 
                
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de la restauration: {str(e)}")

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