# خطة الترقية الاحترافية — El Malick Gest

**تاريخ الإعداد**: 15 مايو 2026  
**الحالة عند الإعداد**: 316 اختباراً ✅ | تغطية 16% | commit `2ec2950`

---

## نقطة الانطلاق — التقييم الحالي

| المجال | الدرجة | الملاحظة |
|---|---|---|
| معمارية الكود | 7.5/10 | Repository + Service Pattern ✅ |
| الأمان | 6.5/10 | config.ini غير محمي، لا rate limiting |
| تغطية الاختبارات | 4.0/10 | 16% فقط، UI = 0% |
| جودة الكود | 7.0/10 | 29 print()، 260 except Exception |
| قاعدة البيانات | 7.0/10 | لا Alembic، لا connection pooling |
| الـ API | 7.0/10 | لا API versioning، لا rate limiting |
| DevOps/CI-CD | 3.0/10 | لا GitHub Actions، لا pre-commit |
| **المجموع** | **6.0/10** | |

---

## المرحلة 1 — إصلاح الأمان الحرج 🔴

**الزمن المقدر: 1-2 أيام | الأولوية: عاجل**

### 1.1 حماية الأسرار من Git

- [ ] إضافة `config.ini` إلى `.gitignore`
- [ ] إنشاء `config.ini.example` بقيم وهمية كمرجع للمطورين
- [ ] إنشاء `.env.example` يوثق متغيرات البيئة المطلوبة
- [ ] التأكد من أن `ELMALICK_API_SECRET_KEY` و `DB_PASSWORD` تأتي من env vars فقط

**الملفات المتأثرة**: `.gitignore`, `config.ini`, `database_setup.py`, `api/auth.py`

### 1.2 تقييد CORS في الإنتاج

- [ ] تغيير `allow_origins="*"` ليقرأ من `ALLOWED_ORIGINS` env var
- [ ] توثيق القيمة الافتراضية لبيئة التطوير vs الإنتاج

**الملف المتأثر**: `api/main.py`

### 1.3 Rate Limiting للـ API

- [ ] تثبيت `slowapi`
- [ ] تطبيق حد 5 محاولات/دقيقة على `POST /api/auth/token`
- [ ] تطبيق حد 10 محاولات/دقيقة على `POST /api/parent/login`

**الملفات المتأثرة**: `api/main.py`, `api/auth.py`, `api/routes_parent.py`

### 1.4 استبدال print() بـ AppLogger

- [ ] `auto_backup.py` — 11 print()
- [ ] `config_manager.py` — 8 print()
- [ ] `validators.py` — 8 print()
- [ ] `app_logger.py` — 2 print()
- [ ] `first_run_wizard.py` — 2 print()

**المجموع**: 31 print() → AppLogger

---

## المرحلة 2 — CI/CD وجودة الكود التلقائية ✅ مكتملة

**منجزة في commit `60a7af4`**

### 2.1 GitHub Actions — CI Pipeline

- [x] إنشاء `.github/workflows/ci.yml`
- [x] يُشغَّل عند كل push وPR على `main`
- [x] خطوات: `pytest` → `flake8` → `black --check` → `mypy services/ repositories/`
- [ ] badge الحالة في README

### 2.2 GitHub Actions — Release Pipeline

- [x] إنشاء `.github/workflows/release.yml`
- [x] يُشغَّل عند إنشاء git tag (`v*`)
- [x] يبني PyInstaller ويرفع الـ artifact

### 2.3 Pre-commit Hooks

- [x] تثبيت `pre-commit`
- [x] إنشاء `.pre-commit-config.yaml`
- [x] Hooks: `black`, `isort`, `flake8`, `mypy` (على services فقط)
- [x] `pre-commit install` منفذ — hooks جاهزة

### 2.4 Type Hints الكاملة

- [ ] إضافة type hints لجميع repositories (حالياً 0)
- [ ] إضافة type hints لـ `database_setup.py`
- [ ] إضافة type hints لـ `config_manager.py`
- [ ] تفعيل `mypy` في وضع strict على `services/` و `repositories/`

---

## المرحلة 3 — قاعدة البيانات 🟡

**الزمن المقدر: 2-3 أيام | الأولوية: حرج لبيئة الإنتاج**

### 3.1 Alembic للـ Database Migrations

- [ ] تثبيت `alembic`
- [ ] تهيئة `alembic init alembic`
- [ ] ربط `env.py` بـ `DatabaseManager`
- [ ] توثيق الـ schema الحالي في migration أولى `001_initial_schema.py`
- [ ] توثيق كيفية الاستخدام في README

**الأوامر الأساسية**:

```bash
alembic revision --autogenerate -m "وصف التغيير"
alembic upgrade head       # تطبيق جميع migrations
alembic downgrade -1       # rollback خطوة واحدة
alembic history            # عرض السجل
```

### 3.2 Connection Pooling

- [ ] استبدال `psycopg2.connect()` بـ `ThreadedConnectionPool`
- [ ] pool_minconn=2, pool_maxconn=10
- [ ] أو الانتقال لـ `psycopg3` (يملك pool built-in)
- [ ] اختبار الأداء قبل/بعد

### 3.3 Database Health Check

- [ ] تحسين endpoint `/api/health` ليتحقق من connection time
- [ ] إضافة معلومات: عدد الجداول، حجم قاعدة البيانات، آخر backup

---

## المرحلة 4 — رفع تغطية الاختبارات 🟡

**الزمن المقدر: 4-5 أيام | الهدف: 16% → 60%**

### 4.1 اختبارات الـ API (أسرع كسب)

- [ ] `tests/test_api_auth.py` — اختبار login, token validation
- [ ] `tests/test_api_students.py` — list, get, grades, attendance, dues
- [ ] `tests/test_api_parent.py` — parent login, me, grades, attendance
- [ ] استخدام `TestClient` من FastAPI (لا server حقيقي مطلوب)

### 4.2 اختبارات الـ Repositories

- [ ] `tests/test_student_repo.py`
- [ ] `tests/test_finance_repo.py`
- [ ] `tests/test_attendance_repo.py`
- [ ] استخدام PostgreSQL test database أو fixtures

### 4.3 اختبارات الـ UI (pytest-qt)

- [ ] تثبيت `pytest-qt`
- [ ] `tests/test_login_ui.py` — نموذج الدخول، رسائل الخطأ
- [ ] `tests/test_validators_ui.py` — التحقق من المدخلات في النماذج

### 4.4 Mutation Testing

- [ ] تثبيت `mutmut`
- [ ] تشغيله على `services/` للتأكد من فاعلية الاختبارات
- [ ] هدف: mutation score ≥ 80% على الـ services

---

## المرحلة 5 — إعادة هيكلة المشروع 🟢

**الزمن المقدر: 3-4 أيام | الأولوية: جودة طويلة الأمد**

### 5.1 تفكيك الملفات الضخمة

| الملف الحالي | السطور | الهدف |
|---|---|---|
| `bulletin_generation.py` | 1525 | `bulletin_generator.py` + `bulletin_pdf.py` + `bulletin_data.py` |
| `student_management.py` | 1205 | `student_list.py` + `student_form.py` |
| `database_setup.py` | 918 | `db_manager.py` + `db_schema.py` |
| `admin_documents.py` | 999 | `documents_list.py` + `documents_editor.py` |

### 5.2 تنظيم هيكل المجلدات

```
El Malick Gest/
├── src/
│   ├── ui/              ← كل نوافذ PyQt6
│   ├── core/            ← business logic (services, validators)
│   ├── data/            ← repositories
│   └── api/             ← FastAPI
├── tests/
├── config/
│   ├── config.ini.example
│   └── .env.example
└── main.py
```

### 5.3 API Versioning

- [ ] تحويل `/api/students/` → `/api/v1/students/`
- [ ] إضافة deprecation headers على `/api/` القديمة
- [ ] توثيق خطة التوافق العكسي

---

## المرحلة 6 — المراقبة والتشخيص 🟢

**الزمن المقدر: 2-3 أيام | الأولوية: للإنتاج**

### 6.1 Structured JSON Logging

- [ ] تحويل `AppLogger` لينتج JSON logs
- [ ] إضافة حقول: `timestamp`, `level`, `module`, `user_id`, `duration_ms`
- [ ] دعم log rotation (حجم أقصى 10MB، الاحتفاظ بـ 7 أيام)

### 6.2 API Request Logging Middleware

- [ ] تسجيل كل طلب: method, path, status_code, duration_ms, user_id
- [ ] استثناء `/api/health` من التسجيل
- [ ] تنبيه عند الطلبات البطيئة (> 2 ثانية)

### 6.3 Sentry Integration (اختياري)

- [ ] تثبيت `sentry-sdk`
- [ ] تتبع الأخطاء تلقائياً في الإنتاج
- [ ] مجاني للمشاريع الصغيرة (< 5000 خطأ/شهر)

---

## خريطة الطريق الزمنية

```
الأسبوع 1    ████████ المرحلة 1: الأمان الحرج
الأسبوع 2    ████████ المرحلة 2: CI/CD + Pre-commit
الأسبوع 3    ████████ المرحلة 3: Alembic + Connection Pool
الأسبوع 4-5  ████████████████ المرحلة 4: رفع التغطية 16%→60%
الأسبوع 6-7  ████████████████ المرحلة 5: إعادة الهيكلة
الأسبوع 8    ████████ المرحلة 6: المراقبة
```

---

## الأهداف المقاسة

| المقياس | الآن | بعد المرحلة 1 | الهدف النهائي |
|---|---|---|---|
| تغطية الاختبارات | 16% | 16% | 60%+ |
| أمان الأسرار | ⚠️ | ✅ | ✅ |
| Schema migrations | ❌ | ❌ | ✅ Alembic |
| CI/CD | ❌ | ❌ | ✅ GitHub Actions |
| print() في الكود | 29 | 0 | 0 |
| Rate limiting | ❌ | ✅ | ✅ |
| درجة التقييم | 6.0/10 | 7.0/10 | 8.5/10 |

---

## سجل التنفيذ

| التاريخ | المرحلة | الإجراء | الحالة |
|---|---|---|---|
| 2026-05-15 | إعداد | إنشاء خطة الترقية | ✅ |
| | 1.1 | حماية config.ini | ⏳ |
| | 1.2 | تقييد CORS | ⏳ |
| | 1.3 | Rate Limiting | ⏳ |
| | 1.4 | استبدال print() | ⏳ |

---

*آخر تحديث: 2026-05-15 | الإصدار: 1.0*
