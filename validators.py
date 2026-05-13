"""
validators.py — طبقة التحقق المركزية
Centralized Validation Layer for El Malick Gest

الاستخدام / Usage:
    from validators import validate_student, validate_payment, format_errors

    errors = validate_student(data_dict)
    if errors:
        QMessageBox.warning(self, "خطأ", format_errors(errors))
        return
"""

from datetime import date
from typing import Optional


# ─────────────────────────────────────────────────────────────
# 1. الطلاب / Students
# ─────────────────────────────────────────────────────────────

def validate_student(data: dict) -> list[str]:
    """
    التحقق من بيانات الطالب قبل الحفظ.
    data: dict يحتوي على مفاتيح من جدول Students.
    العائد: قائمة رسائل الخطأ (فارغة = البيانات صحيحة).
    """
    errors: list[str] = []

    # الاسم الأول بالفرنسية
    if not str(data.get("first_name_fr", "")).strip():
        errors.append("الاسم الأول (FR) مطلوب / Prénom (FR) requis")

    # اسم العائلة بالفرنسية
    if not str(data.get("last_name_fr", "")).strip():
        errors.append("اسم العائلة (FR) مطلوب / Nom (FR) requis")

    # الاسم بالعربية (تحذير غير مانع)
    if not str(data.get("first_name_ar", "")).strip():
        errors.append("الاسم الأول (AR) مطلوب")

    # تاريخ الميلاد
    dob = data.get("birth_date")
    if dob is not None:
        if isinstance(dob, date) and dob > date.today():
            errors.append("تاريخ الميلاد لا يمكن أن يكون في المستقبل")
        if isinstance(dob, date) and dob.year < 1940:
            errors.append("تاريخ الميلاد غير منطقي (قبل 1940)")

    # الجنس
    gender = str(data.get("gender", "")).strip()
    if gender and gender not in ("M", "F", "Masculin", "Féminin", "ذكر", "أنثى"):
        errors.append(f"قيمة الجنس غير صالحة: '{gender}'")

    # بريد إلكتروني ولي الأمر (اختياري لكن يجب أن يكون صحيحاً)
    parent_email = str(data.get("parent_email", "")).strip()
    if parent_email and "@" not in parent_email:
        errors.append("البريد الإلكتروني لولي الأمر غير صالح")

    # هاتف ولي الأمر (اختياري)
    parent_phone = str(data.get("parent_phone", "")).strip()
    if parent_phone:
        clean_phone = parent_phone.replace("+", "").replace(" ", "").replace("-", "")
        if not clean_phone.isdigit():
            errors.append("رقم هاتف ولي الأمر يجب أن يحتوي على أرقام فقط")

    return errors


# ─────────────────────────────────────────────────────────────
# 2. الموظفون / Staff
# ─────────────────────────────────────────────────────────────

def validate_staff(data: dict) -> list[str]:
    """
    التحقق من بيانات الموظف قبل الحفظ.
    """
    errors: list[str] = []

    if not str(data.get("first_name", "")).strip():
        errors.append("الاسم الأول مطلوب / Prénom requis")

    if not str(data.get("last_name", "")).strip():
        errors.append("اسم العائلة مطلوب / Nom requis")

    role = str(data.get("role", "")).strip()
    if not role:
        errors.append("المنصب / الدور مطلوب")

    phone = str(data.get("phone", "")).strip()
    if phone:
        clean = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not clean.isdigit():
            errors.append("رقم الهاتف يجب أن يحتوي على أرقام فقط")

    email = str(data.get("email", "")).strip()
    if email and "@" not in email:
        errors.append("البريد الإلكتروني غير صالح")

    salary = data.get("salary_base", 0)
    if salary is not None:
        try:
            if float(salary) < 0:
                errors.append("الراتب لا يمكن أن يكون سالباً")
        except (ValueError, TypeError):
            errors.append("قيمة الراتب غير صالحة")

    return errors


# ─────────────────────────────────────────────────────────────
# 3. المدفوعات / Payments
# ─────────────────────────────────────────────────────────────

def validate_payment(data: dict) -> list[str]:
    """
    التحقق من بيانات الدفعة قبل التسجيل.
    data يجب أن يحتوي: amount_paid, وبشكل اختياري: total_due
    """
    errors: list[str] = []

    # التحقق من المبلغ
    amount_raw = data.get("amount_paid")
    if amount_raw is None:
        errors.append("مبلغ الدفع مطلوب / Montant requis")
        return errors

    try:
        amount = float(amount_raw)
    except (ValueError, TypeError):
        errors.append("مبلغ الدفع يجب أن يكون رقماً صحيحاً")
        return errors

    if amount <= 0:
        errors.append("مبلغ الدفع يجب أن يكون أكبر من صفر")

    # التحقق من عدم تجاوز المستحق
    total_due_raw = data.get("total_due")
    if total_due_raw is not None:
        try:
            total_due = float(total_due_raw)
            if amount > total_due * 1.01:  # هامش 1% للتقريب العشري
                errors.append(
                    f"المبلغ المدفوع ({amount:,.0f}) يتجاوز المستحق ({total_due:,.0f})"
                )
        except (ValueError, TypeError):
            pass  # إذا لم يكن total_due رقماً نتجاهل هذا الفحص

    # التحقق من نوع الدفع
    payment_type = str(data.get("payment_type", "")).strip()
    valid_types = ("Espèces", "Virement", "Chèque", "Mobile Money", "Autre", "")
    if payment_type and payment_type not in valid_types:
        errors.append(f"نوع الدفع غير معروف: '{payment_type}'")

    return errors


# ─────────────────────────────────────────────────────────────
# 4. الدرجات / Grades
# ─────────────────────────────────────────────────────────────

def validate_grade(data: dict) -> list[str]:
    """
    التحقق من درجة طالب قبل حفظها.
    data: {"score": float, "max_score": float (default 20)}
    """
    errors: list[str] = []

    score_raw = data.get("score")
    if score_raw is None or str(score_raw).strip() == "":
        errors.append("النقطة مطلوبة / Note requise")
        return errors

    try:
        score = float(score_raw)
    except (ValueError, TypeError):
        errors.append("النقطة يجب أن تكون رقماً")
        return errors

    try:
        max_score = float(data.get("max_score", 20))
    except (ValueError, TypeError):
        max_score = 20.0

    if not (0 <= score <= max_score):
        errors.append(f"النقطة يجب أن تكون بين 0 و{max_score:.0f} (القيمة: {score})")

    return errors


# ─────────────────────────────────────────────────────────────
# 5. كلمات المرور / Passwords
# ─────────────────────────────────────────────────────────────

def validate_password_strength(password: str, min_length: int = 8) -> list[str]:
    """
    التحقق من قوة كلمة المرور.
    العائد: قائمة رسائل الخطأ (فارغة = كلمة مرور قوية كافية).
    """
    errors: list[str] = []

    if not password:
        errors.append("كلمة المرور مطلوبة")
        return errors

    if len(password) < min_length:
        errors.append(f"كلمة المرور قصيرة (الحد الأدنى {min_length} أحرف)")

    if not any(c.isalpha() for c in password):
        errors.append("يجب أن تحتوي كلمة المرور على حرف واحد على الأقل")

    if not any(c.isdigit() for c in password):
        errors.append("يجب أن تحتوي كلمة المرور على رقم واحد على الأقل")

    return errors


# ─────────────────────────────────────────────────────────────
# 6. المستخدمون / Users
# ─────────────────────────────────────────────────────────────

def validate_user(data: dict, is_new: bool = True) -> list[str]:
    """
    التحقق من بيانات مستخدم النظام.
    is_new: True عند الإنشاء (يتحقق من كلمة المرور), False عند التعديل.
    """
    errors: list[str] = []

    username = str(data.get("username", "")).strip()
    if not username:
        errors.append("اسم المستخدم مطلوب")
    elif len(username) < 3:
        errors.append("اسم المستخدم قصير جداً (3 أحرف على الأقل)")
    elif not username.replace("_", "").replace(".", "").replace("-", "").isalnum():
        errors.append("اسم المستخدم يجب أن يحتوي على أحرف وأرقام فقط (مع _ . -)")

    email = str(data.get("email", "")).strip()
    if email and "@" not in email:
        errors.append("البريد الإلكتروني غير صالح")

    role = str(data.get("role", "")).strip()
    valid_roles = ("Admin", "Comptable", "Secretaire", "Pédagogique", "Prof")
    if role and role not in valid_roles:
        errors.append(f"الدور '{role}' غير معروف")

    if is_new:
        password = data.get("password", "")
        pass_errors = validate_password_strength(password)
        errors.extend(pass_errors)

    return errors


# ─────────────────────────────────────────────────────────────
# 7. المصروفات / Expenses
# ─────────────────────────────────────────────────────────────

def validate_expense(data: dict) -> list[str]:
    """التحقق من بيانات المصروف"""
    errors: list[str] = []

    amount_raw = data.get("amount")
    if amount_raw is None:
        errors.append("مبلغ المصروف مطلوب")
    else:
        try:
            amount = float(amount_raw)
            if amount <= 0:
                errors.append("مبلغ المصروف يجب أن يكون أكبر من صفر")
        except (ValueError, TypeError):
            errors.append("مبلغ المصروف يجب أن يكون رقماً")

    if not str(data.get("category", "")).strip():
        errors.append("فئة المصروف مطلوبة")

    if not str(data.get("description", "")).strip():
        errors.append("وصف المصروف مطلوب")

    return errors


# ─────────────────────────────────────────────────────────────
# 8. دوال مساعدة / Helpers
# ─────────────────────────────────────────────────────────────

def format_errors(errors: list[str], sep: str = "\n• ") -> str:
    """
    تحويل قائمة الأخطاء إلى نص جاهز للعرض في QMessageBox.

    مثال:
        errors = validate_student(data)
        if errors:
            QMessageBox.warning(self, "بيانات غير مكتملة", format_errors(errors))
    """
    if not errors:
        return ""
    return "• " + sep.join(errors)


def has_errors(*error_lists: list[str]) -> bool:
    """
    التحقق من وجود أخطاء في قوائم متعددة دفعة واحدة.

    مثال:
        if has_errors(student_errors, payment_errors):
            return
    """
    return any(bool(lst) for lst in error_lists)


# ─────────────────────────────────────────────────────────────
# اختبار مستقل / Standalone Test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from datetime import date

    print("=== اختبار validators.py ===\n")

    # طالب صحيح
    ok_student = {
        "first_name_fr": "Ahmed",
        "last_name_fr": "Ba",
        "first_name_ar": "أحمد",
        "birth_date": date(2010, 5, 15),
        "gender": "M",
    }
    errors = validate_student(ok_student)
    print(f"[طالب صحيح] أخطاء: {errors}")  # يجب أن يكون []

    # طالب بتاريخ مستقبلي
    bad_student = {"first_name_fr": "", "last_name_fr": "Ba",
                   "first_name_ar": "أحمد", "birth_date": date(2035, 1, 1)}
    errors = validate_student(bad_student)
    print(f"[طالب خاطئ] أخطاء: {errors}")

    # دفعة صحيحة
    ok_payment = {"amount_paid": 5000, "total_due": 10000}
    errors = validate_payment(ok_payment)
    print(f"[دفعة صحيحة] أخطاء: {errors}")  # يجب أن يكون []

    # دفعة تتجاوز المستحق
    bad_payment = {"amount_paid": 15000, "total_due": 10000}
    errors = validate_payment(bad_payment)
    print(f"[دفعة تتجاوز] أخطاء: {errors}")

    # درجة خارج النطاق
    bad_grade = {"score": 25, "max_score": 20}
    errors = validate_grade(bad_grade)
    print(f"[درجة خاطئة] أخطاء: {errors}")

    # كلمة مرور ضعيفة
    errors = validate_password_strength("abc")
    print(f"[كلمة مرور ضعيفة] أخطاء: {errors}")

    # كلمة مرور قوية
    errors = validate_password_strength("SecurePass123")
    print(f"[كلمة مرور قوية] أخطاء: {errors}")  # يجب أن يكون []

    print("\n✅ اختبار validators.py اكتمل")
