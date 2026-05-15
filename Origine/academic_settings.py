import sys
import sqlite3
import os
from database_setup import DatabaseManager

# محاولة استيراد ConfigManager، وتجاوز الخطأ إن لم يكن متوفراً بالكامل بعد
try:
    from config_manager import ConfigManager
    HAS_CONFIG_MANAGER = True
except ImportError:
    HAS_CONFIG_MANAGER = False

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QFrame, QSpinBox,
                             QTabWidget, QGridLayout, QDoubleSpinBox, QFileDialog, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, Colors, get_table_style, get_tabs_style

THEME_AVAILABLE = True

class AcademicSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Scolaire / الإعدادات المدرسية")
        self.setMinimumSize(1100, 700)

        self.config = ConfigManager() if HAS_CONFIG_MANAGER else None

        # --- تهيئة المتغيرات الأساسية لتجنب أخطاء (AttributeError) ---
        self.current_year_id = None
        self.current_cycle_id = None
        self.current_class_id = None
        self.current_subject_id = None
        self.logo_path_value = ""

        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
            """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.init_ui()
        self.refresh_all_data()

    def init_ui(self):
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # Header Frame
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {colors.BG_HEADER}; border-radius: 10px;")
        header_frame.setMaximumHeight(80)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15); shadow.setColor(QColor(15, 23, 42, 40)); shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        icon_lbl = QLabel("⚙️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_box = QVBoxLayout()
        header_label = QLabel("CONFIGURATION SCOLAIRE")
        header_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_label = QLabel("إعداد البيانات، الهيكل، المواد والتقييمات")
        sub_label.setFont(QFont("Cairo", 11))
        sub_label.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")
        
        title_box.addWidget(header_label)
        title_box.addWidget(sub_label)
        
        header_layout.addWidget(icon_lbl)
        header_layout.addSpacing(15)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        self.main_layout.addWidget(header_frame)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 12px; margin-top: 15px; }}
            QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 12px 30px; margin-right: 6px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-family: 'Segoe UI', 'Cairo'; }}
            QTabBar::tab:selected {{ background: {colors.BG_CARD}; color: {colors.PRIMARY}; border-bottom: 2px solid {colors.PRIMARY}; }}
            QTabBar::tab:hover {{ background: {colors.BORDER}; }}
        """)

        self.setup_school_info_tab()
        self.setup_structure_tab()
        self.setup_subjects_tab()
        self.setup_evaluations_tab()

        self.main_layout.addWidget(self.tabs)

    # Helper Functions
    def create_card(self, title):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER};")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20); shadow.setColor(QColor(15, 23, 42, 15)); shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
            
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        lbl = QLabel(title)
        lbl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        lbl.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; margin-bottom: 10px;")
        layout.addWidget(lbl)
        return frame, layout

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        le.setStyleSheet(f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        le.setMinimumHeight(38)
        return le
    
    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        combo.setMinimumHeight(38)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())

    def safe_text(self, value):
        return "" if value is None else str(value)

    def add_action_buttons(self, table, row_idx, id_val, edit_func=None, delete_func=None):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        if edit_func:
            btn_edit = QPushButton("✎")
            btn_edit.setFixedSize(28, 28)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet(f"background-color: {colors.WARNING}; color: white; border-radius: 4px; border: none;")
            btn_edit.clicked.connect(lambda _, val=id_val: edit_func(val))
            layout.addWidget(btn_edit)
        
        if delete_func:
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 4px; border: none;")
            btn_del.clicked.connect(lambda _, val=id_val: delete_func(val))
            layout.addWidget(btn_del)
            
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setCellWidget(row_idx, table.columnCount() - 1, widget)

    # --- 1. معلومات المؤسسة ---
    def setup_school_info_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        card, grid_lay = self.create_card("🏛️ Identification de l'Établissement / بيانات المؤسسة")
        grid = QGridLayout()
        grid.setSpacing(15)
        
        self.info_inputs = {
            'rep': self.styled_input("Ex: République du Sénégal"),
            'ia': self.styled_input("Inspection d'Académie (IA)"),
            'ief': self.styled_input("Inspection IEF"),
            'name': self.styled_input("Nom de l'établissement"),
            'auth': self.styled_input("N° Autorisation"),
            'director': self.styled_input("Nom du Directeur / اسم المدير"),
            'loc': self.styled_input("Adresse"),
            'tel': self.styled_input("Téléphone")
        }
        
        self.logo_path_display = self.styled_input("Logo Path")
        self.logo_path_display.setReadOnly(True)
        
        labels = {
            'rep': "En-tête:", 'ia': "IA:", 'ief': "IEF:",
            'name': "Nom:", 'auth': "Autorisation:", 
            'director': "Directeur:", 'loc': "Adresse:", 'tel': "Tel:"
        }

        r = 0
        for k, v in self.info_inputs.items():
            grid.addWidget(QLabel(labels[k]), r, 0)
            grid.addWidget(v, r, 1)
            r += 1
            
        grid.addWidget(QLabel("Logo:"), r, 0)
        logo_h = QHBoxLayout()
        logo_h.addWidget(self.logo_path_display)
        btn_logo = QPushButton("📁")
        btn_logo.setFixedSize(40, 38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_logo.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; border-radius: 6px; font-weight: bold;")
        btn_logo.clicked.connect(self.browse_logo)
        logo_h.addWidget(btn_logo)
        grid.addLayout(logo_h, r, 1)
        
        btn_save = QPushButton("💾 Enregistrer / حفظ")
        btn_save.setMinimumHeight(45)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"background-color: {colors.SUCCESS}; color: white; border-radius: 8px; font-weight: bold; font-size: 14px;")
        btn_save.clicked.connect(self.save_school_info)
        
        grid_lay.addLayout(grid)
        grid_lay.addWidget(btn_save)
        layout.addWidget(card)
        layout.addStretch()
        self.tabs.addTab(tab, "  🏛️ Infos / معلومات  ")

    # --- 2. الهيكل ---
    def setup_structure_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # Years
        y_card, y_lay = self.create_card("📅 Années / السنوات")
        self.txt_year = self.styled_input("Ex: 2025-2026")
        self.btn_y = QPushButton("Ajouter")
        self.btn_y.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; padding: 8px; border-radius: 6px; font-weight: bold;")
        self.btn_y.clicked.connect(self.save_year)
        self.table_years = QTableWidget(0, 4) 
        self.style_table(self.table_years)
        self.table_years.setHorizontalHeaderLabels(["ID", "Année", "Actif", "Action"])
        self.table_years.setColumnWidth(0, 40)
        self.table_years.setColumnWidth(2, 80)
        y_lay.addWidget(self.txt_year)
        y_lay.addWidget(self.btn_y)
        y_lay.addWidget(self.table_years)

        # Cycles
        c_card, c_lay = self.create_card("🏫 Cycles / المراحل")
        self.txt_c_fr = self.styled_input("Nom (FR)")
        self.txt_c_ar = self.styled_input("الاسم (عربي)")
        self.btn_c = QPushButton("Ajouter")
        self.btn_c.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; padding: 8px; border-radius: 6px; font-weight: bold;")
        self.btn_c.clicked.connect(self.save_cycle)
        self.table_cycles = QTableWidget(0, 4)
        self.style_table(self.table_cycles)
        self.table_cycles.setHorizontalHeaderLabels(["ID", "Cycle (FR)", "Cycle (AR)", "Action"])
        self.table_cycles.setColumnWidth(0, 40)
        c_lay.addWidget(self.txt_c_fr)
        c_lay.addWidget(self.txt_c_ar)
        c_lay.addWidget(self.btn_c)
        c_lay.addWidget(self.table_cycles)

        # Classes
        cls_card, cls_lay = self.create_card("👥 Classes / الفصول")
        self.combo_cycles_cls = self.styled_combo()
        self.txt_cls_fr = self.styled_input("Nom (FR)")
        self.txt_cls_ar = self.styled_input("الاسم (عربي)")
        self.sp_order = QSpinBox()
        self.sp_order.setRange(1, 20)
        self.sp_order.setMinimumHeight(38)
        self.sp_order.setStyleSheet(f"border: 1px solid {colors.BORDER}; border-radius: 6px; padding: 5px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};")
        
        self.btn_cls = QPushButton("Ajouter")
        self.btn_cls.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; padding: 8px; border-radius: 6px; font-weight: bold;")
        self.btn_cls.clicked.connect(self.save_class)
        
        self.table_classes = QTableWidget(0, 5) 
        self.style_table(self.table_classes)
        self.table_classes.setHorizontalHeaderLabels(["ID", "Cycle", "Classe (FR)", "Classe (AR)", "Action"])
        self.table_classes.setColumnWidth(0, 40)
        
        cls_lay.addWidget(QLabel("Cycle:"))
        cls_lay.addWidget(self.combo_cycles_cls)
        cls_lay.addWidget(self.txt_cls_fr)
        cls_lay.addWidget(self.txt_cls_ar)
        cls_lay.addWidget(QLabel("Ordre:"))
        cls_lay.addWidget(self.sp_order)
        cls_lay.addWidget(self.btn_cls)
        cls_lay.addWidget(self.table_classes)

        layout.addWidget(y_card, 1)
        layout.addWidget(c_card, 1)
        layout.addWidget(cls_card, 1)
        self.tabs.addTab(tab, "  📊 Structure / الهيكل  ")

    # --- 3. المواد ---
    def setup_subjects_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        
        card, vlay = self.create_card("📚 Matières par Cycle / المواد حسب المرحلة")
        
        form = QGridLayout()
        form.setSpacing(10)
        
        self.combo_cycles_sub = self.styled_combo()
        self.txt_sub_fr = self.styled_input("Matière (FR)")
        self.txt_sub_ar = self.styled_input("المادة (عربي)")
        self.sp_coeff = QDoubleSpinBox()
        self.sp_coeff.setRange(0.1, 10.0)
        self.sp_coeff.setSingleStep(0.1)
        self.sp_coeff.setMinimumHeight(38)
        self.sp_coeff.setStyleSheet(f"border: 1px solid {colors.BORDER}; border-radius: 6px; padding: 5px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};")
        
        self.combo_sub_lang = self.styled_combo()
        self.combo_sub_lang.addItems(["Français", "Arabe"])
        
        form.addWidget(QLabel("Cycle:"), 0, 0)
        form.addWidget(self.combo_cycles_sub, 0, 1)
        form.addWidget(QLabel("Nom FR:"), 1, 0)
        form.addWidget(self.txt_sub_fr, 1, 1)
        form.addWidget(QLabel("Nom AR:"), 2, 0)
        form.addWidget(self.txt_sub_ar, 2, 1)
        form.addWidget(QLabel("Coeff:"), 3, 0)
        form.addWidget(self.sp_coeff, 3, 1)
        form.addWidget(QLabel("Langue:"), 4, 0)
        form.addWidget(self.combo_sub_lang, 4, 1)
        
        self.btn_sub = QPushButton("Ajouter Matière")
        self.btn_sub.setMinimumHeight(40)
        self.btn_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sub.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; border-radius: 6px; font-weight: bold;")
        self.btn_sub.clicked.connect(self.save_subject)
        
        vlay.addLayout(form)
        vlay.addWidget(self.btn_sub)
        
        self.table_subjects = QTableWidget(0, 7) 
        self.style_table(self.table_subjects)
        self.table_subjects.setHorizontalHeaderLabels(["ID", "Cycle", "Matière (FR)", "المادة (AR)", "Lang", "Coef", "Act"])
        self.table_subjects.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_subjects.setColumnWidth(0, 40)
        self.table_subjects.setColumnWidth(6, 80)
        vlay.addWidget(self.table_subjects)
        
        layout.addWidget(card)
        self.tabs.addTab(tab, "  📖 Matières / المواد  ")

    # --- 4. التقييمات ---
    def setup_evaluations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        
        gen_card, gen_lay = self.create_card("⚙️ Génération Automatique (Périodes & Évaluations)")
        
        hbox = QHBoxLayout()
        hbox.setSpacing(15)
        self.combo_year_gen = self.styled_combo()
        self.combo_cycle_gen = self.styled_combo()
        btn_gen = QPushButton("⚡ Générer Configuration")
        btn_gen.setMinimumHeight(40)
        btn_gen.setStyleSheet(f"background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px;")
        btn_gen.clicked.connect(self.generate_academic_logic)
        
        hbox.addWidget(QLabel("Année:"))
        hbox.addWidget(self.combo_year_gen, 1)
        hbox.addWidget(QLabel("Cycle:"))
        hbox.addWidget(self.combo_cycle_gen, 1)
        hbox.addWidget(btn_gen)
        gen_lay.addLayout(hbox)
        
        layout.addWidget(gen_card)

        self.table_evals = QTableWidget(0, 7)
        self.style_table(self.table_evals)
        self.table_evals.setHorizontalHeaderLabels(["ID", "Cycle", "Période", "Type (FR)", "النوع (AR)", "Poids", "Act"])
        self.table_evals.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_evals.setColumnWidth(0, 40)
        layout.addWidget(self.table_evals)

        self.tabs.addTab(tab, "  📝 Évaluations / التقييمات  ")

    # --- CRUD Operations ---

    # 1. Years
    def save_year(self):
        label = self.txt_year.text().strip()
        if not label: return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                if self.current_year_id:
                    conn.execute("UPDATE AcademicYears SET year_label=? WHERE id=?", (label, self.current_year_id))
                else:
                    conn.execute("INSERT INTO AcademicYears (year_label, is_active) VALUES (?, 0)", (label,))
                conn.commit()
            self.txt_year.clear()
            self.current_year_id = None
            self.btn_y.setText("Ajouter")
            self.refresh_all_data()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Cette année existe déjà. / هذه السنة موجودة مسبقاً.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur: {e}")

    def edit_year(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = conn.execute("SELECT year_label FROM AcademicYears WHERE id=?", (id,)).fetchone()
        if res:
            self.txt_year.setText(res[0])
            self.current_year_id = id
            self.btn_y.setText("Modifier")

    def activate_year(self, id):
        """تنشيط السنة الدراسية - إزالة التنشيط من جميع السنوات الأخرى"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute("UPDATE AcademicYears SET is_active=0")
                conn.execute("UPDATE AcademicYears SET is_active=1 WHERE id=?", (id,))
                conn.commit()
            self.refresh_all_data()
            QMessageBox.information(self, "Succès", "Année scolaire activée avec succès! / تم تنشيط هذه السنة الدراسية!")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_year(self, id):
        if QMessageBox.question(self, "Supprimer", "Voulez-vous vraiment supprimer cette année ? / هل تريد الحذف؟", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    # Check if active
                    res = conn.execute("SELECT is_active FROM AcademicYears WHERE id=?", (id,)).fetchone()
                    if res and res[0] == 1:
                        QMessageBox.warning(self, "Attention", "Impossible de supprimer l'année active. / لا يمكن حذف السنة النشطة.")
                        return
                    conn.execute("DELETE FROM AcademicYears WHERE id=?", (id,))
                    conn.commit()
                self.refresh_all_data()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible de supprimer, données liées existantes. / توجد بيانات مرتبطة بهذه السنة.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    # 2. Cycles
    def save_cycle(self):
        fr = self.txt_c_fr.text().strip()
        ar = self.txt_c_ar.text().strip()
        if not fr: return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                if self.current_cycle_id:
                    conn.execute("UPDATE Cycles SET name_fr=?, name_ar=? WHERE id=?", (fr, ar, self.current_cycle_id))
                else:
                    conn.execute("INSERT INTO Cycles (name_fr, name_ar) VALUES (?, ?)", (fr, ar))
                conn.commit()
            self.txt_c_fr.clear(); self.txt_c_ar.clear()
            self.current_cycle_id = None
            self.btn_c.setText("Ajouter")
            self.refresh_all_data()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def edit_cycle(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = conn.execute("SELECT name_fr, name_ar FROM Cycles WHERE id=?", (id,)).fetchone()
        if res:
            self.txt_c_fr.setText(res[0])
            self.txt_c_ar.setText(res[1])
            self.current_cycle_id = id
            self.btn_c.setText("Modifier")

    def delete_cycle(self, id):
        if QMessageBox.question(self, "Supprimer", "Supprimer ce cycle ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    conn.execute("DELETE FROM Cycles WHERE id=?", (id,))
                    conn.commit()
                self.refresh_all_data()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible de supprimer, des classes sont liées à ce cycle.")

    # 3. Classes
    def save_class(self):
        cid = self.combo_cycles_cls.currentData()
        fr = self.txt_cls_fr.text().strip()
        ar = self.txt_cls_ar.text().strip()
        order = self.sp_order.value()
        if not cid or not fr: return
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                if self.current_class_id:
                    conn.execute("UPDATE Classes SET cycle_id=?, class_name_fr=?, class_name_ar=?, sort_order=? WHERE id=?", (cid, fr, ar, order, self.current_class_id))
                else:
                    conn.execute("INSERT INTO Classes (cycle_id, class_name_fr, class_name_ar, sort_order) VALUES (?, ?, ?, ?)", (cid, fr, ar, order))
                conn.commit()

            self.txt_cls_fr.clear(); self.txt_cls_ar.clear(); self.sp_order.setValue(1)
            self.current_class_id = None
            self.btn_cls.setText("Ajouter")
            self.refresh_all_data()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def edit_class(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = conn.execute("SELECT cycle_id, class_name_fr, class_name_ar, sort_order FROM Classes WHERE id=?", (id,)).fetchone()
        
        if res:
            idx = self.combo_cycles_cls.findData(res[0])
            self.combo_cycles_cls.setCurrentIndex(idx)
            self.txt_cls_fr.setText(res[1])
            self.txt_cls_ar.setText(res[2])
            self.sp_order.setValue(res[3])
            self.current_class_id = id
            self.btn_cls.setText("Modifier")

    def delete_class(self, id):
        if QMessageBox.question(self, "Supprimer", "Supprimer cette classe ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    conn.execute("DELETE FROM Classes WHERE id=?", (id,))
                    conn.commit()
                self.refresh_all_data()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible, des étudiants sont liés à cette classe.")

    # 4. Subjects
    def save_subject(self):
        cid = self.combo_cycles_sub.currentData()
        fr = self.txt_sub_fr.text().strip()
        ar = self.txt_sub_ar.text().strip()
        coef = self.sp_coeff.value()
        lang = self.combo_sub_lang.currentText()
        if not cid or not fr: return
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                if self.current_subject_id:
                    conn.execute("UPDATE Subjects SET cycle_id=?, subject_name_fr=?, subject_name_ar=?, coefficient=?, subject_lang=? WHERE id=?", (cid, fr, ar, coef, lang, self.current_subject_id))
                else:
                    conn.execute("INSERT INTO Subjects (cycle_id, subject_name_fr, subject_name_ar, coefficient, subject_lang) VALUES (?, ?, ?, ?, ?)", (cid, fr, ar, coef, lang))
                conn.commit()
            
            self.txt_sub_fr.clear(); self.txt_sub_ar.clear(); self.sp_coeff.setValue(1)
            self.current_subject_id = None
            self.btn_sub.setText("Ajouter Matière")
            self.refresh_all_data()
        except Exception as e:
             QMessageBox.critical(self, "Erreur", str(e))

    def edit_subject(self, id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            res = conn.execute("SELECT cycle_id, subject_name_fr, subject_name_ar, coefficient, subject_lang FROM Subjects WHERE id=?", (id,)).fetchone()
        
        if res:
            idx = self.combo_cycles_sub.findData(res[0])
            self.combo_cycles_sub.setCurrentIndex(idx)
            self.txt_sub_fr.setText(res[1])
            self.txt_sub_ar.setText(res[2])
            self.sp_coeff.setValue(float(res[3]))
            self.combo_sub_lang.setCurrentText(res[4] if res[4] else "Français")
            self.current_subject_id = id
            self.btn_sub.setText("Modifier")

    def delete_subject(self, id):
        if QMessageBox.question(self, "Supprimer", "Supprimer cette matière ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    conn.execute("DELETE FROM Subjects WHERE id=?", (id,))
                    conn.commit()
                self.refresh_all_data()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Erreur", "Impossible, des notes existent pour cette matière.")

    # 5. Evaluations
    def delete_evaluation(self, id):
        if QMessageBox.question(self, "Supprimer", "Supprimer cette évaluation ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    conn.execute("DELETE FROM AssessmentTypes WHERE id=?", (id,))
                    conn.commit()
                self.refresh_all_data()
            except sqlite3.IntegrityError:
                 QMessageBox.warning(self, "Erreur", "Impossible, des notes existent pour cette évaluation.")

    # --- Other Methods ---
    def save_school_info(self):
        republic = self.info_inputs['rep'].text()
        ia = self.info_inputs['ia'].text()
        ief = self.info_inputs['ief'].text()
        school_name = self.info_inputs['name'].text()
        auth = self.info_inputs['auth'].text()
        address = self.info_inputs['loc'].text()
        phone = self.info_inputs['tel'].text()
        director = self.info_inputs['director'].text()

        if self.config:
            try:
                self.config.set('APPLICATION', 'school_name', school_name)
                self.config.set('APPLICATION', 'school_location', address)
            except Exception:
                pass

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute("DELETE FROM SchoolInfo")
                conn.execute("""
                    INSERT INTO SchoolInfo (republic, ia, ief, school_name, auth_number, address, phone, logo_path, director_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (republic, ia, ief, school_name, auth, address, phone, self.logo_path_value, director))
                conn.commit()
            QMessageBox.information(self, "Succès", "Informations enregistrées et mises à jour.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
    
    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner le logo", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.logo_path_value = file_path
            self.logo_path_display.setText(os.path.basename(file_path))

    def generate_academic_logic(self):
        year_id = self.combo_year_gen.currentData()
        cycle_id = self.combo_cycle_gen.currentData()
        cycle_name = self.combo_cycle_gen.currentText().lower()

        if not year_id or not cycle_id: 
            QMessageBox.warning(self, "Attention", "Sélectionnez l'année et le cycle.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM AssessmentTypes WHERE period_id IN (SELECT id FROM AcademicPeriods WHERE year_id=? AND cycle_id=?)", (year_id, cycle_id))
                cursor.execute("DELETE FROM AcademicPeriods WHERE year_id=? AND cycle_id=?", (year_id, cycle_id))

                if "elem" in cycle_name or "prim" in cycle_name or "إبتدائ" in cycle_name:
                    periods = [("Trimestre 1", "الفصل الأول"), ("Trimestre 2", "الفصل الثاني"), ("Trimestre 3", "الفصل الثالث")]
                    for idx, (p_fr, p_ar) in enumerate(periods):
                        cursor.execute("INSERT INTO AcademicPeriods (year_id, cycle_id, period_name_fr, period_name_ar, sort_order) VALUES (?, ?, ?, ?, ?)", (year_id, cycle_id, p_fr, p_ar, idx+1))
                        period_id = cursor.lastrowid
                        cursor.execute("INSERT INTO AssessmentTypes (period_id, name_fr, name_ar, type_code, weight_percentage) VALUES (?, 'Composition', 'اختبار فصلي', 'COMPO', 1.0)", (period_id,))
                else:
                    periods = [("Semestre 1", "السداسي الأول"), ("Semestre 2", "السداسي الثاني")]
                    for idx, (p_fr, p_ar) in enumerate(periods):
                        cursor.execute("INSERT INTO AcademicPeriods (year_id, cycle_id, period_name_fr, period_name_ar, sort_order) VALUES (?, ?, ?, ?, ?)", (year_id, cycle_id, p_fr, p_ar, idx+1))
                        period_id = cursor.lastrowid
                        cursor.execute("INSERT INTO AssessmentTypes (period_id, name_fr, name_ar, type_code, weight_percentage) VALUES (?, 'Devoir 1', 'الواجب 1', 'DEV', 1.0)", (period_id,))
                        cursor.execute("INSERT INTO AssessmentTypes (period_id, name_fr, name_ar, type_code, weight_percentage) VALUES (?, 'Devoir 2', 'الواجب 2', 'DEV', 1.0)", (period_id,))
                        cursor.execute("INSERT INTO AssessmentTypes (period_id, name_fr, name_ar, type_code, weight_percentage) VALUES (?, 'Composition', 'الاختبار', 'COMPO', 2.0)", (period_id,))

                conn.commit()

            self.refresh_all_data()
            QMessageBox.information(self, "Succès", "Configuration générée avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def refresh_all_data(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # School Info
                cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
                info = cursor.fetchone()
                if info:
                    if len(info) > 1: self.info_inputs['rep'].setText(str(info[1] or ""))
                    if len(info) > 2: self.info_inputs['ia'].setText(str(info[2] or ""))
                    if len(info) > 3: self.info_inputs['ief'].setText(str(info[3] or ""))
                    if len(info) > 4: self.info_inputs['name'].setText(str(info[4] or ""))
                    if len(info) > 5: self.info_inputs['auth'].setText(str(info[5] or ""))
                    if len(info) > 6: self.info_inputs['loc'].setText(str(info[6] or ""))
                    if len(info) > 7: self.info_inputs['tel'].setText(str(info[7] or ""))
                    if len(info) > 8: 
                        self.logo_path_value = info[8]
                        self.logo_path_display.setText(os.path.basename(info[8]) if info[8] else "")
                    if len(info) > 9: self.info_inputs['director'].setText(str(info[9] or ""))
                else:
                    if self.config:
                        self.info_inputs['name'].setText(self.config.school_name)
                        self.info_inputs['loc'].setText(self.config.school_location)

                # Years
                self.table_years.setRowCount(0)
                self.combo_year_gen.clear()
                cursor.execute("SELECT id, year_label, is_active FROM AcademicYears")
                for r in cursor.fetchall():
                    idx = self.table_years.rowCount()
                    self.table_years.insertRow(idx)
                    self.table_years.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_years.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    
                    status_item = QTableWidgetItem("✓ Actif" if r[2] else "✕")
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if THEME_AVAILABLE:
                        colors = ThemeManager.get_colors()
                        status_item.setForeground(QColor(colors.SUCCESS if r[2] else colors.TEXT_SECONDARY))
                    self.table_years.setItem(idx, 2, status_item)
                    
                    widget = QWidget()
                    layout = QHBoxLayout(widget)
                    layout.setContentsMargins(2, 2, 2, 2)
                    layout.setSpacing(5)
                    
                    colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                    btn_activate = QPushButton("Activer")
                    btn_activate.setFixedHeight(28)
                    btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_activate.setStyleSheet(
                        f"background-color: {colors.SUCCESS}; color: white; border-radius: 4px; border: none; font-weight: bold;"
                        if r[2] else f"background-color: {colors.BORDER}; color: {colors.TEXT_SECONDARY}; border-radius: 4px; border: none;"
                    )
                    btn_activate.clicked.connect(lambda checked, id=r[0]: self.activate_year(id))
                    layout.addWidget(btn_activate)
                    
                    btn_edit = QPushButton("✎")
                    btn_edit.setFixedSize(28, 28)
                    btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_edit.setStyleSheet(f"background-color: {colors.WARNING}; color: white; border-radius: 4px; border: none;")
                    btn_edit.clicked.connect(lambda checked, id=r[0]: self.edit_year(id))
                    layout.addWidget(btn_edit)
                    
                    btn_del = QPushButton("✕")
                    btn_del.setFixedSize(28, 28)
                    btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 4px; border: none;")
                    btn_del.clicked.connect(lambda checked, id=r[0]: self.delete_year(id))
                    layout.addWidget(btn_del)
                    
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table_years.setCellWidget(idx, 3, widget)
                    self.combo_year_gen.addItem(self.safe_text(r[1]), r[0])

                # Cycles
                self.table_cycles.setRowCount(0)
                self.combo_cycles_cls.clear()
                self.combo_cycles_sub.clear()
                self.combo_cycle_gen.clear()
                cursor.execute("SELECT id, name_fr, name_ar FROM Cycles")
                for r in cursor.fetchall():
                    idx = self.table_cycles.rowCount()
                    self.table_cycles.insertRow(idx)
                    self.table_cycles.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_cycles.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    self.table_cycles.setItem(idx, 2, QTableWidgetItem(self.safe_text(r[2])))
                    self.add_action_buttons(self.table_cycles, idx, r[0], self.edit_cycle, self.delete_cycle)
                    
                    cycle_label = self.safe_text(r[1])
                    self.combo_cycles_cls.addItem(cycle_label, r[0])
                    self.combo_cycles_sub.addItem(cycle_label, r[0])
                    self.combo_cycle_gen.addItem(cycle_label, r[0])

                # Classes
                self.table_classes.setRowCount(0)
                cursor.execute("SELECT CL.id, CY.name_fr, CL.class_name_fr, CL.class_name_ar FROM Classes CL JOIN Cycles CY ON CL.cycle_id=CY.id ORDER BY CL.sort_order")
                for r in cursor.fetchall():
                    idx = self.table_classes.rowCount()
                    self.table_classes.insertRow(idx)
                    self.table_classes.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_classes.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    self.table_classes.setItem(idx, 2, QTableWidgetItem(self.safe_text(r[2])))
                    self.table_classes.setItem(idx, 3, QTableWidgetItem(self.safe_text(r[3])))
                    self.add_action_buttons(self.table_classes, idx, r[0], self.edit_class, self.delete_class)

                # Subjects
                self.table_subjects.setRowCount(0)
                cursor.execute("SELECT S.id, C.name_fr, S.subject_name_fr, S.subject_name_ar, S.subject_lang, S.coefficient FROM Subjects S JOIN Cycles C ON S.cycle_id=C.id")
                for r in cursor.fetchall():
                    idx = self.table_subjects.rowCount()
                    self.table_subjects.insertRow(idx)
                    for c, v in enumerate(r): self.table_subjects.setItem(idx, c, QTableWidgetItem(self.safe_text(v)))
                    self.add_action_buttons(self.table_subjects, idx, r[0], self.edit_subject, self.delete_subject)

                # Evals
                self.table_evals.setRowCount(0)
                cursor.execute("SELECT A.id, C.name_fr, P.period_name_fr, A.name_fr, A.name_ar, A.type_code, A.weight_percentage FROM AssessmentTypes A JOIN AcademicPeriods P ON A.period_id = P.id JOIN Cycles C ON P.cycle_id = C.id ORDER BY C.id, P.sort_order")
                for r in cursor.fetchall():
                    idx = self.table_evals.rowCount()
                    self.table_evals.insertRow(idx)
                    self.table_evals.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                    self.table_evals.setItem(idx, 1, QTableWidgetItem(self.safe_text(r[1])))
                    self.table_evals.setItem(idx, 2, QTableWidgetItem(self.safe_text(r[2])))
                    self.table_evals.setItem(idx, 3, QTableWidgetItem(self.safe_text(r[3])))
                    self.table_evals.setItem(idx, 4, QTableWidgetItem(self.safe_text(r[4])))
                    self.table_evals.setItem(idx, 5, QTableWidgetItem(self.safe_text(r[6])))
                    self.add_action_buttons(self.table_evals, idx, r[0], None, self.delete_evaluation)

        except Exception as e:
             QMessageBox.critical(self, "Erreur de chargement", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AcademicSettingsWindow()
    window.show()
    sys.exit(app.exec())