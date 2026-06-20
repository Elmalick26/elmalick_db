import os
import sys
from datetime import datetime

from fpdf import FPDF
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from print_export_service import get_report_output_mode, output_pdf
from repositories.bulletin_repo import BulletinRepository
from services.grade_service import GradeService, is_primary_cycle
from ui_styles import (
    Colors,
    ModuleHeaderWidget,
    ThemeManager,
    apply_shadow_to_widget,
    get_card_style,
    get_module_caps,
    get_table_style,
    get_tabs_style,
)

BULLETIN_SUMMARY_OUTPUT_MODE = get_report_output_mode("bulletin_summary_mode", "save")

from pdf_helpers import ARABIC_SUPPORT
from pdf_helpers import contains_arabic as _contains_arabic
from pdf_helpers import find_arabic_font_path as _get_arabic_font_path
from pdf_helpers import get_pdf_font_name, is_arabic_font_ready
from pdf_helpers import latin_fallback as _latin_fallback_text
from pdf_helpers import prepare_pdf_text as _prepare_pdf_text
from pdf_helpers import sanitize_latin as sanitize
from pdf_helpers import setup_pdf_arabic_font
from ui_components import card_frame, style_table, styled_combo


def _register_arabic_font(pdf):
    return setup_pdf_arabic_font(pdf)


# --- 1. محرك الحسابات المنطقي (Back-End Logic) ---


class GradeCalculator:
    def __init__(self):
        self._grade_service = GradeService()

    def get_class_context(self, class_id):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cycle_name = BulletinRepository(conn).get_cycle_name_for_class(class_id) or ""
        is_primary = is_primary_cycle(cycle_name)
        max_score = 10.0 if is_primary else 20.0
        return is_primary, max_score

    def calculate_rank(self, students_list, key_name='average'):
        # Delegates to the pure, unit-tested service. Handles ex aequo ties
        # (standard competition ranking) instead of assigning sequential ranks.
        return self._grade_service.calculate_rank(students_list, key_name)

    def get_class_subjects(self, repo, class_id):
        """إرجاع المواد الفعلية للفصل: من جدول الحصص أولاً، ثم مواد المرحلة."""
        return repo.get_subjects_for_class(class_id)

    def _get_period_year_id(self, repo, period_id):
        return repo.get_period_year_id(period_id)

    def _get_grade_score(self, repo, student_id, subject_id, assessment_id, year_id):
        return repo.get_grade_score(student_id, subject_id, assessment_id, year_id)

    def _get_attendance_count(self, repo, student_id, status, year_id, period_id=None):
        return repo.get_attendance_count(student_id, status, year_id, period_id)

    def _get_discipline_data(self, repo, student_id, year_id, is_primary, period_id=None):
        total_deducted, records = repo.get_discipline_data_raw(student_id, year_id, period_id)
        base_conduct_score = 10.0 if is_primary else 20.0
        conduct_score = max(0, base_conduct_score - total_deducted)
        return {
            'conduct_score': conduct_score,
            'base_score': base_conduct_score,
            'total_deducted': total_deducted,
            'records': records,
            'appreciation': self.get_conduct_appreciation(conduct_score, base_conduct_score),
        }

    # ===== تعديل مهم: جلب الطلاب من جدول التسجيل (SCN) بناءً على سنة الفترة الدراسية =====
    def get_student_averages(self, class_id, period_id, include_conduct=False):
        db = DatabaseManager()
        is_primary, max_score = self.get_class_context(class_id)

        with db.get_connection() as conn:
            repo = BulletinRepository(conn)
            year_id = self._get_period_year_id(repo, period_id)

            students = repo.list_students_in_class_ordered(class_id, year_id)

            subjects = self.get_class_subjects(repo, class_id)
            if not subjects:
                return []

            assessments = repo.get_assessments_for_period(period_id)

            # Fetch every grade for the class in ONE query instead of one query
            # per (student × subject × assessment) — avoids the N+1 explosion.
            grades_map = repo.get_grades_map_for_students([s[0] for s in students], year_id)

            class_results = []

            for std in students:
                std_id, fname, lname, fname_ar, lname_ar, class_number = std
                student_data = {
                    'id': std_id,
                    'class_number': class_number or None,
                    'name': f"{fname} {lname}",
                    'name_ar': f"{fname_ar} {lname_ar}" if fname_ar or lname_ar else "",
                    'subjects': [],
                    'total_points': 0,
                    'total_coef': 0,
                    'general_average': 0,
                    'is_primary': is_primary,
                    'max_score': max_score,
                }

                for sub in subjects:
                    sub_id, sub_name_fr, sub_name_ar, sub_coef = sub

                    # Classify the period's assessments into devoirs + composition.
                    # Missing grade counts as 0 (school policy: absent = fail, not excluded).
                    devoir_scores = []
                    composition = None
                    for assess in assessments:
                        assess_id, assess_name, assess_code, assess_w = assess
                        score = grades_map.get((std_id, sub_id, assess_id), 0)
                        if self._grade_service.is_devoir_assessment(assess_code, assess_name):
                            devoir_scores.append(score)
                        else:
                            composition = score

                    # Canonical subject average — same logic the promotion decision uses.
                    moy_subject = self._grade_service.subject_average(devoir_scores, composition, is_primary)
                    moy_devoirs = (sum(devoir_scores) / len(devoir_scores)) if devoir_scores else 0
                    has_exam = composition is not None
                    exam_score = composition if composition is not None else 0

                    points = moy_subject * sub_coef

                    subject_label = f"{sub_name_fr} / {sub_name_ar}" if sub_name_ar else sub_name_fr

                    student_data['subjects'].append(
                        {
                            'name': subject_label,
                            'name_fr': sub_name_fr,
                            'name_ar': sub_name_ar,
                            'coef': sub_coef,
                            'moy_devoir': (moy_devoirs if devoir_scores and not is_primary else None),
                            'note_compo': exam_score if has_exam and not is_primary else moy_subject,
                            'avg': moy_subject,
                            'points': points,
                            'appreciation': self.get_appreciation(moy_subject, max_score),
                        }
                    )

                    student_data['total_points'] += points
                    student_data['total_coef'] += sub_coef

                if include_conduct:
                    discipline_data = self._get_discipline_data(repo, std_id, year_id, is_primary, period_id)
                    discipline_coef = 1
                    discipline_points = (
                        (discipline_data['conduct_score'] / discipline_data['base_score']) * max_score * discipline_coef
                    )
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

        if not target_student:
            return None

        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = BulletinRepository(conn)

            target_student['info'] = repo.get_student_details(student_id)

            year_id = self._get_period_year_id(repo, period_id)

            class_size = repo.get_class_size(class_id, year_id)

            abs_cnt = self._get_attendance_count(repo, student_id, 'Absent', year_id, period_id)
            ret_cnt = self._get_attendance_count(repo, student_id, 'Retard', year_id, period_id)
            target_student['attendance'] = {'abs': abs_cnt, 'ret': ret_cnt}

            if 'discipline' not in target_student:
                target_student['discipline'] = self._get_discipline_data(
                    repo, student_id, year_id, target_student['is_primary'], period_id
                )

            target_student['mention'] = self.get_mention(target_student['general_average'], target_student['max_score'])
            target_student['observation'] = self.get_observation(
                target_student['general_average'], target_student['max_score']
            )

            # Annual Logic
            meta = repo.get_period_meta(period_id)
            target_student['annual'] = None

            if meta:
                y_id, c_id = meta
                all_periods = repo.list_periods_for_year_and_cycle(y_id, c_id)

                if all_periods and all_periods[-1][0] == period_id:
                    annual_avgs = []

                    period_results_cache = {}
                    for pid, _, _ in all_periods:
                        period_results_cache[pid] = self.get_student_averages(class_id, pid)

                    # ===== تعديل مهم: جلب الطلاب من جدول التسجيل SCN =====
                    all_ids = repo.list_student_ids_in_class(class_id, y_id)

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

                    verdict = "Admis" if ann_avg >= (target_student['max_score'] / 2) else "Redouble"

                    target_student['annual'] = {
                        'periods': annual_avgs,
                        'annual_average': ann_avg,
                        'annual_rank': annual_rank,
                        'class_size': class_size,
                        'annual_mention': self.get_mention(ann_avg, target_student['max_score']),
                        'verdict': verdict,
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
            'observation': target_student['observation'],
        }

        target_student['transcript'] = []
        for sub in target_student['subjects']:
            target_student['transcript'].append(
                {
                    'subject': sub['name'],
                    'coef': sub['coef'],
                    'points': sub['points'],
                    'appreciation': sub['appreciation'],
                    'moy_devoir': sub['moy_devoir'],
                    'note_compo': sub['note_compo'],
                    'avg': sub['avg'],
                }
            )

        return target_student

    def get_appreciation(self, note, max_s=20):
        ratio = 20 / max_s
        n = note * ratio
        if n < 10:
            return "Faible / ضعيف"
        if n < 12:
            return "Passable / مقبول"
        if n < 14:
            return "A. Bien / حسن"
        if n < 16:
            return "Bien / جيد"
        return "T. Bien / جيد جداً"

    def get_mention(self, avg, max_s=20):
        ratio = 20 / max_s
        n = avg * ratio
        if n < 10:
            return "Insuffisant / غير مقبول"
        if n < 12:
            return "Passable / ضعيف"
        if n < 14:
            return "Assez Bien / مقبول"
        if n < 16:
            return "Bien / جيد"
        if n < 18:
            return "Très Bien / جيد جداً"
        return "Excellent / ممتاز"

    def get_decision(self, avg, is_primary, max_s=20):
        threshold = 5.0 if is_primary else 10.0
        return "Admis" if avg >= threshold else "Ajourné"

    def get_observation(self, avg, max_s=20):
        ratio = 20 / max_s
        n = avg * ratio
        if n < 10:
            return "Des efforts sont nécessaires. Doit redoubler. / يجب بذل جهود أكبر والإعادة."
        if n < 12:
            return "Travail moyen. Doit persévérer. / عمل متوسط ويجب المواصلة."
        if n < 14:
            return "Bon travail. Continuez ainsi. / عمل جيد استمر هكذا."
        if n < 16:
            return "Très bon travail. Félicitations. / عمل ممتاز ومستحق التهاني."
        return "Excellent travail. Tableau d'Honneur. Félicitations. / عمل متميز جداً وجدير بلوحة الشرف."

    def get_conduct_appreciation(self, score, max_s=20):
        ratio = 20 / max_s
        n = score * ratio
        if n >= 18:
            return "Excellent / ممتاز"
        if n >= 16:
            return "Très Bien / جيد جداً"
        if n >= 14:
            return "Bien / جيد"
        if n >= 12:
            return "Assez Bien / مقبول"
        if n >= 10:
            return "Passable / ضعيف"
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
        return sanitize(text)

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
        line_fr = (
            f"Pour ses excellents resultats scolaires en {period_fr} de l'annee scolaire {self.year_label}."
            if period_fr
            else f"Pour ses excellents resultats scolaires de l'annee scolaire {self.year_label}."
        )
        line_ar = (
            f"لتفوقه الدراسي في {period_ar} في السنة الدراسية {self.year_label}."
            if period_ar
            else f"لتفوقه الدراسي في السنة الدراسية {self.year_label}."
        )

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
        return sanitize(text)

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
            except Exception:
                pass
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
        title_fr = (
            f"BULLETIN DE NOTES - {str(period_fr).upper()} ({self.year_label})"
            if period_fr
            else f"BULLETIN DE NOTES ({self.year_label})"
        )
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
        birth_date = data['info'][4] or "N/A"
        birth_place = data['info'][5] or "-"
        class_number = data.get('class_number')
        class_number_txt = str(class_number) if class_number is not None else "-"

        self.cell(47, 6, self.sanitize(f"ELEVE: {full_name}"), 0, 0, 'L', True)
        self.cell(46, 6, self.sanitize(f"الطالب: {full_name_ar}" if full_name_ar else "الطالب:"), 0, 0, 'R', True)
        self.cell(3, 6, self.sanitize(""), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"Ne(e) le: {birth_date} à {birth_place}"), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"المولود في: {birth_date} بـ "), 0, 1, 'R', True)

        self.cell(47, 6, self.sanitize(f"N° ELEVE: {class_number_txt}"), 0, 0, 'L', True)
        self.cell(46, 6, self.sanitize(f"رقم الطالب: {class_number_txt}"), 0, 0, 'R', True)
        self.cell(3, 6, self.sanitize(""), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"CLASSE: {class_name_fr}"), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"الفصل: {class_name_ar}" if class_name_ar else "الفصل:"), 0, 1, 'R', True)

        self.cell(47, 6, self.sanitize(f"RETARDS: {data['attendance']['ret']}"), 0, 0, 'L', True)
        self.cell(46, 6, self.sanitize(f"تأخر: {data['attendance']['ret']}"), 0, 0, 'R', True)
        self.cell(3, 6, self.sanitize(""), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"ABSENCES: {data['attendance']['abs']}"), 0, 0, 'L', True)
        self.cell(47, 6, self.sanitize(f"غياب: {data['attendance']['abs']}"), 0, 1, 'R', True)

        if 'discipline' in data:
            disc = data['discipline']
            self.cell(
                47,
                6,
                self.sanitize(f"CONDUITE: {disc['conduct_score']:.2f}/{int(disc['base_score'])}"),
                0,
                0,
                'L',
                True,
            )
            self.cell(
                46,
                6,
                self.sanitize(f"السلوك: {disc['conduct_score']:.2f}/{int(disc['base_score'])}"),
                0,
                0,
                'R',
                True,
            )
            self.cell(3, 6, self.sanitize(""), 0, 0, 'L', True)
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
            headers = [
                "Matière / المادة",
                "Moy Dev / فروض",
                "Compo / اختبار",
                f"Moy/{max_s}",
                "Coef / معامل",
                "Total",
                "Appreciation / تقدير",
            ]
        else:
            cols = [76, 26, 16, 21, 51]
            headers = [
                "Matière / المادة",
                "Composition / اختبار",
                "Coef / معامل",
                "Total",
                "Appreciation / تقدير",
            ]

        for i, h in enumerate(headers):
            ln_val = 1 if i == len(headers) - 1 else 0
            self.cell(cols[i], 6, self.sanitize(h), 1, ln_val, 'C', True)

        self.set_text_color(0, 0, 0)
        self.set_font(self.font_name, '', 9)

        # FIX 4: Initialize h before the loop — if transcript is empty the discipline
        # row and TOTAL row below the loop both reference h, causing NameError.
        h = 7
        for item in data['transcript']:
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
            self.cell(
                cols[5], h, f"{data['stats']['total_points']:.1f}/{data['stats']['required_points']:.1f}", 1, 0, 'C'
            )
            self.cell(cols[6], h, "", 1, 1, 'C')
        else:
            self.cell(cols[0], h, "TOTAL", 1)
            self.cell(cols[1], h, "", 1, 0, 'C')
            self.cell(cols[2], h, str(data['stats']['total_coef']), 1, 0, 'C')
            self.cell(
                cols[3], h, f"{data['stats']['total_points']:.1f}/{data['stats']['required_points']:.1f}", 1, 0, 'C'
            )
            self.cell(cols[4], h, "", 1, 1, 'C')

        self.ln(3)
        y_start_footer = self.get_y()

        self.set_x(140)
        self.set_fill_color(220, 220, 220)
        self.set_font(self.font_name, 'B', 9)
        stats = data['stats']
        w_lbl, w_val, h_row = 25, 35, 6

        self.cell(w_lbl + w_val, h_row, self.sanitize("RESUME PERIODE / ملخص"), 1, 1, 'C', True)
        self.set_x(140)
        self.cell(w_lbl, h_row, self.sanitize("Moyenne / معدل:"), 1)
        self.cell(w_val, h_row, f"{stats['average']:.2f}/{int(max_s)}", 1, 1, 'R')
        self.set_x(140)
        self.cell(w_lbl, h_row, self.sanitize("Rang / ترتيب:"), 1)
        self.cell(w_val, h_row, f"{stats['rank']}/{stats.get('class_size', '-')}", 1, 1, 'R')
        self.set_x(140)
        self.cell(w_lbl, h_row, self.sanitize("Mention / تقدير:"), 1)
        self.cell(w_val, h_row, self.sanitize(stats['mention']), 1, 1, 'R')

        self.set_xy(10, y_start_footer)
        self.cell(125, h_row, self.sanitize("OBSERVATION / ملاحظة:"), 1, 1, 'L', True)
        self.set_font(self.font_name, 'I', 9)
        self.cell(125, h_row * 3, self.sanitize(stats['observation']), 1, 1, 'C')

        if data['annual']:
            self.set_xy(10, y_start_footer + (h_row * 4) + 2)
            self.set_fill_color(220, 220, 220)
            period_count = len(data['annual']['periods'])
            self.set_font(self.font_name, 'B', 7 if period_count >= 4 else 8)

            periods = data['annual']['periods']
            col_w = 190 / (len(periods) + 3)

            self.cell(190, h_row, self.sanitize("RESUME ANNUEL / ملخص السنة"), 1, 1, 'C', True)
            for pname, _ in periods:
                self.cell(
                    col_w, 6, self.sanitize(pname).replace("Trimestre", "T").replace("Semestre", "S"), 1, 0, 'C', True
                )
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

        self.set_y(y_start_footer + (h_row * 8) + 2)
        self.set_font(self.font_name, 'I', 9)
        self.cell(50, 8, self.sanitize("Cachet du Parent / توقيع الولي"), 0, 0, 'C')
        self.cell(50, 8, "", 0, 0, 'C')
        self.cell(90, 8, self.sanitize("Cachet & Signature du Directeur / توقيع المدير"), 0, 1, 'C')


# --- 3. الواجهة الرسومية (UI) ---


class BulletinComputeWorker(QThread):
    """Runs a heavy bulletin computation off the UI thread (avoids freezing the
    window while a whole class is graded/ranked). Emits the callable's result."""

    done = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            self.done.emit(self._fn())
        except Exception as exc:
            AppLogger.error("BulletinGeneration", f"compute worker: {exc}")
            self.error.emit(str(exc))


class BulletinGenerationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Génération des Bulletins / إصدار الكشوف")
        self.setMinimumSize(1100, 700)
        self._arabic_font_warned = False
        self._worker: BulletinComputeWorker | None = None

        # تطبيق المظهر (Dark Mode أو Light Mode)
        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_filters()
        self.batch_results = []
        self._load_kpi_stats()

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return BulletinRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "bulletin_generation")
        self.btn_calc_batch.setEnabled(caps["can_write"])
        self.btn_calc_batch.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(16)

        # En-tête unifié
        header = ModuleHeaderWidget(
            icon="🖨️",
            title="BULLETINS & RÉSULTATS",
            subtitle="توليد الكشوف، لوحات الشرف، والنتائج السنوية",
        )
        self.layout.addWidget(header)
        self._stat_classes = header.add_stat("🏫", "Classes", "—", "#3B82F6")
        self._stat_students = header.add_stat("👨‍🎓", "Élèves", "—", "#22C55E")
        self._stat_generated = header.add_stat("📄", "Bulletins Générés", "—", "#8B5CF6")
        self._stat_honor = header.add_stat("🏆", "Tableau d'Honneur", "—", "#F59E0B")

        # KPI Cards

        # Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_batch_tab()
        self.setup_individual_tab()
        self.setup_honor_roll_tab()
        self.layout.addWidget(self.tabs)

    def create_card(self):
        return card_frame()

    def styled_combo(self):
        return styled_combo()

    def style_table(self, table):
        style_table(table)

    def _load_kpi_stats(self):
        """Charge les statistiques globales des bulletins."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Nombre de classes actives
                cursor.execute("SELECT COUNT(*) FROM Classes")
                classes = cursor.fetchone()[0] or 0
                # FIX 3a: schema uses status='Active', not is_active=TRUE
                cursor.execute("SELECT COUNT(*) FROM Students WHERE status = 'Active'")
                students = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COUNT(DISTINCT student_id) FROM Grades")
                generated = cursor.fetchone()[0] or 0
                # FIX 3b: COUNT(DISTINCT...) inside GROUP BY always returns 1 per group.
                # Use a subquery to count students whose per-student average >= 15.
                cursor.execute(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT student_id FROM Grades "
                    "  WHERE score IS NOT NULL "
                    "  GROUP BY student_id "
                    "  HAVING AVG(score) >= 15"
                    ") sub"
                )
                honor = cursor.fetchone()[0] or 0

            self._stat_classes.set_value(str(classes))
            self._stat_students.set_value(str(students))
            self._stat_generated.set_value(str(generated))
            self._stat_honor.set_value(str(honor))
        except Exception as e:
            AppLogger.error("BulletinGenerationWindow", f"Erreur KPI stats: {e}")

    def styled_spinbox(self, prefix="", min_val=0, max_val=1000):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        if prefix:
            spin.setPrefix(prefix)
        colors = ThemeManager.get_colors()
        spin.setStyleSheet(
            f"QSpinBox {{ padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; }}"
        )
        spin.setMinimumHeight(42)
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

        self.btn_calc_batch = QPushButton("1. Calculer & Aperçu")
        self.btn_calc_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calc_batch.setMinimumHeight(42)
        colors = ThemeManager.get_colors()
        self.btn_calc_batch.setStyleSheet(
            # FIX 5: Added missing comma between gradient stop values
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER}); color: white; font-weight: bold; padding: 10px; border-radius: 8px; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        self.btn_calc_batch.clicked.connect(self.calculate_batch_results)

        hlay.addWidget(QLabel("Classe:"))
        hlay.addWidget(self.combo_class_batch, 1)
        hlay.addWidget(QLabel("Période:"))
        hlay.addWidget(self.combo_period_batch, 1)
        hlay.addWidget(self.btn_calc_batch)
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
        btn_print_list.setMinimumHeight(42)
        btn_print_list.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {colors.PRIMARY}; font-weight: bold; padding: 10px 16px; border-radius: 8px; border: 1.5px solid {colors.PRIMARY}; }} QPushButton:hover {{ background-color: {colors.PRIMARY_LIGHT}; }}"
        )
        btn_print_list.clicked.connect(self.print_summary_list)

        btn_print_all = QPushButton("🖨️ Imprimer TOUS les Bulletins")
        btn_print_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_all.setMinimumHeight(46)
        btn_print_all.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS}, stop:1 #16A34A); color: white; padding: 12px; font-weight: bold; border-radius: 10px; border: none; }} QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
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
        btn_view.setMinimumHeight(42)
        colors = ThemeManager.get_colors()
        btn_view.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER}); color: white; font-weight: bold; padding: 10px; border-radius: 8px; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_view.clicked.connect(self.view_individual)

        btn_print = QPushButton("🖨️ Imprimer")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setMinimumHeight(46)
        btn_print.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS}, stop:1 #16A34A); color: white; font-weight: bold; padding: 10px; border-radius: 10px; border: none; }} QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
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
        info_frame.setStyleSheet(
            f"QFrame {{ background-color: {colors.BG_MAIN}; border-radius: 8px; border: 1px dashed {colors.BORDER}; }} QLabel {{ font-weight: bold; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}"
        )
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
        self.table_preview.setHorizontalHeaderLabels(
            [
                "Matière / المادة",
                "Évaluations / التقييم",
                "Coef",
                "Moyenne",
                "Points",
                "Appréciation / تقدير",
            ]
        )
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
        btn_calc.setMinimumHeight(42)
        colors = ThemeManager.get_colors()
        btn_calc.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SECONDARY}, stop:1 #0284C7); color: white; font-weight: bold; padding: 10px; border-radius: 8px; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_HOVER}; }}"
        )
        btn_calc.clicked.connect(self.calculate_honor_roll)

        hlay.addWidget(QLabel("Classe:"))
        hlay.addWidget(self.combo_class_honor, 1)
        hlay.addWidget(QLabel("Période:"))
        hlay.addWidget(self.combo_period_honor, 1)
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
        btn_cert.setMinimumHeight(46)
        btn_cert.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.WARNING}, stop:1 #D97706); color: white; padding: 12px; font-weight: bold; border-radius: 10px; border: none; }} QPushButton:hover {{ background: #B45309; }}"
        )
        btn_cert.clicked.connect(self.print_certificates)
        layout.addWidget(btn_cert)

        self.tabs.addTab(tab, "  🏆 Excellence / التميز  ")

    def load_filters(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = BulletinRepository(conn)
                active_year = repo.get_active_year_id()
                classes = repo.list_classes()
                periods = repo.list_periods_for_year(active_year) if active_year != -1 else repo.list_all_periods()

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
        if not class_id:
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                students = BulletinRepository(conn).list_active_students_in_class(class_id, active_year)
                for s in students:
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
                repo = BulletinRepository(conn)
                cycle_id = repo.get_cycle_id_for_class(class_id)
                if cycle_id is None:
                    return None
                active_year = repo.get_active_year_id()
                return repo.get_period_id_by_name(period_name, cycle_id, active_year)
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

        # Run the heavy compute (whole-class grades + ranking) off the UI thread so
        # the window stays responsive for large classes.
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.quit()
            self._worker.wait(3000)

        self.btn_calc_batch.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        calc = GradeCalculator()

        def _work():
            results = calc.get_student_averages(class_id, real_period_id, include_conduct=True)
            is_primary, max_score = calc.get_class_context(class_id)
            return calc, results, is_primary, max_score

        self._worker = BulletinComputeWorker(_work)
        self._worker.done.connect(self._on_batch_done)
        self._worker.error.connect(self._on_batch_error)
        self._worker.start()

    def _on_batch_done(self, payload):
        QApplication.restoreOverrideCursor()
        self.btn_calc_batch.setEnabled(True)
        calc, results, is_primary, max_score = payload
        self.batch_results = results
        class_size = len(results)

        self.table_batch.setRowCount(0)
        for row_data in results:
            idx = self.table_batch.rowCount()
            self.table_batch.insertRow(idx)
            self.table_batch.setItem(idx, 0, QTableWidgetItem(str(row_data['rank'])))
            self.table_batch.setItem(idx, 1, QTableWidgetItem(str(row_data.get('class_number') or "-")))
            self.table_batch.setItem(idx, 2, QTableWidgetItem(row_data['name']))
            self.table_batch.setItem(idx, 3, QTableWidgetItem(f"{row_data['general_average']:.2f}"))
            self.table_batch.setItem(idx, 4, QTableWidgetItem(calc.get_mention(row_data['general_average'], max_score)))
            self.table_batch.setItem(
                idx, 5, QTableWidgetItem(calc.get_decision(row_data['general_average'], is_primary, max_score))
            )
            row_data['class_size'] = class_size

    def _on_batch_error(self, msg):
        QApplication.restoreOverrideCursor()
        self.btn_calc_batch.setEnabled(True)
        QMessageBox.critical(self, "Erreur", f"Erreur de calcul: {msg}")

    def stop_background_workers(self) -> None:
        """Stop the compute worker before the shared DB pool closes (called by the
        main window on shutdown — this module is embedded, so closeEvent never fires)."""
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            worker.quit()
            worker.wait(3000)

    def print_summary_list(self):
        if _get_arabic_font_path() is None and not self._arabic_font_warned:
            QMessageBox.warning(
                self,
                "خط عربي غير موجود",
                "ضع خط عربي (TTF) داخل مجلد Fonts حتى تظهر العربية في التقارير.",
            )
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
                    school_info = BulletinRepository(conn).get_school_info()
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

                pdf.cell(
                    80,
                    3,
                    _prepare_pdf_text(republic) if font_name == "ArabicFont" else sanitize(republic),
                    0,
                    1,
                    'L',
                )
                pdf.cell(
                    80,
                    3,
                    _prepare_pdf_text(ia_text) if font_name == "ArabicFont" else sanitize(ia_text),
                    0,
                    1,
                    'L',
                )
                pdf.cell(
                    80,
                    3,
                    _prepare_pdf_text(ief_text) if font_name == "ArabicFont" else sanitize(ief_text),
                    0,
                    1,
                    'L',
                )
                pdf.cell(
                    80,
                    3,
                    _prepare_pdf_text(school_name) if font_name == "ArabicFont" else sanitize(school_name),
                    0,
                    1,
                    'L',
                )
                pdf.cell(
                    80,
                    3,
                    (
                        _prepare_pdf_text(f"Auto N: {auth_text}")
                        if font_name == "ArabicFont"
                        else sanitize(f"Auto N: {auth_text}")
                    ),
                    0,
                    1,
                    'L',
                )
                pdf.cell(
                    80,
                    3,
                    (
                        _prepare_pdf_text(f"Lieu: {addr_text}")
                        if font_name == "ArabicFont"
                        else sanitize(f"Lieu: {addr_text}")
                    ),
                    0,
                    1,
                    'L',
                )
                pdf.cell(
                    80,
                    3,
                    (
                        _prepare_pdf_text(f"Tel: {phone_text}")
                        if font_name == "ArabicFont"
                        else sanitize(f"Tel: {phone_text}")
                    ),
                    0,
                    1,
                    'L',
                )

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
            pdf.cell(0, 10, _prepare_pdf_text(title) if font_name == "ArabicFont" else sanitize(title), 0, 1, 'C')

            pdf.set_font(font_name, title_style, 9)
            pdf.set_fill_color(30, 58, 95)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(
                20,
                8,
                _prepare_pdf_text("Rang") if font_name == "ArabicFont" else sanitize("Rang"),
                1,
                0,
                'C',
                True,
            )
            pdf.cell(
                12,
                8,
                _prepare_pdf_text("N°") if font_name == "ArabicFont" else sanitize("N°"),
                1,
                0,
                'C',
                True,
            )
            pdf.cell(
                68,
                8,
                _prepare_pdf_text("Nom & Prénom") if font_name == "ArabicFont" else sanitize("Nom & Prénom"),
                1,
                0,
                'C',
                True,
            )
            pdf.cell(
                25,
                8,
                _prepare_pdf_text("Moyenne") if font_name == "ArabicFont" else sanitize("Moyenne"),
                1,
                0,
                'C',
                True,
            )
            pdf.cell(
                40,
                8,
                _prepare_pdf_text("Mention") if font_name == "ArabicFont" else sanitize("Mention"),
                1,
                0,
                'C',
                True,
            )
            pdf.cell(
                25,
                8,
                _prepare_pdf_text("Décision") if font_name == "ArabicFont" else sanitize("Décision"),
                1,
                1,
                'C',
                True,
            )

            pdf.set_font(font_name, '', 9)
            pdf.set_text_color(15, 23, 42)
            calc = GradeCalculator()
            class_id = self.combo_class_batch.currentData()
            is_primary, max_score = calc.get_class_context(class_id)
            class_size = len(self.batch_results)

            for idx, res in enumerate(self.batch_results):
                name_fr = sanitize(res['name'])
                name_ar = res.get('name_ar', '') or ""
                class_number = str(res.get('class_number') or "-")
                name = f"[{class_number}] {name_fr} / {name_ar}" if name_ar else f"[{class_number}] {name_fr}"
                name_out = _prepare_pdf_text(name) if font_name == "ArabicFont" else sanitize(name)
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
                pdf.cell(
                    40,
                    8,
                    _prepare_pdf_text(mention) if font_name == "ArabicFont" else sanitize(mention),
                    1,
                    0,
                    'C',
                    True,
                )
                pdf.cell(
                    25,
                    8,
                    _prepare_pdf_text(dec) if font_name == "ArabicFont" else sanitize(dec),
                    1,
                    1,
                    'C',
                    True,
                )

            class_slug = (
                "".join(
                    ch
                    for ch in (self.combo_class_batch.currentText() or "Toutes_Classes").replace(" ", "_")
                    if ch.isalnum() or ch in "-_"
                )
                or "Classe"
            )
            period_slug = (
                "".join(
                    ch
                    for ch in (self.combo_period_batch.currentText() or "Periode").replace(" ", "_")
                    if ch.isalnum() or ch in "-_"
                )
                or "Periode"
            )
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
            self.generate_bulletins(
                self.combo_class_indiv.currentData(), self.combo_period_indiv.currentText(), [std_id]
            )

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
                self.lbl_final_stats.setText(
                    f"Moyenne / معدل: {avg:.2f} | Rang / ترتيب: {rank}/{class_size} | Mention / تقدير: {mention}"
                )

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
            QMessageBox.warning(
                self,
                "خط عربي غير موجود",
                "ضع خط عربي (TTF) داخل مجلد Fonts حتى تظهر العربية في التقارير.",
            )
            self._arabic_font_warned = True
        real_period_id = self.get_real_period_id(class_id, period_name)
        if not real_period_id:
            QMessageBox.warning(self, "Erreur", "Période invalide.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Dossier de Sauvegarde")
        if not folder:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = BulletinRepository(conn)
                school_info = repo.get_school_info()
                # FIX 2: _get_period_year_id expects a BulletinRepository, not a raw cursor.
                # Passing cursor caused AttributeError on every batch bulletin print.
                year_id = GradeCalculator()._get_period_year_id(repo, real_period_id)
                year_label = repo.get_year_label(year_id) or repo.get_last_year_label() or "202X-202X"
                class_res = repo.get_class_names(class_id)
                class_name = (
                    f"{class_res[0]} / {class_res[1]}"
                    if class_res and class_res[1]
                    else (class_res[0] if class_res else "Classe")
                )

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

                if not full_data:
                    continue

                full_data['stats']['rank'] = std_rank_data['rank']

                pdf = BulletinPDF(school_info, period_name, year_label)
                pdf.draw_bulletin(full_data, class_name)

                student_name = (
                    full_data['info'][0] if full_data and full_data.get('info') else std_rank_data.get('name', 'Eleve')
                )
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
        self._honor_threshold = self.spin_threshold.value()

        if not pid:
            return

        # Whole-class compute off the UI thread (like the batch preview).
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.quit()
            self._worker.wait(3000)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        calc = GradeCalculator()

        def _work():
            all_results = calc.get_student_averages(cid, pid, include_conduct=True)
            _, max_s = calc.get_class_context(cid)
            return calc, all_results, max_s

        self._worker = BulletinComputeWorker(_work)
        self._worker.done.connect(self._on_honor_done)
        self._worker.error.connect(self._on_honor_error)
        self._worker.start()

    def _on_honor_done(self, payload):
        QApplication.restoreOverrideCursor()
        calc, all_results, max_s = payload
        self.honor_list = [s for s in all_results if s['rank'] <= self._honor_threshold]
        self.table_honor.setRowCount(0)
        for s in self.honor_list:
            idx = self.table_honor.rowCount()
            self.table_honor.insertRow(idx)
            self.table_honor.setItem(idx, 0, QTableWidgetItem(str(s['rank'])))
            name_ar = s.get('name_ar', '')
            display_name = f"{s['name']} / {name_ar}" if name_ar else s['name']
            self.table_honor.setItem(idx, 1, QTableWidgetItem(display_name))
            self.table_honor.setItem(idx, 2, QTableWidgetItem(f"{s['general_average']:.2f}"))
            self.table_honor.setItem(idx, 3, QTableWidgetItem(calc.get_mention(s['general_average'], max_s)))

    def _on_honor_error(self, msg):
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "Erreur", f"Erreur de calcul honor roll: {msg}")

    def print_certificates(self):
        if _get_arabic_font_path() is None and not self._arabic_font_warned:
            QMessageBox.warning(
                self,
                "خط عربي غير موجود",
                "ضع خط عربي (TTF) داخل مجلد Fonts حتى تظهر العربية في التقارير.",
            )
            self._arabic_font_warned = True
        if not hasattr(self, 'honor_list') or not self.honor_list:
            return
        folder = QFileDialog.getExistingDirectory(self, "Sauvegarder Certificats")
        if not folder:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = BulletinRepository(conn)
                school_info = repo.get_school_info()

                # Fetch active year from period
                cid = self.combo_class_honor.currentData()
                pname = self.combo_period_honor.currentText()
                pid = self.get_real_period_id(cid, pname)

                if pid:
                    # FIX 2: pass repo, not cursor (same bug as generate_bulletins)
                    year_id = GradeCalculator()._get_period_year_id(repo, pid)
                    year_label = repo.get_year_label(year_id) or "202X-202X"
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
                cert.create_certificate(
                    display_name, class_name, s['general_average'], s['rank'], mention, period_name=period_name
                )
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
