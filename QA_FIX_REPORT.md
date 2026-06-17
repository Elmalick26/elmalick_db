# تقرير المراجعة والإصلاح الشاملة — El Malick Gest

| | |
|---|---|
| **المشروع** | El Malick Gest — تطبيق إدارة مدرسية (PyQt6 + PostgreSQL) |
| **الفرع** | `qa/full-review` (من `main` عند `5ef15a0`) |
| **التاريخ** | 2026-06-17 |
| **النطاق** | مراجعة من 6 مراحل + إصلاح كامل + إنجاز WIP الفرع |
| **عدد الـcommits** | 23 |

---

## 1. الملخّص التنفيذي

| المقياس | قبل | بعد |
|---------|-----|-----|
| الاختبارات | 1047 ناجح + **19 فاشل** | **1134 ناجح، 0 فاشل** |
| ثبات المجموعة | هشّة (أخطاء PyO3 حسب ترتيب التجميع) | **خضراء في كل الترتيبات** (عشوائي + حتمي) |
| سلسلة هجرات alembic في Git | مكسورة (009 يشير إلى 008 غير متتبَّع) | كاملة ومتّسقة `001 → 010` |
| سرّ مكشوف في Git | مفتاح Fernet في `config.ini` | أُلغي التتبّع + دُوِّر المفتاح |
| نسخة القاعدة | `alembic=004` (هجرات السلامة غير مطبَّقة) | `alembic=010` (كل قيود السلامة مطبَّقة) |

كل البنود الحرجة والمتوسطة عُولِجت وتُحقّق منها باختبارات. الفرع نظيف وقابل للدمج.

---

## 2. المنهجية — 6 مراحل

1. **فهم المشروع**: بنية الطبقات (UI / `services` منطق نقي / `src/data` وصول للبيانات / `repositories` shims / `api` FastAPI / `alembic`).
2. **التشغيل والاختبار الوظيفي**: المسارات الأساسية والحالات الحدّية (تنقيط /20، المعدلات، الانتقال، Unicode).
3. **جودة الكود ومعمارية PyQt6**: الخيوط، الإشارات/الفتحات، التسريبات، معالجة الاستثناءات.
4. **قاعدة البيانات والأمان**: حقن SQL، الاتصالات، القيود، الأسرار، RBAC.
5. **الأداء وسلامة البيانات**: N+1، الفهارس، النسخ الاحتياطي/الاستعادة، الحجم الكبير.
6. **الاختبارات والتوثيق والتوزيع**: التغطية، README، PyInstaller.

---

## 3. الاكتشافات والإصلاحات حسب الخطورة

### 🔴 حرج

| المعرّف | المشكلة | السبب الجذري | الإصلاح | Commit |
|---------|---------|--------------|---------|--------|
| **S1** | مفتاح Fernet (يشفّر كلمة مرور SMTP) مكشوف في Git | `config.ini` التُزِم قبل إضافته لـ`.gitignore` | `git rm --cached config.ini` + تدوير المفتاح + توثيق القالب | `698b9c0` |
| **S2** | هجرات السلامة 005–008 غير مطبَّقة (مبالغ سالبة وسجلات يتيمة ممكنة) | لم يُشغَّل `alembic upgrade head` | تطبيق الهجرات (CHECK مالية، FKs ناقصة، فهارس) | (DB) + `2176d11` |
| **P1** | N+1 في توليد الكشوف (~1200 استعلام/صف) | استعلام مفرد لكل (طالب×مادة×تقييم) | `get_grades_map_for_students` — استعلام واحد + بحث في قاموس | `f456d6e` |

### 🟠 متوسط

| المعرّف | المشكلة | الإصلاح | Commit |
|---------|---------|---------|--------|
| **F1/D1** | الترتيب لا يعالج التعادل (ex aequo) وخارج طبقة الاختبار | `GradeService.calculate_rank` (ترتيب تنافسي 1224) + اختبارات | `698b9c0` |
| **F2** | `validators.py` غير موصول بشاشات CRUD | ربط `validate_student`/`validate_staff` قبل الحفظ + اختبارات | `bcef4d8`, `f1db602` |
| **F3/S4/S5** | لا CHECK لمدى الدرجة 0–20، لا وحدانية، upsert غير ذرّي | هجرة 009 (CHECK + UNIQUE) + `INSERT … ON CONFLICT` | `b0c1348` |
| **Q1** | لا تنظيف لعمّال QThread عند الإغلاق (خطر «Destroyed while running») | `stop_background_workers` + `closeEvent` يوقف الخيوط قبل إغلاق الـpool | `571a709` |
| **S3** | ثابت نسخة alembic خاطئ (تحذير انحراف زائف) | تصحيح `_LATEST_ALEMBIC_REVISION` | `571a709`, `6a753a7` |
| **S6** | كلمة مرور SMTP نصاً صريحاً رغم وجود دوال التشفير | تشفير/فكّ في طبقة المستودع (متوافق مع القديم) + اختبارات | `6c0b43c` |
| **P3** | استعادة `.sql` غير ذرّية | `psql --single-transaction -v ON_ERROR_STOP=1` + اختبارات | `571a709` |
| **P2** | (تبيّن أنه مُطبَّق) ترقيم القوائم 50/صفحة خادمي | تأكيد + تغطية اختبار لمنطق `PaginationWidget` | `47f5255` |
| **D2** | لا ملف بناء PyInstaller (`.spec` مفقود) | `El Malick Gest.spec` (onedir) + تحقّق بناء كامل | `857ee17` |
| **D3** | RBAC بلا تغطية (0%) | اختبارات الـAPI + ثوابت أمنية (0%→100%) | `3049982` |
| **D4** | لا README | دليل تثبيت/قاعدة/تشغيل/تغليف | `44193de` |
| **F5** | 19 اختباراً فاشلاً (انحراف) | تحديث المساعِدات لتطابق الكود المحسَّن | `571a709` |

### 🟡 بسيط

| المعرّف | المشكلة | الإصلاح | Commit |
|---------|---------|---------|--------|
| **Q3** | تسريب matplotlib (`plt.subplots` في سجلّ pyplot العالمي) | تحويل لـ`Figure` كائني + إزالة استيراد pyplot | `d228aa0` |
| **Q4** | `requestInterruption()` بلا أثر (الحلقات لا تفحصه) | فحص `isInterruptionRequested()` في حلقات العمّال | `6bae138` |
| **Q5** | DDL وقت التشغيل (فهارس في شاشة المدفوعات) | نقلها إلى هجرة 010 + إزالة الـDDL | `6a753a7` |
| **D6** | `get_honor_mention` بلا اختبار | اختبارات النطاقات (grade_service 100%) | `4292052` |

### 🟦 قرار سياسة (لا إصلاح)

| المعرّف | الوصف | القرار |
|---------|-------|--------|
| **F4** | الدرجة المفقودة تُحسب 0 (رسوب) لا تُستثنى — على مستوى خلية (مادة×تقييم) | **الإبقاء على «المفقود = 0»** (قرار المستخدم)، موثّق في الكود `8fdfebf` |

---

## 4. نقاط القوة المؤكَّدة (لم تتطلّب إصلاحاً)

- ✅ **لا حقن SQL**: كل SQL الديناميكي يستخدم ثوابت/قوائم بيضاء، وكل قيم المستخدم parameterized.
- ✅ **تجزئة كلمات المرور**: `bcrypt` (12 جولة) مع ترحيل SHA256 القديم.
- ✅ **RBAC**: مصفوفة كاملة مع صلاحيات شرطية (`own_class`/`own_student`).
- ✅ **إدارة الاتصالات**: connection pool + context manager (commit/rollback تلقائي).
- ✅ **secret الـAPI**: يفشل-سريعاً في الإنتاج إن بقي افتراضياً.
- ✅ **النسخ الاحتياطي**: `pg_dump` مع `PGPASSWORD` في البيئة (لا في سطر الأوامر).

---

## 5. إنجاز WIP الفرع + إصلاح عزل الاختبارات

- **WIP الفرع** (96+ ملف غير ملتزم): التُزم في مجموعات منطقية — تتبّع الهجرات 003–008، حذف `Origine/` القديم، وحدات البنية الجديدة، التوثيق، الاختبارات، وrefactor الطبقات، مع **62 إصلاح لينت** (`dd0cff9`, `9e6be97`, `bb212c6`, `0bca12b`, `e89b846`, `571a709`).
- **عزل الاختبارات** (`9bf389e`): إصلاح تلوّث matplotlib — `patch.dict(sys.modules)` كان يطرد امتدادات C (numpy/cryptography) المستوردة أثناء الكتلة عند الخروج (تفشل إعادة تهيئتها). الحل: استعادة **مفاتيح الـstubs فقط**. أزال 9 أخطاء تجميع وجعل المجموعة خضراء بثبات.

---

## 6. سجلّ الـcommits (الترتيب الزمني)

```
698b9c0  fix(qa): ranking ex aequo in GradeService + untrack config.ini secret
f456d6e  perf(qa): bulk grade fetch for bulletins (fixes N+1)
3049982  test(qa): cover RBAC permission matrix (D3)
b0c1348  feat(qa): grade integrity constraints migration 009 (F3/S4/S5)
44193de  docs(qa): add README with setup, DB, run and packaging guide (D4)
857ee17  build(qa): add PyInstaller spec for distributable build (D2)
6c0b43c  fix(qa): encrypt SMTP password at rest (S6)
2176d11  chore(db): track migrations 003-008 and ignore DB dumps
dd0cff9  chore: remove legacy Origine/ snapshot and scratch scripts
9e6be97  feat: add core infrastructure modules
bb212c6  feat: add hypercare monitoring script
0bca12b  docs: add design, runbook, release and tracking docs
e89b846  test: add test suite, fixtures and smoke tests
571a709  refactor: layered architecture across application modules
bcef4d8  fix(qa): wire validators into student save flow (F2)
f1db602  fix(qa): wire validators into staff save flow (F2)
47f5255  test(qa): cover student-list pagination logic (P2)
d228aa0  fix(qa): stop matplotlib figure leak in finance dashboard (Q3)
4292052  test(qa): cover get_honor_mention bands (D6)
6a753a7  refactor(qa): move payment indexes to migration 010 (Q5)
6bae138  fix(qa): make worker interruption cooperative (Q4)
8fdfebf  docs(qa): document missing-grade=0 bulletin policy (F4)
9bf389e  test(qa): fix test-isolation pollution from analytics stubs
```

---

## 7. التحقّق (كيفية إعادة الإنتاج)

```bash
# الاختبارات (خضراء في كلا الترتيبين)
.venv/Scripts/python -m pytest                      # عشوائي → 1134 passed
.venv/Scripts/python -m pytest -p no:randomly       # حتمي   → 1134 passed

# قاعدة البيانات
.venv/Scripts/python -m alembic upgrade head        # → 010

# التغليف (خارج مجلد OneDrive)
.venv/Scripts/python -m PyInstaller "El Malick Gest.spec" --noconfirm --clean \
    --distpath C:\Temp\emg_dist --workpath C:\Temp\emg_build
```

---

## 8. توصيات ما قبل الإطلاق

1. **تدوير الأسرار الإنتاجية**: تعيين `ELMALICK_API_SECRET` قوي وتدوير `fernet_key` على بيئة الإنتاج (المكشوف سابقاً لم يكن يحمي قيمة مستخدَمة فعلياً، لكن التدوير ممارسة سليمة).
2. **تنظيف تاريخ Git (اختياري)**: إن كان المستودع سيُنشر علناً، إزالة `config.ini` القديم من التاريخ بـ`git filter-repo`.
3. **التغليف**: البناء من مجلد غير مُزامَن بـOneDrive (يقفل الملفات أثناء COLLECT).
4. **النشر**: اتباع `RUNBOOK.md` (يتضمّن `alembic upgrade head` كخطوة إلزامية).

---

*أُعدّ هذا التقرير ضمن مراجعة جودة شاملة على فرع `qa/full-review`. كل الإصلاحات مُختبَرة والمجموعة خضراء بثبات.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
