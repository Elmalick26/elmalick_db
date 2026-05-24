# خطة المراجعة الشاملة — El Malick Gest
**آخر تحديث:** 23 مايو 2026
**الهدف:** مراجعة كاملة لكل ملف قبل التسليم النهائي — جودة، أمان، أداء، تصميم

---

## محاور المراجعة (تُطبَّق على كل ملف)

| # | المحور | ما نبحث عنه |
|---|--------|-------------|
| 1 | **الأمان** | استعلامات parameterized فقط · RBAC على كل كتابة · التحقق من المدخلات |
| 2 | **جودة الكود** | كود مكرر · دوال طويلة (+60 سطر) · imports غير مستخدمة · تعليقات |
| 3 | **قاعدة البيانات** | N+1 queries · LIMIT للجداول الكبيرة · معالجة أخطاء transactions · indexes |
| 4 | **تصميم الشاشة** | ModuleHeaderWidget موحد · رسائل خطأ واضحة · empty state · lazy loading |
| 5 | **معالجة الأخطاء** | try/except حول كل DB · AppLogger.error() · رسائل مفهومة للمستخدم |
| 6 | **الأداء** | تحميل مؤجل للبيانات الثقيلة · QTimer.singleShot · إغلاق connections |
| 7 | **الاختبار** | حقول فارغة · DB فارغة · سيناريوهات حدية (edge cases) |

---

## قائمة الملفات حسب الأولوية

### 🔴 المجموعة 1 — البنية التحتية (أساس كل شيء)
> أي خطأ هنا يؤثر على كامل التطبيق

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 1 | `database_setup.py` + `db_manager.py` | ✅ مكتمل | schema · migrations · connection pool |
| 2 | `config_manager.py` | ✅ مكتمل | تحسين: تجميع import وحدة لـ sys و keyring مع متغير _KEYRING_AVAILABLE |
| 3 | `security_utils.py` | ✅ مكتمل | إضافة: _BCRYPT_ROUNDS ثابت و generate_parent_pin / hash_pin / verify_pin |
| 4 | `app_logger.py` | ✅ مكتمل | تبسيط console handler (open fileno كان هشاً في EXE) |
| 5 | `db_path.py` + `db_schema.py` | ✅ مكتمل | تصحيح: Path relativ → Path(`__file__`).parent في dev mode |
| 6 | `validators.py` | ✅ مكتمل | حذف import Optional غير مستخدم |
| 7 | `ui_styles.py` | ✅ مكتمل | تجميع imports: QTimer، pyqtSignal، QHBoxLayout، QVBoxLayout، QWidget، math للأعلى |

---

### 🟠 المجموعة 2 — نقطة الدخول
> أول ما يراه المستخدم

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 8 | `login_window.py` | ✅ مكتمل | auth · session · role loading |
| 9 | `main_dashbord.py` | ✅ مكتمل | حذف `self.config` المكررة + حذف `role_permissions` المكررة في `__init__` |
| 10 | `first_run_wizard.py` | ✅ مكتمل | نقل `validate_password_strength` + `format_errors` إلى القمة |

---

### 🔴 المجموعة 3 — المالية (الأعلى خطورة)
> تتعامل مع بيانات مالية حساسة

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 11 | `finance_fees_setup.py` | ✅ مكتمل | حذف `THEME_AVAILABLE` + else branches الميتة |
| 12 | `payment_management.py` | ✅ مكتمل | حذف `THEME_AVAILABLE` + جميع if/else الميتة |
| 13 | `finance_payments.py` | ✅ مكتمل | حذف `THEME_AVAILABLE` + جميع if/else الميتة |
| 14 | `finance_expenses.py` | ✅ مكتمل | حذف `THEME_AVAILABLE` + جميع if/else الميتة |
| 15 | `finance_dashboard.py` | ✅ مكتمل | حذف `THEME_AVAILABLE` + جميع if/else الميتة |

---

### 🟡 المجموعة 4 — الطلاب (الاستخدام اليومي)
> الأكثر استخداماً يومياً

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 16 | `student_management.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل get_module_caps للقمة |
| 17 | `student_attendance.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل date للقمة |
| 18 | `student_grades.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل get_module_caps + date للقمة |
| 19 | `student_discipline.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل date للقمة |
| 20 | `bulletin_generation.py` | ✅ مكتمل | حذف THEME_AVAILABLE · لا imports مفقودة |

---

### 🟡 المجموعة 5 — الموظفون

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 21 | `staff_management.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل get_module_caps للقمة |
| 22 | `staff_attendance.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل date للقمة |
| 23 | `staff_leaves.py` | ✅ مكتمل | حذف THEME_AVAILABLE · لا imports مفقودة |

---

### 🟢 المجموعة 6 — الإدارة والإعدادات

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 24 | `academic_settings.py` | ✅ مكتمل | حذف THEME_AVAILABLE · لا imports مفقودة |
| 25 | `user_management.py` | ✅ مكتمل | حذف THEME_AVAILABLE · لا imports مفقودة |
| 26 | `admin_documents.py` | ✅ مكتمل | حذف THEME_AVAILABLE · لا imports مفقودة |
| 27 | `timetable_manager.py` | ✅ مكتمل | نظيف — لا THEME_AVAILABLE ولا imports مفقودة |

---

### 🟢 المجموعة 7 — الخدمات المساعدة

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 28 | `print_export_service.py` | ✅ مكتمل | نظيف — لا مشاكل |
| 29 | `pdf_report_style.py` | ✅ مكتمل | نظيف — لا مشاكل |
| 30 | `advanced_reports.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل subprocess للقمة |
| 31 | `analytics_dashboard.py` | ✅ مكتمل | نقل get_tabs_style للقمة |
| 32 | `global_search_dialog.py` | ✅ مكتمل | نقل QEvent للقمة |

---

### 🔵 المجموعة 8 — النظام والصيانة

| # | الملف | الحالة | ملاحظات |
|---|-------|--------|---------|
| 33 | `auto_backup.py` | ✅ مكتمل | نظيف — لا THEME_AVAILABLE ولا imports مفقودة |
| 34 | `system_maintenance.py` | ✅ مكتمل | حذف THEME_AVAILABLE · لا imports مفقودة |
| 35 | `inventory_management.py` | ✅ مكتمل | حذف THEME_AVAILABLE (17 حالة) · لا imports مفقودة |
| 36 | `communication_ui.py` | ✅ مكتمل | حذف THEME_AVAILABLE · نقل security_utils للقمة |
| 37 | `year_end_migration.py` | ✅ مكتمل | حذف THEME_AVAILABLE · لا imports مفقودة |
| 38 | `import_wizard.py` | ✅ مكتمل | حذف `date as _date` غير مستخدم |

---

## سجل التقدم

| التاريخ | الملف | ما تم | المشاكل المكتشفة | الحالة |
|---------|-------|-------|-----------------|--------|
| 23/05/2026 | `payment_management.py` | إضافة `ModuleHeaderWidget` للـ import | `NameError` عند تحميل الوحدة | ✅ مكتمل |
| 23/05/2026 | `main_dashbord.py` | حذف تعليق CSS + تصحيح `font-family` | `Could not parse stylesheet` × 3 | ✅ مكتمل |
| 23/05/2026 | `database_setup.py` | حذف `import logging` المكرر داخل except | استخدام `logger` المعرَّف في أعلى الملف | ✅ مكتمل |
| 23/05/2026 | `db_manager.py` | ثوابت `_POOL_MIN_CONN/MAX_CONN` + `connect_timeout` + توثيق `get_connection()` | أرقام مدفونة في الكود · لا timeout للاتصال | ✅ مكتمل |
| 23/05/2026 | `db_schema.py` | إضافة `is_active BOOLEAN DEFAULT TRUE` لـ Students + `_ensure_column` + `_safe_execute` للقيم القديمة · حذف docstring مكرر · حذف `conn.commit()` الزائد | **بمثابة ثغرة**: تثبيت جديد = Students بدون is_active = crash | ✅ مكتمل |

---

## رموز الحالة

| الرمز | المعنى |
|-------|--------|
| ⬜ لم يبدأ | لم يتم مراجعته بعد |
| 🔄 جارٍ | المراجعة جارية الآن |
| ⚠️ مشاكل | اكتُشفت مشاكل وتحتاج إصلاح |
| ✅ مكتمل | المراجعة اكتملت والملف جاهز |

---

## الملف الحالي قيد المراجعة

> **التالي: المجموعة 1 — `database_setup.py` + `db_manager.py`**
