# دليل التصميم المعياري — El Malick Gest
## Guide de Design — El Malick Gest

> Version 2026-06-07 · Python 3.12 / PyQt6
> هذا الملف هو المرجع الوحيد للتصميم في المشروع. أي مكوّن جديد يجب أن يتبع هذا الدليل.

---

## 1. نظام الألوان — Système de couleurs

جميع الألوان تُقرأ من `ThemeManager.get_colors()`. **لا تضع ألواناً ثابتة (hex) مباشرةً في الكود.**

```python
from ui_styles import ThemeManager

colors = ThemeManager.get_colors()  # يعيد Colors أو DarkColors حسب الثيم الحالي
```

### الألوان الأساسية

| الاسم | Light | Dark | الاستخدام |
|-------|-------|------|-----------|
| `PRIMARY` | `#4F46E5` Indigo | `#818CF8` | أزرار الإجراء الرئيسي، تركيز الحدود |
| `SECONDARY` | `#7C3AED` Violet | `#A78BFA` | إجراءات ثانوية، شارات |
| `SUCCESS` | `#059669` Emerald | `#34D399` | تأكيد، حفظ ناجح |
| `WARNING` | `#D97706` Amber | `#FBBF24` | تحذيرات، حالات انتبه |
| `DANGER` | `#DC2626` Red | `#F87171` | حذف، خطأ، خروج |
| `INFO` | `#0284C7` Sky | `#38BDF8` | معلومات، تلميح |

### ألوان الخلفية

| الاسم | الاستخدام |
|-------|-----------|
| `BG_MAIN` | الخلفية العامة للصفحة — خلف البطاقات |
| `BG_CARD` | سطح البطاقة / الحوار |
| `SIDEBAR_BG` | القائمة الجانبية الداكنة |
| `INPUT_BG` | خلفية حقول الإدخال في حالة الراحة |
| `INPUT_BG_FOCUS` | خلفية حقل الإدخال عند التركيز |

### ألوان النص

| الاسم | الاستخدام |
|-------|-----------|
| `TEXT_PRIMARY` | نص رئيسي، عناوين، بيانات جدول |
| `TEXT_SECONDARY` | تسميات حقول، نص مساعد، timestamps |
| `HEADER_TEXT` | نص على خلفيات داكنة (sidebar، header) |

---

## 2. البطاقات — Cartes

### create_card — بطاقة مع عنوان وـ layout جاهز

```python
from ui_components import create_card

# ✅ استخدام صحيح — يُعيد (frame, layout) يضيف المحتوى على layout
card, layout = create_card("📋 قائمة الطلاب")
layout.addWidget(my_table)
parent_layout.addWidget(card)

# مع حجم أدنى وظل
card, layout = create_card("📊 إحصائيات", min_height=200, with_shadow=True)
```

### card_frame — بطاقة بدون layout مرفق

```python
from ui_components import card_frame

# ✅ عندما تريد إضافة QHBoxLayout أو QGridLayout على الـ frame مباشرةً
frame = card_frame()
toolbar = QHBoxLayout(frame)   # ← أمان — الـ frame بدون layout مسبق
toolbar.addWidget(btn_add)
toolbar.addWidget(btn_delete)

# مع ظل وارتفاع أدنى
frame = card_frame(with_shadow=True, min_height=60)
```

> **قاعدة مهمة:** `create_card()` تُنشئ `QVBoxLayout` على الـ frame داخلياً.
> إذا أضفت layout ثانياً على نفس الـ frame، Qt يرفض الربط صامتاً → ينشئ layout بدون parent → كل الـ widgets تطير كنوافذ مستقلة.
> **الحل:** `create_card()` إذا ستضيف على `layout`، و`card_frame()` إذا ستضيف `QHBoxLayout(frame)` أو `QGridLayout(frame)`.

---

## 3. الجداول — Tables

```python
from ui_components import style_table
from PyQt6.QtWidgets import QTableWidget

# ✅ الطريقة الصحيحة الوحيدة
self.table = QTableWidget()
self.table.setColumnCount(4)
self.table.setHorizontalHeaderLabels(["الاسم", "القسم", "الحضور", "الإجراء"])
style_table(self.table)  # ← يطبق كل الإعدادات المعيارية دفعةً واحدة
```

`style_table()` تطبق:
- `setShowGrid(False)` — بدون شبكة
- `setAlternatingRowColors(True)` — تلوين متناوب للصفوف
- `setSelectionBehavior(SelectRows)` — تحديد الصف كاملاً
- `setEditTriggers(NoEditTriggers)` — الجدول للقراءة فقط
- `verticalHeader().setVisible(False)` — إخفاء الأرقام الجانبية
- `setStyleSheet(get_table_style())` — النمط الكامل بألوان الثيم

---

## 4. التبويبات — Onglets

```python
from ui_styles import get_tabs_style
from PyQt6.QtWidgets import QTabWidget

tabs = QTabWidget()
tabs.setStyleSheet(get_tabs_style())
tabs.addTab(widget_students, "👨‍🎓 الطلاب")
tabs.addTab(widget_reports, "📊 التقارير")
```

---

## 5. حقول الإدخال — Champs de saisie

```python
from ui_components import (
    styled_input, styled_combo, styled_date_edit,
    styled_time_edit, styled_spinbox, styled_text_edit,
)

# نص حر
name_input = styled_input("أدخل الاسم الكامل")

# نص للقراءة فقط
code_input = styled_input("كود الطالب", read_only=True)

# قائمة منسدلة
class_combo = styled_combo()
class_combo.addItems(["الابتدائي", "الإعدادي", "الثانوي"])

# تاريخ
birth_date = styled_date_edit("yyyy-MM-dd")

# وقت
start_time = styled_time_edit("HH:mm")

# رقم (مبلغ مالي)
amount = styled_spinbox(prefix="FCFA ", max_value=9_999_999)

# نص طويل (ملاحظة)
notes = styled_text_edit("أدخل الملاحظات...", min_height=100)
```

---

## 6. الأزرار — Boutons

```python
from ui_components import styled_button
from ui_styles import ThemeManager

colors = ThemeManager.get_colors()

# زر إجراء رئيسي (أزرق/indigo)
btn_save = styled_button("💾 حفظ", bg_color=colors.PRIMARY)

# زر حذف (أحمر)
btn_delete = styled_button("🗑️ حذف", bg_color=colors.DANGER)

# زر نجاح (أخضر)
btn_confirm = styled_button("✅ تأكيد", bg_color=colors.SUCCESS)

# زر تحذير (برتقالي)
btn_archive = styled_button("📦 أرشفة", bg_color=colors.WARNING, text_color="#1C1400")

# زر ثانوي (شفاف بحدود)
btn_cancel = styled_button("إلغاء", bg_color="transparent",
                            text_color=colors.TEXT_SECONDARY)

# تخصيص الارتفاع الأدنى
btn_wide = styled_button("تصدير Excel", bg_color=colors.SUCCESS, min_height=38)
```

---

## 7. تسميات الأقسام والفواصل — Labels de section

```python
from ui_components import section_label, horizontal_separator, vertical_separator, FormSection

# عنوان قسم داخل نموذج
lbl = section_label("👤", "المعلومات الشخصية")
layout.addWidget(lbl)

# فاصل أفقي
layout.addWidget(horizontal_separator())

# فاصل عمودي (في toolbar)
toolbar.addWidget(vertical_separator())

# مجموعة نموذج كاملة
sec = FormSection("📅", "بيانات التسجيل")
sec.add_row("تاريخ الميلاد", styled_date_edit(), required=True)
sec.add_row("الجنسية", styled_combo())
sec.add_row("ملاحظات", styled_text_edit())
layout.addWidget(sec)
```

---

## 8. الحوارات — Dialogues

### الهيكل المعياري

```python
from ui_components import BaseDialog, dialog_button_row, dialog_error_label, section_label
from ui_components import styled_input, styled_combo, styled_date_edit

class StudentDialog(BaseDialog):
    def __init__(self, student=None, parent=None):
        super().__init__("إضافة طالب / Ajouter un élève", parent)
        self.setMinimumWidth(500)
        self._build_ui()
        if student:
            self._fill(student)

    def _build_ui(self):
        # ── رسالة الخطأ (مخفية افتراضياً) ──
        self.err_label = dialog_error_label()
        self.dialog_layout.addWidget(self.err_label)

        # ── قسم المعلومات الشخصية ──
        self.dialog_layout.addWidget(section_label("👤", "المعلومات الشخصية"))

        self.inp_name = styled_input("الاسم الكامل")
        self.dialog_layout.addWidget(self.inp_name)

        self.cmb_class = styled_combo()
        self.cmb_class.addItems(["1A", "1B", "2A"])
        self.dialog_layout.addWidget(self.cmb_class)

        # ── صف الأزرار ──
        self.dialog_layout.addLayout(
            dialog_button_row("💾 حفظ", self._save, self.reject)
        )

    def _save(self):
        name = self.inp_name.text().strip()
        if not name:
            # ✅ التحقق inline — لا QMessageBox.warning()
            self.err_label.setText("الاسم مطلوب / Le nom est obligatoire")
            self.err_label.setVisible(True)
            return
        self.err_label.setVisible(False)
        self.accept()

    def _fill(self, student):
        self.inp_name.setText(student.full_name)
```

### قواعد الحوارات

| القاعدة | التفاصيل |
|---------|---------|
| يرث من `BaseDialog` | يطبق الثيم تلقائياً، `self.dialog_layout` جاهز |
| لا `QVBoxLayout(self)` | `BaseDialog.__init__` ينشئه مسبقاً — إضافة ثانٍ يسبب تعارضاً |
| `dialog_error_label()` للتحقق | رسالة حمراء inline بدلاً من `QMessageBox.warning()` |
| `dialog_button_row()` للأزرار | "Annuler" يسار + "Enregistrer" يمين بشكل موحد |
| `setMinimumWidth(420+)` | الحوارات الصغيرة 420px، المعقدة 600px |

---

## 9. نافذة الوحدات — Fenêtre de module

```python
from ui_components import BaseWindow

class MyModuleWindow(BaseWindow):
    def __init__(self):
        super().__init__("عنوان الوحدة", min_width=1100, min_height=700)
        self._build_ui()

    def _build_ui(self):
        # self.main_layout جاهز — QVBoxLayout بهوامش (24,20,24,20)
        card, layout = create_card("📋 البيانات")
        layout.addWidget(...)
        self.main_layout.addWidget(card)
```

---

## 10. بطاقات KPI — KPI Cards

```python
from ui_styles import KpiCard, ThemeManager

colors = ThemeManager.get_colors()

kpi = KpiCard("👨‍🎓", "إجمالي الطلاب", "0", colors.PRIMARY, theme_mode="default")
kpi_revenue = KpiCard("💰", "الإيرادات", "0 FCFA", colors.SUCCESS, theme_mode="default")
```

---

## 11. معالجة أخطاء قاعدة البيانات — Erreurs DB

```python
from ui_styles import friendly_db_error

try:
    db.execute(...)
except Exception as e:
    QMessageBox.critical(self, "خطأ", friendly_db_error(e))
    # ✅ رسالة خطأ مفهومة للمستخدم — لا stack trace خام
```

---

## 12. مساعدات PDF — Helpers PDF

كل دوال PDF مركزة في `pdf_helpers.py`. **لا تعرّف هذه الدوال محلياً في الوحدات.**

```python
from pdf_helpers import (
    get_arabic_font_path,     # مسار خط عربي متاح
    contains_arabic,          # هل النص يحتوي عربي؟
    prepare_pdf_text,         # reshape + bidi للنص العربي
    sanitize_latin,           # تنظيف الحروف غير المدعومة
)
```

---

## 13. أمثلة من شاشات حقيقية

### مثال 1 — شاشة إدارة الطلاب (student_management.py)

```python
class StudentManagementWindow(BaseWindow):
    def __init__(self):
        super().__init__("إدارة الطلاب")
        self._build_ui()

    def _build_ui(self):
        # شريط البحث والأزرار
        toolbar_frame = card_frame(min_height=60)
        toolbar = QHBoxLayout(toolbar_frame)          # ← card_frame بدون layout مسبق
        self.search_input = styled_input("🔍 بحث...")
        toolbar.addWidget(self.search_input)
        toolbar.addWidget(vertical_separator())
        toolbar.addWidget(styled_button("➕ طالب جديد", bg_color=ThemeManager.get_colors().PRIMARY))
        self.main_layout.addWidget(toolbar_frame)

        # جدول البيانات
        data_card, data_layout = create_card("👨‍🎓 قائمة الطلاب")
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        style_table(self.table)
        data_layout.addWidget(self.table)
        self.main_layout.addWidget(data_card)
```

### مثال 2 — شاشة المالية (finance_payments.py)

```python
class FinancePaymentsWindow(BaseWindow):
    def __init__(self):
        super().__init__("سجل المدفوعات")
        self._build_ui()

    def _build_ui(self):
        # تبويبات المدفوعات
        tabs = QTabWidget()
        tabs.setStyleSheet(get_tabs_style())

        # تبويب الدفعات المعلقة
        pending_widget = QWidget()
        pending_layout = QVBoxLayout(pending_widget)
        pending_table = QTableWidget()
        style_table(pending_table)
        pending_layout.addWidget(pending_table)
        tabs.addTab(pending_widget, "⏳ معلقة")

        # تبويب الدفعات المؤكدة
        confirmed_widget = QWidget()
        confirmed_layout = QVBoxLayout(confirmed_widget)
        confirmed_table = QTableWidget()
        style_table(confirmed_table)
        confirmed_layout.addWidget(confirmed_table)
        tabs.addTab(confirmed_widget, "✅ مؤكدة")

        self.main_layout.addWidget(tabs)
```

### مثال 3 — حوار إدخال العقوبة (student_discipline.py)

```python
class DisciplineEntryDialog(BaseDialog):
    def __init__(self, student_name: str, parent=None):
        super().__init__(f"تسجيل مخالفة — {student_name}", parent)
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        self.err_label = dialog_error_label()
        self.dialog_layout.addWidget(self.err_label)

        self.dialog_layout.addWidget(section_label("📅", "تفاصيل المخالفة"))

        self.date_edit = styled_date_edit()
        self.dialog_layout.addWidget(self.date_edit)

        self.cmb_type = styled_combo()
        self.cmb_type.addItems(["غياب بدون عذر", "سلوك سيء", "تأخر"])
        self.dialog_layout.addWidget(self.cmb_type)

        self.notes_edit = styled_text_edit("ملاحظات إضافية...")
        self.dialog_layout.addWidget(self.notes_edit)

        self.dialog_layout.addWidget(horizontal_separator())
        self.dialog_layout.addLayout(
            dialog_button_row("💾 تسجيل", self._save, self.reject)
        )

    def _save(self):
        if self.cmb_type.currentIndex() < 0:
            self.err_label.setText("يجب اختيار نوع المخالفة")
            self.err_label.setVisible(True)
            return
        self.err_label.setVisible(False)
        self.accept()
```

---

## 14. ✅ مسموح — ❌ ممنوع

### ✅ مسموح

| النمط | السبب |
|-------|-------|
| `create_card(title)` → `(frame, layout)` | بطاقة مع `QVBoxLayout` جاهز |
| `card_frame()` → `frame` ثم `QHBoxLayout(frame)` | بطاقة بدون layout مسبق |
| `style_table(self.table)` | يطبق كل الإعدادات دفعةً واحدة |
| `tabs.setStyleSheet(get_tabs_style())` | نمط موحد لجميع التبويبات |
| `styled_input/combo/date_edit/...` | حقول متسقة مع الثيم |
| `styled_button(label, bg_color=colors.X)` | أزرار موحدة |
| `BaseDialog` + `dialog_error_label()` | تحقق inline بدلاً من نوافذ منبثقة |
| `friendly_db_error(e)` | رسائل خطأ مفهومة |
| `ThemeManager.get_colors().X` | ألوان تتبع الثيم تلقائياً |

### ❌ ممنوع

| النمط | السبب والبديل |
|-------|--------------|
| `QFrame.setStyleSheet("background:...; border-radius:16px")` محلياً | ← استخدم `card_frame()` أو `create_card()` |
| `QHBoxLayout(frame)` على frame أعادته `create_card()` | ← يسبب الأزرار الطائرة — استخدم `card_frame()` |
| `table.setStyleSheet(get_table_style())` مباشرةً | ← استخدم `style_table(table)` الكاملة |
| إعادة تعريف `_get_arabic_font_path`, `_contains_arabic`, `_prepare_pdf_text`, `_sanitize_latin` محلياً | ← استورد من `pdf_helpers` |
| `QMessageBox.warning(self, "خطأ", "الحقل مطلوب")` للتحقق من الحقول | ← استخدم `dialog_error_label()` inline |
| ألوان hex ثابتة مثل `color: #4F46E5` في `setStyleSheet` | ← استخدم `colors.PRIMARY` من `ThemeManager.get_colors()` |
| `QVBoxLayout(self)` داخل `BaseDialog.__init__` | ← `self.dialog_layout` موجود مسبقاً |
| `super().__init__` ثم `self.setLayout(...)` في `BaseDialog` | ← نفس السبب |
| نسخ كود `style_table` يدوياً مع إعدادات ناقصة | ← دائماً `style_table()` من `ui_components` |

---

## 15. خلاصة الاستيرادات المعيارية

```python
# المكونات المرئية
from ui_components import (
    create_card, card_frame,
    styled_input, styled_combo, styled_date_edit, styled_time_edit,
    styled_spinbox, styled_text_edit,
    styled_button,
    style_table,
    BaseWindow, BaseDialog,
    dialog_button_row, dialog_error_label,
    section_label, FormSection,
    horizontal_separator, vertical_separator,
    set_tab_order,   # ترتيب Tab بين الحقول في الحوارات
)

# الثيم والأنماط
from ui_styles import (
    ThemeManager,
    get_tabs_style,
    KpiCard,
    friendly_db_error,
    get_module_caps,   # للـ RBAC على مستوى الأزرار
)

# مساعدات PDF
from pdf_helpers import (
    get_arabic_font_path, contains_arabic,
    prepare_pdf_text, sanitize_latin,
)
```

---

*آخر تحديث: 2026-06-07 — الوحدة 5 من خطة توحيد واجهة المستخدم*
