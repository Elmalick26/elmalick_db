# El Malick Gest — خطة التطوير الشاملة
>
> **المرجع الرسمي لمسار التطوير** — آخر تحديث: 08 مايو 2026
> لا تحذف هذا الملف. راجعه قبل كل مرحلة تطوير.

---

## الوضع الحالي للمشروع (نقطة الانطلاق)

### ✅ نقاط القوة المثبتة

| الجانب | التفاصيل |
|---|---|
| التغطية الوظيفية | ~75% من احتياجات K-12: طلاب، موظفون، حضور، درجات، مالية، وثائق، نسخ احتياطي |
| نظام الثيم | مركزي في `ui_styles.py` — Dark/Light، ألوان موحّدة، QSS متسق |
| طبقة DB | psycopg2 + Context Managers + Parameterized queries + SAVEPOINT |
| التسجيل | AppLogger موحّد مع وسوم الوحدات، ملفات يومية UTF-8 |
| الأمان الأساسي | bcrypt + auto-upgrade هاشات SHA256 القديمة + قفل بعد محاولات فاشلة |
| النسخ الاحتياطي | pg_dump SQL + احتفاظ 30 يوم + استعادة ذكية (PGDMP magic bytes) |
| الثنائية اللغوية | عربي/فرنسي في النصوص والخطوط (Amiri, Cairo, Noto Naskh) |

### ❌ نقاط الضعف المثبتة

| المشكلة | الأثر | الملف/السطر |
|---|---|---|
| كلمة مرور DB نصية في config.ini | خطر أمني واضح، password=2121 مكشوف | `config_manager.py` → `db_password` property |
| منطق الأعمال داخل QMainWindow | لا اختبارات، صعوبة الصيانة | `year_end_migration.py` lines 55-120 |
| لا Audit Log فعلي | جدول موجود لكن فارغ | `database_setup.py` جدول AuditLogs |
| لا validation مركزية | كل وحدة تتحقق بطريقتها | 20+ ملف |
| 30+ ملف في الجذر | صعوبة الملاحة | هيكل الـ workspace |
| لا اختبارات آلية | pytest مثبت لكن لا tests/ | غياب تام لـ test_*.py |
| لا First-Run Wizard | المستخدم يعدّل config.ini يدوياً | `config_manager.py` |
| default admin/admin غير مُجبر على التغيير | ثغرة أمنية عند الإنتاج | `login_window.py` |

---

## ملفات جديدة يُنشئها هذا المشروع

```
validators.py           ← طبقة التحقق المركزية (المرحلة 1.5)
first_run_wizard.py     ← معالج الإعداد الأول (المرحلة 1.2)
tests/
  __init__.py
  test_validators.py    ← (المرحلة 3)
  test_grade_service.py ← (المرحلة 3)
  test_finance_service.py
  test_auth.py
services/               ← (المرحلة 2)
  __init__.py
  grade_service.py
  finance_service.py
  migration_service.py
  attendance_service.py
repositories/           ← (المرحلة 2)
  __init__.py
  base_repo.py
  student_repo.py
  finance_repo.py
  grades_repo.py
  staff_repo.py
  attendance_repo.py
```

---

## المرحلة الأولى: التحصين والاستقرار (أسابيع 1–6)
>
> **الهدف:** نظام مقاوم للأخطاء، آمن، وجاهز للإنتاج

### 1.1 — تأمين بيانات الاعتماد (keyring) 🔐

**المشكلة:** `config.ini` يحتوي `password = 2121` بنص واضح.
**الحل:** حزمة `keyring` تخزّن في Windows Credential Manager.

**التغييرات المطلوبة في `config_manager.py`:**

```python
# استبدال property db_password بهذا الكود:
import keyring

KEYRING_SERVICE = "ElMalickGest"

@property
def db_password(self):
    # 1. تحقق من Windows Credential Manager أولاً
    stored = keyring.get_password(KEYRING_SERVICE, self.db_user)
    if stored:
        return stored
    # 2. fallback لمتغير البيئة (CI/CD)
    env_pass = os.environ.get("ELMALICK_DB_PASSWORD", "")
    if env_pass:
        return env_pass
    # 3. fallback للـ config.ini (فقط للتطوير المحلي)
    return self._config.get("DATABASE", "password", fallback="")

def set_db_password(self, password: str):
    """حفظ كلمة المرور في Keyring وحذفها من config.ini"""
    keyring.set_password(KEYRING_SERVICE, self.db_user, password)
    # حذف كلمة المرور من config.ini لأمان أفضل
    if self._config.has_option("DATABASE", "password"):
        self._config.remove_option("DATABASE", "password")
        self._save_config()
```

**التثبيت:**

```powershell
.venv\Scripts\pip.exe install keyring
```

**الترحيل (تُنفَّذ مرة واحدة عبر first_run_wizard.py):**

```python
# كود الترحيل من config.ini إلى keyring:
old_pass = config._config.get("DATABASE", "password", fallback="")
if old_pass and old_pass != "your_password_here":
    config.set_db_password(old_pass)
    # الآن حُذفت من config.ini وأصبحت في keyring
```

---

### 1.2 — معالج الإعداد الأول (first_run_wizard.py) 🧙

**متى يظهر:** عند أول تشغيل إذا لم تكن كلمة المرور في keyring، أو إذا `school_name == "El Malick School Management System"`.

**الخطوات:**

1. مرحبًا + شرح البرنامج
2. معلومات المدرسة (الاسم، الشعار، الموقع، الهاتف)
3. إعداد اتصال PostgreSQL (host, port, dbname, user, password) + **زر Test Connection**
4. إنشاء حساب المسؤول الأول بكلمة مرور قوية (تُطبَّق `validate_password`)
5. مسار النسخ الاحتياطي
6. ملخص + **زر إنهاء**

**الملف:** `first_run_wizard.py` — شاشة `QDialog` متعددة الخطوات (QStackedWidget).

**الاستدعاء من `main_dashbord.py`:**

```python
# قبل عرض نافذة تسجيل الدخول:
from first_run_wizard import should_run_wizard, FirstRunWizard
if should_run_wizard():
    wiz = FirstRunWizard()
    wiz.exec()
```

**`should_run_wizard()` تعيد `True` إذا:**

- `keyring.get_password("ElMalickGest", db_user)` فارغ و config.ini يحتوي كلمة مرور افتراضية
- أو اسم المدرسة لم يُعدَّل بعد

---

### 1.3 — Audit Log فعلي 📋

**الجدول موجود:** `AuditLogs(id, actor, action, target, timestamp)` — **لكنه فارغ حالياً**.

**الحل:** دالة مركزية في `database_setup.py` تُستدعى من كل CRUD حساس.

**الكود المضاف في `database_setup.py` (في نهاية الملف، قبل if **name**):**

```python
def log_audit(conn, actor: str, action: str, target: str) -> None:
    """
    تسجيل عملية في جدول AuditLogs.
    يجب استدعاؤها داخل نفس الاتصال المفتوح لضمان الـ atomicity.
    
    مثال:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Students ...", (...))
            log_audit(conn, "admin", "ADD_STUDENT", "Ahmed Ben Ali")
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO AuditLogs (actor, action, target) VALUES (%s, %s, %s)",
            (str(actor)[:100], str(action)[:100], str(target)[:200])
        )
    except Exception as e:
        # لا نوقف العملية بسبب فشل تسجيل الـ audit
        import logging
        logging.getLogger("DatabaseManager").warning(f"Audit log failed: {e}")
```

**أين تُستدعى:**

| الملف | الحدث | الاستدعاء |
|---|---|---|
| `login_window.py` | نجاح تسجيل الدخول | `log_audit(conn, user, "LOGIN", user)` |
| `login_window.py` | فشل تسجيل الدخول | `log_audit(conn, user, "LOGIN_FAILED", user)` |
| `student_management.py` | إضافة/تعديل/حذف طالب | `log_audit(conn, self.username, "ADD_STUDENT", name)` |
| `user_management.py` | إنشاء/تعديل/حذف مستخدم | `log_audit(conn, actor, "CREATE_USER", username)` |
| `finance_payments.py` | تسجيل دفعة | `log_audit(conn, actor, "PAYMENT", f"{student} - {amount} FCFA")` |
| `staff_management.py` | إضافة/تعديل موظف | `log_audit(conn, actor, "ADD_STAFF", name)` |

**ملاحظة:** يجب تمرير `self.username` (أو اسم المستخدم الحالي) إلى الوحدات المحتاجة له. حالياً النوافذ لا تستقبل اسم المستخدم — يُضاف كـ parameter في `__init__`.

---

### 1.4 — فرض تغيير كلمة المرور الافتراضية 🔒

**المشكلة:** النظام يحذّر عند استخدام admin/admin لكن لا يُجبر على التغيير.

**الحل في `login_window.py`:**

```python
# بعد التحقق الناجح من كلمة المرور، قبل self.accept():
if user == "admin" and security_utils.verify_password("admin", stored_hash):
    # فرض تغيير كلمة المرور قبل الدخول
    from PyQt6.QtWidgets import QInputDialog
    new_pass, ok = QInputDialog.getText(
        self, "تغيير كلمة المرور / Changer le mot de passe",
        "أنت تستخدم كلمة المرور الافتراضية.\nيجب تغييرها الآن:\n\nLe mot de passe par défaut doit être changé.\nNouveau mot de passe:",
        QLineEdit.EchoMode.Password
    )
    if ok and new_pass:
        valid, msg = security_utils.validate_password(new_pass)
        if valid:
            new_hash = security_utils.hash_password(new_pass)
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE Users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
                conn.commit()
        else:
            QMessageBox.warning(self, "كلمة المرور ضعيفة", msg)
            return  # لا يكمل الدخول
    else:
        return  # المستخدم ألغى — لا يدخل
```

---

### 1.5 — Validation Layer مركزية (validators.py) ✅

**الملف:** `validators.py` — **منشأ فعلياً في هذا المشروع**

```python
# validators.py
from datetime import date
from typing import Optional

def validate_student(data: dict) -> list[str]:
    errors = []
    if not str(data.get("first_name_fr", "")).strip():
        errors.append("الاسم الأول (FR) مطلوب")
    if not str(data.get("last_name_fr", "")).strip():
        errors.append("اسم العائلة (FR) مطلوب")
    if not str(data.get("first_name_ar", "")).strip():
        errors.append("الاسم الأول (AR) مطلوب")
    dob = data.get("birth_date")
    if dob and isinstance(dob, date) and dob > date.today():
        errors.append("تاريخ الميلاد لا يمكن أن يكون في المستقبل")
    gender = data.get("gender", "")
    if gender and gender not in ("M", "F", "Masculin", "Féminin"):
        errors.append("الجنس غير صالح")
    return errors

def validate_staff(data: dict) -> list[str]:
    errors = []
    if not str(data.get("first_name", "")).strip():
        errors.append("الاسم الأول مطلوب")
    if not str(data.get("last_name", "")).strip():
        errors.append("اسم العائلة مطلوب")
    if not str(data.get("role", "")).strip():
        errors.append("المنصب مطلوب")
    phone = str(data.get("phone", "")).strip()
    if phone and not phone.replace("+", "").replace(" ", "").replace("-", "").isdigit():
        errors.append("رقم الهاتف غير صالح")
    email = str(data.get("email", "")).strip()
    if email and "@" not in email:
        errors.append("البريد الإلكتروني غير صالح")
    return errors

def validate_payment(data: dict) -> list[str]:
    errors = []
    amount = data.get("amount_paid", 0)
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        errors.append("مبلغ الدفع يجب أن يكون رقماً")
        return errors
    if amount <= 0:
        errors.append("مبلغ الدفع يجب أن يكون أكبر من صفر")
    if data.get("total_due") is not None:
        try:
            total = float(data["total_due"])
            if amount > total * 1.01:  # هامش 1% للتقريب
                errors.append(f"المبلغ المدفوع ({amount:.0f}) أكبر من المستحق ({total:.0f})")
        except (ValueError, TypeError):
            pass
    return errors

def validate_grade(data: dict) -> list[str]:
    errors = []
    score = data.get("score")
    if score is None:
        errors.append("النقطة مطلوبة")
        return errors
    try:
        score = float(score)
    except (ValueError, TypeError):
        errors.append("النقطة يجب أن تكون رقماً")
        return errors
    max_score = float(data.get("max_score", 20))
    if not (0 <= score <= max_score):
        errors.append(f"النقطة يجب أن تكون بين 0 و{max_score:.0f}")
    return errors

def validate_password_strength(password: str, min_length: int = 8) -> list[str]:
    errors = []
    if len(password) < min_length:
        errors.append(f"كلمة المرور قصيرة (الحد الأدنى {min_length} أحرف)")
    if not any(c.isalpha() for c in password):
        errors.append("يجب أن تحتوي كلمة المرور على حرف واحد على الأقل")
    if not any(c.isdigit() for c in password):
        errors.append("يجب أن تحتوي كلمة المرور على رقم واحد على الأقل")
    return errors

def format_errors(errors: list[str], sep: str = "\n• ") -> str:
    """تحويل قائمة الأخطاء إلى نص جاهز للعرض في QMessageBox"""
    if not errors:
        return ""
    return "• " + sep.join(errors)
```

---

## المرحلة الثانية: إعادة الهيكلة المعمارية (أسابيع 7–16)
>
> **الهدف:** فصل المسؤوليات — UI / Business Logic / Data Access

### 2.1 — هيكل المجلدات المستهدف

```
El Malick Gest/
├── core/                    # البنية التحتية (تُنقل هنا)
│   ├── __init__.py
│   ├── database_setup.py
│   ├── config_manager.py
│   ├── app_logger.py
│   ├── db_path.py
│   └── security_utils.py
│
├── repositories/            # طبقة الوصول إلى البيانات
│   ├── __init__.py
│   ├── base_repo.py         # منطق مشترك (get_active_year, etc.)
│   ├── student_repo.py
│   ├── finance_repo.py
│   ├── grades_repo.py
│   ├── staff_repo.py
│   └── attendance_repo.py
│
├── services/                # منطق الأعمال (Business Logic)
│   ├── __init__.py
│   ├── grade_service.py
│   ├── migration_service.py
│   ├── finance_service.py
│   ├── attendance_service.py
│   └── backup_service.py
│
├── ui/                      # الواجهات
│   ├── windows/             # النوافذ الرئيسية
│   ├── dialogs/             # حوارات مخصصة
│   └── widgets/             # عناصر مشتركة
│
├── tests/                   # الاختبارات
│   ├── __init__.py
│   ├── test_validators.py
│   ├── test_grade_service.py
│   └── test_finance_service.py
│
├── validators.py            # (مرحلة 1 — يبقى في الجذر مؤقتاً)
├── first_run_wizard.py      # (مرحلة 1)
└── main_dashbord.py         # نقطة الدخول (يبقى دائماً في الجذر)
```

### 2.2 — Repository Pattern (مثال: student_repo.py)

```python
# repositories/student_repo.py
class StudentRepository:
    def __init__(self, conn):
        self._conn = conn

    def get_active_in_class(self, year_id: int, class_id: int) -> list[dict]:
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT S.id, S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar,
                   SCN.class_number
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE S.status = 'Active' AND SCN.year_id = %s AND SCN.class_id = %s
            ORDER BY S.last_name_fr, S.first_name_fr
        """, (year_id, class_id))
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_by_id(self, student_id: int) -> dict | None:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM Students WHERE id = %s", (student_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    
    def search(self, query: str, year_id: int = None) -> list[dict]:
        cursor = self._conn.cursor()
        pattern = f"%{query}%"
        sql = """
            SELECT S.id, S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar
            FROM Students S
            WHERE (S.first_name_fr ILIKE %s OR S.last_name_fr ILIKE %s
                   OR S.first_name_ar ILIKE %s OR S.last_name_ar ILIKE %s)
              AND S.status = 'Active'
        """
        params = [pattern, pattern, pattern, pattern]
        if year_id:
            sql += " AND EXISTS (SELECT 1 FROM StudentClassNumbers SCN WHERE SCN.student_id=S.id AND SCN.year_id=%s)"
            params.append(year_id)
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
```

### 2.3 — Service Layer (مثال: grade_service.py)

```python
# services/grade_service.py
class GradeService:
    
    def calculate_period_average(self, scores: list[tuple[float, float]]) -> float:
        """
        scores: قائمة من (score, coefficient)
        العائد: المعدل المرجّح
        """
        total_pts = sum(s * c for s, c in scores if s is not None)
        total_coef = sum(c for s, c in scores if s is not None)
        return round(total_pts / total_coef, 2) if total_coef > 0 else 0.0

    def calculate_annual_average(self, period_averages: list[float]) -> float:
        if not period_averages:
            return 0.0
        return round(sum(period_averages) / len(period_averages), 2)

    def get_promotion_decision(self, average: float, cycle_name: str) -> str:
        """قرار الترحيل السنوي بناءً على المعدل والمرحلة الدراسية"""
        cycle_lower = (cycle_name or "").lower()
        is_primary = any(k in cycle_lower for k in ["elem", "prim", "ibtida", "élémen"])
        threshold = 5.0 if is_primary else 10.0
        return "Admis" if average >= threshold else "Redouble"

    def get_honor_mention(self, average: float) -> str:
        if average >= 18: return "Excellent"
        if average >= 16: return "Très Bien"
        if average >= 14: return "Bien"
        if average >= 12: return "Assez Bien"
        if average >= 10: return "Passable"
        return "Insuffisant"
    
    def rank_students(self, students: list[dict]) -> list[dict]:
        """
        students: قائمة من dicts تحتوي على 'id' و'average'
        العائد: نفس القائمة مع إضافة حقل 'rank'
        """
        sorted_students = sorted(students, key=lambda x: x.get("average", 0), reverse=True)
        for i, student in enumerate(sorted_students, 1):
            student["rank"] = i
        return sorted_students
```

### 2.4 — خطة نقل الكود

| الخطوة | ما يُفعل | الملف المصدر → الوجهة |
|---|---|---|
| أ | نسخ منطق حساب المعدل | `year_end_migration.py` lines 55-100 → `services/grade_service.py` |
| ب | نسخ استعلامات الطلاب | `student_management.py` → `repositories/student_repo.py` |
| ج | نسخ استعلامات المالية | `finance_payments.py` + `finance_dashboard.py` → `repositories/finance_repo.py` |
| د | تحديث النوافذ لاستخدام الـ repos | استبدال SQL المباشر بـ `StudentRepository(conn).get_active_in_class(...)` |
| هـ | اختبار كل وحدة بعد الترحيل | تشغيل `python main_dashbord.py` وفحص كل شاشة |

**ملاحظة هامة:** الترحيل يجب أن يكون **تدريجياً** — وحدة بوحدة — وليس دفعة واحدة.

---

## المرحلة الثالثة: جودة الكود والاختبارات (أسابيع 17–22)
>
> **الهدف:** شبكة أمان تمنع الانحدار عند كل تعديل

### pytest موجود + pytest-qt + pytest-cov ✅

### الاختبارات الأساسية المطلوبة

```python
# tests/test_validators.py
from validators import validate_student, validate_payment, validate_grade
from datetime import date

def test_student_missing_name():
    errors = validate_student({"first_name_fr": "", "last_name_fr": "Diallo"})
    assert any("الاسم الأول" in e for e in errors)

def test_student_future_birthdate():
    errors = validate_student({
        "first_name_fr": "Ahmed", "last_name_fr": "Ba",
        "first_name_ar": "أحمد", "birth_date": date(2030, 1, 1)
    })
    assert any("مستقبل" in e for e in errors)

def test_payment_negative_amount():
    errors = validate_payment({"amount_paid": -100})
    assert len(errors) > 0

def test_payment_exceeds_due():
    errors = validate_payment({"amount_paid": 50000, "total_due": 10000})
    assert len(errors) > 0

def test_grade_out_of_range():
    errors = validate_grade({"score": 25, "max_score": 20})
    assert len(errors) > 0
```

```python
# tests/test_grade_service.py
from services.grade_service import GradeService

class TestGradeService:
    def setup_method(self): self.svc = GradeService()

    def test_passing_secondary(self):
        assert self.svc.get_promotion_decision(10.5, "Collège") == "Admis"

    def test_failing_secondary(self):
        assert self.svc.get_promotion_decision(9.9, "Collège") == "Redouble"

    def test_passing_primary_lower_threshold(self):
        assert self.svc.get_promotion_decision(5.0, "Élémentaire") == "Admis"

    def test_honor_mention_excellent(self):
        assert self.svc.get_honor_mention(18.5) == "Excellent"

    def test_weighted_average(self):
        # مادة بمعامل 3 ومادة بمعامل 1
        avg = self.svc.calculate_period_average([(15, 3), (10, 1)])
        assert avg == 13.75

    def test_rank_students(self):
        students = [{"id": 1, "average": 14}, {"id": 2, "average": 16}, {"id": 3, "average": 12}]
        ranked = self.svc.rank_students(students)
        assert ranked[0]["id"] == 2  # الأعلى معدلاً
        assert ranked[0]["rank"] == 1
```

### تشغيل الاختبارات

```powershell
# من مجلد المشروع:
.venv\Scripts\pytest.exe tests/ -v --tb=short
# مع تغطية الكود:
.venv\Scripts\pytest.exe tests/ --cov=. --cov-report=html
```

---

## المرحلة الرابعة: تحسينات وظيفية عالية القيمة (أسابيع 23–32)
>
> **الهدف:** ميزات تغير تجربة المدرسة يومياً

### 4.1 — مركز التنبيهات الذكي

بطاقة تظهر في لوحة التحكم الرئيسية تعرض:

- طلاب بنسبة غياب > 20% (من `StudentAttendance`)
- مستحقات متأخرة > 30 يوم (من `StudentDues` حيث `is_paid=0 AND due_date < today`)
- طلاب بمعدل < 8 في الفصل الحالي (من `Grades`)
- موظفون بطلبات إجازة معلقة (من `StaffLeaves WHERE status='En Attente'`)

```sql
-- استعلام تنبيهات الغياب:
SELECT S.first_name_fr || ' ' || S.last_name_fr, 
       COUNT(*) FILTER (WHERE SA.status='Absent') * 100.0 / COUNT(*) as absence_rate
FROM Students S
JOIN StudentAttendance SA ON S.id = SA.student_id
WHERE SA.year_id = %s
GROUP BY S.id, S.first_name_fr, S.last_name_fr
HAVING COUNT(*) FILTER (WHERE SA.status='Absent') * 100.0 / COUNT(*) > 20
```

### 4.2 — استيراد جماعي Excel/CSV

- نافذة `ImportWizard` تقبل ملف Excel/CSV
- معاينة الأعمدة + Mapping (أي عمود يقابل أي حقل)
- تحقق عبر `validators.py` لكل صف
- تقرير نتيجة الاستيراد: X تم، Y أخفق مع الأسباب

```python
# استخدام openpyxl (مثبت):
import openpyxl
wb = openpyxl.load_workbook(filepath)
ws = wb.active
for row in ws.iter_rows(min_row=2, values_only=True):
    data = {"first_name_fr": row[0], "last_name_fr": row[1], ...}
    errors = validate_student(data)
    if not errors:
        # INSERT ...
    else:
        failed_rows.append((row, errors))
```

### 4.3 — بحث عالمي Ctrl+K

نافذة `GlobalSearchDialog` تُفعَّل بـ `Ctrl+K` من أي مكان في التطبيق:

```python
# في main_dashbord.py:
from PyQt6.QtGui import QShortcut, QKeySequence
shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
shortcut.activated.connect(self.open_global_search)
```

تبحث في: Students (الاسم FR/AR)، Staff، Payments (رقم الوصل)، AuditLogs.

### 4.4 — تحسين Dashboard

إضافة بطاقات KPI تُحدَّث كل 5 دقائق:

- نسبة الحضور اليوم (حاضر/إجمالي)
- المستحقات غير المسددة هذا الشهر
- آخر 5 عمليات مالية
- عدد طلبات الإجازة المعلقة

---

## المرحلة الخامسة: قابلية التوسع والـ API (أسابيع 33–48)
>
> **الهدف:** تجاوز حدود Desktop-only

### 5.1 — REST API (FastAPI)

```python
# api/main.py
from fastapi import FastAPI, Depends
from services.grade_service import GradeService
from repositories.student_repo import StudentRepository

app = FastAPI(title="El Malick Gest API")

@app.get("/students/{student_id}/summary")
def get_student_summary(student_id: int, year_id: int):
    # نفس الخدمة المستخدمة في PyQt
    with DatabaseManager() as db:
        conn = db.get_connection()
        repo = StudentRepository(conn)
        student = repo.get_by_id(student_id)
        ...
    return student
```

**التثبيت:**

```powershell
.venv\Scripts\pip.exe install fastapi uvicorn
```

### 5.2 — بوابة أولياء الأمور

واجهة ويب خفيفة (HTML/JS أو React) تُقدَّم عبر FastAPI:

- `/parent/login` — دخول عبر `student_code` ثابت (EMG-XXXX) + رمز PIN
- `/parent/grades` — درجات الفصل الحالي
- `/parent/attendance` — الحضور والغياب
- `/parent/dues` — المستحقات المالية

#### تحديث التنفيذ الميداني (08 مايو 2026)

- ✅ 5.1 منفذة: FastAPI + JWT + مسارات API فعالة في بيئة العمل.
- ✅ 5.2 منفذة: بوابة أولياء فعالة مع تسجيل دخول عبر `student_code` بدل الرقم غير الثابت.
- ✅ تأمين PIN عبر `bcrypt` مع ترقية تلقائية للبيانات القديمة (plain PIN -> hash).
- ✅ تكامل واجهات العرض: إظهار "Code Accès" في بطاقات الطالب وجداول الإدارة وتقارير الطباعة.
- ✅ حزمة QA الآلية لبوابة الأولياء: `7 passed` (اختبارات الانحدار + E2E).
- ✅ مرجع الإغلاق اليدوي للـ QA: راجع `QA_PHASE5_MANUAL_CHECKLIST.md`.
- ✅ سجل الإغلاق النهائي للمرحلة: راجع `QA_PHASE5_SIGNOFF.md`.
- 🟡 المتبقي قبل الإغلاق النهائي: QA يدوي سريع (واجهة PyQt + تنسيق PDF).

### 5.3 — SSL للاتصال بقاعدة البيانات

```python
# في database_setup.py:
conn = psycopg2.connect(
    host=self.config.db_host,
    port=self.config.db_port,
    dbname=self.config.db_name,
    user=self.config.db_user,
    password=self.config.db_password,
    sslmode="require"  # ← إضافة هذا في الإنتاج
)
```

### 5.4 — دعم متعدد المدارس

إضافة `school_id INTEGER` إلى الجداول الرئيسية:

- `Students`, `Staff`, `Payments`, `AcademicYears`, `Classes`
- مع Row-Level Security في PostgreSQL

---

## جدول التنفيذ الإجمالي

| الأسابيع | المرحلة | الأولوية |
|---|---|---|
| 1–2 | 1.3 Audit Log + 1.5 validators.py | 🔴 الأعلى |
| 3–4 | 1.1 Keyring + 1.2 First-Run Wizard | 🔴 عالية |
| 5–6 | 1.4 فرض تغيير كلمة المرور | 🟡 متوسطة |
| 7–10 | 2.1-2.2 إنشاء repositories/ | 🔴 عالية |
| 11–14 | 2.3 إنشاء services/ | 🔴 عالية |
| 15–16 | 2.4 ترحيل تدريجي للوحدات | 🟡 متوسطة |
| 17–20 | 3. اختبارات validators + services | 🔴 عالية |
| 21–22 | 3. CI Pre-commit hooks | 🟢 منخفضة |
| 23–26 | 4.1 مركز التنبيهات | 🔴 عالية |
| 27–28 | 4.2 استيراد Excel/CSV | 🟡 متوسطة |
| 29–30 | 4.3 بحث عالمي Ctrl+K | 🟢 منخفضة |
| 31–32 | 4.4 تحسين Dashboard | 🟡 متوسطة |
| 33–40 | 5.1-5.2 FastAPI + بوابة الأولياء (✅ منجز فعليًا) | 🟢 منخفضة |
| 41–48 | 5.3-5.4 SSL + Multi-school | 🟢 مستقبلية |

---

## مؤشرات النجاح

| المؤشر | الآن | بعد M1 | بعد M2 | بعد M3 | بعد M5 |
|---|---|---|---|---|---|
| تغطية الاختبارات | 0% | 0% | 0% | 60% | 80% |
| طبقات المعمارية | 1 مختلطة | 1 + audit | 3 منفصلة | 3 + tests | 4 + API |
| أمان بيانات الاعتماد | نص عادي | Keyring | Keyring | Keyring | Keyring + SSL |
| وقت استيعاب مطور جديد | أيام | أيام | ساعات | ساعة | ساعة |
| قنوات الوصول | Desktop | Desktop | Desktop | Desktop | Desktop + ويب |

---

## ملاحظات تقنية هامة

- **الترقيم النسبي:** جميع استعلامات PostgreSQL تستخدم `%s` لا `?`
- **ILIKE بدل LIKE:** دائماً للبحث النصي (case-insensitive)
- **SAVEPOINT:** عند الـ migrations لحماية الـ transaction الرئيسي
- **BOM:** `bulletin_generation.py` يحتوي BOM في أوله — استخدم `utf-8-sig` عند القراءة
- **AppLogger:** `AppLogger.info/warning/error("ModuleName", "message")` — لا print
- **القاموس:** `ThemeManager.get_colors()` وليس `Colors()` المباشر في الوحدات

---

آخر مراجعة: 08 مايو 2026 — El Malick Gest v1.0 → v2.0 Roadmap
