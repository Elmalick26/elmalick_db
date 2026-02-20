import sys
import sqlite3
import os
from datetime import datetime
from database_setup import DatabaseManager
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QDateEdit, 
                             QTabWidget, QGridLayout, QDoubleSpinBox, QTextEdit, 
                             QFrame, QGraphicsDropShadowEffect, QScrollArea, QDialog, QFileDialog)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style

THEME_AVAILABLE = True

# --- دعم اللغة العربية في FPDF ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ModuleNotFoundError:
    ARABIC_SUPPORT = False
    # تم تعطيل التحذير لتجنب ظهوره في Console للنسخة النهائية
    # print("Warning: arabic_reshaper or python-bidi not found. Arabic text might not render correctly.")

def _get_arabic_font_path():
    """البحث عن خط عربي مناسب في النظام أو المجلد"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "Fonts", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "fonts", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "Amiri-Regular.ttf"),
        "C:\\Windows\\Fonts\\arial.ttf", # قد يدعم العربية في بعض النسخ
        "C:\\Windows\\Fonts\\tahoma.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def fix_text(text):
    """معالجة النص العربي للظهور بشكل صحيح في PDF"""
    if not text: return ""
    text = str(text)
    if ARABIC_SUPPORT:
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except:
            return text
    return text.encode('latin-1', 'ignore').decode('latin-1') # Fallback for french accents if no arabic support

# --- فئة تقارير الانضباط (FPDF Native) ---
class DisciplinePDF(FPDF):
    def __init__(self, school_info):
        # هوامش ضيقة (10mm)
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_margins(10, 10, 10)
        self.school_info = school_info
        
        # محاولة تحميل خط عربي
        self.font_family = 'Arial'
        font_path = _get_arabic_font_path()
        if font_path and ARABIC_SUPPORT:
            try:
                self.add_font('ArabicFont', '', font_path, uni=True)
                self.add_font('ArabicFont', 'B', font_path, uni=True)
                self.font_family = 'ArabicFont'
            except:
                pass

    def sanitize(self, text):
        """تنظيف النص وجعله مناسبًا للطباعة بالعربية"""
        return fix_text(text)

    def header(self):
        left_x, left_y = 10, 5
        self.set_xy(left_x, left_y)
        self.set_font(self.font_family, '', 8)
        
        if self.school_info:
            republic = self.sanitize(self.school_info[1])
            self.cell(80, 3, republic, 0, 1, 'L')
            ia_text = self.sanitize(self.school_info[2])
            self.cell(80, 3, ia_text, 0, 1, 'L')
            ief_text = self.sanitize(self.school_info[3])
            self.cell(80, 3, ief_text, 0, 1, 'L')
            school_name = self.sanitize(self.school_info[4])
            self.cell(80, 3, school_name, 0, 1, 'L')
            auth_text = self.sanitize(self.school_info[5])
            self.cell(80, 3, f"Auto N: {auth_text}", 0, 1, 'L')
            addr_text = self.sanitize(self.school_info[6])
            self.cell(80, 3, f"Lieu: {addr_text}", 0, 1, 'L')
            phone_text = self.sanitize(self.school_info[7])
            self.cell(80, 3, f"Tel: {phone_text}", 0, 1, 'L')

        right_x = 175
        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=20, h=22)
            except: pass
        
        self.set_xy(right_x, left_y + 22)
        self.set_y(self.get_y() + 2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, '', 8)
        self.cell(0, 10, fix_text('Document généré par le système - وثيقة مستخرجة من النظام'), 0, 0, 'C')

    def create_convocation(self, data):
        self.add_page()
        
        # العنوان في إطار
        self.set_font(self.font_family, 'B', 18)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 15, fix_text("CONVOCATION / استدعاء ولي أمر"), 1, 1, 'C', True)
        self.ln(15)

        # المحتوى
        self.set_font(self.font_family, '', 14)
        
        # نوجه الكلام للولي
        self.cell(0, 10, fix_text("A l'attention du Tuteur de l'élève :"), 0, 1, 'L')
        self.set_font(self.font_family, 'B', 16)
        self.cell(0, 10, fix_text(f"   {data['name']}"), 0, 1, 'L')
        self.set_font(self.font_family, '', 14)
        self.cell(0, 10, fix_text(f"   Classe: {data['class']}"), 0, 1, 'L')
        
        self.ln(10)
        self.multi_cell(0, 10, fix_text(
            "Monsieur/Madame,\n\n"
            "Vous êtes prié(e) de bien vouloir vous présenter à la direction de l'école "
            "le plus tôt possible (ou à la date indiquée ci-dessous) pour une affaire concernant votre enfant.\n"
        ))
        
        self.ln(5)
        self.set_font(self.font_family, 'B', 14)
        self.cell(0, 10, fix_text("Motif de la convocation / سبب الاستدعاء :"), 0, 1, 'L')
        
        # مربع للملاحظة
        self.set_font(self.font_family, '', 12)
        self.set_fill_color(255, 245, 245) # لون خفيف
        self.multi_cell(0, 10, fix_text(f"\n{data['inc']} (Date: {data['date']})\n\nDétails: {data['obs']}\n"), 1, 'L', True)
        
        self.ln(20)
        
        # التوقيع
        self.set_font(self.font_family, 'B', 12)
        self.cell(95, 10, fix_text("Signature du Tuteur"), 0, 0, 'C')
        self.cell(95, 10, fix_text("Le Directeur / Administration"), 0, 1, 'C')

    def create_sanction_notice(self, data):
        self.add_page()
        
        # العنوان
        self.set_font(self.font_family, 'B', 20)
        self.set_text_color(200, 0, 0) # أحمر
        self.cell(0, 15, fix_text("NOTIFICATION DE SANCTION / إشعار بعقوبة"), 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(10)
        
        # تفاصيل الطالب
        self.set_font(self.font_family, 'B', 14)
        self.cell(0, 10, fix_text(f"Élève : {data['name']}   -   Classe : {data['class']}"), 0, 1, 'C')
        self.line(40, self.get_y(), 170, self.get_y())
        self.ln(15)
        
        # العقوبة
        self.set_font(self.font_family, '', 14)
        self.multi_cell(0, 10, fix_text(
            "Suite aux faits relevés, le Conseil de Discipline a décidé de la sanction suivante :\n"
        ))
        
        self.ln(5)
        self.set_font(self.font_family, 'B', 24)
        self.set_fill_color(230, 230, 230)
        self.multi_cell(0, 20, fix_text(data['sanction']), 1, 'C', True)
        
        self.ln(10)
        if float(data['pts']) > 0:
            self.set_text_color(200, 0, 0)
            self.set_font(self.font_family, 'B', 16)
            self.cell(0, 10, fix_text(f"DÉDUCTION DE POINTS (Conduite) : -{data['pts']}"), 0, 1, 'C')
            self.set_text_color(0, 0, 0)
            self.ln(10)
            
        # التفاصيل
        self.set_font(self.font_family, 'B', 12)
        self.cell(0, 10, fix_text("Détails de l'infraction :"), 0, 1, 'L')
        self.set_font(self.font_family, '', 12)
        self.multi_cell(0, 8, fix_text(f"Type: {data['inc']}\nDate: {data['date']}\nObservation: {data['obs']}"))
        
        self.ln(30)
        self.set_font(self.font_family, 'B', 12)
        self.cell(0, 10, fix_text("Le Directeur / Le Surveillant Général"), 0, 1, 'R')


class DisciplineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discipline & Sanctions / الانضباط والسلوك")
        self.setMinimumSize(1100, 700)
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            # Deep Slate Theme
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors.BG_MAIN};
                }}
                QLabel {{
                    font-family: 'Segoe UI', 'Cairo', sans-serif;
                    color: {colors.TEXT_PRIMARY};
                }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    margin-top: 10px;
                    background-color: {colors.BG_CARD};
                    font-weight: bold;
                    color: {colors.TEXT_SECONDARY};
                }}
            """)
        
        # self.init_db() - centralized
        self.init_ui()
        self.load_classes()

    # init_db removed - handled by database_setup.py

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # 1. Header Frame
        header_frame = QFrame()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_HEADER};
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
        
        icon_lbl = QLabel("⚖️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DE LA DISCIPLINE")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {Colors().HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("تسجيل المخالفات، العقوبات، واستدعاءات الأولياء")
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
        
        self.layout.addWidget(header_frame)

        # 2. Tabs
        self.tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.tabs.setStyleSheet(get_tabs_style())
        else:
            colors = Colors()
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ 
                    border: 1px solid {colors.BORDER}; 
                    background: {colors.BG_CARD}; 
                    border-radius: 12px; 
                    margin-top: 15px; 
                }}
                QTabBar::tab {{ 
                    background: {colors.BG_MAIN}; 
                    color: {colors.TEXT_SECONDARY}; 
                    padding: 12px 30px; 
                    margin-right: 6px; 
                    border-top-left-radius: 8px; 
                    border-top-right-radius: 8px; 
                    font-weight: bold; 
                    font-family: 'Segoe UI', 'Cairo';
                }}
                QTabBar::tab:selected {{ 
                    background: {colors.BG_HEADER}; 
                    color: {colors.HEADER_TEXT}; 
                }}
                QTabBar::tab:hover {{
                    background: {colors.BORDER}; 
                }}
            """)
        
        self.setup_entry_tab()
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
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        combo = QComboBox()
        combo.setMinimumHeight(38)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())
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

    def setup_entry_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else None
        
        # --- Form Card (Left) ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        if THEME_AVAILABLE:
            scroll_area.setStyleSheet(f"""
                QScrollArea {{ background: transparent; border: none; }}
                QScrollBar:vertical {{
                    border: none;
                    background: {colors.SCROLL_BG};
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: {colors.SCROLL_HANDLE};
                    min-height: 20px;
                    border-radius: 4px;
                }}
            """)
        else:
            colors = Colors()
            scroll_area.setStyleSheet(f"""
                QScrollArea {{ background: transparent; border: none; }}
                QScrollBar:vertical {{
                    border: none;
                    background: {colors.BG_MAIN};
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: {colors.TEXT_SECONDARY};
                    min-height: 20px;
                    border-radius: 4px;
                }}
            """)

        form_card = self.create_card()
        form_card.setMinimumWidth(350) 
        
        flay = QVBoxLayout(form_card)
        flay.setContentsMargins(20, 20, 20, 20)
        flay.setSpacing(15)
        
        lbl_title = QLabel("Nouveau Signalement / تسجيل مخالفة")
        if THEME_AVAILABLE:
            lbl_title.setStyleSheet(f"font-weight: bold; color: {colors.DANGER}; font-size: 14px;")
        else:
            lbl_title.setStyleSheet(f"font-weight: bold; color: {Colors().DANGER}; font-size: 14px;")
        flay.addWidget(lbl_title)
        
        self.combo_class_entry = self.styled_combo()
        self.combo_class_entry.currentIndexChanged.connect(self.load_students_entry)
        self.combo_student_entry = self.styled_combo()
        
        self.date_incident = QDateEdit()
        self.date_incident.setCalendarPopup(True)
        self.date_incident.setDate(QDate.currentDate())
        if THEME_AVAILABLE:
            self.date_incident.setStyleSheet(
                f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
            )
        else:
            colors = Colors()
            self.date_incident.setStyleSheet(
                f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
            )
        self.date_incident.setMinimumHeight(38)
        
        self.combo_type = self.styled_combo()
        self.combo_type.addItems([
            "Bavardage / ثرثرة", "Retard / تأخر", "Absence injustifiée / غياب غير مبرر", 
            "Non port de la tenue / عدم ارتداء الزي", "Insolence / وقاحة", 
            "Bagarre / شجار", "Tricherie / غش", "Dégradation de matériel / تخريب"
        ])
        
        self.txt_sanction = self.styled_input("Sanction (ex: Avertissement)")
        
        self.lbl_points_title = QLabel("Points à déduire (Note Conduite / 20):")
        self.spin_points = QDoubleSpinBox()
        self.spin_points.setRange(0, 20)
        self.spin_points.setPrefix("Déduction: -")
        if THEME_AVAILABLE:
            self.spin_points.setStyleSheet(
                f"QDoubleSpinBox {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.BG_MAIN}; color: {colors.DANGER}; font-weight: bold; }}"
            )
        else:
            colors = Colors()
            self.spin_points.setStyleSheet(
                f"QDoubleSpinBox {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.BG_MAIN}; color: {colors.DANGER}; font-weight: bold; }}"
            )
        self.spin_points.setMinimumHeight(38)
        
        self.txt_obs = QTextEdit()
        self.txt_obs.setPlaceholderText("Détails de l'incident...")
        self.txt_obs.setMaximumHeight(80)
        self.txt_obs.setMinimumHeight(60) 
        if THEME_AVAILABLE:
            self.txt_obs.setStyleSheet(
                f"QTextEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
            )
        else:
            colors = Colors()
            self.txt_obs.setStyleSheet(
                f"QTextEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
            )
        
        btn_save = QPushButton("💾 Enregistrer / حفظ")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_save.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.DANGER}; color: white; font-weight: bold; 
                    border-radius: 8px; border: none; font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_save.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.DANGER}; color: white; font-weight: bold; 
                    border-radius: 8px; border: none; font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
        btn_save.clicked.connect(self.save_incident)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(QLabel("Classe:"), 0, 0); grid.addWidget(self.combo_class_entry, 0, 1)
        grid.addWidget(QLabel("Élève:"), 1, 0); grid.addWidget(self.combo_student_entry, 1, 1)
        grid.addWidget(QLabel("Date:"), 2, 0); grid.addWidget(self.date_incident, 2, 1)
        grid.addWidget(QLabel("Type:"), 3, 0); grid.addWidget(self.combo_type, 3, 1)
        
        flay.addLayout(grid)
        flay.addWidget(QLabel("Sanction prise:"))
        flay.addWidget(self.txt_sanction)
        flay.addWidget(self.lbl_points_title)
        flay.addWidget(self.spin_points)
        flay.addWidget(QLabel("Observation:"))
        flay.addWidget(self.txt_obs)
        flay.addSpacing(10)
        flay.addWidget(btn_save)
        flay.addStretch()

        scroll_area.setWidget(form_card)
        layout.addWidget(scroll_area, 2) 

        # --- Recent Incidents (Right) ---
        list_card = self.create_card()
        llay = QVBoxLayout(list_card)
        llay.setContentsMargins(20, 20, 20, 20)
        
        lbl_recent = QLabel("Derniers Incidents / آخر المخالفات")
        if THEME_AVAILABLE:
            lbl_recent.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        else:
            lbl_recent.setStyleSheet(f"font-weight: bold; color: {Colors().TEXT_PRIMARY}; font-size: 14px;")
        llay.addWidget(lbl_recent)
        
        self.table_recent = QTableWidget(0, 4)
        self.style_table(self.table_recent)
        self.table_recent.setHorizontalHeaderLabels(["Élève", "Date", "Type", "Pts"])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_recent.setColumnWidth(3, 50)
        llay.addWidget(self.table_recent)
        
        layout.addWidget(list_card, 2) 
        
        self.tabs.addTab(tab, "  📝 Saisie Incident / تسجيل  ")

    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Filter Card
        filter_card = self.create_card()
        hlay = QHBoxLayout(filter_card)
        hlay.setContentsMargins(15, 15, 15, 15)
        
        self.combo_class_hist = self.styled_combo()
        self.combo_class_hist.currentIndexChanged.connect(self.load_history)
        self.combo_class_hist.setFixedWidth(200)
        
        self.txt_search = self.styled_input("🔍 Chercher un élève...")
        self.txt_search.textChanged.connect(self.load_history)
        
        hlay.addWidget(QLabel("Filtrer par Classe:"))
        hlay.addWidget(self.combo_class_hist)
        hlay.addWidget(self.txt_search)
        layout.addWidget(filter_card)

        # Table
        self.table_history = QTableWidget(0, 7)
        self.style_table(self.table_history)
        self.table_history.setHorizontalHeaderLabels(["Élève", "Classe", "Date", "Incident", "Sanction",  "Pts", "Action"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_history.setColumnWidth(0, 50)
        self.table_history.setColumnWidth(6, 60)
        self.table_history.itemClicked.connect(self.on_history_item_clicked)
        layout.addWidget(self.table_history)

        self.tabs.addTab(tab, "  📋 Historique & Rapports / السجل  ")

    # --- Logic ---
    def load_classes(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, class_name_fr FROM Classes")
            classes = cursor.fetchall()
        
        self.combo_class_entry.clear()
        self.combo_class_hist.clear()
        
        self.combo_class_entry.addItem("-", None)
        self.combo_class_hist.addItem("Toutes", None)
        
        for c in classes:
            self.combo_class_entry.addItem(c[1], c[0])
            self.combo_class_hist.addItem(c[1], c[0])
        conn.close()

    def load_students_entry(self):
        cid = self.combo_class_entry.currentData()
        self.combo_student_entry.clear()
        if not cid: return
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check cycle for points scale
            cursor.execute("""
                SELECT CY.name_fr 
                FROM Classes CL 
                JOIN Cycles CY ON CL.cycle_id = CY.id 
                WHERE CL.id = ?
            """, (cid,))
            res = cursor.fetchone()
            
            is_primary = False
            if res:
                cycle_name = res[0].lower()
                if "elem" in cycle_name or "prim" in cycle_name or "ibtida" in cycle_name:
                    is_primary = True
            
            if is_primary:
                self.spin_points.setRange(0, 10)
                self.lbl_points_title.setText("Points à déduire (Note Conduite / 10):")
            else:
                self.spin_points.setRange(0, 20)
                self.lbl_points_title.setText("Points à déduire (Note Conduite / 20):")
            
            cursor.execute("SELECT id, first_name_fr || ' ' || last_name_fr FROM Students WHERE class_id=?", (cid,))
            for s in cursor.fetchall():
                self.combo_student_entry.addItem(s[1], s[0])

    def save_incident(self):
        sid = self.combo_student_entry.currentData()
        inc_type = self.combo_type.currentText()
        date_inc = self.date_incident.date().toString("yyyy-MM-dd")
        sanction = self.txt_sanction.text()
        pts = self.spin_points.value()
        obs = self.txt_obs.toPlainText()

        if not sid:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève.")
            return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # الحصول على السنة الدراسية النشطة
            cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
            active_year = cursor.fetchone()
            year_id = active_year[0] if active_year else None
            
            cursor.execute("""
                INSERT INTO StudentDiscipline (student_id, incident_date, incident_type, sanction, points_deducted, observation, year_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sid, date_inc, inc_type, sanction, pts, obs, year_id))
            conn.commit()
        
        self.load_recent()
        self.load_history()
        self.txt_sanction.clear(); self.txt_obs.clear(); self.spin_points.setValue(0)
        QMessageBox.information(self, "Succès", "Incident enregistré.")

    def load_recent(self):
        self.table_recent.setRowCount(0)
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT S.first_name_fr, D.incident_date, D.incident_type, D.points_deducted
                FROM StudentDiscipline D JOIN Students S ON D.student_id = S.id
                ORDER BY D.id DESC LIMIT 10
            """)
            for r in cursor.fetchall():
                idx = self.table_recent.rowCount()
                self.table_recent.insertRow(idx)
                self.table_recent.setItem(idx, 0, QTableWidgetItem(r[0]))
                self.table_recent.setItem(idx, 1, QTableWidgetItem(r[1]))
                self.table_recent.setItem(idx, 2, QTableWidgetItem(r[2]))
                
                pts_item = QTableWidgetItem(f"-{r[3]}")
                pts_item.setForeground(QColor(Colors().DANGER))
                pts_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table_recent.setItem(idx, 3, pts_item)

    def load_history(self):
        self.table_history.setRowCount(0)
        cid = self.combo_class_hist.currentData()
        search = self.txt_search.text()
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT D.id, S.first_name_fr || ' ' || S.last_name_fr, C.class_name_fr, 
                    D.incident_date, D.incident_type, D.sanction, D.points_deducted, D.observation
                FROM StudentDiscipline D 
                JOIN Students S ON D.student_id = S.id
                JOIN Classes C ON S.class_id = C.id
                WHERE 1=1
            """
            params = []
            if cid:
                query += " AND S.class_id = ?"
                params.append(cid)
            if search:
                query += " AND (S.first_name_fr LIKE ? OR S.last_name_fr LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
                
            query += " ORDER BY D.incident_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        for r in rows:
            idx = self.table_history.rowCount()
            self.table_history.insertRow(idx)
            # 0:ID, 1:Name, 2:Class, 3:Date, 4:Type, 5:Sanction, 6:Pts, 7:Obs
            for i in range(6):
                self.table_history.setItem(idx, i, QTableWidgetItem(str(r[i+1]))) 
                
            # Actions
            btn_print = QPushButton("🖨️")
            btn_print.setToolTip("Imprimer Convocation / Notification")
            btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                btn_print.setStyleSheet(f"""
                    QPushButton {{ background-color: {colors.PRIMARY}; color: white; border-radius: 4px; border: none; font-weight: bold; }}
                    QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
                """)
            else:
                colors = Colors()
                btn_print.setStyleSheet(f"""
                    QPushButton {{ background-color: {colors.PRIMARY}; color: white; border-radius: 4px; border: none; font-weight: bold; }}
                    QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
                """)
            data = {'name': r[1], 'class': r[2], 'inc': r[4], 'date': r[3], 'obs': r[7], 'sanction': r[5], 'pts': r[6]}
            btn_print.clicked.connect(lambda ch, d=data: self.print_action(d))
            
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(0,0,0,0)
            l.addWidget(btn_print)
            self.table_history.setCellWidget(idx, 6, w)

    def get_incident_details(self, incident_id):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT D.id, S.first_name_fr || ' ' || S.last_name_fr, C.class_name_fr, 
                        S.class_id, D.incident_date, D.incident_type, D.sanction, D.points_deducted, D.observation
                    FROM StudentDiscipline D 
                    JOIN Students S ON D.student_id = S.id
                    JOIN Classes C ON S.class_id = C.id
                    WHERE D.id = ?
                """, (incident_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            return {
                'id': row[0], 'student_name': row[1], 'class_name': row[2], 'class_id': row[3],
                'date': row[4], 'incident': row[5], 'sanction': row[6], 'points': row[7], 'observation': row[8]
            }
        except Exception:
            return None

    def is_primary_class(self, class_id):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT CY.name_fr FROM Classes CL 
                    JOIN Cycles CY ON CL.cycle_id = CY.id WHERE CL.id = ?
                """, (class_id,))
                res = cursor.fetchone()
            
            if not res: return False
            cycle_name = res[0].lower()
            return "elem" in cycle_name or "prim" in cycle_name or "ibtida" in cycle_name
        except Exception:
            return False

    def on_history_item_clicked(self, item):
        row = item.row()
        id_item = self.table_history.item(row, 0)
        if not id_item: return

        try:
            incident_id = int(id_item.text())
        except ValueError: return

        details = self.get_incident_details(incident_id)
        if not details: return

        msg = QMessageBox(self)
        msg.setWindowTitle("Action")
        msg.setText("Choisir une action / اختر العملية:")
        btn_view = msg.addButton("Voir / عرض", QMessageBox.ButtonRole.ActionRole)
        btn_edit = msg.addButton("Modifier / تعديل", QMessageBox.ButtonRole.ActionRole)
        btn_delete = msg.addButton("Supprimer / حذف", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_view:
            self.show_incident_details(details)
        elif msg.clickedButton() == btn_edit:
            self.open_edit_dialog(details)
        elif msg.clickedButton() == btn_delete:
            self.delete_incident(details['id'], details['student_name'])

    def show_incident_details(self, details):
        info = (
            f"Elève: {details['student_name']}\n"
            f"Classe: {details['class_name']}\n"
            f"Date: {details['date']}\n"
            f"Incident: {details['incident']}\n"
            f"Sanction: {details['sanction']}\n"
            f"Pts: -{details['points']}\n"
            f"Note: {details['observation']}"
        )
        QMessageBox.information(self, "Détails", info)

    def open_edit_dialog(self, details):
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier / تعديل")
        dialog.setMinimumWidth(400)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            dialog.setStyleSheet(f"background-color: {colors.BG_MAIN};")
        else:
            dialog.setStyleSheet(f"background-color: {Colors().BG_MAIN};")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Modification: {details['student_name']}"))

        grid = QGridLayout()
        
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.fromString(details['date'], "yyyy-MM-dd"))
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            date_edit.setStyleSheet(
                f"padding: 5px; border: 1px solid {colors.BORDER}; border-radius: 4px; background: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};"
            )
        else:
            colors = Colors()
            date_edit.setStyleSheet(
                f"padding: 5px; border: 1px solid {colors.BORDER}; border-radius: 4px; background: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};"
            )
        
        type_combo = self.styled_combo()
        type_combo.addItems([
            "Bavardage / ثرثرة", "Retard / تأخر", "Absence injustifiée / غياب غير مبرر", 
            "Non port de la tenue / عدم ارتداء الزي", "Insolence / وقاحة", 
            "Bagarre / شجار", "Tricherie / غش", "Dégradation de matériel / تخريب"
        ])
        type_combo.setCurrentText(details['incident'])

        sanction_input = self.styled_input("Sanction")
        sanction_input.setText(details['sanction'] or "")

        points_spin = QDoubleSpinBox()
        points_spin.setPrefix("Déduction: -")
        points_spin.setRange(0, 10 if self.is_primary_class(details['class_id']) else 20)
        points_spin.setValue(float(details['points'] or 0))
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            points_spin.setStyleSheet(
                f"padding: 5px; border: 1px solid {colors.BORDER}; border-radius: 4px; background: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};"
            )
        else:
            colors = Colors()
            points_spin.setStyleSheet(
                f"padding: 5px; border: 1px solid {colors.BORDER}; border-radius: 4px; background: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};"
            )

        obs_input = QTextEdit()
        obs_input.setMinimumHeight(60)
        obs_input.setText(details['observation'] or "")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            obs_input.setStyleSheet(
                f"padding: 5px; border: 1px solid {colors.BORDER}; border-radius: 4px; background: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};"
            )
        else:
            colors = Colors()
            obs_input.setStyleSheet(
                f"padding: 5px; border: 1px solid {colors.BORDER}; border-radius: 4px; background: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};"
            )

        grid.addWidget(QLabel("Date:"), 0, 0); grid.addWidget(date_edit, 0, 1)
        grid.addWidget(QLabel("Type:"), 1, 0); grid.addWidget(type_combo, 1, 1)
        grid.addWidget(QLabel("Sanction:"), 2, 0); grid.addWidget(sanction_input, 2, 1)
        grid.addWidget(QLabel("Points:"), 3, 0); grid.addWidget(points_spin, 3, 1)
        grid.addWidget(QLabel("Obs:"), 4, 0); grid.addWidget(obs_input, 4, 1)
        
        layout.addLayout(grid)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("Enregistrer")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_save.setStyleSheet(f"background-color: {colors.SUCCESS}; color: white; padding: 6px; border-radius: 4px; font-weight: bold;")
        else:
            colors = Colors()
            btn_save.setStyleSheet(f"background-color: {colors.SUCCESS}; color: white; padding: 6px; border-radius: 4px; font-weight: bold;")
        btn_cancel = QPushButton("Annuler")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_cancel.setStyleSheet(f"background-color: {colors.TEXT_SECONDARY}; color: white; padding: 6px; border-radius: 4px;")
        else:
            colors = Colors()
            btn_cancel.setStyleSheet(f"background-color: {colors.TEXT_SECONDARY}; color: white; padding: 6px; border-radius: 4px;")
        
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

        btn_cancel.clicked.connect(dialog.reject)
        
        def on_save():
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    conn.execute("""
                        UPDATE StudentDiscipline SET incident_date=?, incident_type=?, sanction=?, points_deducted=?, observation=?
                        WHERE id=?
                    """, (date_edit.date().toString("yyyy-MM-dd"), type_combo.currentText(), sanction_input.text(), points_spin.value(), obs_input.toPlainText(), details['id']))
                    conn.commit()
                
                self.load_history()
                self.load_recent()
                dialog.accept()
                QMessageBox.information(self, "Succès", "Modification enregistrée.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

        btn_save.clicked.connect(on_save)
        dialog.exec()

    def delete_incident(self, incident_id, student_name):
        if QMessageBox.question(self, "Confirmation", f"Supprimer l'incident de {student_name} ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute("DELETE FROM StudentDiscipline WHERE id=?", (incident_id,))
                conn.commit()
            self.load_history()
            self.load_recent()

    def print_action(self, data):
        msg = QMessageBox()
        msg.setWindowTitle("Impression / طباعة")
        msg.setText("Choisir le document à imprimer:")
        btn_convoc = msg.addButton("Convocation Parents", QMessageBox.ButtonRole.ActionRole)
        btn_sanction = msg.addButton("Notification Sanction", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        
        if msg.clickedButton() == btn_cancel:
            return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
            school_info = cursor.fetchone()
        
        pdf = DisciplinePDF(school_info)
        
        # Use QFileDialog to ask user where to save the file (Simulating "Print" action via File)
        file_name = "Convocation.pdf" if msg.clickedButton() == btn_convoc else "Sanction.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer PDF", file_name, "PDF Files (*.pdf)")
        
        if not file_path:
            return

        if msg.clickedButton() == btn_convoc:
            pdf.create_convocation(data)
        elif msg.clickedButton() == btn_sanction:
            pdf.create_sanction_notice(data)
            
        try:
            pdf.output(file_path)
            QMessageBox.information(self, "Succès", f"Fichier enregistré sous : {file_path}")
            
            # Try to open the file automatically (Windows/Linux/Mac)
            if os.name == 'nt':
                os.startfile(file_path)
            else:
                # For Linux/Mac compatibility
                import subprocess
                try:
                    subprocess.call(('xdg-open', file_path))
                except:
                    pass 
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la création du PDF : {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DisciplineWindow()
    window.show()
    sys.exit(app.exec())