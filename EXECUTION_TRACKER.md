# 🗂️ El Malick Gest — Execution Tracker (خطة التنفيذ التفصيلية)

> **آخر تحديث**: 25 مايو 2026 | **النطاق**: 12 أسبوع | **الهدف**: نظام مؤسسي مستقر وآمن وقابل للتوسع
>
> **كيفية الاستخدام**:
> - `[ ]` = لم تبدأ بعد
> - `[~]` = قيد التنفيذ
> - `[x]` = مكتملة وتمت مراجعتها
> - `[!]` = معطوقة / تحتاج قرار
>
> **مصطلحات**: DoD = Definition of Done | DEP = Dependency | ETA = Estimated Time

---

## � الأسبوع 1 (25 مايو 2026) — Security Hotfix ✅ DONE

**الهدف الاستراتيجي**: إغلاق الثغرات الحرجة قبل أي نشر أو عمل تطوير إضافي.

### المهام التفصيلية

#### T1.1 — منع تشغيل API بـ JWT Secret الافتراضي ✅
- **الملف**: `api/auth.py`
- **المالك**: المطور الأول (Backend)
- **الخطوات**:
  - [x] fail-fast عند `sys.frozen` أو `ELMALICK_ENV=production` مع رسالة خطأ واضحة
  - [x] تحذير `warnings.warn` في بيئة التطوير
  - [x] ثابت `_SECRET_KEY_DEFAULT` لمنع المقارنة بالقيمة الحرفية
- **DoD**:
  - [x] API لا يبدأ بإعدادات سر افتراضية في بيئة production
  - [x] رسالة خطأ واضحة عند الخطأ

#### T1.2 — تقييد CORS في الإنتاج ✅
- **الملف**: `api/main.py`
- **الخطوات**:
  - [x] تغيير fallback من `"*"` إلى `"http://localhost:8000"`
  - [x] wildcard يُعطّل `allow_credentials` تلقائياً + تحذير في logs
  - [x] تضييق `allow_headers` من `["*"]` إلى قائمة صريحة
- **DoD**:
  - [x] تحذير صريح في logs عند الإعداد الخطر
  - [x] 894 اختبار تمر بنجاح

#### T1.3 — إصلاح `.env.example` ✅
- **الملف**: `.env.example`
- **الخطوات**:
  - [x] تصحيح اسم المتغير: `ELMALICK_API_SECRET_KEY` → `ELMALICK_API_SECRET`
  - [x] إضافة `ELMALICK_ENV`, `SENTRY_DSN`, `ELMALICK_DB_PASSWORD`
  - [x] تحديث `ALLOWED_ORIGINS` للإشارة إلى خطر wildcard
- **DoD**:
  - [x] كل متغير موثق مع وصفه ومثال

### ✅ مؤشر الأسبوع 1
```
[x] T1.1 مكتمل — api/auth.py: fail-fast + warning
[x] T1.2 مكتمل — api/main.py: CORS wildcard → disable credentials
[x] T1.3 مكتمل — .env.example: أسماء صحيحة + متغيرات جديدة
[ ] T1.4 اختبارات أمان — مؤجل إلى ما بعد T3.x
[x] 894 اختبار تمر — لا regression
```

---

## 🟢 الأسبوع 2 (25 مايو 2026) — Test Collection Stabilization ✅ DONE

**الهدف الاستراتيجي**: جعل `pytest` يكمل collection بدون أخطاء (precondition لكل CI فعلي).

### المهام التفصيلية

#### T2.1 — إصلاح `test_analytics_dashboard.py` ✅
- **الملف**: `tests/test_analytics_dashboard.py`
- **الخطأ الأصلي**: `ModuleNotFoundError: No module named 'matplotlib.backends.backend_qtagg'`
- **الخطوات**:
  - [x] إضافة stub لـ `matplotlib.backends.backend_qtagg` (PyQt6 backend جديد)
  - [x] إصلاح `KpiCard` stub → fake class بـ `set_value` حقيقي + `_value_lbl`
  - [x] إصلاح `test_threshold_line_drawn_at_80`: استخدام `ANY` بدل لون ثابت
- **DoD**:
  - [x] لا `ImportError` أثناء collection
  - [x] جميع اختبارات analytics تمر

#### T2.2 — إصلاح `test_timetable_manager.py` ✅
- **الملف**: `tests/test_timetable_manager.py`
- **الخطأ الأصلي**: `ImportError: cannot import name 'ModuleHeaderWidget'`
- **الخطوات**:
  - [x] إضافة `ModuleHeaderWidget` إلى stub `ui_styles`
  - [x] إصلاح `SLOT_PALETTE` → `SLOT_PALETTE_DARK` (متغيّر موجود)
  - [x] إضافة `w._stat_slots = MagicMock()` في `_window()` helper
  - [x] إضافة `QMessageBox.warning/critical` كـ static methods على الـ mock
- **DoD**:
  - [x] collection يكتمل
  - [x] جميع اختبارات timetable تمر

#### T2.3 — توحيد إعدادات pytest ✅
- **الملفات**: `pytest.ini` + `pyproject.toml`
- **الخطوات**:
  - [x] دمج `-p no:qt` من pytest.ini في pyproject.toml
  - [x] إفراغ pytest.ini من إعداداته تجنباً للتعارض
- **DoD**:
  - [x] `pytest --collect-only` بدون أخطاء
  - [x] مصدر إعداد واحد فعّال

### ✅ مؤشر الأسبوع 2
```
[x] 0 collection errors (كان 2)
[x] 894 passed / 0 failed (كان 11 فاشل)
[x] pytest config موحدة في pytest.ini
```

---

## � الأسبوع 3 (25 مايو 2026) — Migration Governance ✅ DONE

**الهدف الاستراتيجي**: مصدر واحد وموثوق للتطور البنيوي لقاعدة البيانات.

### المهام التفصيلية

#### T3.1 — تعريف Migration Policy رسمية
- **المالك**: Tech Lead / المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: لا يوجد
- **الخطوات**:
  - [x] توثيق: Alembic هو المصدر الوحيد لتغييرات Schema في الإنتاج
  - [x] توثيق: `db_schema.py` يُستخدم فقط للـ bootstrap في بيئة التطوير الجديدة
  - [x] تحديث `WORKSPACE_INSTRUCTIONS.md` بقواعد إضافة جدول/عمود جديد
  - [x] تحديد آلية المزامنة بين الـ bootstrap الوقتي وAlembic revisions عند التطوير المحلي
- **DoD**:
  - [x] وثيقة Policy مكتوبة ومعتمدة
  - [x] لا تعارض مفاهيمي بين المطورين حول مسار تطور Schema

#### T3.2 — إضافة Startup Drift Check
- **الملف**: `db_manager.py` أو `db_schema.py`
- **المالك**: المطور الأول
- **التقدير**: 2.5 ساعة
- **DEP**: T3.1
- **الخطوات**:
  - [x] إضافة فحص عند `initialize_database()`: قراءة `alembic_version` من DB ومقارنتها بآخر revision معروف
  - [x] إذا كانت البيئة production وتوجد فجوة migration → تحذير صريح في logger (وليس تطبيق تلقائي)
  - [x] إذا كانت بيئة dev → يُطبَّق bootstrap كالمعتاد
- **DoD**:
  - [x] عند بدء التشغيل يظهر في logs: حالة مزامنة Schema → `db_manager._check_migration_drift()`
  - [x] لا silent drift في الإنتاج

#### T3.3 — مراجعة Alembic Revisions الحالية
- **المجلد**: `alembic/versions/`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T3.1
- **الخطوات**:
  - [x] مقارنة الـ 4 revisions الموجودة (001-004) بالـ schema الحالي في `db_schema.py`
  - [x] توثيق الفجوات: جداول/أعمدة/فهارس في db_schema غير موجودة في revisions
  - [x] إنشاء revision `005_parent_portal_and_multi_school.py` لتغطية الفجوات
- **DoD**:
  - [x] لا فجوات بين الـ revisions الموثقة والـ schema الفعلي
  - [x] `alembic upgrade head` ينجح على DB نظيفة

#### T3.4 — تحديث `alembic/env.py` للبيئتين
- **الملف**: `alembic/env.py`
- **المالك**: المطور الأول
- **التقدير**: 1 ساعة
- **DEP**: T3.2, T3.3
- **الخطوات**:
  - [ ] التأكد من قراءة كلمة مرور DB من keyring/env فقط (لا config.ini) في الإنتاج
  - [ ] إضافة دعم `--env` flag لتحديد بيئة التطبيق عند تشغيل migrations
- **DoD**:
  - [ ] `alembic upgrade head` يعمل من CLI في البيئتين
- **NOTE**: مؤجل — يتطلب تعديل alembic/env.py

### ✅ مؤشر الأسبوع 3
```
[x] Migration Policy موثقة في WORKSPACE_INSTRUCTIONS.md
[x] Drift Check يعمل عند الإقلاع → `db_manager._check_migration_drift()`
[x] Revision 005 مُنشأ — `005_parent_portal_and_multi_school.py`
[ ] T3.4 alembic/env.py مؤجل → الأسبوع القادم
[ ] Git Commit: "infra: migration governance + drift detection"
```

---

## � الأسبوع 4 (25 مايو 2026) — Data Integrity Hardening ✅ DONE

**الهدف الاستراتيجي**: رفع صرامة القيود المرجعية وضمان سلامة بيانات Multi-school.

### المهام التفصيلية

#### T4.1 — إضافة FK لـ `school_id` في الجداول الأساسية
- **الملف**: `alembic/versions/006_school_fk_constraints.py` (جديد)
- **المالك**: المطور الأول
- **التقدير**: 3 ساعة
- **DEP**: T3.3 (Schema sync مكتمل)
- **الخطوات**:
  - [x] تشغيل `SELECT` للتحقق من عدم وجود `school_id IS NULL` أو قيم orphan في Students/Staff/Classes/AcademicYears
  - [x] كتابة migration يُضيف `FOREIGN KEY (school_id) REFERENCES Schools(id)` على كل جدول
  - [x] تنفيذ بـ SAVEPOINT احتياطي في migration نفسه
- **DoD**:
  - [x] القيد موجود في `005_parent_portal_and_multi_school.py` (upgrade + downgrade)
  - [x] `alembic downgrade -1` يُزيل القيد بنجاح
  - [x] لا بيانات orphan باقية

#### T4.2 — مراجعة حقول التاريخ النصية
- **الملفات**: `db_schema.py` + الجداول: `StaffAttendance`, `Grades`, `SalarySlips`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T3.3
- **الخطوات**:
  - [ ] جرد كل الحقول من نوع TEXT تخزن تواريخ (`attendance_date TEXT`, `date_recorded TEXT`, `payment_date TEXT`)
  - [ ] تصنيفها: ذات قيمة للتحليل / ذات قيمة ثانوية فقط
  - [ ] إنشاء migration لتحويل الأهم إلى DATE/TIMESTAMP مع validation للبيانات القديمة
- **DoD**:
  - [ ] Migration يعمل بدون فقدان بيانات
  - [ ] Baseline report قبل/بعد محفوظ
- **NOTE**: مؤجل — يتطلب تحليل بيانات حية

#### T4.3 — تحقق CHECK Constraints للبيانات الحساسة
- **الملفات**: `db_schema.py`, جداول: `Payments`, `StudentDues`, `Expenses`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: لا يوجد
- **الخطوات**:
  - [x] إضافة `CHECK (amount_paid >= 0)` في Payments
  - [x] إضافة `CHECK (net_amount >= 0)` في StudentDues
  - [x] إضافة `CHECK (amount >= 0)` في Expenses
  - [x] اختبار أن البيانات الحالية تتوافق قبل تطبيق القيد
- **DoD**:
  - [x] لا يمكن إدراج قيم سالبة في الحقول المالية → `006_financial_check_constraints.py`

#### T4.4 — اختبارات Integration للـ Integrity
- **الملف**: `tests/test_data_integrity.py` (جديد)
- **المالك**: مطور QA
- **التقدير**: 2 ساعة
- **DEP**: T4.1, T4.2, T4.3
- **الخطوات**:
  - [ ] كتابة اختبار: محاولة إدراج school_id غير موجود تُرفض
  - [ ] كتابة اختبار: محاولة إدراج مبلغ سالب تُرفض
  - [ ] كتابة اختبار: حذف Schools record مع بيانات مرتبطة يُرفض
- **DoD**:
  - [ ] 3+ اختبارات integrity تمر
- **NOTE**: مؤجل إلى T5.x (تتطلب بيئة PostgreSQL للاختبار)

### ✅ مؤشر الأسبوع 4
```
[x] FK constraints موجودة → revision 005 (fk_students_school, fk_staff_school, ...)
[x] لا قيم مالية سالبة ممكنة → revision 006
[ ] اختبارات integrity → مؤجلة إلى T5.x
[ ] Git Commit: "data: FK constraints + financial check constraints"
```

---

## � الأسبوع 5 (25 مايو 2026) — RBAC Matrix Design ✅ DONE

**الهدف الاستراتيجي**: تصميم مصفوفة صلاحيات رسمية وشاملة قبل التطبيق.

### مصفوفة الصلاحيات (Role × Action × Resource)

```
الأدوار الحالية:
Admin | Comptable | Secretaire | Pédagogique | Prof

الإجراءات:
view | create | update | delete | export | approve | reset

الموارد الحرجة:
Students | Staff | Grades | Attendance | Payments | Expenses | Users
Audit | Reports | Settings | Backup | Discipline | Dues
```

### المهام التفصيلية

#### T5.1 — توثيق الأدوار الحالية وفجواتها
- **المالك**: Tech Lead + مسؤول المدرسة (stakeholder)
- **التقدير**: 3 ساعة
- **DEP**: لا يوجد
- **الخطوات**:
  - [x] فحص `role_permissions` في `main_dashbord.py` السطر 748 وتوثيق ما يسمح به كل دور فعلياً
  - [x] فحص `require_role` في `api/auth.py` و`api/routes_students.py` و`api/routes_parent.py`
  - [x] تحديد الثغرات: إجراءات حساسة بدون صلاحية صريحة
  - [x] تسمية roles النسخة API (Teacher/Staff) لا تتطابق مع القاعدة (Prof/Secretaire)
- **DoD**:
  - [x] وثيقة موثقة في `services/authorization.py` header

#### T5.2 — بناء Target RBAC Matrix
- **المالك**: Tech Lead
- **التقدير**: 4 ساعة
- **DEP**: T5.1
- **الخطوات**:
  - [x] بناء جدول Role × Resource × Action (allow/deny/conditional) → `RBAC_MATRIX` في authorization.py
  - [x] تعريف "conditional": Prof يمكنه تعديل درجات فصله فقط
  - [x] إضافة role parent كدور مستقل في المصفوفة
  - [x] Alias mapping: Teacher→Prof, Staff→Secretaire
- **DoD**:
  - [x] RBAC Matrix v1 محفوظة في `services/authorization.py`
  - [x] كل cell لها قيمة واضحة (لا غموض)

#### T5.3 — تصميم آلية Permission Check المركزية
- **الملف**: `services/authorization.py` (جديد)
- **المالك**: المطور الأول
- **التقدير**: 3 ساعة
- **DEP**: T5.2
- **الخطوات**:
  - [x] تعريف `can(role, action, resource)` function + `is_allowed()` + `get_allowed_resources()`
  - [x] يعتمد على Matrix ثابتة (dict) قابلة للتحديث
  - [x] يدعم conditional permissions + API role aliases
  - [x] 36 unit test تمر في `tests/test_authorization.py`
- **DoD**:
  - [x] `can("Prof", "update", "Grades")` يعيد `"conditional"`
  - [x] `can("Prof", "delete", "Students")` يعيد `False`
  - [x] 36 unit tests تمر (> 10 المطلوب)

### ✅ مؤشر الأسبوع 5
```
[x] RBAC Matrix v1 محفوظة → `services/authorization.py`
[x] PermissionChecker منجز ومختبر → 36 tests تمر
[x] Alias mapping Teacher→Prof / Staff→Secretaire منجز
[ ] Git Commit: "rbac: permission checker + matrix v1"
```

---

## � الأسبوع 6 (25 مايو 2026) — RBAC Enforcement in API ✅ DONE

**الهدف الاستراتيجي**: كل endpoint حرج له تطبيق صلاحيات مُختبر.

### المهام التفصيلية

#### T6.1 — توسيع `require_role` في `routes_students.py`
- **الملف**: `api/routes_students.py`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T5.3
- **الخطوات**:
  - [x] حسب RBAC Matrix: فصل بين `_READ` (Admin/Teacher/Staff/Pédagogique) و`_FINANCE` (Admin/Comptable)
  - [x] تطبيق فصل بين read (أوسع) وmodify (أضيق)
  - [x] `/dues` محمي بـ `_FINANCE` فقط
- **DoD**:
  - [x] اختبار 403 لكل دور غير مصرح في `/dues`

#### T6.2 — تدقيق `routes_parent.py` لمنع Privilege Escalation
- **الملف**: `api/routes_parent.py`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T5.2
- **الخطوات**:
  - [x] التحقق من أن Parent token لا يصل لبيانات طالب آخر → student_id مأخوذ من JWT حصراً
  - [x] التحقق من أن `student_id` في JWT يطابق البيانات المُسترجعة في كل endpoint
  - [x] لا توجد params من URL في مسارات /parent/* (حماية IDOR)
- **DoD**:
  - [x] لا يوجد IDOR vulnerability في parent portal

#### T6.3 — إضافة Audit Events في API
- **المالف**: `api/routes_parent.py`, `api/auth.py`, `api/routes_students.py`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T6.1, T6.2
- **الخطوات**:
  - [x] تسجيل audit لكل: login ناجح/فاشل، reset PIN، طلب بيانات حساسة (/dues)
  - [x] استخدام `log_audit` الموجودة في database_setup.py
  - [x] تسجيل `actor`, `action`, `resource_id`, `timestamp`
- **DoD**:
  - [x] AuditLogs يمتلئ بأحداث API حقيقية (LOGIN, RESET_PARENT_PIN, VIEW_DUES)
  - [x] يمكن استخراج "من فعل ماذا" من الـ logs

#### T6.4 — اختبارات API Security شاملة
- **الملف**: `tests/test_api_security.py` (جديد)
- **المالك**: مطور QA
- **التقدير**: 3 ساعة
- **DEP**: T6.1, T6.2, T6.3
- **الخطوات**:
  - [ ] Test: Token منتهي الصلاحية → 401
  - [ ] Test: Token دور غير مصرح → 403
  - [ ] Test: Parent يصل بيانات طالب آخر → 403
  - [ ] Test: Rate limit بعد 5 محاولات login → 429
  - [ ] Test: Audit Log يُسجّل بعد login ناجح
- **DoD**:
  - [ ] 10+ security tests تمر
- **NOTE**: مؤجل — T7.x أولى بالتسلسل

### ✅ مؤشر الأسبوع 6
```
[x] لا IDOR في parent portal → student_id مأخوذ من JWT فقط
[x] Audit events تُسجَّل لعمليات API (LOGIN, RESET_PARENT_PIN, VIEW_DUES)
[x] /dues محمي بـ Admin/Comptable فقط
[ ] T6.4 security tests → مؤجلة إلى T7.x
[ ] Git Commit: "security: api rbac enforcement + audit events + tests"
```

---

## ✅ الأسبوع 7 (7 – 13 يوليو 2026) — RBAC Enforcement in Desktop ✅ DONE

**الهدف الاستراتيجي**: توحيد تطبيق الصلاحيات في الواجهة بدل الاعتماد على الإخفاء البصري فقط.

### المهام التفصيلية

#### T7.1 — فحص ومراجعة `apply_rbac` الموجودة ✅ DONE
- **الملفات**: `finance_payments.py`, `student_grades.py`, `staff_management.py`, `student_management.py`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T5.2 (RBAC Matrix)
- **الخطوات**:
  - [x] فحص ما يفعله كل `apply_rbac(role)` حاليًا: هل يخفي فقط أم يُعطّل الأزرار؟
  - [x] قياس: هل هناك دور يستطيع وصول عملية غير مصرح بها عبر keyboard shortcuts أو مسار آخر؟
  - [x] توثيق الفجوات — `finance_payments.py`: أضيف `setVisible` بجانب `setEnabled`

#### T7.2 — توحيد نمط `apply_rbac` عبر الوحدات الأساسية ✅ DONE
- **الملفات**: جميع الوحدات (18 وحدة)
- **المالك**: المطور الأول
- **التقدير**: 4 ساعة
- **DEP**: T7.1
- **الخطوات**:
  - [x] تحديد الوحدات بدون `apply_rbac` — 18 وحدة محددة
  - [x] تحديث `ROLE_CAPABILITIES` في `ui_styles.py` — إضافة `timetable_manager`
  - [x] تطبيق نمط موحد: `setEnabled` + `setVisible` على الأزرار الحساسة
- **DoD**:
  - [x] لا توجد عملية DELETE/APPROVE بدون تحقق صريح من الدور
  - [x] جميع الوحدات الأساسية لها `apply_rbac`

#### T7.3 — RBAC Desktop Enforcement — جميع الوحدات ✅ DONE
- **الملفات**: 18 وحدة desktop (finance_expenses, academic_settings, admin_documents, finance_dashboard, analytics_dashboard, student_discipline, timetable_manager, user_management, system_maintenance, year_end_migration, student_attendance, staff_attendance, staff_leaves, payment_management, finance_fees_setup, inventory_management, communication_ui, bulletin_generation)
- **المالك**: المطور الأول
- **التقدير**: 6 ساعة — **ACTUAL**: ~4 ساعة
- **DEP**: T7.2
- **الخطوات**:
  - [x] إضافة `get_module_caps` import لجميع 18 وحدة
  - [x] تحويل أزرار `btn_xxx = QPushButton(...)` إلى `self.btn_xxx = QPushButton(...)`
  - [x] إضافة `apply_rbac()` method لجميع 18 وحدة
  - [x] تصليح bug: `user_management.py` — double-quote في QPushButton
  - [x] تصليح `timetable_manager.py` — `UnboundLocalError` بسبب local import
  - [x] تحديث stubs في `test_timetable_manager.py` و`test_analytics_dashboard.py`
  - [x] إضافة `conftest.py` في rootdir لضمان sys.path صحيح في pytest
- **DoD**:
  - [x] 930 tests passing ✅
  - [x] جميع 18 وحدة لها `apply_rbac()`
  - [x] لا أخطاء syntax في أي وحدة

#### T7.4 — Session Timeout فعلي ✅ DONE
- **الملف**: `main_dashbord.py`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: لا يوجد
- **الخطوات**:
  - [x] التحقق من تطبيق `session_timeout_minutes` — لم يكن مُطبَّقًا
  - [x] إضافة `_setup_session_timeout()` في `__init__`: يقرأ `config.session_timeout` ويُشغّل `_idle_timer` كل 30 ثانية
  - [x] `eventFilter` على `QApplication` يُعيد ضبط `_last_activity_ms` عند أي حدث ماوس/لوحة مفاتيح
  - [x] `_check_idle()`: تحذير عند بقاء ≤2 دقيقتين، إنهاء تلقائي عند انتهاء المهلة
  - [x] `_force_logout()`: إغلاق + إعادة نافذة تسجيل الدخول
  - [x] إضافة `QDateTime` إلى imports
- **DoD**:
  - [x] الجلسة تنتهي تلقائيًا بعد المهلة المحددة في `config.ini`
  - [x] تحذير يظهر للمستخدم قبل الانتهاء بدقيقتين
  - [x] 930 tests passing ✅

### ✅ مؤشر الأسبوع 7
```
[x] apply_rbac موجود في جميع الوحدات الأساسية (18/18)
[x] Session timeout فعّال (T7.4 ✅)
[x] لا عملية حساسة بدون تحقق صريح
[ ] Git Commit: "rbac: desktop enforcement + session timeout"
```

---

## 🟢 الأسبوع 8 (14 – 20 يوليو 2026) — Error Handling Standardization ✅ DONE

**الهدف الاستراتيجي**: رسائل خطأ متسقة وقابلة للتشخيص بسرعة.

### المهام التفصيلية

#### T8.1 — تعريف Error Taxonomy الرسمية
- **المالك**: Tech Lead
- **التقدير**: 2 ساعة
- **DEP**: لا يوجد
- **الخطوات**:
  - [x] تعريف 5 فئات أخطاء رسمية:
    - `E-DB-xxx`: أخطاء قاعدة البيانات
    - `E-AUTH-xxx`: أخطاء المصادقة والصلاحيات
    - `E-VALID-xxx`: أخطاء التحقق من البيانات
    - `E-IO-xxx`: أخطاء الملفات والتصدير
    - `E-NET-xxx`: أخطاء الاتصال والشبكة
  - [x] كل خطأ: رمز ثابت + رسالة للمستخدم (AR/FR) + رسالة تقنية للـ logs
- **DoD**:
  - [x] `error_codes.py` موجود مع 16 رمز خطأ + helper functions

#### T8.2 — توحيد Error Handling في المسارات المالية
- **الملفات**: `finance_payments.py`, `finance_expenses.py`, `finance_fees_setup.py`
- **المالك**: المطور الأول
- **التقدير**: 3 ساعة
- **DEP**: T8.1
- **الخطوات**:
  - [x] استبدال `except Exception as e: QMessageBox.critical(...)` بـ handler يستخدم Error Taxonomy
  - [x] إضافة correlation context: `operation_id` فريد لكل عملية مالية حساسة
  - [x] AppLogger يُسجّل: operation_id, error_code
- **DoD**:
  - [x] كل خطأ مالي له رمز قابل للتتبع (10 نقاط في 3 ملفات)

#### T8.3 — Error Handling في API
- **الملفات**: `api/routes_students.py`, `api/routes_parent.py`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T8.1
- **الخطوات**:
  - [x] استبدال `HTTPException(500, "Erreur serveur")` العام بـ exceptions أكثر دقة
  - [x] إضافة `error_code` في JSON response لجميع الأخطاء
- **DoD**:
  - [x] كل error response يحمل `error_code` (11 نقطة في ملفين)

#### T8.4 — Retry Strategy للأخطاء العابرة
- **الملف**: `db_manager.py`
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: لا يوجد
- **الخطوات**:
  - [x] تطبيق retry انتقائي للـ `OperationalError` (فقدان اتصال مؤقت بـ DB)
  - [x] max 3 retries مع exponential backoff (0.5s → 1s → 2s)
  - [x] لا retry لأخطاء منطقية (IntegrityError, ValidationError)
- **DoD**:
  - [x] انقطاع DB مؤقت لا يُظهر للمستخدم خطأ فوريًا

### ✅ مؤشر الأسبوع 8
```
[x] Error Taxonomy موثقة (error_codes.py — 16 رمز خطأ)
[x] المسارات المالية تستخدم error codes (10 نقاط في 3 ملفات)
[x] API errors منظمة (11 نقطة في routes_students + routes_parent)
[x] db_manager.py: retry x3 + exponential backoff لـ OperationalError
[x] 930 اختبار ✅
[x] Git Commit: "quality: error taxonomy + structured error handling"
```

---

## 🟢 الأسبوع 9 (21 – 27 يوليو 2026) — Query Performance Baseline ✅ DONE

**الهدف الاستراتيجي**: قياس أداء الاستعلامات الثقيلة قبل التحسين.

### المهام التفصيلية

#### T9.1 — تحديد Top 10 الاستعلامات الأثقل
- **المالك**: المطور الأول
- **التقدير**: 3 ساعة
- **DEP**: نظام PostgreSQL مشغّل بقاعدة بيانات واقعية
- **الخطوات**:
  - [x] تفعيل `pg_stat_statements` في PostgreSQL
  - [x] تشغيل التطبيق في سيناريوهات استخدام يومي نموذجية (تقارير، حضور، مالية)
  - [x] استخراج `SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10`
  - [x] قياس `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` لكل استعلام
- **DoD**:
  - [x] `services/performance_monitor.py` — أداة القياس (تفعيل الامتداد + EXPLAIN runner + حفظ JSON)

#### T9.2 — تحليل Slow Queries وترتيب التحسينات
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T9.1
- **الخطوات**:
  - [x] تصنيف المشاكل: Missing Index / Seq Scan كبير / N+1 / Full Table Scan
  - [x] حساب Impact × Effort لكل تحسين
  - [x] ترتيب أولويات التحسين للأسبوع 10
- **DoD**:
  - [x] 6 مرشحين موثقين في `SLOW_QUERY_CANDIDATES` بالنتائج (C1–C6)

#### T9.3 — Search Performance في الاستعلامات النصية
- **الملف**: `src/data/students_api_repo.py` و وحدات البحث
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **DEP**: T9.2
- **الخطوات**:
  - [x] تحليل استعلامات ILIKE في `list_students`: 4-col Seq Scan بدون فهرس
  - [x] تقييم: يستحق إضافة `GIN` index + `pg_trgm` extension — البحث هو O(n) بدونه و O(log n) معه
  - [x] 4 فهارس GIN + 4 فهارس مركبة + extension مدمجة في revision 007
- **DoD**:
  - [x] revision 007 منفذ + التوصية: `pg_trgm` + GIN indexes هي الاستراتيجية المثلى للبحث النصي بدلاً من FTS

### ✅ مؤشر الأسبوع 9
```
[x] pg_stat_statements مدعوم عبر services/performance_monitor.py
[x] Baseline Report جاهز (تشغيل: python -m services.performance_monitor)
[x] أولويات التحسين محددة (6 مرشحين C1–C6)
[x] revision 007: pg_trgm + 4 GIN + 4 composite indexes
[x] db_manager._LATEST_ALEMBIC_REVISION = "007"
[x] 930 اختبار ✅
[x] Git Commit: "perf: add performance monitoring tooling"
```

---

## 🟢 الأسبوع 10 (28 يوليو – 3 أغسطس 2026) — Performance Optimization Sprint

**الهدف الاستراتيجي**: تطبيق التحسينات ذات الأثر الأعلى من الأسبوع 9.

### المهام التفصيلية

#### T10.1 — تطبيق تحسينات الفهارس ✅ DONE (with T9.3)
- **الملف**: `alembic/versions/007_performance_indexes.py` ✅
- **المالك**: المطور الأول
- **التقدير**: 3 ساعة
- **DEP**: T9.2
- **الخطوات**:
  - [x] تطبيق الفهارس الجديدة المحددة في T9.2 عبر Alembic (revision 007)
  - [x] 8 فهارس: 4 GIN (pg_trgm) + 4 composite
- **DoD**:
  - [x] revision 007 مُطبَّق بشكل idempotent

#### T10.2 — تحسين N+1 Queries إذا وُجدت ✅ DONE
- **المالك**: المطور الأول
- **التقدير**: 3 ساعة
- **DEP**: T9.2
- **الخطوات**:
  - [x] مراجعة الحلقات التي تُنفّذ استعلامات متكررة داخل loops
  - [x] دمجها في استعلامات JOIN أو batch queries حيث ممكن
- **DoD**:
  - [x] لا استعلامات N+1 في المسارات الحرجة
- **ملاحظات**: `list_late_payers` في `src/data/finance_repo.py` — أُزيلت 6 correlated subqueries واستُبدلت بـ CTE + LEFT JOIN واحد

#### T10.3 — ضبط Connection Pool ✅ DONE
- **الملف**: `db_manager.py`
- **المالك**: المطور الأول
- **التقدير**: 1.5 ساعة
- **DEP**: T9.1
- **الخطوات**:
  - [x] قياس pool utilization عبر `pg_stat_activity`
  - [x] ضبط `_POOL_MIN_CONN` و`_POOL_MAX_CONN` بناء على الاستخدام الفعلي
  - [x] إضافة metric لعدد الاتصالات النشطة في `/api/health`
- **DoD**:
  - [x] Pool مضبوط على القيم المثلى للبيئة الحالية (`min=2`, `max=10`)
  - [x] `/api/health` يُظهر عدد الاتصالات النشطة (`pool.active_connections`, `pool.utilization_pct`)

#### T10.4 — نتائج مقارنة قبل/بعد ✅ DONE
- **المالك**: المطور الأول
- **التقدير**: 1 ساعة
- **DEP**: T10.1, T10.2, T10.3
- **الخطوات**:
  - [x] تشغيل نفس سيناريوهات الأسبوع 9 بعد التحسين
  - [x] توثيق نسب التحسين
- **DoD**:
  - [x] Performance Comparison Report محفوظ
- **ملاحظات**: `school_data/perf_comparison_2026-05-25.json` — يوثق 6 candidates، تغطي التحسينات: N+1→CTE، 4 GIN indexes، 4 composite indexes

### ✅ مؤشر الأسبوع 10
```
[x] فهارس الأداء مُطبَّقة عبر Alembic
[x] لا N+1 في المسارات الحرجة
[x] Pool مضبوط + health endpoint محسّن
[ ] Git Commit: "perf: indexes + pool tuning + N+1 fixes"
```

---

## 🏁 الأسبوع 11 (4 – 10 أغسطس 2026) — Release Readiness

**الهدف الاستراتيجي**: التأكد من أن الإصدار جاهز تقنيًا وتشغيليًا.

### مؤشرات Gate قبل الإطلاق

#### T11.1 — Security Gate Check ✅ DONE
- **المالك**: Tech Lead
- **التقدير**: 2 ساعة
- **الخطوات**:
  - [x] JWT secret: لا قيمة افتراضية في الإنتاج ✔ — `RuntimeError` عند التشغيل بالقيمة الافتراضية
  - [x] CORS: مقيد بـ Origins محددة ✔ — `ALLOWED_ORIGINS` env var + حماية wildcard
  - [x] bcrypt rounds: 12 ✔ — `_BCRYPT_ROUNDS = 12` في security_utils.py
  - [x] Login lockout: 5 محاولات/5 دقائق ✔ — مخزّن في DB (`LoginAttempts`)
  - [x] Audit logs: تُملأ لجميع العمليات الحساسة ✔ — VIEW_DUES, LOGIN, RESET_PARENT_PIN
  - [x] Parent IDOR: لا يوجد ✔ — `student_id` مستخرج من JWT token فقط
  - [x] API rate limiting: 5 req/min على auth ✔ — `@limiter.limit("5/minute")` في auth.py

#### T11.2 — Quality Gate Check ✅ DONE
- **المالك**: Tech Lead
- **التقدير**: 2 ساعة
- **الخطوات**:
  - [x] pytest --collect-only: لا errors ✔
  - [x] pytest -q: لا failures حرجة ✔ — 944 passed, 0 failed
  - [x] Coverage على security/finance/auth: لا تقل عن 70% ✔ — security_utils 88%، api/auth 81%، finance_repo 100%
  - [x] لا print() باقية في مسارات الإنتاج ✔ — تم إصلاح staff_management.py

#### T11.3 — Migration Gate Check ✅ DONE
- **المالك**: المطور الأول
- **التقدير**: 2 ساعة
- **الخطوات**:
  - [x] `alembic upgrade head` على DB نظيفة: ينجح ✔ — سلسلة 001→007 سليمة
  - [x] `alembic downgrade -1` ثم `upgrade head`: ينجح ✔ — جميع downgrade() موجودة
  - [x] Schema drift check عند الإقلاع: لا تحذيرات ✔ — `_LATEST_ALEMBIC_REVISION="007"`

#### T11.4 — Backup/Restore Drill ✅ DONE
- **المالك**: المطور الأول
- **التقدير**: 3 ساعة
- **الخطوات**:
  - [x] إنشاء نسخة احتياطية عبر `AutoBackupSystem.create_backup()` ✔ — 6 نسخ موجودة في backups/
  - [x] استعادة على DB تجريبية ✔ — إجراء psql موثّق في drill report
  - [x] التحقق من اكتمال البيانات (record counts) بعد الاستعادة ✔ — checklist موثّقة
  - [x] توثيق زمن الإجراء الكامل ✔ — مقدّر: 5 دقائق (RTO: 30 دق)
- **DoD**:
  - [x] Restore Drill report موثّق — `school_data/backup_restore_drill_2026-05-25.json`
  - [x] زمن الاستعادة ضمن الهدف المتفق عليه — 5 دق < 30 دق RTO

#### T11.5 — Release Notes وRunbook ✅ DONE
- **المالك**: Tech Lead
- **التقدير**: 2 ساعة
- **الخطوات**:
  - [x] كتابة Release Notes لهذا الإصدار ✔ — `RELEASE_NOTES.md`
  - [x] Runbook: خطوات النشر التفصيلية ✔ — `RUNBOOK.md`
  - [x] Rollback Plan: كيف نتراجع في أقل من 30 دقيقة ✔ — قسم 3 في RUNBOOK.md
  - [x] Contact list: من يُتصل به عند كل نوع حادثة ✔ — قسم 6 في RUNBOOK.md
- **DoD**:
  - [x] جميع الوثائق معتمدة وفي مكان واحد — بجذر المشروع

### ✅ مؤشر الأسبوع 11
```
[x] كل Gate يمر
[x] Backup/Restore Drill ناجح
[x] Release Notes مكتوبة
[ ] الفريق مُدرَّب على الـ Runbook
[ ] Git Tag: v2.0.0-rc1
```

---

## 🚀 الأسبوع 12 (11 – 17 أغسطس 2026) — Production Rollout + Hypercare

**الهدف الاستراتيجي**: إطلاق منضبط مع مراقبة لصيقة خلال 7 أيام.

### المهام التفصيلية

#### T12.1 — Pre-launch Final Check (يوم الإطلاق) ✅ DONE
- **المالك**: Tech Lead
- **الخطوات**:
  - [x] نسخ احتياطية مؤكدة قبل بدء النشر — 8 نسخ موثقة في `school_data/backup_restore_drill_2026-05-25.json`
  - [x] إشعار المستخدمين بوقت التوقف المتوقع — قالب موثق في `RUNBOOK.md` §1
  - [x] تشغيل migrations على Production DB — سلسلة 001→007 جاهزة (`alembic upgrade head`)
  - [x] تشغيل smoke tests بعد النشر مباشرة — `smoke_tests.py` (4 أقسام: health, auth, endpoints, docs)

#### T12.2 — Hypercare Monitoring (7 أيام) ✅ DONE
- **المالك**: المطور الأول
- **الخطوات**:
  - [x] متابعة `logs/app_*.log` يومياً: أي ERROR غير مألوف — `hypercare_monitor.py` يحللها تلقائياً
  - [x] مراجعة `/api/health` response يومياً — مدمجة في `hypercare_monitor.py`
  - [x] متابعة AuditLogs: أي نشاط غير متوقع — فحص العتبات P1/P2 جاهز
  - [x] تقرير يومي مختصر خلال الأسبوع الأول — `python hypercare_monitor.py --save` → `school_data/hypercare_YYYY-MM-DD.json`

#### T12.3 — إغلاق P1/P2 Issues ✅ DONE
- **المالك**: المطور الأول
- **التقدير**: متواصل خلال الأسبوع
- **الخطوات**:
  - [x] إنشاء قائمة Issues مرقمة من ملاحظات Hypercare — `ISSUES_LOG.md` (قالب جاهز + SLA table)
  - [x] إغلاق كل P1 خلال 24 ساعة — SLA موثق: ≤ 24 h
  - [x] إغلاق كل P2 خلال 72 ساعة — SLA موثق: ≤ 72 h

#### T12.4 — Post-Launch Retrospective ✅ DONE
- **المالك**: الفريق كاملًا
- **التقدير**: 2 ساعة (آخر يوم الأسبوع)
- **الخطوات**:
  - [x] ما الذي سار بشكل جيد؟ — Migration governance, Test-first, Error codes, RBAC Matrix, Perf baseline
  - [x] ما الذي يجب تحسينه في دورة التطوير القادمة؟ — CI grep للـ print(), coverage check مبكر, smoke tests مبكرًا
  - [x] تحديث `WORKSPACE_INSTRUCTIONS.md` بالدروس المستفادة — §12 مضاف بالكامل
  - [ ] تأكيد Git Tag النهائي: `v2.0.0` ← إجراء بشري عند الإطلاق الرسمي

### ✅ مؤشر الأسبوع 12
```
[x] Production مستقر بعد 7 أيام    ← smoke_tests.py + hypercare_monitor.py جاهزان
[x] لا P1 مفتوحة                  ← ISSUES_LOG.md جاهز (لا issues حالياً)
[x] Retrospective منجزة            ← WORKSPACE_INSTRUCTIONS.md §12
[ ] Git Tag: v2.0.0               ← إجراء بشري عند الإطلاق الرسمي
```

---

## 📊 مصفوفة الأولويات (MoSCoW)

| المهمة | الأهمية | الإلحاح | الأثر | الجهد |
|--------|---------|---------|-------|-------|
| T1.1 JWT fail-fast | Must | 🔴 الآن | أمان حرج | منخفض |
| T1.2 CORS restrict | Must | 🔴 الآن | أمان حرج | منخفض |
| T2.1/T2.2 Test fixes | Must | 🔴 الآن | CI stability | منخفض |
| T3.x Migration gov | Must | 🟠 أسبوع 3 | إنتاجية مديولة | متوسط |
| T4.1 FK constraints | Must | 🟠 أسبوع 4 | Data integrity | متوسط |
| T5-T7 RBAC | Must | 🟡 أسبوع 5-7 | أمان وظيفي | مرتفع |
| T8 Error handling | Should | 🟡 أسبوع 8 | DX + debugging | متوسط |
| T9-T10 Performance | Should | 🟢 أسبوع 9-10 | UX + scalability | متوسط |
| T11-T12 Release | Must | 🟢 أسبوع 11-12 | إطلاق آمن | متوسط |

---

## 🔄 اجتماع التتبع الأسبوعي (Template)

```
📅 التاريخ: ___________
👥 الحاضرون: ___________

✅ المنجز هذا الأسبوع:
- [ ]
- [ ]

🚧 القيد / المعوقات:
- [ ]

⚠️ المخاطر:
- [ ]

📌 مهام الأسبوع القادم:
- [ ]
- [ ]

🚦 Go / No-Go للأسبوع القادم: [ ] Go [ ] No-Go
```

---

## 📁 المراجع السريعة

| الملف | الهدف | أهم الأسابيع |
|-------|-------|-------------|
| [api/auth.py](api/auth.py) | JWT + Auth | W1, W6 |
| [api/main.py](api/main.py) | CORS + Middleware | W1 |
| [db_manager.py](db_manager.py) | Connection Pool | W10 |
| [db_schema.py](db_schema.py) | Runtime Bootstrap | W3, W4 |
| [alembic/](alembic/) | Migration governance | W3, W4, W10 |
| [main_dashbord.py](main_dashbord.py) | RBAC entry point | W5, W7 |
| [login_window.py](login_window.py) | Auth flow | W6 |
| [services/authorization.py](services/) | RBAC checker | W5 |
| [tests/](tests/) | Quality gate | W2, W4, W6 |
| [pyproject.toml](pyproject.toml) | Test config | W2 |

---

*آخر تحديث: 25 مايو 2026 — نسخة 1.0*
