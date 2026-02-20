import sys
from datetime import datetime
# الحفاظ على الاستيرادات المطلوبة
from database_setup import DatabaseManager
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QSpinBox, 
                             QDoubleSpinBox, QTabWidget, QFrame, QDateEdit, 
                             QGridLayout, QGraphicsDropShadowEffect, QScrollArea)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QIcon

# الحفاظ على استيراد الثيم
from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style

THEME_AVAILABLE = True

class InventoryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion de Stock / إدارة المخزون")
        self.setMinimumSize(1100, 700)
        
        # تطبيق تصميم Deep Slate يدوياً لضمان التناسق، مع مراعاة ThemeManager إذا لزم الأمر
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        
        # self.init_db() - معالجة قاعدة البيانات تتم عبر DatabaseManager أو خارجياً كما هو في الكود الأصلي
        self.init_ui()
        self.load_inventory()
        self.load_history()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame (تصميم الهيدر الجديد)
        header_frame = QFrame()
        if THEME_AVAILABLE:
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {ThemeManager.get_colors().BG_HEADER};
                    border-radius: 10px;
                }}
            """)
        header_frame.setMaximumHeight(80)
        
        # إضافة الظل للهيدر
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 10, 20, 10)
        
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DE STOCK")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("متابعة المخزون، المشتريات، والاستهلاك")
        sub_lbl.setFont(QFont("Cairo", 11))
        if THEME_AVAILABLE:
            sub_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        
        title_layout.addWidget(header_lbl)
        title_layout.addWidget(sub_lbl)
        
        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_layout)
        hl.addStretch()
        
        self.main_layout.addWidget(header_frame)

        # 2. Tabs (تصميم التبويبات)
        self.tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.tabs.setStyleSheet(get_tabs_style())
        
        self.setup_stock_tab()
        self.setup_movement_tab()
        self.setup_history_tab()
        
        self.main_layout.addWidget(self.tabs)

    # --- دوال مساعدة للتصميم (Helper Methods) ---
    def create_card(self):
        """إنشاء إطار بطاقة بيضاء مع ظل"""
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        return frame

    def styled_input(self, placeholder):
        """تنسيق حقول الإدخال"""
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            le.setStyleSheet(f"""
                QLineEdit {{ 
                    padding: 8px 12px; 
                    border: 1px solid {colors.BORDER}; 
                    border-radius: 6px; 
                    background: {colors.INPUT_BG}; 
                    color: {colors.TEXT_PRIMARY}; 
                }}
                QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        """تنسيق القوائم المنسدلة"""
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
        combo.setMinimumHeight(38)
        return combo

    def styled_spinbox(self, suffix=""):
        """تنسيق حقول الأرقام"""
        sb = QSpinBox()
        sb.setRange(0, 100000)
        sb.setSuffix(suffix)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            sb.setStyleSheet(f"""
                QSpinBox {{
                    padding: 8px 12px;
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    background: {colors.INPUT_BG};
                    color: {colors.TEXT_PRIMARY};
                }}
                QSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        sb.setMinimumHeight(38)
        return sb

    def styled_double_spin(self, prefix=""):
        """تنسيق الحقول الرقمية العشرية"""
        spin = QDoubleSpinBox()
        spin.setRange(0, 1000000)
        spin.setPrefix(prefix)
        spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            spin.setStyleSheet(
                f"QDoubleSpinBox {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
            )
        spin.setMinimumHeight(38)
        return spin

    def styled_date(self):
        """تنسيق حقل التاريخ"""
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            date_edit.setStyleSheet(
                f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
            )
        date_edit.setMinimumHeight(38)
        return date_edit

    def style_table(self, table):
        """تنسيق الجداول"""
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())

    # ---------------------------------------------------------
    # TAB 1: Stock Overview
    # ---------------------------------------------------------
    def setup_stock_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # --- Form Card (Left) ---
        form_card = self.create_card()
        form_card.setMinimumWidth(360)
        flay = QVBoxLayout(form_card)
        flay.setContentsMargins(20, 20, 20, 20)
        flay.setSpacing(15)
        
        lbl_title = QLabel("Nouveau Article / مادة جديدة")
        if THEME_AVAILABLE:
            lbl_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")
        flay.addWidget(lbl_title)
        
        self.txt_name_fr = self.styled_input("Nom (FR)")
        self.txt_name_ar = self.styled_input("الاسم (عربي)")
        
        self.combo_cat = self.styled_combo()
        self.combo_cat.addItems(["Fournitures (قرطاسية)", "Mobilier (أثاث)", "Électronique (إلكترونيات)", "Hygiène (نظافة)", "Autre"])
        
        self.spin_qty = self.styled_spinbox()
        self.spin_min = self.styled_spinbox()
        self.spin_min.setValue(5)
        
        self.spin_price = self.styled_double_spin("FCFA ")
        
        self.txt_loc = self.styled_input("Emplacement / المكان")
        
        btn_add = QPushButton("Ajouter Article")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_add.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_add.clicked.connect(self.add_item)

        flay.addWidget(QLabel("Nom FR:"))
        flay.addWidget(self.txt_name_fr)
        flay.addWidget(QLabel("Nom AR:"))
        flay.addWidget(self.txt_name_ar)
        flay.addWidget(QLabel("Catégorie:"))
        flay.addWidget(self.combo_cat)
        
        row_qty = QHBoxLayout()
        row_qty.addWidget(QLabel("Qté Init:"))
        row_qty.addWidget(self.spin_qty)
        row_qty.addWidget(QLabel("Min:"))
        row_qty.addWidget(self.spin_min)
        flay.addLayout(row_qty)
        
        flay.addWidget(QLabel("Prix Unitaire:"))
        flay.addWidget(self.spin_price)
        flay.addWidget(QLabel("Emplacement:"))
        flay.addWidget(self.txt_loc)
        flay.addSpacing(10)
        flay.addWidget(btn_add)
        flay.addStretch()

        scroll_form = QScrollArea()
        scroll_form.setWidgetResizable(True)
        scroll_form.setFrameShape(QFrame.Shape.NoFrame)
        scroll_form.setFixedWidth(380)
        scroll_form.setWidget(form_card)
        layout.addWidget(scroll_form)

        # --- Table (Right) ---
        table_layout = QVBoxLayout()
        
        # Stats Bar
        self.lbl_stats = QLabel("Valeur: 0.00 FCFA | Rupture: 0")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.lbl_stats.setStyleSheet(f"background-color: {colors.BG_MAIN}; padding: 12px; border-radius: 8px; color: {colors.TEXT_PRIMARY}; font-weight: bold; border: 1px solid {colors.BORDER};")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table_layout.addWidget(self.lbl_stats)

        self.table_stock = QTableWidget(0, 8)
        self.style_table(self.table_stock)
        self.table_stock.setHorizontalHeaderLabels(["ID", "Article (FR)", "Article (AR)", "Catégorie", "Qté", "Min", "Prix", "Total"])
        self.table_stock.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_stock.setColumnWidth(0, 40)
        table_layout.addWidget(self.table_stock)
        
        layout.addLayout(table_layout)
        self.tabs.addTab(tab, "  📦 État du Stock / المخزون  ")

    # ---------------------------------------------------------
    # TAB 2: Movements
    # ---------------------------------------------------------
    def setup_movement_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        move_card = self.create_card()
        vlay = QVBoxLayout(move_card)
        vlay.setContentsMargins(20, 20, 20, 20)
        vlay.setSpacing(15)
        
        lbl_title = QLabel("Enregistrer un Mouvement / تسجيل حركة")
        if THEME_AVAILABLE:
            lbl_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")
        vlay.addWidget(lbl_title)
        
        row1 = QHBoxLayout()
        self.combo_items = self.styled_combo()
        self.combo_type = self.styled_combo()
        self.combo_type.addItems(["ENTRÉE (Achat/Retour)", "SORTIE (Consommation/Perte)"])
        
        self.spin_move_qty = self.styled_spinbox()
        self.spin_move_qty.setRange(1, 1000)
        
        row1.addWidget(QLabel("Article:"))
        row1.addWidget(self.combo_items, 2)
        row1.addWidget(QLabel("Type:"))
        row1.addWidget(self.combo_type, 1)
        row1.addWidget(QLabel("Quantité:"))
        row1.addWidget(self.spin_move_qty, 1)
        
        row2 = QHBoxLayout()
        self.date_move = self.styled_date()
        self.date_move.setDate(QDate.currentDate())
        
        self.txt_notes = self.styled_input("Motif / Bénéficiaire...")
        
        btn_exec = QPushButton("Valider Mouvement")
        btn_exec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exec.setMinimumHeight(40)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_exec.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_exec.clicked.connect(self.execute_movement)
        
        row2.addWidget(QLabel("Date:"))
        row2.addWidget(self.date_move)
        row2.addWidget(QLabel("Notes:"))
        row2.addWidget(self.txt_notes, 2)
        row2.addWidget(btn_exec)
        
        vlay.addLayout(row1)
        vlay.addLayout(row2)
        layout.addWidget(move_card)
        
        layout.addStretch()
        
        info_frame = QFrame()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            info_frame.setStyleSheet(f"background-color: {colors.BG_MAIN}; border-radius: 8px; border: 1px dashed {colors.WARNING}; padding: 10px;")
        ilay = QHBoxLayout(info_frame)
        ilay.addWidget(QLabel("💡 Astuce: Les 'Sorties' diminuent le stock, les 'Entrées' l'augmentent."))
        layout.addWidget(info_frame)
        
        self.tabs.addTab(tab, "  🔄 Mouvements / الحركات  ")

    # ---------------------------------------------------------
    # TAB 3: History
    # ---------------------------------------------------------
    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.table_log = QTableWidget(0, 5)
        self.style_table(self.table_log)
        self.table_log.setHorizontalHeaderLabels(["Date", "Type", "Article", "Qté", "Notes / Motif"])
        self.table_log.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_refresh.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 15px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_refresh.clicked.connect(self.load_history)
        
        layout.addWidget(btn_refresh)
        layout.addWidget(self.table_log)
        
        self.tabs.addTab(tab, "  📜 Historique / السجل  ")

    # --- Logic ---
    def add_item(self):
        fr = self.txt_name_fr.text()
        ar = self.txt_name_ar.text()
        cat = self.combo_cat.currentText()
        qty = self.spin_qty.value()
        min_q = self.spin_min.value()
        price = self.spin_price.value()
        loc = self.txt_loc.text()
        
        if not fr: return
        
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO InventoryItems (name_fr, name_ar, category, quantity, min_quantity, unit_price, location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fr, ar, cat, qty, min_q, price, loc))
            item_id = cursor.lastrowid
            conn.commit()
        
        # Record initial stock as movement
        if qty > 0:
            self.log_movement_db(item_id, "ENTRÉE", qty, "Stock Initial")

        self.txt_name_fr.clear(); self.txt_name_ar.clear()
        self.load_inventory()
        QMessageBox.information(self, "Succès", "Article ajouté.")

    def log_movement_db(self, item_id, m_type, qty, notes):
        date_str = datetime.now().strftime("%Y-%m-%d")
        with DatabaseManager() as db:
            conn = db.get_connection()
            conn.execute("""
                INSERT INTO InventoryLog (item_id, transaction_type, quantity, transaction_date, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (item_id, m_type, qty, date_str, notes))
            conn.commit()

    def load_inventory(self):
        self.table_stock.setRowCount(0)
        self.combo_items.clear()
        
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM InventoryItems ORDER BY name_fr")
            rows = cursor.fetchall()
        
        total_val = 0
        alert_count = 0
        
        for r in rows:
            # 0:id, 1:fr, 2:ar, 3:cat, 4:qty, 5:min, 6:price, 7:loc
            idx = self.table_stock.rowCount()
            self.table_stock.insertRow(idx)
            
            self.combo_items.addItem(f"{r[1]} (Stock: {r[4]})", r[0])
            
            row_total = r[4] * r[6]
            total_val += row_total
            
            self.table_stock.setItem(idx, 0, QTableWidgetItem(str(r[0])))
            self.table_stock.setItem(idx, 1, QTableWidgetItem(r[1]))
            self.table_stock.setItem(idx, 2, QTableWidgetItem(r[2]))
            self.table_stock.setItem(idx, 3, QTableWidgetItem(r[3]))
            
            qty_item = QTableWidgetItem(str(r[4]))
            if r[4] <= r[5]: # Low Stock Alert
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    qty_item.setForeground(QColor(colors.DANGER))
                    bg_color = QColor(colors.DANGER)
                    bg_color.setAlpha(40)
                    qty_item.setBackground(bg_color)
                qty_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                alert_count += 1
            else:
                if THEME_AVAILABLE:
                    qty_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
            
            self.table_stock.setItem(idx, 4, qty_item)
            self.table_stock.setItem(idx, 5, QTableWidgetItem(str(r[5])))
            self.table_stock.setItem(idx, 6, QTableWidgetItem(f"{r[6]:.2f}"))
            self.table_stock.setItem(idx, 7, QTableWidgetItem(f"{row_total:.2f}"))

        self.lbl_stats.setText(f"💰 Valeur Totale: {total_val:,.2f} FCFA   |   ⚠️ Alertes Rupture: {alert_count}")

    def execute_movement(self):
        item_id = self.combo_items.currentData()
        move_type = "IN" if "ENTRÉE" in self.combo_type.currentText() else "OUT"
        qty = self.spin_move_qty.value()
        notes = self.txt_notes.text()
        date_str = self.date_move.date().toString("yyyy-MM-dd")
        
        if not item_id: return
        
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
        
            # Check current stock if OUT
            if move_type == "OUT":
                cursor.execute("SELECT quantity FROM InventoryItems WHERE id=?", (item_id,))
                current = cursor.fetchone()[0]
                if current < qty:
                    QMessageBox.warning(self, "Erreur", f"Stock insuffisant! (Disponible: {current})")
                    return
                new_qty = current - qty
            else:
                cursor.execute("SELECT quantity FROM InventoryItems WHERE id=?", (item_id,))
                current = cursor.fetchone()[0]
                new_qty = current + qty
            
            # Update Stock
            cursor.execute("UPDATE InventoryItems SET quantity=? WHERE id=?", (new_qty, item_id))
            
            # Log
            cursor.execute("""
                INSERT INTO InventoryLog (item_id, transaction_type, quantity, transaction_date, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (item_id, move_type, qty, date_str, notes))
            
            conn.commit()
        
        self.load_inventory()
        self.load_history()
        self.txt_notes.clear()
        self.spin_move_qty.setValue(1)
        QMessageBox.information(self, "Succès", "Mouvement enregistré.")

    def load_history(self):
        self.table_log.setRowCount(0)
        with DatabaseManager() as db:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT L.transaction_date, L.transaction_type, I.name_fr, L.quantity, L.notes
                FROM InventoryLog L JOIN InventoryItems I ON L.item_id = I.id
                ORDER BY L.id DESC LIMIT 50
            """)
            rows = cursor.fetchall()
        for r in rows:
            idx = self.table_log.rowCount()
            self.table_log.insertRow(idx)
            
            self.table_log.setItem(idx, 0, QTableWidgetItem(r[0]))
            
            type_item = QTableWidgetItem(r[1])
            if r[1] == "IN": 
                if THEME_AVAILABLE:
                    type_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                type_item.setText("ENTRÉE")
            else: 
                if THEME_AVAILABLE:
                    type_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                type_item.setText("SORTIE")
                
            self.table_log.setItem(idx, 1, type_item)
            self.table_log.setItem(idx, 2, QTableWidgetItem(r[2]))
            self.table_log.setItem(idx, 3, QTableWidgetItem(str(r[3])))
            self.table_log.setItem(idx, 4, QTableWidgetItem(r[4]))
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InventoryWindow()
    window.show()
    sys.exit(app.exec())