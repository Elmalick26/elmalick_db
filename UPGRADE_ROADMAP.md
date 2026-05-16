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

### 2.4 Type Hints الكاملة ✅

- [x] إضافة type hints لجميع repositories (حالياً 0)
- [x] إضافة type hints لـ `database_setup.py`
- [x] إضافة type hints لـ `config_manager.py`
- [x] تفعيل `mypy` على `services/` و `repositories/` — `27 source files` بدون أخطاء

---

## المرحلة 3 — قاعدة البيانات ✅ مكتملة

**منجزة في commits `1df6d20` (3.1) و `<next>` (3.2/3.3)**

### 3.1 Alembic للـ Database Migrations ✅

- [x] تثبيت `alembic==1.13.1`
- [x] تهيئة `alembic init alembic`
- [x] ربط `env.py` بـ `ConfigManager` (قراءة كلمة المرور من keyring)
- [x] توثيق الـ schema الحالي في `alembic/versions/001_initial_schema.py` (30 جدول)
- [x] أوامر: `alembic history`, `alembic upgrade head`, `alembic downgrade -1`

### 3.2 Connection Pooling ✅

- [x] استبدال `psycopg2.connect()` بـ `ThreadedConnectionPool`
- [x] pool_minconn=2, pool_maxconn=10
- [x] Singleton على مستوى الـ class — مشترك بين جميع الـ instances
- [x] `close_pool()` عند إغلاق التطبيق في `main_dashbord.py`
- [x] `reset_pool()` لإعادة الإنشاء عند تغيير الإعدادات

### 3.3 Database Health Check ✅

- [x] تحسين endpoint `/api/health` ليتحقق من connection time
- [x] إضافة معلومات: عدد الجداول، حجم قاعدة البيانات، آخر backup
- [x] إضافة `/api/v1/health` كـ canonical route مع إبقاء `/api/health` للتوافق

---

## المرحلة 4 — رفع تغطية الاختبارات ✅

**التغطية: 7% → 63% (570 اختبار) | الهدف: 60%+ ✅ محقق**

### 4.1 اختبارات الـ API (أسرع كسب) ✅

- [x] `tests/test_api_endpoints.py` — login, token, students routes, parent portal (31 اختبار)
  - `api/auth.py` → 79% | `api/routes_students.py` → 84% | `api/routes_parent.py` → 76%
- [x] استخدام `TestClient` من FastAPI (لا server حقيقي مطلوب)

### 4.2 اختبارات الـ Repositories ✅

- [x] `tests/test_small_repos.py` — UserRepository (100%) + GlobalSearchRepository (83%)
- [x] `tests/test_security_utils.py` — security_utils.py (69%)
- [x] `tests/test_student_repo.py` — StudentRepository (93%)
- [x] `tests/test_repos_phase4b.py` — LoginRepository, AttendanceRepository, GradesRepository, StaffRepository (89 اختبار)
  - `repositories/login_repo.py` → 98% | `repositories/attendance_repo.py` → 95%
  - `repositories/grades_repo.py` → 92% | `repositories/staff_repo.py` → 94%

### 4.3 اختبارات الـ UI (pytest-qt)

- [ ] تثبيت `pytest-qt`
- [ ] `tests/test_login_ui.py` — نموذج الدخول، رسائل الخطأ
- [ ] `tests/test_validators_ui.py` — التحقق من المدخلات في النماذج

### 4.4 Mutation Testing ✅

- [x] تثبيت `mutatest` (بديل `mutmut` — أسرع وأكثر استقراراً)
- [x] تشغيله على `services/` — 7 mutations باقية → 7 اختبارات جديدة لقتلها
- [x] mutation score: 100% على `services/` (جميع الـ mutations مقتولة)

---

## المرحلة 5 — إعادة هيكلة المشروع ✅ (جزئي)

**المنجز: 5.1 + 5.3 | المتبقي: 5.2 (تنظيم المجلدات)**

### 5.1 تفكيك الملفات الضخمة ✅

| الملف | قبل | بعد | |
|---|---|---|---|
| `database_setup.py` | 1063 سطر | **36 سطر** (shim) | ✅ مُنجز |
| `db_manager.py` | — | **130 سطر** (pool + context manager) | ✅ جديد |
| `db_schema.py` | — | **903 سطر** (DDL schema) | ✅ جديد |
| `bulletin_generation.py` | 1525 | — | ⏸ مؤجل (UI/PyInstaller) |
| `student_management.py` | 1205 | — | ⏸ مؤجل (UI/PyInstaller) |

### 5.2 تنظيم هيكل المجلدات

- [ ] نقل UI files إلى `src/ui/`
- [ ] نقل repositories إلى `src/data/`
- [ ] تحديث جميع الـ imports

### 5.3 API Versioning ✅

- [x] تحويل `/api/students/` → `/api/v1/students/` (canonical)
- [x] `/api/auth/`, `/api/parent/` → `/api/v1/auth/`, `/api/v1/parent/`
- [x] إضافة `Deprecation: true` + `Sunset` + `Link` headers على `/api/` القديمة
- [x] اختبارات: deprecation header present on legacy, absent on v1 (5 tests)

---

## المرحلة 6 — المراقبة والتشخيص ✅

**المنجز في commit `phase6` | 481 اختبار ✅**

### 6.1 Structured JSON Logging ✅

- [x] تحويل `AppLogger` لينتج JSON logs (`JSONLogFormatter`)
- [x] إضافة حقول: `timestamp`, `level`, `module`, `user_id`, `duration_ms`
- [x] دعم log rotation (حجم أقصى 10MB، الاحتفاظ بـ 7 نسخ — `RotatingFileHandler`)

### 6.2 API Request Logging Middleware ✅

- [x] تسجيل كل طلب: method, path, status_code, duration_ms, user_id
- [x] استثناء `/api/health` من التسجيل
- [x] تنبيه WARNING عند الطلبات البطيئة (> 2000ms)
- [x] `extract_token_subject()` لاستخراج user_id من JWT
- [x] 26 اختبار جديد في `tests/test_logging_phase6.py`

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
| 2026-05-15 | 1.1–1.4 | الأمان الحرج (CORS, Rate Limiting, secrets, print→AppLogger) | ✅ commit `9983665` |
| 2026-05-15 | 2.1–2.3 | CI/CD + pre-commit hooks | ✅ commit `60a7af4` |
| 2026-05-15 | 3.1–3.2 | Alembic + Connection Pooling | ✅ |
| 2026-05-15 | 5.1 | تفكيك `database_setup.py` | ✅ |
| 2026-05-15 | 5.3 | API v1 versioning + Deprecation headers | ✅ |
| 2026-05-15 | 6.1–6.2 | JSON Logging + Request Middleware | ✅ |
| 2026-05-15 | 4.1–4.3 | رفع التغطية 16%→63% (577 اختبار) | ✅ |
| 2026-05-15 | 4.4 | Mutation testing — 7/7 mutations killed | ✅ commit `6345fb8` |
| 2026-05-16 | 2.4 | Type hints لجميع repositories + database_setup + config_manager | ✅ commit `25a0f67` |
| 2026-05-16 | 3.3 | Health check محسّن (latency, table_count, db_size, last_backup, /v1/health) | ✅ |

---

*آخر تحديث: 2026-05-16 | الإصدار: 1.1*
