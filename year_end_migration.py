import sys
from database_setup import DatabaseManager
from db_path import DB_PATH
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QComboBox, QMessageBox, 
                             QHeaderView, QFrame, QGroupBox, QProgressBar, 
                             QCheckBox, QGridLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, Colors, get_table_style

THEME_AVAILABLE = True


class MigrationCalculator(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, db_path, current_year_id, filter_class_id=None):
        super().__init__()
        self.db_path = db_path
        self.current_year_id = current_year_id
        self.filter_class_id = filter_class_id

    def run(self):
        results = []
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()

                class_map = {}
                try:
                    cursor.execute("SELECT id, class_name_fr, cycle_id, sort_order FROM Classes ORDER BY sort_order")
                    for cid, name, cycle_id, order_val in cursor.fetchall():
                        class_map[cid] = {'name': name, 'cycle': cycle_id, 'order': order_val}
                except Exception:
                    cursor.execute("SELECT id, class_name_fr, cycle_id FROM Classes")
                    for cid, name, cycle_id in cursor.fetchall():
                        class_map[cid] = {'name': name, 'cycle': cycle_id, 'order': cid}

                period_ids = []
                try:
                    cursor.execute("SELECT id FROM Periods WHERE school_year_id=?", (self.current_year_id,))
                    period_ids = [row[0] for row in cursor.fetchall()]
                except Exception:
                    period_ids = []

                if self.filter_class_id:
                    cursor.execute("SELECT id, first_name_fr, last_name_fr, class_id FROM Students WHERE status='Active' AND class_id=?", (self.filter_class_id,))
                else:
                    cursor.execute("SELECT id, first_name_fr, last_name_fr, class_id FROM Students WHERE status='Active'")
                students = cursor.fetchall()

                total = max(len(students), 1)
                for i, (std_id, fname, lname, class_id) in enumerate(students):
                    cycle_id = class_map.get(class_id, {}).get('cycle', 0)
                    subjects = []
                    try:
                        cursor.execute("SELECT id, coefficient FROM Subjects WHERE cycle_id=?", (cycle_id,))
                        subjects = cursor.fetchall()
                    except Exception:
                        cursor.execute("SELECT id, coefficient FROM Subjects")
                        subjects = cursor.fetchall()

                    period_avgs = []
                    if period_ids and subjects:
                        for pid in period_ids:
                            total_pts = 0
                            total_coef = 0
                            for sub_id, coef in subjects:
                                cursor.execute("""
                                    SELECT AVG(G.score) FROM Grades G
                                    JOIN AssessmentTypes A ON G.assessment_id = A.id
                                    WHERE G.student_id=? AND G.subject_id=? AND A.period_id=?
                                """, (std_id, sub_id, pid))
                                res = cursor.fetchone()
                                if res and res[0] is not None:
                                    total_pts += res[0] * coef
                                    total_coef += coef
                            period_avgs.append(total_pts / total_coef if total_coef > 0 else 0.0)

                    if period_avgs:
                        avg_annual = sum(period_avgs) / len(period_avgs)
                    else:
                        cursor.execute("SELECT AVG(score) FROM Grades WHERE student_id=?", (std_id,))
                        res = cursor.fetchone()
                        avg_annual = res[0] if res and res[0] is not None else 0.0

                    # --- Decision Logic ---
                    threshold = 10.0
                    cursor.execute("SELECT name_fr FROM Cycles WHERE id=?", (cycle_id,))
                    cname_res = cursor.fetchone()
                    if cname_res:
                        cname = cname_res[0].lower()
                        if "elem" in cname or "prim" in cname:
                            threshold = 5.0

                    decision = "Admis" if avg_annual >= threshold else "Redouble"

                    # --- Next Class Logic ---
                    next_class_id = class_id
                    next_class_name = class_map.get(class_id, {}).get('name', '?') + " (Redouble)"
                    if decision == "Admis":
                        current_order = class_map.get(class_id, {}).get('order', 0)
                        found_next = False
                        for cid, cdata in class_map.items():
                            if cdata['cycle'] == cycle_id and cdata['order'] == current_order + 1:
                                next_class_id = cid
                                next_class_name = cdata['name']
                                found_next = True
                                break
                        if not found_next:
                            next_class_id = None
                            next_class_name = "Fin de Cycle (Orientation)"

                    results.append({
                        'id': std_id,
                        'name': f"{fname} {lname}",
                        'current_class': class_map.get(class_id, {}).get('name', '?'),
                        'avg': avg_annual,
                        'decision': decision,
                        'next_class_id': next_class_id,
                        'next_class_name': next_class_name,
                        'current_class_id': class_id
                    })

                    self.progress.emit(int((i + 1) / total * 100))

        except Exception:
            pass

        self.finished.emit(results)

class MigrationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clôture de l'Année & Migration / الترحيل السنوي")
        self.setMinimumSize(1100, 700)
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            # Deep Slate Theme Application
            self.setStyleSheet(f"""
                QMainWindow {
                    background-color: {colors.BG_MAIN};
                }
                QLabel {
                    font-family: 'Segoe UI', 'Cairo', sans-serif;
                    color: {colors.TEXT_PRIMARY};
                }
                QProgressBar {
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    text-align: center;
                    background-color: {colors.BG_CARD};
                    color: {colors.TEXT_PRIMARY};
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: {colors.PRIMARY};
                    border-radius: 5px;
                }
            """)
        
        self.init_ui()
        self.load_initial_data()
        self.migration_data = []

    def init_ui(self):
        fallback_colors = Colors()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # 1. Header Frame (Deep Slate Style)
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
                QFrame {
                    background-color: {fallback_colors.BG_HEADER};
                    border-radius: 10px;
                }
            """)
        header_frame.setFixedHeight(80)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(20, 10, 20, 10)
        
        icon_lbl = QLabel("🔄")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_box = QVBoxLayout()
        title = QLabel("MIGRATION ANNUELLE")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            title.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            title.setStyleSheet(f"color: {fallback_colors.HEADER_TEXT}; background: transparent;")
        
        subtitle = QLabel("إغلاق السنة الدراسية وترحيل الطلاب")
        subtitle.setFont(QFont("Cairo", 11))
        if THEME_AVAILABLE:
            subtitle.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        else:
            subtitle.setStyleSheet(f"color: {fallback_colors.TEXT_SECONDARY}; background: transparent;")
        
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        
        h_layout.addWidget(icon_lbl)
        h_layout.addSpacing(15)
        h_layout.addLayout(title_box)
        h_layout.addStretch()
        
        self.main_layout.addWidget(header_frame)

        # 2. Configuration Card
        config_card = self.create_card()
        grid_config = QGridLayout(config_card)
        grid_config.setSpacing(15)
        grid_config.setContentsMargins(20, 20, 20, 20)
        
        # Title inside card
        card_title = QLabel("1. Configuration & Filtrage / الإعدادات")
        if THEME_AVAILABLE:
            card_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 10px;")
        else:
            card_title.setStyleSheet(f"font-weight: bold; color: {fallback_colors.TEXT_PRIMARY}; font-size: 14px; margin-bottom: 10px;")
        grid_config.addWidget(card_title, 0, 0, 1, 4)
        
        # Controls
        self.combo_current_year = self.styled_combo()
        self.combo_target_year = self.styled_combo()
        
        grid_config.addWidget(QLabel("Année Source (Actuelle):"), 1, 0)
        grid_config.addWidget(self.combo_current_year, 1, 1)
        grid_config.addWidget(QLabel("➡ Année Cible (Nouvelle):"), 1, 2)
        grid_config.addWidget(self.combo_target_year, 1, 3)

        self.combo_filter_class = self.styled_combo()
        self.combo_filter_class.addItem("Toutes les Classes / كل الفصول", None)
        
        btn_calc = QPushButton("Calculer les Décisions / حساب")
        btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_calc.setMinimumHeight(40)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_calc.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 6px; 
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        else:
            btn_calc.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {fallback_colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 6px; 
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {fallback_colors.PRIMARY_HOVER}; }}
            """)
        btn_calc.clicked.connect(self.start_calculation)

        grid_config.addWidget(QLabel("Filtrer par Classe:"), 2, 0)
        grid_config.addWidget(self.combo_filter_class, 2, 1)
        grid_config.addWidget(btn_calc, 2, 3)
        
        self.main_layout.addWidget(config_card)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # 3. Preview Table
        preview_label = QLabel("2. Aperçu et Validation / المعاينة والتنقيح:")
        if THEME_AVAILABLE:
            preview_label.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; margin-left: 5px;")
        else:
            preview_label.setStyleSheet(f"font-weight: bold; color: {fallback_colors.TEXT_PRIMARY}; margin-left: 5px;")
        self.main_layout.addWidget(preview_label)

        self.table_preview = QTableWidget()
        self.style_table(self.table_preview)
        self.table_preview.setColumnCount(6)
        self.table_preview.setHorizontalHeaderLabels(["ID", "Élève", "Classe Actuelle", "Moyenne", "Décision", "Classe Future"])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_preview.setColumnWidth(0, 60)
        self.table_preview.verticalHeader().setDefaultSectionSize(40)
        
        self.main_layout.addWidget(self.table_preview)

        # 4. Execution Area
        action_layout = QHBoxLayout()
        self.chk_archive = QCheckBox("Archiver l'historique / حفظ في الأرشيف")
        self.chk_archive.setChecked(True)
        if THEME_AVAILABLE:
            self.chk_archive.setStyleSheet(f"font-size: 14px; color: {ThemeManager.get_colors().TEXT_PRIMARY};")
        else:
            self.chk_archive.setStyleSheet(f"font-size: 14px; color: {fallback_colors.TEXT_PRIMARY};")
        
        btn_execute = QPushButton("🚀 CONFIRMER LA MIGRATION / تنفيذ")
        btn_execute.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_execute.setMinimumHeight(50)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_execute.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.DANGER};
                    color: white; 
                    font-weight: bold; 
                    padding: 0 20px; 
                    font-size: 14px; 
                    border-radius: 8px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
        else:
            btn_execute.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {fallback_colors.DANGER};
                    color: white; 
                    font-weight: bold; 
                    padding: 0 20px; 
                    font-size: 14px; 
                    border-radius: 8px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {fallback_colors.DANGER_HOVER}; }}
            """)
        btn_execute.clicked.connect(self.execute_migration)
        
        action_layout.addWidget(self.chk_archive)
        action_layout.addStretch()
        action_layout.addWidget(btn_execute)
        
        self.main_layout.addLayout(action_layout)

    # --- Helper Styling Methods ---
    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            fallback_colors = Colors()
            frame.setStyleSheet(f"""
                QFrame {
                    background-color: {fallback_colors.BG_CARD}; 
                    border-radius: 12px; 
                    border: 1px solid {fallback_colors.BORDER};
                }
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_combo(self):
        combo = QComboBox()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 8px 12px;
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    background: {colors.INPUT_BG};
                    color: {colors.TEXT_PRIMARY};
                }}
                QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            fallback_colors = Colors()
            combo.setStyleSheet(f"""
                QComboBox {
                    padding: 8px 12px;
                    border: 1px solid {fallback_colors.BORDER};
                    border-radius: 6px;
                    background: {fallback_colors.INPUT_BG};
                    color: {fallback_colors.TEXT_PRIMARY};
                }
                QComboBox:focus {{ border: 2px solid {fallback_colors.BORDER_FOCUS}; background: {fallback_colors.INPUT_BG_FOCUS}; }}
            """)
        combo.setMinimumHeight(40)
        return combo

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
                    padding: 6px;
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
            fallback_colors = Colors()
            table.setStyleSheet(f"""
                QTableWidget {
                    background-color: {fallback_colors.BG_CARD};
                    border: 1px solid {fallback_colors.BORDER};
                    border-radius: 8px;
                    gridline-color: {fallback_colors.BORDER};
                    font-size: 13px;
                }
                QTableWidget::item {
                    padding: 6px;
                    border-bottom: 1px solid {fallback_colors.BG_MAIN};
                }
                QTableWidget::item:selected {
                    background-color: {fallback_colors.PRIMARY};
                    color: white;
                }
                QHeaderView::section {
                    background-color: {fallback_colors.BG_HEADER};
                    color: white;
                    padding: 10px;
                    border: none;
                    font-weight: bold;
                }
            """)

    # --- Logic Methods ---
    def load_initial_data(self):
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Load Years
            cursor.execute("SELECT id, year_label, is_active FROM AcademicYears ORDER BY id DESC")
            years = cursor.fetchall()
            
            self.combo_current_year.clear()
            self.combo_target_year.clear()
            
            for y in years:
                self.combo_current_year.addItem(y[1], y[0])
                self.combo_target_year.addItem(y[1], y[0])
                if y[2] == 1: 
                    self.combo_current_year.setCurrentIndex(self.combo_current_year.count()-1)

            # Load Classes
            cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY sort_order")
            classes = cursor.fetchall()
            self.combo_filter_class.clear()
            self.combo_filter_class.addItem("Toutes les Classes / كل الفصول", None)
            for c in classes:
                self.combo_filter_class.addItem(c[1], c[0])

    def start_calculation(self):
        curr_id = self.combo_current_year.currentData()
        targ_id = self.combo_target_year.currentData()
        filter_cls = self.combo_filter_class.currentData()
        
        if curr_id == targ_id:
            QMessageBox.warning(self, "Attention", "L'année source et cible doivent être différentes !")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.table_preview.setRowCount(0)
        
        self.calc_thread = MigrationCalculator(DB_PATH, curr_id, filter_cls)
        self.calc_thread.progress.connect(self.progress_bar.setValue)
        self.calc_thread.finished.connect(self.display_results)
        self.calc_thread.start()

    def display_results(self, results):
        self.migration_data = results
        self.progress_bar.setVisible(False)
        self.table_preview.setRowCount(0)
        fallback_colors = Colors()
        
        if not results:
            QMessageBox.information(self, "Info", "Aucun élève trouvé pour les critères sélectionnés.")
            return

        for r in results:
            idx = self.table_preview.rowCount()
            self.table_preview.insertRow(idx)
            
            # Read-only items
            id_item = QTableWidgetItem(str(r['id']))
            id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_preview.setItem(idx, 0, id_item)
            
            name_item = QTableWidgetItem(r['name'])
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_preview.setItem(idx, 1, name_item)
            
            cls_item = QTableWidgetItem(r['current_class'])
            cls_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_preview.setItem(idx, 2, cls_item)
            
            avg_item = QTableWidgetItem(f"{r['avg']:.2f}")
            avg_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                avg_item.setForeground(QColor(colors.SUCCESS) if r['decision'] == "Admis" else QColor(colors.DANGER))
            else:
                avg_item.setForeground(QColor(fallback_colors.SUCCESS) if r['decision'] == "Admis" else QColor(fallback_colors.DANGER))
            avg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_preview.setItem(idx, 3, avg_item)
            
            # Editable Decision
            combo_dec = QComboBox()
            combo_dec.addItems(["Admis", "Redouble", "Exclu"])
            combo_dec.setCurrentText(r['decision'])
            combo_dec.setStyleSheet("QComboBox { border: none; background: transparent; }")
            self.table_preview.setCellWidget(idx, 4, combo_dec)
            
            dest_txt = r['next_class_name']
            dest_item = QTableWidgetItem(dest_txt)
            dest_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if "Fin de Cycle" in dest_txt:
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    dest_item.setBackground(QColor(colors.WARNING))
                    dest_item.setForeground(QColor(colors.BG_MAIN))
                else:
                    dest_item.setBackground(QColor(fallback_colors.WARNING))
                    dest_item.setForeground(QColor(fallback_colors.BG_MAIN))
            self.table_preview.setItem(idx, 5, dest_item)

    def execute_migration(self):
        if not self.migration_data: return
        
        msg = f"Êtes-vous sûr de vouloir traiter {len(self.migration_data)} élèves ?\n"
        if self.combo_filter_class.currentData():
            msg += "(Filtre appliqué : Seulement la classe sélectionnée)"
        
        reply = QMessageBox.question(self, "Confirmation", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes: return

        change_active_year = (self.combo_filter_class.currentData() is None) 
        target_year_id = self.combo_target_year.currentData()
        
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            try:
                count = 0
                for idx in range(self.table_preview.rowCount()):
                    std_id = int(self.table_preview.item(idx, 0).text())
                    
                    original_data = next((item for item in self.migration_data if item['id'] == std_id), None)
                    if not original_data: continue

                    decision_widget = self.table_preview.cellWidget(idx, 4)
                    decision = decision_widget.currentText()
                    
                    new_class_id = None
                    if decision == "Admis":
                        new_class_id = original_data['next_class_id']
                    elif decision == "Redouble":
                        new_class_id = original_data['current_class_id']
                    # Else Exclu -> new_class_id is None

                    if decision == "Exclu":
                        cursor.execute("UPDATE Students SET status='Exclu' WHERE id=?", (std_id,))
                    elif new_class_id:
                        cursor.execute("UPDATE Students SET class_id=? WHERE id=?", (new_class_id, std_id))
                    
                    count += 1
                
                if change_active_year:
                    cursor.execute("UPDATE AcademicYears SET is_active=0")
                    cursor.execute("UPDATE AcademicYears SET is_active=1 WHERE id=?", (target_year_id,))
                
                conn.commit()
                QMessageBox.information(self, "Succès", f"Opération terminée. {count} élèves mis à jour.")
                self.table_preview.setRowCount(0)
                self.migration_data = []
                
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MigrationWindow()
    window.show()
    sys.exit(app.exec())