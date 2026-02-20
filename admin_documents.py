import sys
import sqlite3
import os
import shutil
from datetime import datetime
from database_setup import DatabaseManager
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QFileDialog, 
                             QTabWidget, QGridLayout, QDateEdit, QTextEdit, 
                             QFrame, QGraphicsDropShadowEffect, QLineEdit)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QPixmap
from fpdf import FPDF

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, Colors, get_tabs_style

THEME_AVAILABLE = True

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ModuleNotFoundError:
    ARABIC_SUPPORT = False

def _get_arabic_font_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "fonts", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "fonts", "NotoNaskhArabic-Regular.ttf"),
        os.path.join(base_dir, "fonts", "Cairo-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "NotoNaskhArabic-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Cairo", "Cairo-Regular.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def _contains_arabic(text):
    if text is None:
        return False
    if not isinstance(text, str):
        text = str(text)
    return any(
        "\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" or "\u08A0" <= ch <= "\u08FF"
        for ch in text
    )

def _prepare_pdf_text(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if _contains_arabic(text) and ARABIC_SUPPORT:
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
    return text

def _sanitize_latin(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def _register_arabic_font(pdf):
    font_path = _get_arabic_font_path()
    if not font_path:
        return False
    try:
        pdf.add_font("ArabicFont", "", font_path, uni=True)
        pdf.add_font("ArabicFont", "B", font_path, uni=True)
        pdf.add_font("ArabicFont", "I", font_path, uni=True)
        pdf.add_font("ArabicFont", "BI", font_path, uni=True)
        return True
    except Exception:
        return False

# --- فئة توليد PDF للوثائق ---
class DocumentPDF(FPDF):
    def __init__(self, school_info, year_label, page_format=None):
        if page_format:
              super().__init__(orientation='P', unit='mm', format=page_format)
        else:
            super().__init__()
        self.school_info = school_info
        self.year_label = year_label
        self.font_name = "Arial"
        self.arabic_font_ready = False
        if _register_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def draw_header_official(self):
        left_x, left_y = 10, 10
        self.set_xy(left_x, left_y)
        self.set_font(self.font_name, '', 8)

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
            except:
                pass



        line_y = max(self.get_y(), left_y + 26)
        self.set_y(line_y)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    # --- 1. شهادة مدرسية ---
    def generate_certificat_scolarite(self, student):
        self.add_page()
        self.draw_header_official()
        
        self.set_font(self.font_name, 'B', 24)
        self.cell(0, 20, "CERTIFICAT DE SCOLARITE", 0, 1, 'C')
        self.ln(10)
        
        self.set_font(self.font_name, '', 14)
        txt = (f"Je soussigné, Directeur de l'établissement, certifie que l'élève :\n\n"
             f"Prénom et Nom : {self.sanitize(student['name']).upper()}\n"
             f"Date de Naissance  : {student['dob']}"
             f"  à  {self.sanitize(student['birth_place'])}\n"
               f"Matricule : {student['id']}\n\n"
               f"Est régulièrement inscrit(e) dans notre établissement en classe de :"
               f"{self.sanitize(student['class']).upper()}\n\n"
               f"Pour l'année scolaire {self.year_label}.\n\n"
               f"Ce certificat est délivré pour servir et valoir ce que de droit.")
        
        self.multi_cell(0, 10, txt)
        
        self.ln(30)
        self.set_font(self.font_name, 'I', 12)
        date_str = datetime.now().strftime("%d/%m/%Y")
        city = self.sanitize(self.school_info[6].split(' ')[0]) if self.school_info and self.school_info[6] else "Ville"
        self.cell(0, 10, f"Fait à {city}, le {date_str}", 0, 1, 'R')
        self.ln(5)
        self.set_font(self.font_name, 'B', 12)
        self.cell(0, 10, "Le Directeur (Cachet et Signature)", 0, 1, 'R')

    # --- 2. بطاقة الطالب (مع الصورة) ---
    def generate_id_card(self, student):
        # Card size approx 85x55 mm (Standard ID-1)
        self.add_page()
        self.set_auto_page_break(False)
        
        # Background / Border
        self.set_line_width(0.5)
        self.rect(0, 0, 85, 55)
        
        # Header Background strip
        self.set_fill_color(30, 58, 138) # Dark Blue (Deep Slate style)
        self.rect(0, 0, 85, 12, 'F')
        
        # School Name
        self.set_xy(0, 2)
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_name, 'B', 9)
        name = self.sanitize(self.school_info[4]) if self.school_info else "ECOLE"
        self.cell(85, 5, name, 0, 1, 'C')
        
        # Title
        self.set_font(self.font_name, 'B', 6)
        self.cell(85, 5, "CARTE D'ETUDIANT", 0, 1, 'C')
        
        # Reset colors
        self.set_text_color(0, 0, 0)
        
        # Photo Area Logic
        photo_x, photo_y = 3, 14
        photo_w, photo_h = 22, 28
        self.rect(photo_x, photo_y, photo_w, photo_h)
        
        # التحقق من وجود الصورة ورسمها
        if student.get('photo') and os.path.exists(student['photo']):
            try:
                self.image(student['photo'], photo_x, photo_y, photo_w, photo_h)
            except:
                self.set_xy(photo_x, photo_y + 10)
                self.set_font(self.font_name, '', 5)
                self.cell(photo_w, 4, "Error", 0, 0, 'C')
        else:
            self.set_xy(photo_x, photo_y + 10)
            self.set_font(self.font_name, '', 5)
            self.cell(photo_w, 4, "PHOTO", 0, 0, 'C')

        # Details
        text_x = 28
        start_y = 15
        line_h = 4.5
        
        self.set_xy(text_x, start_y)
        self.set_font(self.font_name, 'B', 10)
        self.cell(55, 5, self.sanitize(student['name']).upper(), 0, 1)
        
        self.set_font(self.font_name, '', 8)
        self.set_xy(text_x, self.get_y())
        self.cell(55, line_h, f"Ne(e) le: {student['dob']}" , 0, 1)
        
        self.set_xy(text_x, self.get_y())
        self.set_font(self.font_name, '', 8)
        self.cell(55, line_h, f"à : {self.sanitize(student['birth_place'])}", 0, 1)
        
        self.set_xy(text_x, self.get_y())
        self.set_font(self.font_name, 'B', 8)
        self.cell(55, line_h, f"Classe: {self.sanitize(student['class'])}", 0, 1)
        
        self.set_xy(text_x, self.get_y())
        self.set_font(self.font_name, '', 7)
        self.cell(55, line_h, f"Matricule: {student['id']}", 0, 1)
        
        self.set_xy(text_x, self.get_y())
        self.cell(55, line_h, f"Annee: {self.year_label}", 0, 1)

        # Footer Strip (Decoration)
        self.set_fill_color(16, 185, 129) # Emerald Green
        self.rect(0, 52, 85, 3, 'F')

    # --- 3. استدعاء ولي الأمر ---
    def generate_convocation(self, student, motif, date_conv):
        self.add_page()
        self.draw_header_official()
        
        self.set_font(self.font_name, 'B', 20)
        self.cell(0, 15, "CONVOCATION", 0, 1, 'C')
        self.ln(10)
        
        self.set_font(self.font_name, '', 12)
        parent = self.sanitize(student['parent']) if student['parent'] else "Le Tuteur"
        
        txt = (f"M./Mme {parent},\n\n"
               f"Vous êtes prié(e) de bien vouloir vous présenter à la direction de l'école "
               f"le {date_conv} pour une affaire concernant votre enfant :\n\n"
               f"Nom : {self.sanitize(student['name']).upper()}\n"
               f"Classe : {self.sanitize(student['class'])}\n\n"
               f"Motif : {self.sanitize(motif)}\n\n"
               "Nous comptons sur votre présence.")
        
        self.multi_cell(0, 10, txt)
        
        self.ln(30)
        self.set_font(self.font_name, 'B', 12)
        self.cell(0, 10, "Le Directeur", 0, 1, 'R')

class AdminDocsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Générateur de Documents Administratifs / الوثائق الإدارية")
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
        
        # self.init_db() # Removed
        self.init_ui()
        self.load_classes()

    # init_db removed

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # Header Frame
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

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
                    background-color: {colors.BG_HEADER};
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
        
        icon_lbl = QLabel("🗂️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("DOCUMENTS & CARTES")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("إصدار الوثائق الرسمية والبطاقات")
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

        # Tabs
        self.tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.tabs.setStyleSheet(get_tabs_style())
        else:
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane { 
                    border: 1px solid {colors.BORDER}; 
                    background: {colors.BG_CARD}; 
                    border-radius: 12px; 
                    margin-top: 15px; 
                }
                QTabBar::tab { 
                    background: {colors.BG_MAIN}; 
                    color: {colors.TEXT_SECONDARY}; 
                    padding: 12px 30px; 
                    margin-right: 6px; 
                    border-top-left-radius: 8px; 
                    border-top-right-radius: 8px; 
                    font-weight: bold; 
                    font-family: 'Segoe UI', 'Cairo';
                }
                QTabBar::tab:selected { 
                    background: {colors.BG_HEADER}; 
                    color: {colors.HEADER_TEXT}; 
                }
                QTabBar::tab:hover {
                    background: {colors.BORDER}; 
                }
            """)
        
        self.setup_cert_tab()
        self.setup_card_tab()
        self.setup_convoc_tab()
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
            colors = Colors()
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
        combo.setMinimumHeight(40)
        return combo

    def styled_date(self):
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            date_edit.setStyleSheet(f"""
                QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            date_edit.setStyleSheet(f"""
                QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        date_edit.setMinimumHeight(40)
        return date_edit

    def styled_text_edit(self, placeholder=""):
        text_edit = QTextEdit()
        if placeholder:
            text_edit.setPlaceholderText(placeholder)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            text_edit.setStyleSheet(f"""
                QTextEdit {{ padding: 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            text_edit.setStyleSheet(f"""
                QTextEdit {{ padding: 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
                QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        return text_edit

    def setup_cert_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        grp_card = self.create_card()
        glay = QGridLayout(grp_card)
        glay.setContentsMargins(20, 20, 20, 20)
        glay.setSpacing(15)
        
        # Title inside card
        card_title = QLabel("Certificat de Scolarité / شهادة مدرسية")
        if THEME_AVAILABLE:
            card_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")
        else:
            card_title.setStyleSheet(f"font-weight: bold; color: {Colors().TEXT_PRIMARY}; font-size: 14px;")
        glay.addWidget(card_title, 0, 0, 1, 2)
        
        self.combo_class_cert = self.styled_combo()
        self.combo_class_cert.currentIndexChanged.connect(lambda: self.load_students(self.combo_class_cert, self.combo_student_cert))
        
        self.combo_student_cert = self.styled_combo()
        
        btn_print = QPushButton("🖨️ Imprimer Certificat (PDF)")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_print.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    padding: 10px; 
                    border-radius: 8px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_print.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    padding: 10px; 
                    border-radius: 8px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_print.clicked.connect(self.print_certificate)

        glay.addWidget(QLabel("1. Classe:"), 1, 0)
        glay.addWidget(self.combo_class_cert, 1, 1)
        glay.addWidget(QLabel("2. Élève:"), 2, 0)
        glay.addWidget(self.combo_student_cert, 2, 1)
        glay.addWidget(btn_print, 3, 1)
        
        layout.addWidget(grp_card)
        layout.addStretch()
        self.tabs.addTab(tab, "  📜 Certificats  ")

    def setup_card_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        grp_card = self.create_card()
        glay = QGridLayout(grp_card)
        glay.setContentsMargins(20, 20, 20, 20)
        glay.setSpacing(15)
        
        card_title = QLabel("Carte d'Étudiant / بطاقة الطالب")
        if THEME_AVAILABLE:
            card_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")
        else:
            card_title.setStyleSheet(f"font-weight: bold; color: {Colors().TEXT_PRIMARY}; font-size: 14px;")
        glay.addWidget(card_title, 0, 0, 1, 2)
        
        self.combo_class_card = self.styled_combo()
        self.combo_class_card.currentIndexChanged.connect(lambda: self.load_students(self.combo_class_card, self.combo_student_card))
        
        self.combo_student_card = self.styled_combo()
        self.combo_student_card.currentIndexChanged.connect(self.check_photo_status)
        
        # Photo Management
        photo_layout = QHBoxLayout()
        self.btn_upload_photo = QPushButton("📷 Ajouter Photo")
        self.btn_upload_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.btn_upload_photo.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_SECONDARY}; border-radius: 6px; padding: 8px; border: 1px solid {colors.BORDER}; font-weight: bold; }}
                QPushButton:hover {{ background-color: {colors.BG_MAIN}; }}
            """)
        else:
            colors = Colors()
            self.btn_upload_photo.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY}; border-radius: 6px; padding: 8px; border: 1px solid {colors.BORDER}; font-weight: bold; }}
                QPushButton:hover {{ background-color: {colors.BG_MAIN}; }}
            """)
        self.btn_upload_photo.clicked.connect(self.upload_student_photo)
        
        self.lbl_photo_status = QLabel("...")
        if THEME_AVAILABLE:
            self.lbl_photo_status.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; font-size: 11px; margin-left: 10px;")
        else:
            self.lbl_photo_status.setStyleSheet(f"color: {Colors().TEXT_SECONDARY}; font-size: 11px; margin-left: 10px;")
        
        photo_layout.addWidget(self.btn_upload_photo)
        photo_layout.addWidget(self.lbl_photo_status)
        photo_layout.addStretch()
        
        btn_print_one = QPushButton("Imprimer Carte (Seul)")
        btn_print_one.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_one.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_print_one.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_print_one.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_print_one.clicked.connect(lambda: self.print_card(mode='single'))
        
        btn_print_all = QPushButton("Imprimer Toute la Classe")
        btn_print_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_all.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_print_all.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_print_all.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_print_all.clicked.connect(lambda: self.print_card(mode='batch'))

        glay.addWidget(QLabel("1. Classe:"), 1, 0)
        glay.addWidget(self.combo_class_card, 1, 1)
        glay.addWidget(QLabel("2. Élève:"), 2, 0)
        glay.addWidget(self.combo_student_card, 2, 1)
        glay.addLayout(photo_layout, 3, 1)
        glay.addWidget(btn_print_one, 4, 0)
        glay.addWidget(btn_print_all, 4, 1)
        
        layout.addWidget(grp_card)
        layout.addStretch()
        self.tabs.addTab(tab, "  💳 Cartes  ")

    def setup_convoc_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        grp_card = self.create_card()
        glay = QGridLayout(grp_card)
        glay.setContentsMargins(20, 20, 20, 20)
        glay.setSpacing(15)
        
        card_title = QLabel("Convocation des Parents / استدعاء ولي الأمر")
        if THEME_AVAILABLE:
            card_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().DANGER}; font-size: 14px;")
        else:
            card_title.setStyleSheet(f"font-weight: bold; color: {Colors().DANGER}; font-size: 14px;")
        glay.addWidget(card_title, 0, 0, 1, 2)
        
        self.combo_class_conv = self.styled_combo()
        self.combo_class_conv.currentIndexChanged.connect(lambda: self.load_students(self.combo_class_conv, self.combo_student_conv))
        
        self.combo_student_conv = self.styled_combo()
        
        self.date_conv = self.styled_date()
        self.date_conv.setDate(QDate.currentDate().addDays(1))
        
        self.txt_motif = self.styled_text_edit("Motif de la convocation (ex: Absence prolongée, Comportement...)")
        self.txt_motif.setMaximumHeight(80)
        
        btn_print = QPushButton("Générer Convocation")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_print.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_print.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; border-radius: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
        btn_print.clicked.connect(self.print_convocation)

        glay.addWidget(QLabel("1. Classe:"), 1, 0)
        glay.addWidget(self.combo_class_conv, 1, 1)
        glay.addWidget(QLabel("2. Élève:"), 2, 0)
        glay.addWidget(self.combo_student_conv, 2, 1)
        glay.addWidget(QLabel("3. Date RDV:"), 3, 0)
        glay.addWidget(self.date_conv, 3, 1)
        glay.addWidget(QLabel("4. Motif:"), 4, 0)
        glay.addWidget(self.txt_motif, 4, 1)
        glay.addWidget(btn_print, 5, 1)
        
        layout.addWidget(grp_card)
        layout.addStretch()
        self.tabs.addTab(tab, "  ⚠️ Convocations  ")

    # --- Logic ---
    def load_classes(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, class_name_fr FROM Classes")
            classes = cursor.fetchall()
        
        combos = [self.combo_class_cert, self.combo_class_card, self.combo_class_conv]
        for combo in combos:
            combo.clear()
            combo.addItem("-", None)
            for c in classes:
                combo.addItem(c[1], c[0])

    def load_students(self, class_combo, student_combo):
        class_id = class_combo.currentData()
        student_combo.clear()
        if not class_id: return
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, first_name_fr || ' ' || last_name_fr FROM Students WHERE class_id=? AND status='Active'", (class_id,))
            for s in cursor.fetchall():
                student_combo.addItem(s[1], s[0])

    def check_photo_status(self):
        sid = self.combo_student_card.currentData()
        if not sid:
            self.lbl_photo_status.setText("...")
            return
            
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT photo_path FROM Students WHERE id=?", (sid,))
                res = cursor.fetchone()
                if res and res[0] and os.path.exists(res[0]):
                    self.lbl_photo_status.setText("✅ Photo disponible")
                    colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                    self.lbl_photo_status.setStyleSheet(f"color: {colors.SUCCESS}; font-weight: bold; margin-left: 10px;")
                else:
                    self.lbl_photo_status.setText("❌ Pas de photo")
                    colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                    self.lbl_photo_status.setStyleSheet(f"color: {colors.DANGER}; font-weight: bold; margin-left: 10px;")
        except:
            self.lbl_photo_status.setText("❌ Erreur DB")

    def upload_student_photo(self):
        sid = self.combo_student_card.currentData()
        if not sid:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un élève d'abord.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Photo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            save_dir = "school_data/photos" # Use consistent path
            if not os.path.exists(save_dir): os.makedirs(save_dir)
            ext = os.path.splitext(file_path)[1]
            new_path = os.path.join(save_dir, f"std_{sid}{ext}")
            
            try:
                shutil.copy(file_path, new_path)
                
                db = DatabaseManager()
                with db.get_connection() as conn:
                    conn.execute("UPDATE Students SET photo_path=? WHERE id=?", (new_path, sid))
                    conn.commit()
                self.check_photo_status() # Update label
                QMessageBox.information(self, "Succès", "Photo enregistrée avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def get_common_data(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
            info = cursor.fetchone()
            cursor.execute("SELECT year_label FROM AcademicYears WHERE is_active=1")
            yr = cursor.fetchone()
        year = yr[0] if yr else "202X"
        return info, year

    def get_student_data(self, sid):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr, S.birth_date, S.birth_place, C.class_name_fr, S.parent_name, S.photo_path
                FROM Students S JOIN Classes C ON S.class_id = C.id
                WHERE S.id=?
            """, (sid,))
            res = cursor.fetchone()
        
        if res:
            return {
                'id': res[0], 'name': res[1], 'dob': res[2],
                'birth_place': res[3], 'class': res[4], 'parent': res[5], 'photo': res[6]
            }
        return None

    def print_certificate(self):
        sid = self.combo_student_cert.currentData()
        if not sid: return
        
        info, year = self.get_common_data()
        std = self.get_student_data(sid)
        
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"Certificat_{sid}.pdf", "PDF (*.pdf)")
        if path:
            pdf = DocumentPDF(info, year)
            pdf.generate_certificat_scolarite(std)
            pdf.output(path)
            QMessageBox.information(self, "Succès", "Certificat généré.")

    def print_convocation(self):
        sid = self.combo_student_conv.currentData()
        motif = self.txt_motif.toPlainText()
        date = self.date_conv.date().toString("dd/MM/yyyy")
        if not sid or not motif: return
        
        info, year = self.get_common_data()
        std = self.get_student_data(sid)
        
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"Convocation_{sid}.pdf", "PDF (*.pdf)")
        if path:
            pdf = DocumentPDF(info, year)
            pdf.generate_convocation(std, motif, date)
            pdf.output(path)
            QMessageBox.information(self, "Succès", "Convocation générée.")

    def print_card(self, mode='single'):
        info, year = self.get_common_data()
        
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "Cartes_Etudiant.pdf", "PDF (*.pdf)")
        if not path: return

        pdf = DocumentPDF(info, year, page_format=(85, 55))
        
        if mode == 'single':
            sid = self.combo_student_card.currentData()
            if not sid: return
            std = self.get_student_data(sid)
            pdf.generate_id_card(std)
        else:
            cid = self.combo_class_card.currentData()
            if not cid: return
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM Students WHERE class_id=? AND status='Active'", (cid,))
                ids = [r[0] for r in cursor.fetchall()]
            
            for sid in ids:
                std = self.get_student_data(sid)
                pdf.generate_id_card(std)
        
        pdf.output(path)
        QMessageBox.information(self, "Succès", "Carte(s) générée(s).")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminDocsWindow()
    window.show()
    sys.exit(app.exec())