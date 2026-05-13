import sys
import psycopg2
import os
from datetime import datetime
from database_setup import DatabaseManager
from app_logger import AppLogger
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QFrame, QGridLayout, 
                             QDoubleSpinBox, QDateEdit, QTabWidget,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, get_table_style, Colors
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_grades_sheet_header

THEME_AVAILABLE = True
STUDENT_DUES_REPORT_OUTPUT_MODE = get_report_output_mode("student_dues_report_mode", "save")


class StudentDuesReportPDF(FPDF):
    def sanitize(self, text):
        if text is None:
            return ""
        value = str(text)
        return value.encode("latin-1", "ignore").decode("latin-1")

class StudentDuesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Factures / إدارة الفواتير والمطالبات")
        self.setMinimumSize(1100, 700)
        self._ensure_student_dues_schema()
        
        # تطبيق المظهر
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
            """)
            
        self.init_ui()
        self.load_classes()

    # ===== تم التعديل: التوافق مع PostgreSQL في قراءة أسماء الأعمدة =====
    def _ensure_student_dues_schema(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'studentdues'")
                cols = {row[0].lower() for row in cursor.fetchall()}
                if cols and "fee_description" not in cols:
                    cursor.execute("ALTER TABLE StudentDues ADD COLUMN fee_description TEXT")
                    conn.commit()
        except Exception:
            pass

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
                row = cursor.fetchone()
                if not row:
                    cursor.execute("SELECT id FROM AcademicYears ORDER BY id DESC LIMIT 1")
                    row = cursor.fetchone()
                return row[0] if row else -1
        except Exception:
            return -1

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # ================= 1. Header (الترويسة) =================
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        header_frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 10px; }}")
        header_frame.setFixedHeight(80)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)
        
        icon_lbl = QLabel("🧾")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_box = QVBoxLayout()
        header_lbl = QLabel("GESTION DES FACTURES & ENGAGEMENTS")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        sub_lbl = QLabel("إدارة المطالبات، الفواتير، والخصومات الاستثنائية")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")
        title_box.addWidget(header_lbl)
        title_box.addWidget(sub_lbl)
        
        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_box)
        hl.addStretch()
        self.main_layout.addWidget(header_frame)

        # ================= 2. شريط الفلترة واختيار الطالب =================
        sel_card = self.create_card()
        slay = QHBoxLayout(sel_card)
        slay.setContentsMargins(20, 15, 20, 15)
        slay.setSpacing(15)
        
        self.combo_classes = self.styled_combo()
        self.combo_classes.currentIndexChanged.connect(self.load_students)
        
        self.combo_students = self.styled_combo()
        self.combo_students.currentIndexChanged.connect(self.load_student_dues)
        
        slay.addWidget(QLabel("📂 Classe (الفصل):"))
        slay.addWidget(self.combo_classes, 1)
        slay.addWidget(QLabel("👤 Élève (الطالب):"))
        slay.addWidget(self.combo_students, 2)
        
        self.main_layout.addWidget(sel_card)

        # ================= 3. منطقة العمل (تقسيم الشاشة لجزئين) =================
        work_layout = QHBoxLayout()
        
        # --- الجزء الأيسر: لوحة التحكميات (إضافة فاتورة / تطبيق خصم) ---
        control_panel = self.create_card()
        control_panel.setFixedWidth(350)
        c_layout = QVBoxLayout(control_panel)
        c_layout.setContentsMargins(15, 15, 15, 15)
        
        self.tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 8px; margin-top: 10px; }}
                QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 10px 15px; border-radius: 6px; margin-right: 2px; font-weight: bold; }}
                QTabBar::tab:selected {{ background: {colors.PRIMARY}; color: white; }}
            """)
        else:
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 8px; margin-top: 10px; }}
                QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 10px 15px; border-radius: 6px; margin-right: 2px; font-weight: bold; }}
                QTabBar::tab:selected {{ background: {colors.PRIMARY}; color: white; }}
            """)

        # التبويب 1: إضافة فاتورة مخصصة
        tab_add = QWidget()
        tab_add_layout = QVBoxLayout(tab_add)
        tab_add_layout.setSpacing(12)
        
        self.txt_fee_title = self.styled_input("Ex: Frais de Transport (وصف الرسوم)")
        self.spin_fee_amount = self.styled_spinbox("Montant: ")
        self.date_fee_due = self.styled_date()
        self.date_fee_due.setDate(QDate.currentDate())
        
        btn_add_fee = QPushButton("➕ Ajouter la Facture (إضافة)")
        self.style_action_button(btn_add_fee, colors.SUCCESS)
        btn_add_fee.clicked.connect(self.add_custom_due)
        
        tab_add_layout.addWidget(QLabel("Type / Description:"))
        tab_add_layout.addWidget(self.txt_fee_title)
        tab_add_layout.addWidget(QLabel("Montant (المبلغ):"))
        tab_add_layout.addWidget(self.spin_fee_amount)
        tab_add_layout.addWidget(QLabel("Date d'échéance (تاريخ الاستحقاق):"))
        tab_add_layout.addWidget(self.date_fee_due)
        tab_add_layout.addStretch()
        tab_add_layout.addWidget(btn_add_fee)
        
        # التبويب 2: تطبيق خصم (Remise)
        tab_discount = QWidget()
        tab_disc_layout = QVBoxLayout(tab_discount)
        tab_disc_layout.setSpacing(12)
        
        self.lbl_selected_due = QLabel("Sélectionnez une facture dans le tableau\n(اختر فاتورة من الجدول أولاً)")
        self.lbl_selected_due.setStyleSheet(f"color: {colors.WARNING}; font-style: italic;")
        self.lbl_selected_due.setWordWrap(True)
        
        self.spin_discount_val = self.styled_spinbox("Remise: ")
        
        btn_apply_disc = QPushButton("🎁 Appliquer Remise (تطبيق الخصم)")
        self.style_action_button(btn_apply_disc, colors.PRIMARY)
        btn_apply_disc.clicked.connect(self.apply_discount)
        
        tab_disc_layout.addWidget(self.lbl_selected_due)
        tab_disc_layout.addWidget(QLabel("Montant de la remise (قيمة الخصم):"))
        tab_disc_layout.addWidget(self.spin_discount_val)
        tab_disc_layout.addStretch()
        tab_disc_layout.addWidget(btn_apply_disc)

        self.tabs.addTab(tab_add, "➕ Nouvelle")
        self.tabs.addTab(tab_discount, "🎁 Remise")
        
        c_layout.addWidget(self.tabs)
        
        # زر توليد الرسوم التلقائية للصف (اختياري)
        btn_generate_auto = QPushButton("⚙️ Générer Mensualités (توليد أقساط)")
        if THEME_AVAILABLE:
            self.style_action_button(btn_generate_auto, ThemeManager.get_colors().PRIMARY_DARK)
        else:
            self.style_action_button(btn_generate_auto, Colors().PRIMARY_DARK)
        btn_generate_auto.clicked.connect(self.generate_auto_dues)
        c_layout.addWidget(btn_generate_auto)

        # --- الجزء الأيمن: جدول الفواتير (Ledger) ---
        table_panel = self.create_card()
        t_layout = QVBoxLayout(table_panel)
        
        table_title = QLabel("📄 Relevé de Compte (كشف حساب المطالبات)")
        table_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        table_title.setStyleSheet(f"color: {colors.TEXT_PRIMARY};")

        btn_export = QPushButton("🖨️ Exporter Rapport Factures")
        self.style_action_button(btn_export, colors.PRIMARY)
        btn_export.setMinimumHeight(38)
        btn_export.clicked.connect(self.export_student_dues_report)

        title_row = QHBoxLayout()
        title_row.addWidget(table_title)
        title_row.addStretch()
        title_row.addWidget(btn_export)
        
        self.table_dues = QTableWidget()
        self.style_table(self.table_dues)
        self.table_dues.setColumnCount(8)
        self.table_dues.setHorizontalHeaderLabels([
            "ID", "Description", "Date", "Montant",
            "Remise", "Net", "Statut", "Actions"
        ])
        self.table_dues.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_dues.itemSelectionChanged.connect(self.on_due_selected)
        
        t_layout.addLayout(title_row)
        t_layout.addWidget(self.table_dues)
        
        work_layout.addWidget(control_panel)
        work_layout.addWidget(table_panel, 1)
        
        self.main_layout.addLayout(work_layout)

    # ================== Helper UI Methods ==================
    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20); shadow.setColor(QColor(15, 23, 42, 15)); shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"""
            QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-weight: bold; }}
        """)
        combo.setMinimumHeight(40)
        return combo

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        le.setMinimumHeight(40)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        le.setStyleSheet(f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        return le

    def styled_spinbox(self, prefix):
        sb = QDoubleSpinBox()
        sb.setRange(0, 10000000)
        sb.setPrefix(prefix)
        sb.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        sb.setMinimumHeight(40)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        sb.setStyleSheet(f"QDoubleSpinBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-weight: bold; }}")
        return sb
        
    def styled_date(self):
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setMinimumHeight(40)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        de.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        return de

    def style_action_button(self, btn, bg_color):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(45)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {bg_color}; color: white; font-weight: bold; border-radius: 6px; border: none; font-size: 13px; }}
            QPushButton:hover {{ opacity: 0.8; }}
        """)

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())
        else:
            colors = Colors()
            table.setStyleSheet(f"""
                QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
            """)

    # ================== Logic Methods ==================
    def load_classes(self):
        self.combo_classes.clear()
        self.combo_classes.addItem("- Choisir Classe -", None)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, COALESCE(class_name_fr, '-') FROM Classes ORDER BY class_name_fr")
                for c in cursor.fetchall(): 
                    self.combo_classes.addItem(str(c[1] or "-"), c[0])
        except Exception as e:
            AppLogger.error("PaymentManagement", f"Error loading classes: {e}")

    def load_students(self):
        cid = self.combo_classes.currentData()
        self.combo_students.clear()
        self.combo_students.addItem("- Tous les élèves (الكل) -", None)
        if not cid: return

        active_year = self.get_active_year_id()
        if active_year == -1: return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT S.id,
                           TRIM(COALESCE(S.first_name_fr, '') || ' ' || COALESCE(S.last_name_fr, '')) AS student_name
                    FROM Students S
                    JOIN StudentClassNumbers SCN ON S.id = SCN.student_id 
                    WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
                """, (cid, active_year))
                for s in cursor.fetchall(): 
                    self.combo_students.addItem((str(s[1] or "").strip() or "[Élève]"), s[0])
        except Exception as e:
            AppLogger.error("PaymentManagement", f"Error loading students: {e}")

    def load_student_dues(self):
        self.table_dues.setRowCount(0)
        self.lbl_selected_due.setText("Sélectionnez une facture dans le tableau")
        self.spin_discount_val.setValue(0)
        
        sid = self.combo_students.currentData()
        if not sid: return
        
        active_year = self.get_active_year_id()
        if active_year == -1: return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, fee_type, fee_description, original_amount, discount_amount, net_amount, due_date, is_paid
                    FROM StudentDues
                    WHERE student_id=%s AND year_id=%s
                    ORDER BY due_date ASC, id ASC
                """, (sid, active_year))
                rows = cursor.fetchall()
                
                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

                def _to_float(value):
                    try:
                        return float(value)
                    except Exception:
                        return 0.0

                for row in rows:
                    idx = self.table_dues.rowCount()
                    self.table_dues.insertRow(idx)

                    original_amount = _to_float(row[3])
                    discount_amount = _to_float(row[4])
                    net_amount = _to_float(row[5])
                    
                    self.table_dues.setItem(idx, 0, QTableWidgetItem(str(row[0])))
                    
                    desc = (str(row[2] or row[1] or "-")).strip() or "-"
                    self.table_dues.setItem(idx, 1, QTableWidgetItem(desc))
                    self.table_dues.setItem(idx, 2, QTableWidgetItem(str(row[6] or "-")))
                    
                    self.table_dues.setItem(idx, 3, QTableWidgetItem(f"{original_amount:,.0f}"))
                    self.table_dues.setItem(idx, 4, QTableWidgetItem(f"{discount_amount:,.0f}"))
                    
                    net_item = QTableWidgetItem(f"{net_amount:,.0f}")
                    net_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                    self.table_dues.setItem(idx, 5, net_item)
                    
                    status_txt = "✅ Réglé (مدفوع)" if row[7] else "⏳ En attente (مستحق)"
                    status_item = QTableWidgetItem(status_txt)
                    status_item.setForeground(QColor(colors.SUCCESS if row[7] else colors.WARNING))
                    self.table_dues.setItem(idx, 6, status_item)
                    
                    container = QWidget()
                    btn_layout = QHBoxLayout(container)
                    btn_layout.setContentsMargins(2, 2, 2, 2)
                    if not row[7]: # إذا لم تكن مدفوعة
                        btn_del = QPushButton("✕")
                        btn_del.setFixedSize(28, 28)
                        btn_del.setStyleSheet(f"background: {colors.DANGER}; color: white; border-radius: 4px;")
                        btn_del.clicked.connect(lambda ch, fid=row[0]: self.delete_due(fid))
                        btn_layout.addWidget(btn_del)
                    self.table_dues.setCellWidget(idx, 7, container)
        except Exception as e:
            AppLogger.error("PaymentManagement", f"Error loading dues: {e}")

    def on_due_selected(self):
        rows = self.table_dues.selectedItems()
        if not rows: return
        r = rows[0].row()
        
        due_id = self.table_dues.item(r, 0).text()
        desc = self.table_dues.item(r, 1).text()
        original = float(self.table_dues.item(r, 3).text().replace(',', ''))
        discount = float(self.table_dues.item(r, 4).text().replace(',', ''))
        
        self.lbl_selected_due.setText(f"Facture sélectionnée:\n[{due_id}] {desc}\nOriginal: {original:,.0f}")
        self.spin_discount_val.setMaximum(original)
        self.spin_discount_val.setValue(discount)
        
        self.tabs.setCurrentIndex(1)

    def add_custom_due(self):
        sid = self.combo_students.currentData()
        if not sid:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève d'abord.")
            return
            
        desc = self.txt_fee_title.text().strip()
        amt = self.spin_fee_amount.value()
        date_d = self.date_fee_due.date().toString("yyyy-MM-dd")
        
        if not desc or amt <= 0:
            QMessageBox.warning(self, "Erreur", "La description et le montant sont obligatoires.")
            return
            
        active_year = self.get_active_year_id()
        if active_year == -1: return
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO StudentDues (student_id, year_id, fee_type, fee_description, original_amount, net_amount, due_date)
                    VALUES (%s, %s, 'Custom', %s, %s, %s, %s)
                """, (sid, active_year, desc, amt, amt, date_d))
                conn.commit()
                
            QMessageBox.information(self, "Succès", "Facture ajoutée avec succès.")
            self.txt_fee_title.clear()
            self.spin_fee_amount.setValue(0)
            self.load_student_dues()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def apply_discount(self):
        rows = self.table_dues.selectedItems()
        if not rows:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une facture.")
            return
            
        r = rows[0].row()
        due_id = self.table_dues.item(r, 0).text()
        original_amt = float(self.table_dues.item(r, 3).text().replace(',', ''))
        new_discount = self.spin_discount_val.value()
        
        if new_discount > original_amt:
            QMessageBox.warning(self, "Erreur", "La remise ne peut pas dépasser le montant original.")
            return
            
        new_net = original_amt - new_discount
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT is_paid FROM StudentDues WHERE id=%s", (due_id,))
                res = cursor.fetchone()
                if res and res[0]:
                    QMessageBox.warning(self, "Erreur", "Impossible de modifier une facture déjà payée.")
                    return
                    
                cursor.execute("""
                    UPDATE StudentDues 
                    SET discount_amount=%s, net_amount=%s 
                    WHERE id=%s
                """, (new_discount, new_net, due_id))
                conn.commit()
                
            QMessageBox.information(self, "Succès", "Remise appliquée avec succès.")
            self.load_student_dues()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_due(self, due_id):
        reply = QMessageBox.question(self, "Confirmation", "Voulez-vous supprimer cette facture ?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM StudentDues WHERE id=%s", (due_id,))
                    conn.commit()
                self.load_student_dues()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def generate_auto_dues(self):
        cid = self.combo_classes.currentData()
        if not cid:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner une classe pour générer les factures.")
            return
            
        active_year = self.get_active_year_id()
        if active_year == -1: return

        reply = QMessageBox.question(self, "Confirmation", 
            "Cette action va générer les factures (Inscription et Mensualités) pour TOUS les élèves de cette classe qui n'en ont pas encore. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if reply != QMessageBox.StandardButton.Yes: return
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT amount FROM RegistrationFees WHERE class_id=%s", (cid,))
                reg_res = cursor.fetchone()
                reg_amt = reg_res[0] if reg_res else 0.0
                
                cursor.execute("SELECT month_index, month_name, amount FROM MonthlyFeeSchedule WHERE class_id=%s", (cid,))
                monthly_fees = cursor.fetchall()
                
                cursor.execute("""
                    SELECT S.id 
                    FROM Students S
                    JOIN StudentClassNumbers SCN ON S.id = SCN.student_id 
                    WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
                """, (cid, active_year))
                students = cursor.fetchall()
                
                generated_count = 0
                today_str = QDate.currentDate().toString("yyyy-MM-dd")
                
                for (sid,) in students:
                    if reg_amt > 0:
                        cursor.execute("SELECT COUNT(*) FROM StudentDues WHERE student_id=%s AND year_id=%s AND fee_type='Registration'", (sid, active_year))
                        if cursor.fetchone()[0] == 0:
                            cursor.execute("""
                                INSERT INTO StudentDues (student_id, year_id, fee_type, fee_description, original_amount, net_amount, due_date)
                                VALUES (%s, %s, 'Registration', 'Frais d''inscription', %s, %s, %s)
                            """, (sid, active_year, reg_amt, reg_amt, today_str))
                            generated_count += 1
                            
                    for m_idx, m_name, m_amt in monthly_fees:
                        cursor.execute("SELECT COUNT(*) FROM StudentDues WHERE student_id=%s AND year_id=%s AND fee_type=%s", (sid, active_year, f'Month_{m_idx}'))
                        if cursor.fetchone()[0] == 0:
                            due_y = datetime.now().year
                            if m_idx < 9: due_y += 1 
                            due_d = f"{due_y}-{m_idx:02d}-05"
                            
                            cursor.execute("""
                                INSERT INTO StudentDues (student_id, year_id, fee_type, fee_description, original_amount, net_amount, due_date)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (sid, active_year, f'Month_{m_idx}', f'Mensualité {m_name}', m_amt, m_amt, due_d))
                            generated_count += 1
                            
                conn.commit()
                QMessageBox.information(self, "Terminé", f"Opération terminée. {generated_count} factures générées.")
                self.load_student_dues() 
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _slugify(self, value):
        text = (value or "").strip().replace(" ", "_")
        clean = "".join(ch for ch in text if ch.isalnum() or ch in "-_")
        return clean or "NA"

    def export_student_dues_report(self):
        student_id = self.combo_students.currentData()
        if not student_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève d'abord.")
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            QMessageBox.warning(self, "Erreur", "Aucune année scolaire active trouvée.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
                school_info = cursor.fetchone()

                cursor.execute("""
                    SELECT
                        TRIM(COALESCE(S.first_name_fr, '') || ' ' || COALESCE(S.last_name_fr, '')),
                        COALESCE(C.class_name_fr, '-'),
                        COALESCE((SELECT year_label FROM AcademicYears WHERE id = %s), '-')
                    FROM Students S
                    LEFT JOIN StudentClassNumbers SCN ON SCN.student_id = S.id AND SCN.year_id = %s
                    LEFT JOIN Classes C ON C.id = SCN.class_id
                    WHERE S.id = %s
                    LIMIT 1
                """, (active_year, active_year, student_id))
                student_meta = cursor.fetchone()

                cursor.execute("""
                    SELECT fee_type, fee_description, due_date, original_amount, discount_amount, net_amount, is_paid
                    FROM StudentDues
                    WHERE student_id = %s AND year_id = %s
                    ORDER BY due_date ASC, id ASC
                """, (student_id, active_year))
                dues_rows = cursor.fetchall()

            if not dues_rows:
                QMessageBox.information(self, "Aucune donnée", "Aucune facture à exporter pour cet élève.")
                return

            student_name = student_meta[0] if student_meta else self.combo_students.currentText()
            class_name = student_meta[1] if student_meta else (self.combo_classes.currentText() or "-")
            year_name = student_meta[2] if student_meta else "-"

            pdf = StudentDuesReportPDF(orientation='L', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            apply_grades_sheet_header(pdf, school_info, "RAPPORT DES FACTURES ET ENGAGEMENTS", "Helvetica")

            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, pdf.sanitize(f"Eleve: {student_name}"), 0, 1, 'L')
            pdf.cell(0, 6, pdf.sanitize(f"Classe: {class_name} | Annee: {year_name}"), 0, 1, 'L')
            pdf.cell(0, 6, f"Genere le: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'L')
            pdf.ln(2)

            headers = ["Description", "Echeance", "Montant", "Remise", "Net", "Statut"]
            col_widths = [110, 35, 30, 30, 30, 35]
            pdf.set_fill_color(30, 41, 59)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 10)
            for idx, header in enumerate(headers):
                ln_value = 1 if idx == len(headers) - 1 else 0
                pdf.cell(col_widths[idx], 8, header, 1, ln_value, 'C', True)

            total_original = 0.0
            total_discount = 0.0
            total_net = 0.0
            total_paid = 0.0
            total_pending = 0.0

            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 9)
            for index, row in enumerate(dues_rows):
                fee_type, fee_desc, due_date, original, discount, net, is_paid = row
                desc = str(fee_desc or fee_type or "-")
                original_val = float(original or 0)
                discount_val = float(discount or 0)
                net_val = float(net or 0)
                status = "Regle" if int(is_paid or 0) == 1 else "En attente"

                total_original += original_val
                total_discount += discount_val
                total_net += net_val
                if int(is_paid or 0) == 1:
                    total_paid += net_val
                else:
                    total_pending += net_val

                if index % 2 == 0:
                    pdf.set_fill_color(245, 247, 250)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.cell(col_widths[0], 7, pdf.sanitize(desc), 1, 0, 'L', True)
                pdf.cell(col_widths[1], 7, str(due_date or "-"), 1, 0, 'C', True)
                pdf.cell(col_widths[2], 7, f"{original_val:,.0f}", 1, 0, 'R', True)
                pdf.cell(col_widths[3], 7, f"{discount_val:,.0f}", 1, 0, 'R', True)
                pdf.cell(col_widths[4], 7, f"{net_val:,.0f}", 1, 0, 'R', True)
                pdf.cell(col_widths[5], 7, status, 1, 1, 'C', True)

            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"Total Montant: {total_original:,.0f} | Total Remise: {total_discount:,.0f}", 0, 1, 'R')
            pdf.cell(0, 6, f"Total Net: {total_net:,.0f} | Regle: {total_paid:,.0f} | En attente: {total_pending:,.0f}", 0, 1, 'R')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            student_slug = self._slugify(student_name)
            class_slug = self._slugify(class_name)
            default_name = f"Factures_Eleve_{student_slug}_{class_slug}_{timestamp}.pdf"

            output_pdf(
                pdf,
                self,
                default_name,
                mode=STUDENT_DUES_REPORT_OUTPUT_MODE,
                dialog_title="Sauvegarder rapport des factures",
                success_save_message="Rapport des factures exporte avec succes.",
                success_print_message="Rapport des factures envoye a l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export du rapport: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentDuesWindow()
    window.show()
    sys.exit(app.exec())