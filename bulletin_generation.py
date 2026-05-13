import sys
import os
from datetime import datetime
from database_setup import DatabaseManager
from app_logger import AppLogger
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QComboBox, QMessageBox, 
                             QHeaderView, QFrame, QGroupBox, QFileDialog, 
                             QTabWidget, QGridLayout, QSpinBox, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, Colors, get_table_style, get_tabs_style
from print_export_service import output_pdf, get_report_output_mode

THEME_AVAILABLE = True
BULLETIN_SUMMARY_OUTPUT_MODE = get_report_output_mode("bulletin_summary_mode", "save")

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

# --- 1. محرك الحسابات المنطقي (Back-End Logic) ---
class GradeCalculator:
    def __init__(self):
        pass

    def get_class_context(self, class_id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT CY.name_fr 
                FROM Classes CL 
                JOIN Cycles CY ON CL.cycle_id = CY.id 
                WHERE CL.id = %s
            """, (class_id,))
            res = cursor.fetchone()
        
        cycle_name = res[0].lower() if res else ""
        is_primary = "elem" in cycle_name or "prim" in cycle_name or "ibtida" in cycle_name
        max_score = 10.0 if is_primary else 20.0
        return is_primary, max_score

    def calculate_rank(self, students_list, key_name='average'):
        students_list.sort(key=lambda x: x[key_name], reverse=True)
        for i, std in enumerate(students_list):
            std['rank'] = i + 1
        return students_list

    def get_class_subjects(self, cursor, class_id):
        """إرجاع المواد الفعلية للفصل: من جدول الحصص أولاً، ثم مواد المرحلة."""
        cursor.execute("""
            SELECT DISTINCT S.id, S.subject_name_fr, S.subject_name_ar, S.coefficient
            FROM Timetable T
            JOIN Subjects S ON T.subject_id = S.id
            WHERE T.class_id = %s
            ORDER BY S.id
        """, (class_id,))
        subjects = cursor.fetchall()
        if subjects:
            return subjects

        cursor.execute("SELECT cycle_id FROM Classes WHERE id=%s", (class_id,))
        res = cursor.fetchone()
        if not res:
            return []
        cycle_id = res[0]
        cursor.execute("SELECT id, subject_name_fr, subject_name_ar, coefficient FROM Subjects WHERE cycle_id=%s ORDER BY id", (cycle_id,))
        return cursor.fetchall()

    def _get_period_year_id(self, cursor, period_id):
        cursor.execute("SELECT year_id FROM AcademicPeriods WHERE id=%s", (period_id,))
        res = cursor.fetchone()
        return res[0] if res else None

    def _get_grade_score(self, cursor, student_id, subject_id, assessment_id, year_id):
        if year_id:
            cursor.execute("""
                SELECT score
                FROM Grades
                WHERE student_id=%s AND subject_id=%s AND assessment_id=%s
                AND (year_id=%s OR year_id IS NULL)
                ORDER BY CASE WHEN year_id=%s THEN 0 ELSE 1 END, id DESC
                LIMIT 1
            """, (student_id, subject_id, assessment_id, year_id, year_id))
        else:
            cursor.execute(
                "SELECT score FROM Grades WHERE student_id=%s AND subject_id=%s AND assessment_id=%s ORDER BY id DESC LIMIT 1",
                (student_id, subject_id, assessment_id)
            )
        res = cursor.fetchone()
        return res[0] if res else 0

    def _get_table_columns(self, cursor, table_name):
        """Read table columns in PostgreSQL using information_schema."""
        try:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND lower(table_name) = lower(%s)
                """,
                (table_name,)
            )
            return {row[0] for row in cursor.fetchall()}
        except Exception:
            return set()

    def _get_attendance_count(self, cursor, student_id, status, year_id, period_id=None):
        attendance_cols = self._get_table_columns(cursor, "StudentAttendance")
        has_period_col = "period_id" in attendance_cols

        if period_id and has_period_col:
            cursor.execute(
                "SELECT COUNT(*) FROM StudentAttendance WHERE student_id=%s AND status=%s AND period_id=%s",
                (student_id, status, period_id)
            )
            return int(cursor.fetchone()[0] or 0)

        if year_id:
            cursor.execute(
                "SELECT COUNT(*) FROM StudentAttendance WHERE student_id=%s AND status=%s AND year_id=%s",
                (student_id, status, year_id)
            )
            return int(cursor.fetchone()[0] or 0)

        cursor.execute(
            "SELECT COUNT(*) FROM StudentAttendance WHERE student_id=%s AND status=%s",
            (student_id, status)
        )
        return int(cursor.fetchone()[0] or 0)

    def _get_discipline_data(self, cursor, student_id, year_id, is_primary, period_id=None):
        discipline_cols = self._get_table_columns(cursor, "StudentDiscipline")
        points_col = "points_deducted" if "points_deducted" in discipline_cols else "0"
        sanction_col = "sanction" if "sanction" in discipline_cols else ("action_taken" if "action_taken" in discipline_cols else "''")
        observation_col = "observation" if "observation" in discipline_cols else ("description" if "description" in discipline_cols else "''")
        has_period_col = "period_id" in discipline_cols

        if period_id and has_period_col:
            cursor.execute(f"""
                SELECT COALESCE(SUM({points_col}), 0)
                FROM StudentDiscipline
                WHERE student_id=%s AND period_id=%s
            """, (student_id, period_id))
            total_deducted = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT incident_type, {sanction_col}, {points_col}, {observation_col}
                FROM StudentDiscipline
                WHERE student_id=%s AND period_id=%s
                ORDER BY incident_date DESC
                LIMIT 5
            """, (student_id, period_id))
            discipline_records = cursor.fetchall()

            base_conduct_score = 10.0 if is_primary else 20.0
            conduct_score = max(0, base_conduct_score - total_deducted)

            return {
                'conduct_score': conduct_score,
                'base_score': base_conduct_score,
                'total_deducted': total_deducted,
                'records': discipline_records,
                'appreciation': self.get_conduct_appreciation(conduct_score, base_conduct_score)
            }

        if year_id:
            cursor.execute("SELECT COUNT(*) FROM StudentDiscipline WHERE student_id=%s AND year_id=%s", (student_id, year_id))
            has_year_data = cursor.fetchone()[0] > 0
        else:
            has_year_data = False

        if has_year_data:
            cursor.execute(f"""
                SELECT COALESCE(SUM({points_col}), 0)
                FROM StudentDiscipline
                WHERE student_id=%s AND year_id=%s
            """, (student_id, year_id))
            total_deducted = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT incident_type, {sanction_col}, {points_col}, {observation_col}
                FROM StudentDiscipline
                WHERE student_id=%s AND year_id=%s
                ORDER BY incident_date DESC
                LIMIT 5
            """, (student_id, year_id))
            discipline_records = cursor.fetchall()
        else:
            cursor.execute(f"""
                SELECT COALESCE(SUM({points_col}), 0)
                FROM StudentDiscipline
                WHERE student_id=%s
            """, (student_id,))
            total_deducted = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT incident_type, {sanction_col}, {points_col}, {observation_col}
                FROM StudentDiscipline
                WHERE student_id=%s
                ORDER BY incident_date DESC
                LIMIT 5
            """, (student_id,))
            discipline_records = cursor.fetchall()

        base_conduct_score = 10.0 if is_primary else 20.0
        conduct_score = max(0, base_conduct_score - total_deducted)

        return {
            'conduct_score': conduct_score,
            'base_score': base_conduct_score,
            'total_deducted': total_deducted,
            'records': discipline_records,
            'appreciation': self.get_conduct_appreciation(conduct_score, base_conduct_score)
        }

    # ===== تعديل مهم: جلب الطلاب من جدول التسجيل (SCN) بناءً على سنة الفترة الدراسية =====
    def get_student_averages(self, class_id, period_id, include_conduct=False):
        db = DatabaseManager()
        is_primary, max_score = self.get_class_context(class_id)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            year_id = self._get_period_year_id(cursor, period_id)

            cursor.execute("""
                SELECT S.id, S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar, COALESCE(SCN.class_number, 0)
                FROM Students S
                JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
                WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
                ORDER BY COALESCE(SCN.class_number, 9999), S.last_name_fr, S.first_name_fr
            """, (class_id, year_id))
            students = cursor.fetchall()
            
            subjects = self.get_class_subjects(cursor, class_id)
            if not subjects:
                return []

            cursor.execute("SELECT id, name_fr, type_code, weight_percentage FROM AssessmentTypes WHERE period_id=%s", (period_id,))
            assessments = cursor.fetchall()

            class_results = []

            for std in students:
                std_id, fname, lname, fname_ar, lname_ar, class_number = std
                student_data = {
                    'id': std_id,
                    'class_number': class_number if class_number else None,
                    'name': f"{fname} {lname}",
                    'name_ar': f"{fname_ar} {lname_ar}" if fname_ar or lname_ar else "",
                    'subjects': [],
                    'total_points': 0,
                    'total_coef': 0,
                    'general_average': 0,
                    'is_primary': is_primary,
                    'max_score': max_score
                }

                for sub in subjects:
                    sub_id, sub_name_fr, sub_name_ar, sub_coef = sub
                    
                    sum_devoirs = 0
                    count_devoirs = 0
                    exam_score = 0
                    has_exam = False
                    
                    weighted_sum_prim = 0
                    total_weight_prim = 0

                    for assess in assessments:
                        assess_id, assess_name, assess_code, assess_w = assess
                        score = self._get_grade_score(cursor, std_id, sub_id, assess_id, year_id)
                        
                        if not is_primary:
                            if 'DEV' in str(assess_code).upper() or 'DEVOIR' in str(assess_name).upper():
                                sum_devoirs += score
                                count_devoirs += 1
                            else:
                                exam_score = score
                                has_exam = True
                        else:
                            weighted_sum_prim += score * assess_w
                            total_weight_prim += assess_w

                    moy_subject = 0
                    if not is_primary:
                        moy_devoirs = (sum_devoirs / count_devoirs) if count_devoirs > 0 else 0
                    if count_devoirs > 0 and has_exam:
                        moy_subject = (moy_devoirs + (exam_score * 2)) / 3
                    elif has_exam:
                        moy_subject = exam_score
                    elif count_devoirs > 0:
                        moy_subject = moy_devoirs
                    else:
                        moy_subject = (weighted_sum_prim / total_weight_prim) if total_weight_prim > 0 else 0

                    points = moy_subject * sub_coef
                    
                    subject_label = f"{sub_name_fr} / {sub_name_ar}" if sub_name_ar else sub_name_fr

                    student_data['subjects'].append({
                        'name': subject_label,
                        'name_fr': sub_name_fr,
                        'name_ar': sub_name_ar,
                        'coef': sub_coef,
                        'moy_devoir': (sum_devoirs / count_devoirs) if count_devoirs > 0 and not is_primary else None,
                        'note_compo': exam_score if has_exam and not is_primary else moy_subject,
                        'avg': moy_subject,
                        'points': points,
                        'appreciation': self.get_appreciation(moy_subject, max_score)
                    })
                    
                    student_data['total_points'] += points
                    student_data['total_coef'] += sub_coef

                if include_conduct:
                    discipline_data = self._get_discipline_data(cursor, std_id, year_id, is_primary, period_id)
                    discipline_coef = 1
                    discipline_points = (discipline_data['conduct_score'] / discipline_data['base_score']) * max_score * discipline_coef
                    student_data['discipline'] = discipline_data
                    student_data['total_points'] += discipline_points
                    student_data['total_coef'] += discipline_coef

                if student_data['total_coef'] > 0:
                    student_data['general_average'] = student_data['total_points'] / student_data['total_coef']
                
                class_results.append(student_data)

        return self.calculate_rank(class_results, 'general_average')

    def get_student_bulletin_data(self, student_id, class_id, period_id):
        all_results = self.get_student_averages(class_id, period_id, include_conduct=True)
        target_student = next((s for s in all_results if s['id'] == student_id), None)
        
        if not target_student: return None

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT first_name_fr, last_name_fr, first_name_ar, last_name_ar, birth_date, birth_place, parent_name FROM Students WHERE id=%s", (student_id,))
            target_student['info'] = cursor.fetchone()
            
            year_id = self._get_period_year_id(cursor, period_id)

            cursor.execute(
                "SELECT COUNT(*) FROM StudentClassNumbers WHERE class_id=%s AND year_id=%s",
                (class_id, year_id)
            )
            class_size = int(cursor.fetchone()[0] or 0)
            
            abs_cnt = self._get_attendance_count(cursor, student_id, 'Absent', year_id, period_id)
            ret_cnt = self._get_attendance_count(cursor, student_id, 'Retard', year_id, period_id)
            target_student['attendance'] = {'abs': abs_cnt, 'ret': ret_cnt}
            
            if 'discipline' not in target_student:
                target_student['discipline'] = self._get_discipline_data(
                    cursor, student_id, year_id, target_student['is_primary'], period_id
                )
            
            target_student['mention'] = self.get_mention(target_student['general_average'], target_student['max_score'])
            target_student['observation'] = self.get_observation(target_student['general_average'], target_student['max_score'])

            # Annual Logic
            cursor.execute("SELECT year_id, cycle_id FROM AcademicPeriods WHERE id=%s", (period_id,))
            meta = cursor.fetchone()
            target_student['annual'] = None
            
            if meta:
                y_id, c_id = meta
                cursor.execute("SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods WHERE year_id=%s AND cycle_id=%s ORDER BY sort_order", (y_id, c_id))
                all_periods = cursor.fetchall()
                
                if all_periods and all_periods[-1][0] == period_id:
                    annual_avgs = []
                    
                    period_results_cache = {}
                    for pid, _, _ in all_periods:
                        period_results_cache[pid] = self.get_student_averages(class_id, pid)

                    # ===== تعديل مهم: جلب الطلاب من جدول التسجيل SCN =====
                    cursor.execute("""
                        SELECT S.id 
                        FROM Students S
                        JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
                        WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
                    """, (class_id, y_id))
                    all_ids = [r[0] for r in cursor.fetchall()]
                    
                    class_annual_avgs = {}
                    for sid in all_ids:
                        s_sum = 0
                        s_cnt = 0
                        for pid, _, _ in all_periods:
                            p_res = next((x for x in period_results_cache[pid] if x['id'] == sid), None)
                            if p_res:
                                s_sum += p_res['general_average']
                                s_cnt += 1
                        class_annual_avgs[sid] = s_sum / s_cnt if s_cnt > 0 else 0.0

                    ann_avg = class_annual_avgs.get(student_id, 0.0)
                    
                    for pid, pname_fr, pname_ar in all_periods:
                        p_res = next((x for x in period_results_cache[pid] if x['id'] == student_id), None)
                        val = p_res['general_average'] if p_res else 0.0
                        period_label = f"{pname_fr} / {pname_ar}" if pname_ar else pname_fr
                        annual_avgs.append((period_label, val))

                    sorted_students = sorted(class_annual_avgs.items(), key=lambda x: x[1], reverse=True)
                    annual_rank = next((i + 1 for i, (sid, _) in enumerate(sorted_students) if sid == student_id), 1)
                    
                    verdict = "Admis" if ann_avg >= (target_student['max_score']/2) else "Redouble"
                    
                    target_student['annual'] = {
                        'periods': annual_avgs,
                        'annual_average': ann_avg,
                        'annual_rank': annual_rank,
                        'class_size': class_size,
                        'annual_mention': self.get_mention(ann_avg, target_student['max_score']),
                        'verdict': verdict
                    }

        required_points = target_student['total_coef'] * target_student['max_score']
        target_student['stats'] = {
            'total_points': target_student['total_points'],
            'required_points': required_points,
            'total_coef': target_student['total_coef'],
            'average': target_student['general_average'],
            'rank': target_student['rank'], 
            'class_size': class_size,
            'mention': target_student['mention'],
            'observation': target_student['observation']
        }
        
        target_student['transcript'] = []
        for sub in target_student['subjects']:
            target_student['transcript'].append({
                'subject': sub['name'],
                'coef': sub['coef'],
                'points': sub['points'],
                'appreciation': sub['appreciation'],
                'moy_devoir': sub['moy_devoir'],
                'note_compo': sub['note_compo'],
                'avg': sub['avg']
            })

        return target_student

    def get_appreciation(self, note, max_s=20):
        ratio = 20 / max_s
        n = note * ratio
        if n < 10: return "Faible / ضعيف"
        if n < 12: return "Passable / مقبول"
        if n < 14: return "A. Bien / حسن"
        if n < 16: return "Bien / جيد"
        return "T. Bien / جيد جداً"

    def get_mention(self, avg, max_s=20):
        ratio = 20 / max_s
        n = avg * ratio
        if n < 10: return "Insuffisant / غير مقبول"
        if n < 12: return "Passable / ضعيف"
        if n < 14: return "Assez Bien / مقبول"
        if n < 16: return "Bien / جيد"
        if n < 18: return "Très Bien / جيد جداً"
        return "Excellent / ممتاز"
    
    def get_decision(self, avg, is_primary, max_s=20):
        threshold = 5.0 if is_primary else 10.0
        return "Admis" if avg >= threshold else "Ajourné"

    def get_observation(self, avg, max_s=20):
        ratio = 20 / max_s
        n = avg * ratio
        if n < 10: return "Des efforts sont nécessaires. Doit redoubler. / يجب بذل جهود أكبر والإعادة."
        if n < 12: return "Travail moyen. Doit persévérer. / عمل متوسط ويجب المواصلة."
        if n < 14: return "Bon travail. Continuez ainsi. / عمل جيد استمر هكذا."
        if n < 16: return "Très bon travail. Félicitations. / عمل ممتاز ومستحق التهاني."
        return "Excellent travail. Tableau d'Honneur. Félicitations. / عمل متميز جداً وجدير بلوحة الشرف."
    
    def get_conduct_appreciation(self, score, max_s=20):
        ratio = 20 / max_s
        n = score * ratio
        if n >= 18: return "Excellent / ممتاز"
        if n >= 16: return "Très Bien / جيد جداً"
        if n >= 14: return "Bien / جيد"
        if n >= 12: return "Assez Bien / مقبول"
        if n >= 10: return "Passable / ضعيف"
        return "Insuffisant / غير مقبول"

# --- 2. شهادة التفوق (Certificate PDF) ---
class CertificatePDF(FPDF):
    def __init__(self, school_info, year_label):
        super().__init__(orientation='L')
        self.school_info = school_info
        self.year_label = year_label
        self.font_name = "Arial"
        self.arabic_font_ready = False
        if _register_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True
        self.printed_at = datetime.now().strftime('%d/%m/%Y %H:%M')

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def _draw_official_header(self):
        left_x, left_y = 14, 14
        self.set_xy(left_x, left_y)
        self.set_font(self.font_name, '', 8)

        if self.school_info:
            republic = self.sanitize(self.school_info[1])
            self.cell(90, 3, f"{republic}", 0, 1, 'L')
            ia_text = self.sanitize(self.school_info[2])
            self.cell(90, 3, f"    {ia_text}", 0, 1, 'L')
            ief_text = self.sanitize(self.school_info[3])
            self.cell(90, 3, f"    {ief_text}", 0, 1, 'L')
            school_name = self.sanitize(self.school_info[4])
            self.cell(90, 3, f"    {school_name}", 0, 1, 'L')
            auth_text = self.sanitize(self.school_info[5])
            self.cell(90, 3, f"    Auto N: {auth_text}", 0, 1, 'L')
            addr_text = self.sanitize(self.school_info[6])
            self.cell(90, 3, f"    Lieu: {addr_text}", 0, 1, 'L')
            phone_text = self.sanitize(self.school_info[7])
            self.cell(90, 3, f"    Tel: {phone_text}", 0, 1, 'L')

        right_x = 262
        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=18, h=20)
            except Exception:
                pass

        self.set_draw_color(0, 0, 0)
        self.set_xy(right_x, left_y + 22)
        self.set_y(self.get_y() + 2)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(5)


    def footer(self):
        self.set_y(-10)
        self.set_font(self.font_name, 'I', 9)
        self.cell(0, 6, self.sanitize(f"Date d'impression: {self.printed_at}"), 0, 0, 'C')

    def create_certificate(self, student_name, class_name, avg, rank, mention, period_name=""):
        self.add_page()
        self.set_line_width(2)
        self.set_draw_color(0, 0, 0)
        self.rect(10, 10, 277, 190)
        self.set_line_width(0.5)
        self.set_draw_color(0, 0, 0)

        self._draw_official_header()
        
        self.set_font(self.font_name, 'B', 40)
        self.set_text_color(25, 25, 112)
        self.cell(0, 20, self.sanitize("TABLEAU D'HONNEUR / لوحة الشرف"), 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(10)
        
        self.set_font(self.font_name, '', 18)
        self.cell(0, 15, self.sanitize("Decerne a l'eleve / يمنح للتلميذ:"), 0, 1, 'C')
        
        self.set_font(self.font_name, 'BI', 28)
        self.cell(0, 20, self.sanitize(student_name), 0, 1, 'C')
        
        self.set_font(self.font_name, '', 16)
        self.cell(0, 15, self.sanitize(f"De la classe de / القسم: {class_name}"), 0, 1, 'C')
        period_text = period_name.strip() if isinstance(period_name, str) else ""
        period_fr = period_text
        period_ar = period_text
        if "/" in period_text:
            parts = [p.strip() for p in period_text.split("/") if p.strip()]
            if len(parts) >= 2:
                period_fr = parts[0]
                period_ar = " / ".join(parts[1:])
        line_fr = f"Pour ses excellents resultats scolaires en {period_fr} de l'annee scolaire {self.year_label}." if period_fr else f"Pour ses excellents resultats scolaires de l'annee scolaire {self.year_label}."
        line_ar = f"لتفوقه الدراسي في {period_ar} في السنة الدراسية {self.year_label}." if period_ar else f"لتفوقه الدراسي في السنة الدراسية {self.year_label}."

        self.set_font(self.font_name, '', 13)
        self.cell(260, 8, self.sanitize(line_fr), 0, 1, 'C')
        self.cell(260, 8, self.sanitize(line_ar), 0, 1, 'C')
        
        self.ln(5)
        self.set_font(self.font_name, 'B', 14)
        stats_txt = f"Moyenne: {avg:.2f}   |   Rang: {rank}   |   Mention: {mention}"
        self.cell(0, 15, self.sanitize(stats_txt), 1, 1, 'C')
        
        self.ln(5)
        self.set_font(self.font_name, 'I', 12)
        self.cell(90, 10, "", 0, 0, 'C')
        self.cell(90, 10, "", 0, 0, 'C')
        self.cell(90, 10, "Le Directeur", 0, 1, 'C')

# --- 3. كلاس PDF للكشف (Bulletin) ---
class BulletinPDF(FPDF):
    def __init__(self, school_info, period_name, year_label):
        super().__init__()
        self.school_info = school_info
        self.period_name = period_name
        self.year_label = year_label
        self.font_name = "Helvetica"
        self.arabic_font_ready = False
        if _register_arabic_font(self):
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def header(self):
        left_x, left_y = 10, 5
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
            except Exception: pass
        self.set_xy(right_x, left_y + 22)
        self.set_y(self.get_y() + 2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, 'I', 6)
        date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        self.cell(0, 3, f"Imprime le {date_str}", 0, 1, 'C')
        self.cell(0, 3, f'Page {self.page_no()}', 0, 0, 'R')

    def draw_bulletin(self, data, class_name):
        self.add_page()
        self.set_font(self.font_name, 'B', 11)
        self.set_fill_color(230, 230, 230)
        period_fr = self.period_name
        period_ar = ""
        if isinstance(self.period_name, str) and "/" in self.period_name:
            parts = [p.strip() for p in self.period_name.split("/") if p.strip()]
            if len(parts) >= 2:
                period_fr, period_ar = parts[0], " / ".join(parts[1:])
        title_fr = f"BULLETIN DE NOTES - {str(period_fr).upper()} ({self.year_label})" if period_fr else f"BULLETIN DE NOTES ({self.year_label})"
        title_ar = f"كشف النقاط - {str(period_ar).strip()}" if period_ar else f"كشف النقاط ({self.year_label})"
        self.cell(120, 7, self.sanitize(title_fr), 0, 0, 'R', True)
        self.cell(70, 7, self.sanitize(title_ar), 0, 1, 'L', True)
        self.ln(2)
        
        self.set_font(self.font_name, '', 9)
        full_name = f"{data['info'][0]} {data['info'][1]}".upper()
        full_name_ar = f"{data['info'][2]} {data['info'][3]}".strip()

        class_name_fr = class_name
        class_name_ar = ""
        if isinstance(class_name, str) and "/" in class_name:
            parts = [p.strip() for p in class_name.split("/") if p.strip()]
            if len(parts) >= 2:
                class_name_fr, class_name_ar = parts[0], " / ".join(parts[1:])

        self.set_fill_color(240, 240, 240)
        birth_date = data['info'][4] if data['info'][4] else "N/A"
        birth_place = data['info'][5] if data['info'][5] else "-"
        class_number = data.get('class_number')
        class_number_txt = str(class_number) if class_number is not None else "-"

        self.cell(47, 6, self.sanitize(f"ELEVE: {full_name}"), 0, 0, 'L', True)
        self.cell(46, 6, self.sanitize(f"الطالب: {full_name_ar}" if full_name_ar else "الطالب:"), 0, 0, 'R', True)
        self.cell(3, 6, self.sanitize(f""), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"Ne(e) le: {birth_date} à {birth_place}"), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"المولود في: {birth_date} بـ "), 0, 1, 'R', True)

        self.cell(47, 6, self.sanitize(f"N° ELEVE: {class_number_txt}"), 0, 0, 'L', True)
        self.cell(46, 6, self.sanitize(f"رقم الطالب: {class_number_txt}"), 0, 0, 'R', True)
        self.cell(3, 6, self.sanitize(f""), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"CLASSE: {class_name_fr}"), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"الفصل: {class_name_ar}" if class_name_ar else "الفصل:"), 0, 1, 'R', True)

        self.cell(47, 6, self.sanitize(f"RETARDS: {data['attendance']['ret']}"), 0, 0, 'L', True)
        self.cell(46, 6, self.sanitize(f"تأخر: {data['attendance']['ret']}"), 0, 0, 'R', True)
        self.cell(3, 6, self.sanitize(f""), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"ABSENCES: {data['attendance']['abs']}"), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"غياب: {data['attendance']['abs']}"), 0, 1, 'R', True)
        
        if 'discipline' in data:
            disc = data['discipline']
            self.cell(47, 6, self.sanitize(f"CONDUITE: {disc['conduct_score']:.2f}/{int(disc['base_score'])}"), 0, 0, 'L', True)
            self.cell(46, 6, self.sanitize(f"السلوك: {disc['conduct_score']:.2f}/{int(disc['base_score'])}"), 0, 0, 'R', True)
            self.cell(3, 6, self.sanitize(f""), 0, 0, 'L', True)
            self.cell(47, 6, self.sanitize(f"Pts deduits: {disc['total_deducted']:.1f}"), 0, 0, 'L', True)
            self.cell(47, 6, self.sanitize(f"نقاط محذوفة: {disc['total_deducted']:.1f}"), 0, 1, 'R', True)
        
        self.ln(2)
        
        is_primary = data.get('is_primary', False)
        max_s = int(data.get('max_score', 20))
        
        self.set_fill_color(52, 73, 94)
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_name, 'B', 9)
        
        if not is_primary:
            cols = [50, 25, 20, 20, 20, 20, 35]
            headers = ["Matière / المادة", "Moy Dev / فروض", "Compo / اختبار", f"Moy/{max_s}", "Coef / معامل", "Total", "Appreciation / تقدير"]
        else:
            cols = [76, 26, 16, 21, 51]
            headers = ["Matière / المادة", "Composition / اختبار", "Coef / معامل", "Total", "Appreciation / تقدير"]

        for i, h in enumerate(headers):
            ln_val = 1 if i == len(headers)-1 else 0
            self.cell(cols[i], 6, self.sanitize(h), 1, ln_val, 'C', True)

        self.set_text_color(0, 0, 0)
        self.set_font(self.font_name, '', 9)
        
        for item in data['transcript']:
            h = 7
            if not is_primary:
                self.cell(cols[0], h, self.sanitize(item['subject']), 1)
                m_dev = f"{item['moy_devoir']:.2f}" if item['moy_devoir'] is not None else "-"
                self.cell(cols[1], h, m_dev, 1, 0, 'C')
                note_compo = f"{item['note_compo']:.2f}"
                self.cell(cols[2], h, note_compo, 1, 0, 'C')
                self.set_font(self.font_name, 'B', 9)
                self.cell(cols[3], h, f"{item['avg']:.2f}", 1, 0, 'C')
                self.set_font(self.font_name, '', 9)
                self.cell(cols[4], h, str(item['coef']), 1, 0, 'C')
                self.cell(cols[5], h, f"{item['points']:.1f}", 1, 0, 'C')
                self.cell(cols[6], h, self.sanitize(item['appreciation']), 1, 1, 'C')
            else:
                self.cell(cols[0], h, self.sanitize(item['subject']), 1)
                self.cell(cols[1], h, f"{item['note_compo']:.2f}", 1, 0, 'C')
                self.cell(cols[2], h, str(item['coef']), 1, 0, 'C')
                self.cell(cols[3], h, f"{item['points']:.1f}", 1, 0, 'C')
                self.cell(cols[4], h, self.sanitize(item['appreciation']), 1, 1, 'C')

            self.set_font(self.font_name, 'B', 9)
        
        if 'discipline' in data:
            disc = data['discipline']
            discipline_coef = 1 
            discipline_points = (disc['conduct_score'] / disc['base_score']) * max_s * discipline_coef
            
            if not is_primary:
                self.set_font(self.font_name, '', 9)
                self.cell(cols[0], h, self.sanitize("Conduite / السلوك"), 1)
                self.cell(cols[1], h, "-", 1, 0, 'C')
                self.cell(cols[2], h, f"{disc['conduct_score']:.2f}", 1, 0, 'C')
                self.set_font(self.font_name, 'B', 9)
                self.cell(cols[3], h, f"{disc['conduct_score']:.2f}", 1, 0, 'C')
                self.set_font(self.font_name, '', 9)
                self.cell(cols[4], h, str(discipline_coef), 1, 0, 'C')
                self.cell(cols[5], h, f"{discipline_points:.1f}", 1, 0, 'C')
                self.cell(cols[6], h, self.sanitize(disc['appreciation']), 1, 1, 'C')
            else:
                self.set_font(self.font_name, '', 9)
                self.cell(cols[0], h, self.sanitize("Conduite / السلوك"), 1)
                self.cell(cols[1], h, f"{disc['conduct_score']:.2f}", 1, 0, 'C')
                self.cell(cols[2], h, str(discipline_coef), 1, 0, 'C')
                self.cell(cols[3], h, f"{discipline_points:.1f}", 1, 0, 'C')
                self.cell(cols[4], h, self.sanitize(disc['appreciation']), 1, 1, 'C')
        
        self.set_fill_color(200, 200, 200)
        self.set_font(self.font_name, 'B', 9)
        
        if not is_primary:
            self.cell(cols[0], h, "TOTAL", 1)
            self.cell(cols[1], h, "", 1, 0, 'C')
            self.cell(cols[2], h, "", 1, 0, 'C')
            self.cell(cols[3], h, f"{data['stats']['average']:.2f}", 1, 0, 'C')
            self.cell(cols[4], h, str(data['stats']['total_coef']), 1, 0, 'C')
            self.cell(cols[5], h, f"{data['stats']['total_points']:.1f}/{data['stats']['required_points']:.1f}", 1, 0, 'C')
            self.cell(cols[6], h, "", 1, 1, 'C')
        else:
            self.cell(cols[0], h, "TOTAL", 1)
            self.cell(cols[1], h, "", 1, 0, 'C')
            self.cell(cols[2], h, str(data['stats']['total_coef']), 1, 0, 'C')
            self.cell(cols[3], h, f"{data['stats']['total_points']:.1f}/{data['stats']['required_points']:.1f}", 1, 0, 'C')
            self.cell(cols[4], h, "", 1, 1, 'C')

        self.ln(3)
        y_start_footer = self.get_y()
        
        self.set_x(140)
        self.set_fill_color(220, 220, 220)
        self.set_font(self.font_name, 'B', 9)
        stats = data['stats']
        w_lbl, w_val, h_row = 25, 35, 6
        
        self.cell(w_lbl+w_val, h_row, self.sanitize("RESUME PERIODE / ملخص"), 1, 1, 'C', True)
        self.set_x(140); self.cell(w_lbl, h_row, self.sanitize("Moyenne / معدل:"), 1); self.cell(w_val, h_row, f"{stats['average']:.2f}/{int(max_s)}", 1, 1, 'R')
        self.set_x(140); self.cell(w_lbl, h_row, self.sanitize("Rang / ترتيب:"), 1); self.cell(w_val, h_row, f"{stats['rank']}/{stats.get('class_size', '-')}", 1, 1, 'R')
        self.set_x(140); self.cell(w_lbl, h_row, self.sanitize("Mention / تقدير:"), 1); self.cell(w_val, h_row, self.sanitize(stats['mention']), 1, 1, 'R')
        
        self.set_xy(10, y_start_footer)
        self.cell(125, h_row, self.sanitize("OBSERVATION / ملاحظة:"), 1, 1, 'L', True)
        self.set_font(self.font_name, 'I', 9)
        self.cell(125, h_row*3, self.sanitize(stats['observation']), 1, 1, 'C')

        
        if data['annual']:
            self.set_xy(10, y_start_footer + (h_row*4) + 2)
            self.set_fill_color(220, 220, 220)
            period_count = len(data['annual']['periods'])
            self.set_font(self.font_name, 'B', 7 if period_count >= 4 else 8)
            
            periods = data['annual']['periods']
            col_w = 190 / (len(periods) + 3)
            
            self.cell(190, h_row, self.sanitize("RESUME ANNUEL / ملخص السنة"), 1, 1, 'C', True)
            for pname, _ in periods:
                self.cell(col_w, 6, self.sanitize(pname).replace("Trimestre", "T").replace("Semestre", "S"), 1, 0, 'C', True)
            self.cell(col_w, 6, self.sanitize("MOY ANN"), 1, 0, 'C', True)
            self.cell(col_w, 6, self.sanitize("RANG / ترتيب"), 1, 0, 'C', True)
            self.cell(col_w, 6, self.sanitize("DECISION / قرار"), 1, 1, 'C', True)
            
            self.set_y(self.get_y())
            self.set_x(10)
            self.set_font(self.font_name, '', 7 if period_count >= 4 else 8)
            for _, avg in periods:
                self.cell(col_w, 6, f"{avg:.2f}", 1, 0, 'C')
            
            self.set_font(self.font_name, 'B', 7 if period_count >= 4 else 8)
            self.cell(col_w, 6, f"{data['annual']['annual_average']:.2f}", 1, 0, 'C')
            self.cell(col_w, 6, f"{data['annual']['annual_rank']}/{data['annual'].get('class_size', '-')}", 1, 0, 'C')
            self.cell(col_w, 6, data['annual']['verdict'], 1, 1, 'C')

        self.set_y(y_start_footer + (h_row*8) + 2)
        self.set_font(self.font_name, 'I', 9)
        self.cell(50, 8, self.sanitize("Cachet du Parent / توقيع الولي"), 0, 0, 'C')
        self.cell(50, 8, "", 0, 0, 'C')
        self.cell(90, 8, self.sanitize("Cachet & Signature du Directeur / توقيع المدير"), 0, 1, 'C')

# --- 3. الواجهة الرسومية (UI) ---
class BulletinGenerationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Génération des Bulletins / إصدار الكشوف")
        self.setMinimumSize(1100, 700)
        self._arabic_font_warned = False
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER}; border-radius: 8px; margin-top: 10px;
                    background-color: {colors.BG_CARD}; font-weight: bold; color: {colors.TEXT_SECONDARY};
                }}
                QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }}
            """)
        
        self.init_ui()
        self.load_filters()
        self.batch_results = []

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
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # Header Frame
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
        
        icon_lbl = QLabel("🖨️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("BULLETINS & RÉSULTATS")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("توليد الكشوف، لوحات الشرف، والنتائج السنوية")
        sub_lbl.setFont(QFont("Cairo", 11))
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
                QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 12px; margin-top: 15px; }}
                QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 12px 30px; margin-right: 6px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-family: 'Segoe UI', 'Cairo'; }}
                QTabBar::tab:selected {{ background: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; }}
                QTabBar::tab:hover {{ background: {colors.BORDER}; }}
            """)
        
        self.setup_batch_tab()
        self.setup_individual_tab()
        self.setup_honor_roll_tab()
        self.layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"QComboBox {{ padding: 6px 10px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
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
                QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item:alternate {{ background-color: {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 8px; border: none; font-weight: bold; }}
            """)

    def styled_spinbox(self, prefix="", min_val=0, max_val=1000):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        if prefix:
            spin.setPrefix(prefix)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        spin.setStyleSheet(f"QSpinBox {{ padding: 6px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        spin.setMinimumHeight(38)
        return spin

    def setup_batch_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        filter_card = self.create_card()
        hlay = QHBoxLayout(filter_card)
        hlay.setContentsMargins(15, 15, 15, 15)
        hlay.setSpacing(15)

        self.combo_class_batch = self.styled_combo()
        self.combo_period_batch = self.styled_combo()
        
        btn_calc_batch = QPushButton("1. Calculer & Aperçu")
        btn_calc_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_calc_batch.setStyleSheet(f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_calc_batch.clicked.connect(self.calculate_batch_results)
        
        hlay.addWidget(QLabel("Classe:"))
        hlay.addWidget(self.combo_class_batch, 1)
        hlay.addWidget(QLabel("Période:"))
        hlay.addWidget(self.combo_period_batch, 1)
        hlay.addWidget(btn_calc_batch)
        layout.addWidget(filter_card)
        
        layout.addWidget(QLabel("Aperçu Rapide / معاينة النتائج:"))
        self.table_batch = QTableWidget()
        self.style_table(self.table_batch)
        self.table_batch.setColumnCount(6)
        self.table_batch.setHorizontalHeaderLabels(["Rang", "N°", "Nom et Prénom", "Moyenne", "Mention", "Décision"])
        self.table_batch.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_batch)

        btn_layout = QHBoxLayout()
        btn_print_list = QPushButton("🖨️ Liste Récapitulative")
        btn_print_list.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_list.setStyleSheet(f"QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY}; padding: 12px; font-weight: bold; border-radius: 8px; border: 1px solid {colors.BORDER}; }} QPushButton:hover {{ background-color: {colors.BG_MAIN}; }}")
        btn_print_list.clicked.connect(self.print_summary_list)

        btn_print_all = QPushButton("🖨️ Imprimer TOUS les Bulletins")
        btn_print_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_all.setStyleSheet(f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}")
        btn_print_all.clicked.connect(self.print_all_bulletins)
        
        btn_layout.addWidget(btn_print_list)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_print_all)
        layout.addLayout(btn_layout)
        
        self.tabs.addTab(tab, "  👥 Classe Complète / فصل كامل  ")

    def setup_individual_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        filter_card = self.create_card()
        glay = QGridLayout(filter_card)
        glay.setContentsMargins(15, 15, 15, 15)
        glay.setSpacing(15)
        
        self.combo_class_indiv = self.styled_combo()
        self.combo_class_indiv.currentIndexChanged.connect(self.load_students_indiv)
        self.combo_student_indiv = self.styled_combo()
        self.combo_period_indiv = self.styled_combo()
        
        btn_view = QPushButton("👁️ Afficher")
        btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_view.setStyleSheet(f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_view.clicked.connect(self.view_individual)
        
        btn_print = QPushButton("🖨️ Imprimer")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setStyleSheet(f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}")
        btn_print.clicked.connect(self.print_individual)

        glay.addWidget(QLabel("1. Classe:"), 0, 0)
        glay.addWidget(self.combo_class_indiv, 0, 1)
        glay.addWidget(QLabel("2. Élève:"), 0, 2)
        glay.addWidget(self.combo_student_indiv, 0, 3)
        glay.addWidget(QLabel("3. Période:"), 1, 0)
        glay.addWidget(self.combo_period_indiv, 1, 1)
        glay.addWidget(btn_view, 1, 2)
        glay.addWidget(btn_print, 1, 3)
        
        layout.addWidget(filter_card)

        info_frame = QFrame()
        info_frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_MAIN}; border-radius: 8px; border: 1px dashed {colors.BORDER}; }} QLabel {{ font-weight: bold; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}")
        ilayout = QHBoxLayout(info_frame)
        
        self.lbl_attendance = QLabel("Absences: -- | Retards: --")
        self.lbl_attendance.setStyleSheet(f"color: {colors.DANGER};")
        
        self.lbl_final_stats = QLabel("Moyenne: -- | Rang: -- | Mention: --")
        self.lbl_final_stats.setStyleSheet(f"color: {colors.SUCCESS};")
        
        ilayout.addWidget(self.lbl_attendance)
        ilayout.addStretch()
        ilayout.addWidget(self.lbl_final_stats)
        
        layout.addWidget(info_frame)

        layout.addWidget(QLabel("Détails des Notes / تفاصيل الدرجات:"))
        self.table_preview = QTableWidget()
        self.style_table(self.table_preview)
        self.table_preview.setColumnCount(6)
        self.table_preview.setHorizontalHeaderLabels(["Matière / المادة", "Évaluations / التقييم", "Coef", "Moyenne", "Points", "Appréciation / تقدير"])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_preview.setColumnWidth(1, 220)
        layout.addWidget(self.table_preview)
        
        self.tabs.addTab(tab, "  👤 Bulletin Individuel / كشف فردي  ")

    def setup_honor_roll_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        grp_card = self.create_card()
        hlay = QHBoxLayout(grp_card)
        hlay.setContentsMargins(15, 15, 15, 15)
        hlay.setSpacing(15)
        
        self.combo_class_honor = self.styled_combo()
        self.combo_period_honor = self.styled_combo()
        self.spin_threshold = self.styled_spinbox(prefix="Top: ", min_val=1, max_val=50)
        self.spin_threshold.setValue(3)
        
        btn_calc = QPushButton("Afficher Liste")
        btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        btn_calc.setStyleSheet(f"QPushButton {{ background-color: {colors.SECONDARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_calc.clicked.connect(self.calculate_honor_roll)
        
        hlay.addWidget(QLabel("Classe:")); hlay.addWidget(self.combo_class_honor, 1)
        hlay.addWidget(QLabel("Période:")); hlay.addWidget(self.combo_period_honor, 1)
        hlay.addWidget(self.spin_threshold)
        hlay.addWidget(btn_calc)
        layout.addWidget(grp_card)
        
        self.table_honor = QTableWidget(0, 4)
        self.style_table(self.table_honor)
        self.table_honor.setHorizontalHeaderLabels(["Rang", "Élève", "Moyenne", "Mention"])
        self.table_honor.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_honor)
        
        btn_cert = QPushButton("🏆 Imprimer Attestations d'Excellence")
        btn_cert.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cert.setStyleSheet(f"QPushButton {{ background-color: {colors.WARNING}; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_cert.clicked.connect(self.print_certificates)
        layout.addWidget(btn_cert)
        
        self.tabs.addTab(tab, "  🏆 Excellence / التميز  ")

    def load_filters(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                active_year = self.get_active_year_id()
                
                cursor.execute("SELECT id, class_name_fr, class_name_ar FROM Classes")
                classes = cursor.fetchall()

                if active_year != -1:
                    cursor.execute(
                        "SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods WHERE year_id=%s ORDER BY sort_order",
                        (active_year,)
                    )
                else:
                    cursor.execute("SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods ORDER BY sort_order")
                periods = cursor.fetchall()

            self.combo_class_batch.clear()
            self.combo_class_indiv.clear()
            self.combo_class_honor.clear()
            self.combo_period_batch.clear()
            self.combo_period_indiv.clear()
            self.combo_period_honor.clear()

            for c in classes:
                name_fr = str(c[1] or "-")
                name_ar = str(c[2] or "").strip()
                class_label = f"{name_fr} / {name_ar}" if name_ar else name_fr
                self.combo_class_batch.addItem(class_label, c[0])
                self.combo_class_indiv.addItem(class_label, c[0])
                self.combo_class_honor.addItem(class_label, c[0])
                
            seen_periods = set()
            for p in periods:
                if p[1] not in seen_periods:
                    period_label = f"{p[1]} / {p[2]}" if p[2] else p[1]
                    self.combo_period_batch.addItem(period_label, p[1])
                    self.combo_period_indiv.addItem(period_label, p[1])
                    self.combo_period_honor.addItem(period_label, p[1])
                    seen_periods.add(p[1])
        except Exception as e:
            AppLogger.error("BulletinGeneration", f"Error loading filters: {e}")

    # ===== تعديل مهم: جلب الطلاب للمنسدلة بناءً على SCN =====
    def load_students_indiv(self):
        class_id = self.combo_class_indiv.currentData()
        self.combo_student_indiv.clear()
        if not class_id: return
        
        active_year = self.get_active_year_id()
        if active_year == -1: return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT S.id, S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar 
                    FROM Students S
                    JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
                    WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
                """, (class_id, active_year))
                for s in cursor.fetchall():
                    first_fr = str(s[1] or "").strip()
                    last_fr = str(s[2] or "").strip()
                    first_ar = str(s[3] or "").strip()
                    last_ar = str(s[4] or "").strip()

                    name_fr = f"{first_fr} {last_fr}".strip() or "[Élève]"
                    name_ar = f"{first_ar} {last_ar}".strip()
                    label = f"{name_fr} / {name_ar}" if name_ar else name_fr
                    self.combo_student_indiv.addItem(label, s[0])
        except Exception as e:
            AppLogger.error("BulletinGeneration", f"Error loading students indiv: {e}")

    def get_real_period_id(self, class_id, period_name):
        if isinstance(period_name, str) and "/" in period_name:
            period_name = period_name.split("/")[0].strip()
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT cycle_id FROM Classes WHERE id=%s", (class_id,))
                res = cursor.fetchone()
                if not res: return None
                cycle_id = res[0]
                active_year = self.get_active_year_id()
                if active_year != -1:
                    cursor.execute(
                        "SELECT id FROM AcademicPeriods WHERE period_name_fr=%s AND cycle_id=%s AND year_id=%s ORDER BY sort_order LIMIT 1",
                        (period_name, cycle_id, active_year)
                    )
                    res = cursor.fetchone()
                    if res:
                        return res[0]

                cursor.execute(
                    "SELECT id FROM AcademicPeriods WHERE period_name_fr=%s AND cycle_id=%s ORDER BY id DESC LIMIT 1",
                    (period_name, cycle_id)
                )
                res = cursor.fetchone()
            return res[0] if res else None
        except Exception:
            return None

    def _filename_safe_slug(self, text, fallback="NA"):
        value = str(text or "").strip().replace(" ", "_")
        value = value.encode("ascii", "ignore").decode("ascii")
        clean = "".join(ch for ch in value if ch.isalnum() or ch in "-_")
        return clean or fallback

    def calculate_batch_results(self):
        class_id = self.combo_class_batch.currentData()
        p_name = self.combo_period_batch.currentText()
        real_period_id = self.get_real_period_id(class_id, p_name)
        
        if not real_period_id:
            QMessageBox.warning(self, "Erreur", "Période invalide pour cette classe.")
            return

        try:
            calc = GradeCalculator()
            self.batch_results = calc.get_student_averages(class_id, real_period_id, include_conduct=True)
            is_primary, max_score = calc.get_class_context(class_id)
            class_size = len(self.batch_results)
            
            self.table_batch.setRowCount(0)
            for row_data in self.batch_results:
                idx = self.table_batch.rowCount()
                self.table_batch.insertRow(idx)
                self.table_batch.setItem(idx, 0, QTableWidgetItem(str(row_data['rank'])))
                self.table_batch.setItem(idx, 1, QTableWidgetItem(str(row_data.get('class_number') or "-")))
                self.table_batch.setItem(idx, 2, QTableWidgetItem(row_data['name']))
                self.table_batch.setItem(idx, 3, QTableWidgetItem(f"{row_data['general_average']:.2f}"))
                mention = calc.get_mention(row_data['general_average'], max_score)
                self.table_batch.setItem(idx, 4, QTableWidgetItem(mention))
                dec = calc.get_decision(row_data['general_average'], is_primary, max_score)
                self.table_batch.setItem(idx, 5, QTableWidgetItem(dec))

            for row_data in self.batch_results:
                row_data['class_size'] = class_size
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de calcul: {e}")

    def print_summary_list(self):
        if _get_arabic_font_path() is None and not self._arabic_font_warned:
            QMessageBox.warning(self, "خط عربي غير موجود", "ضع خط عربي (TTF) داخل مجلد Fonts حتى تظهر العربية في التقارير.")
            self._arabic_font_warned = True
        if not self.batch_results:
            QMessageBox.warning(self, "Vide", "Calculez d'abord les résultats.")
            return

        try:
            pdf = FPDF()
            font_path = _get_arabic_font_path()
            font_name = "Arial"
            if font_path:
                try:
                    pdf.add_font("ArabicFont", "", font_path, uni=True)
                    font_name = "ArabicFont"
                except Exception:
                    font_name = "Arial"
            pdf.add_page()

            school_info = None
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
                    school_info = cursor.fetchone()
            except Exception:
                school_info = None

            left_x, left_y = 10, 5
            pdf.set_xy(left_x, left_y)
            pdf.set_font(font_name, '', 8)
            if school_info:
                republic = str(school_info[1] or "")
                ia_text = str(school_info[2] or "")
                ief_text = str(school_info[3] or "")
                school_name = str(school_info[4] or "")
                auth_text = str(school_info[5] or "")
                addr_text = str(school_info[6] or "")
                phone_text = str(school_info[7] or "")

                pdf.cell(80, 3, _prepare_pdf_text(republic) if font_name == "ArabicFont" else _sanitize_latin(republic), 0, 1, 'L')
                pdf.cell(80, 3, _prepare_pdf_text(ia_text) if font_name == "ArabicFont" else _sanitize_latin(ia_text), 0, 1, 'L')
                pdf.cell(80, 3, _prepare_pdf_text(ief_text) if font_name == "ArabicFont" else _sanitize_latin(ief_text), 0, 1, 'L')
                pdf.cell(80, 3, _prepare_pdf_text(school_name) if font_name == "ArabicFont" else _sanitize_latin(school_name), 0, 1, 'L')
                pdf.cell(80, 3, _prepare_pdf_text(f"Auto N: {auth_text}") if font_name == "ArabicFont" else _sanitize_latin(f"Auto N: {auth_text}"), 0, 1, 'L')
                pdf.cell(80, 3, _prepare_pdf_text(f"Lieu: {addr_text}") if font_name == "ArabicFont" else _sanitize_latin(f"Lieu: {addr_text}"), 0, 1, 'L')
                pdf.cell(80, 3, _prepare_pdf_text(f"Tel: {phone_text}") if font_name == "ArabicFont" else _sanitize_latin(f"Tel: {phone_text}"), 0, 1, 'L')

                logo_path = school_info[8] if len(school_info) > 8 else None
                if logo_path and os.path.exists(logo_path):
                    try:
                        pdf.image(logo_path, x=175, y=left_y, w=20, h=22)
                    except Exception:
                        pass

            pdf.set_xy(175, left_y + 22)
            pdf.set_y(pdf.get_y() + 2)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)

            title_style = '' if font_name == "ArabicFont" else 'B'
            pdf.set_font(font_name, title_style, 12)
            pdf.set_text_color(15, 23, 42)
            
            title = f"Liste Récapitulative des Résultats - {self.combo_period_batch.currentText()} - {self.combo_class_batch.currentText()}"
            pdf.cell(0, 10, _prepare_pdf_text(title) if font_name == "ArabicFont" else _sanitize_latin(title), 0, 1, 'C')
            
            pdf.set_font(font_name, title_style, 9)
            pdf.set_fill_color(30, 58, 95)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(20, 8, _prepare_pdf_text("Rang") if font_name == "ArabicFont" else _sanitize_latin("Rang"), 1, 0, 'C', True)
            pdf.cell(12, 8, _prepare_pdf_text("N°") if font_name == "ArabicFont" else _sanitize_latin("N°"), 1, 0, 'C', True)
            pdf.cell(68, 8, _prepare_pdf_text("Nom & Prénom") if font_name == "ArabicFont" else _sanitize_latin("Nom & Prénom"), 1, 0, 'C', True)
            pdf.cell(25, 8, _prepare_pdf_text("Moyenne") if font_name == "ArabicFont" else _sanitize_latin("Moyenne"), 1, 0, 'C', True)
            pdf.cell(40, 8, _prepare_pdf_text("Mention") if font_name == "ArabicFont" else _sanitize_latin("Mention"), 1, 0, 'C', True)
            pdf.cell(25, 8, _prepare_pdf_text("Décision") if font_name == "ArabicFont" else _sanitize_latin("Décision"), 1, 1, 'C', True)
            
            pdf.set_font(font_name, '', 9)
            pdf.set_text_color(15, 23, 42)
            calc = GradeCalculator()
            class_id = self.combo_class_batch.currentData()
            is_primary, max_score = calc.get_class_context(class_id)
            class_size = len(self.batch_results)
            
            for idx, res in enumerate(self.batch_results):
                name_fr = _sanitize_latin(res['name'])
                name_ar = res.get('name_ar', '') or ""
                class_number = str(res.get('class_number') or "-")
                name = f"[{class_number}] {name_fr} / {name_ar}" if name_ar else f"[{class_number}] {name_fr}"
                name_out = _prepare_pdf_text(name) if font_name == "ArabicFont" else _sanitize_latin(name)
                avg = f"{res['general_average']:.2f}"
                mention = calc.get_mention(res['general_average'], max_score)
                dec = calc.get_decision(res['general_average'], is_primary, max_score)

                if idx % 2 == 0:
                    pdf.set_fill_color(241, 245, 249)
                else:
                    pdf.set_fill_color(255, 255, 255)
                
                pdf.cell(20, 8, f"{res['rank']}/{class_size}", 1, 0, 'C', True)
                pdf.cell(12, 8, class_number, 1, 0, 'C', True)
                pdf.cell(68, 8, name_out, 1, 0, 'L', True)
                pdf.cell(25, 8, avg, 1, 0, 'C', True)
                pdf.cell(40, 8, _prepare_pdf_text(mention) if font_name == "ArabicFont" else _sanitize_latin(mention), 1, 0, 'C', True)
                pdf.cell(25, 8, _prepare_pdf_text(dec) if font_name == "ArabicFont" else _sanitize_latin(dec), 1, 1, 'C', True)

            class_slug = "".join(ch for ch in (self.combo_class_batch.currentText() or "Toutes_Classes").replace(" ", "_") if ch.isalnum() or ch in "-_") or "Classe"
            period_slug = "".join(ch for ch in (self.combo_period_batch.currentText() or "Periode").replace(" ", "_") if ch.isalnum() or ch in "-_") or "Periode"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            output_pdf(
                pdf,
                self,
                f"Liste_Recap_{class_slug}_{period_slug}_{timestamp}.pdf",
                mode=BULLETIN_SUMMARY_OUTPUT_MODE,
                dialog_title="Save PDF",
                success_save_message="Liste récapitulative générée.",
                success_print_message="Liste récapitulative envoyée à l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def print_all_bulletins(self):
        self.generate_bulletins(self.combo_class_batch.currentData(), self.combo_period_batch.currentText(), None)

    def print_individual(self):
        std_id = self.combo_student_indiv.currentData()
        if std_id:
            self.generate_bulletins(self.combo_class_indiv.currentData(), self.combo_period_indiv.currentText(), [std_id])

    def view_individual(self):
        class_id = self.combo_class_indiv.currentData()
        student_id = self.combo_student_indiv.currentData()
        p_name = self.combo_period_indiv.currentText()
        
        real_period_id = self.get_real_period_id(class_id, p_name)
        if not real_period_id:
            QMessageBox.warning(self, "Erreur", "Période invalide.")
            return

        if not student_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève.")
            return

        try:
            calc = GradeCalculator()
            is_primary, max_score = calc.get_class_context(class_id)
            
            batch_results = calc.get_student_averages(class_id, real_period_id, include_conduct=True)
            rank = "--"
            mention = "--"
            for res in batch_results:
                if res['id'] == student_id:
                    rank = res['rank']
                    mention = calc.get_mention(res['general_average'], max_score)
                    break
            
            data = calc.get_student_bulletin_data(student_id, class_id, real_period_id)
            
            if data:
                absences = data['attendance']['abs']
                retards = data['attendance']['ret']
                avg = data['stats']['average']
                
                self.lbl_attendance.setText(f"Absences / غياب: {absences} | Retards / تأخر: {retards}")
                class_size = len(batch_results)
                self.lbl_final_stats.setText(f"Moyenne / معدل: {avg:.2f} | Rang / ترتيب: {rank}/{class_size} | Mention / تقدير: {mention}")
                
                self.table_preview.setRowCount(0)
                for sub in data['transcript']:
                    idx = self.table_preview.rowCount()
                    self.table_preview.insertRow(idx)
                    self.table_preview.setItem(idx, 0, QTableWidgetItem(sub['subject']))
                    
                    details = ""
                    if not data['is_primary']:
                        if sub['moy_devoir'] is not None:
                            details = f"Dev / فرض: {sub['moy_devoir']:.2f} | Compo / اختبار: {sub['note_compo']:.2f}"
                        else:
                            details = f"Compo / اختبار: {sub['note_compo']:.2f}"
                    else:
                        details = f"Composition / اختبار: {sub['note_compo']:.2f}"
                    
                    self.table_preview.setItem(idx, 1, QTableWidgetItem(details))
                    self.table_preview.setItem(idx, 2, QTableWidgetItem(str(sub['coef'])))
                    self.table_preview.setItem(idx, 3, QTableWidgetItem(f"{sub['avg']:.2f}"))
                    self.table_preview.setItem(idx, 4, QTableWidgetItem(f"{sub['points']:.2f}"))
                    self.table_preview.setItem(idx, 5, QTableWidgetItem(sub['appreciation']))
            else:
                QMessageBox.warning(self, "Info", "Aucune donnée trouvée.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur d'affichage: {e}")

    def generate_bulletins(self, class_id, period_name, specific_ids=None):
        if _get_arabic_font_path() is None and not self._arabic_font_warned:
            QMessageBox.warning(self, "خط عربي غير موجود", "ضع خط عربي (TTF) داخل مجلد Fonts حتى تظهر العربية في التقارير.")
            self._arabic_font_warned = True
        real_period_id = self.get_real_period_id(class_id, period_name)
        if not real_period_id: 
            QMessageBox.warning(self, "Erreur", "Période invalide.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Dossier de Sauvegarde")
        if not folder: return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
                school_info = cursor.fetchone()
                
                # Fetch active year label based on period's year
                year_id = GradeCalculator()._get_period_year_id(cursor, real_period_id)
                cursor.execute("SELECT year_label FROM AcademicYears WHERE id=%s", (year_id,))
                yr = cursor.fetchone()
                if yr:
                    year_label = yr[0]
                else:
                    cursor.execute("SELECT year_label FROM AcademicYears ORDER BY id DESC LIMIT 1")
                    yr_alt = cursor.fetchone()
                    year_label = yr_alt[0] if yr_alt else "202X-202X"
                    
                cursor.execute("SELECT class_name_fr, class_name_ar FROM Classes WHERE id=%s", (class_id,))
                class_res = cursor.fetchone()
                if class_res:
                    class_name = f"{class_res[0]} / {class_res[1]}" if class_res[1] else class_res[0]
                else:
                    class_name = "Classe"

            calc = GradeCalculator()
            all_ranks = calc.get_student_averages(class_id, real_period_id, include_conduct=True)
            class_slug = self._filename_safe_slug(class_name, "Classe")
            period_slug = self._filename_safe_slug(period_name, "Periode")
            year_slug = self._filename_safe_slug(year_label, "Annee")
            batch_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            count = 0
            for std_rank_data in all_ranks:
                if specific_ids and std_rank_data['id'] not in specific_ids:
                    continue
                    
                full_data = calc.get_student_bulletin_data(std_rank_data['id'], class_id, real_period_id)
                
                if not full_data: continue
                
                full_data['stats']['rank'] = std_rank_data['rank']
                
                pdf = BulletinPDF(school_info, period_name, year_label)
                pdf.draw_bulletin(full_data, class_name)
                
                student_name = full_data['info'][0] if full_data and full_data.get('info') else std_rank_data.get('name', 'Eleve')
                student_slug = self._filename_safe_slug(student_name, f"Eleve_{std_rank_data.get('id', 'NA')}")
                bulletin_name = (
                    f"Bulletin_{class_slug}_{period_slug}_{year_slug}_"
                    f"{student_slug}_R{std_rank_data['rank']}_{batch_stamp}.pdf"
                )
                pdf.output(os.path.join(folder, bulletin_name))
                count += 1

            QMessageBox.information(self, "Terminé", f"{count} bulletins générés avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération: {str(e)}")

    def calculate_honor_roll(self):
        cid = self.combo_class_honor.currentData()
        pname = self.combo_period_honor.currentText()
        pid = self.get_real_period_id(cid, pname)
        threshold_rank = self.spin_threshold.value()
        
        if not pid: return
        
        try:
            calc = GradeCalculator()
            all_results = calc.get_student_averages(cid, pid, include_conduct=True)
            _, max_s = calc.get_class_context(cid)
            
            self.honor_list = [s for s in all_results if s['rank'] <= threshold_rank]
            
            self.table_honor.setRowCount(0)
            for s in self.honor_list:
                idx = self.table_honor.rowCount()
                self.table_honor.insertRow(idx)
                self.table_honor.setItem(idx, 0, QTableWidgetItem(str(s['rank'])))
                name_fr = s['name']
                name_ar = s.get('name_ar', '')
                display_name = f"{name_fr} / {name_ar}" if name_ar else name_fr
                self.table_honor.setItem(idx, 1, QTableWidgetItem(display_name))
                self.table_honor.setItem(idx, 2, QTableWidgetItem(f"{s['general_average']:.2f}"))
                mention = calc.get_mention(s['general_average'], max_s)
                self.table_honor.setItem(idx, 3, QTableWidgetItem(mention))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de calcul honor roll: {e}")

    def print_certificates(self):
        if _get_arabic_font_path() is None and not self._arabic_font_warned:
            QMessageBox.warning(self, "خط عربي غير موجود", "ضع خط عربي (TTF) داخل مجلد Fonts حتى تظهر العربية في التقارير.")
            self._arabic_font_warned = True
        if not hasattr(self, 'honor_list') or not self.honor_list: return
        folder = QFileDialog.getExistingDirectory(self, "Sauvegarder Certificats")
        if not folder: return
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
                school_info = cursor.fetchone()
                
                # Fetch active year from period
                cid = self.combo_class_honor.currentData()
                pname = self.combo_period_honor.currentText()
                pid = self.get_real_period_id(cid, pname)
                
                if pid:
                    year_id = GradeCalculator()._get_period_year_id(cursor, pid)
                    cursor.execute("SELECT year_label FROM AcademicYears WHERE id=%s", (year_id,))
                    yr = cursor.fetchone()
                    year_label = yr[0] if yr else "202X-202X"
                else:
                    year_label = "202X-202X"
        
            class_name = self.combo_class_honor.currentText()
            period_name = self.combo_period_honor.currentText()
            calc = GradeCalculator()
            _, max_s = calc.get_class_context(cid)
            class_slug = self._filename_safe_slug(class_name, "Classe")
            period_slug = self._filename_safe_slug(period_name, "Periode")
            year_slug = self._filename_safe_slug(year_label, "Annee")
            batch_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            count = 0
            for s in self.honor_list:
                cert = CertificatePDF(school_info, year_label)
                mention = calc.get_mention(s['general_average'], max_s)
                name_fr = s['name']
                name_ar = s.get('name_ar', '')
                display_name = f"{name_fr} / {name_ar}" if name_ar else name_fr
                cert.create_certificate(display_name, class_name, s['general_average'], s['rank'], mention, period_name=period_name)
                student_slug = self._filename_safe_slug(name_fr, "Eleve")
                cert_name = (
                    f"Certificat_Honneur_{class_slug}_{period_slug}_{year_slug}_"
                    f"{student_slug}_R{s['rank']}_{batch_stamp}.pdf"
                )
                cert.output(os.path.join(folder, cert_name))
                count += 1
                
            QMessageBox.information(self, "Succès", f"{count} certificats générés.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de génération des certificats: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BulletinGenerationWindow()
    window.show()
    sys.exit(app.exec())

