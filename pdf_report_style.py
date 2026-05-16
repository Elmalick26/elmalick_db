import os
from database_setup import DatabaseManager
from repositories.staff_repo import StaffRepository

SLATE_HEADER_BG = (30, 41, 59)
SLATE_HEADER_TEXT = (248, 250, 252)
SLATE_BODY_TEXT = (51, 65, 85)
SLATE_BORDER = (203, 213, 225)
SLATE_ROW_ALT = (241, 245, 249)
SLATE_ROW_BASE = (255, 255, 255)


def apply_title_style(pdf, font_name="Arial", size=14):
    pdf.set_font(font_name, "B", size)
    pdf.set_text_color(*SLATE_HEADER_BG)


def apply_table_header_style(pdf, font_name="Arial", size=10):
    pdf.set_draw_color(*SLATE_BORDER)
    pdf.set_fill_color(*SLATE_HEADER_BG)
    pdf.set_text_color(*SLATE_HEADER_TEXT)
    pdf.set_font(font_name, "B", size)


def apply_table_body_style(pdf, font_name="Arial", size=10):
    pdf.set_text_color(*SLATE_BODY_TEXT)
    pdf.set_font(font_name, "", size)


def set_zebra_row_fill(pdf, row_index):
    fill_color = SLATE_ROW_ALT if row_index % 2 == 0 else SLATE_ROW_BASE
    pdf.set_fill_color(*fill_color)


def _sanitize_latin(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.encode('latin-1', 'ignore').decode('latin-1')


def get_school_info_row():
    try:
        with DatabaseManager() as db:
            conn = db.get_connection()
            return StaffRepository(conn).get_school_info()
    except Exception:
        return None


def apply_grades_sheet_header(pdf, school_info, title_doc, font_name="Helvetica"):
    left_x, left_y = 10, 5
    pdf.set_xy(left_x, left_y)
    pdf.set_font(font_name, '', 8)

    if school_info:
        republic = _sanitize_latin(school_info[1])
        pdf.cell(80, 3, republic, 0, 1, 'L')
        ia_text = _sanitize_latin(school_info[2])
        pdf.cell(80, 3, ia_text, 0, 1, 'L')
        ief_text = _sanitize_latin(school_info[3])
        pdf.cell(80, 3, ief_text, 0, 1, 'L')
        school_name = _sanitize_latin(school_info[4])
        pdf.cell(80, 3, school_name, 0, 1, 'L')
        auth_text = _sanitize_latin(school_info[5])
        pdf.cell(80, 3, f"Auto N: {auth_text}", 0, 1, 'L')
        addr_text = _sanitize_latin(school_info[6])
        pdf.cell(80, 3, f"Lieu: {addr_text}", 0, 1, 'L')
        phone_text = _sanitize_latin(school_info[7])
        pdf.cell(80, 3, f"Tel: {phone_text}", 0, 1, 'L')

    right_x = 175 if pdf.w <= 220 else pdf.w - 35
    logo_path = school_info[8] if school_info and len(school_info) > 8 else None
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=right_x, y=left_y, w=20, h=22)
        except Exception:
            pass

    pdf.set_xy(right_x, left_y + 22)
    pdf.set_y(pdf.get_y() + 2)
    pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
    pdf.ln(4)

    pdf.set_font(font_name, 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, _sanitize_latin(title_doc), 0, 1, 'C')
    pdf.ln(2)
