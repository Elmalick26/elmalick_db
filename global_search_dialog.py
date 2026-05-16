"""
global_search_dialog.py — نافذة البحث العالمي (Ctrl+K)

يبحث في 4 مصادر بالتوازي:
  • Students  — first_name_fr, last_name_fr, first_name_ar, last_name_ar
               (status != 'Archived')
  • Staff     — first_name, last_name, role
               (COALESCE(status,'Actif') != 'Archived')
  • Payments  — id (رقم الوصل)، details — مع JOIN Students للاسم
  • AuditLogs — actor, action, target

التفاصيل المخطط المراعاة:
  - Students.status = 'Active' | 'Archived' | ...
  - Staff.status    = 'Actif'  | 'Archived'
  - Payments.id     = SERIAL  — البحث عنه بـ CAST(id AS TEXT) ILIKE
  - AuditLogs: actor TEXT, action TEXT, target TEXT, timestamp TIMESTAMP
  - كل استعلامات %s (PostgreSQL)، وليس ?
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QLabel, QFrame, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QColor

from database_setup import DatabaseManager
from app_logger import AppLogger
from repositories.global_search_repo import GlobalSearchRepository
from ui_styles import ThemeManager


# نوع النتيجة: (category, display_text, subtitle, module_id, record_id)
ResultItem = tuple[str, str, str, str, int]

CATEGORY_ICONS = {
    "Élève": "👨‍🎓",
    "Personnel": "👥",
    "Paiement": "💰",
    "Audit": "🔍",
}

CATEGORY_MODULES = {
    "Élève": "student_management",
    "Personnel": "staff_management",
    "Paiement": "finance_payments",
    "Audit": None,          # pas de navigation pour audit
}


def _search(query: str, limit: int = 40) -> list[ResultItem]:
    """
    Exécute les 4 requêtes et retourne une liste fusionnée de résultats.
    Appelée depuis le thread principal (résultats < 40 ms sur réseau local).
    """
    results: list[ResultItem] = []
    if not query.strip():
        return results

    pat = f"%{query.strip()}%"

    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            results.extend(GlobalSearchRepository(conn).search_all(pat, limit))
    except Exception as e:
        AppLogger.error("GlobalSearch", f"Search error: {e}")

    return results


class GlobalSearchDialog(QDialog):
    """
    Fenêtre de recherche globale activée par Ctrl+K.

    Signal:
        navigate_to(module_id: str, record_id: int)
        → émis quand l'utilisateur clique sur un résultat navigable.
    """

    navigate_to = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)
        ThemeManager.apply_theme(self)
        self._results: list[ResultItem] = []
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)      # 250 ms debounce
        self._debounce.timeout.connect(self._do_search)
        self._build_ui()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        colors = ThemeManager.get_colors()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # carte principale
        card = QFrame()
        card.setMinimumWidth(580)
        card.setMaximumWidth(680)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {colors.BG_CARD};
                border-radius: 14px;
                border: 1px solid {colors.BORDER};
            }}
        """)

        vlay = QVBoxLayout(card)
        vlay.setContentsMargins(16, 14, 16, 14)
        vlay.setSpacing(10)

        # — champ de recherche —
        search_row = QHBoxLayout()
        lbl_glass = QLabel("🔍")
        lbl_glass.setStyleSheet("font-size: 18px; border: none;")
        search_row.addWidget(lbl_glass)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Recherche globale... / البحث العام  (Esc pour fermer)")
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none;
                color: {colors.TEXT_PRIMARY}; font-size: 15px; padding: 2px 4px;
            }}
        """)
        self.txt_search.textChanged.connect(lambda: self._debounce.start())
        self.txt_search.installEventFilter(self)
        search_row.addWidget(self.txt_search, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 11px; border: none;")
        search_row.addWidget(self.lbl_count)

        vlay.addLayout(search_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {colors.BORDER}; max-height: 1px; border: none;")
        vlay.addWidget(sep)

        # — liste des résultats —
        self.result_list = QListWidget()
        self.result_list.setMinimumHeight(60)
        self.result_list.setMaximumHeight(400)
        self.result_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent; border: none;
                outline: none;
            }}
            QListWidget::item {{
                border-radius: 8px; padding: 6px 8px;
                color: {colors.TEXT_PRIMARY};
            }}
            QListWidget::item:selected, QListWidget::item:hover {{
                background-color: {colors.PRIMARY}22;
            }}
        """)
        self.result_list.itemActivated.connect(self._on_activate)
        self.result_list.itemDoubleClicked.connect(self._on_activate)
        vlay.addWidget(self.result_list)

        # — pied de page —
        footer = QLabel("↑↓ naviguer  •  Entrée sélectionner  •  Esc fermer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 10px; border: none;")
        vlay.addWidget(footer)

        outer.addWidget(card)

    # ---------------------------------------------------------------- Events
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self.txt_search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.close()
                return True
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                self.result_list.setFocus()
                row = self.result_list.currentRow()
                total = self.result_list.count()
                if key == Qt.Key.Key_Down:
                    self.result_list.setCurrentRow(min(row + 1, total - 1))
                else:
                    self.result_list.setCurrentRow(max(row - 1, 0))
                return True
            if key == Qt.Key.Key_Return:
                item = self.result_list.currentItem()
                if item:
                    self._on_activate(item)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.txt_search.clear()
        self.result_list.clear()
        self.lbl_count.setText("")
        self.txt_search.setFocus()
        self._center_on_parent()

    # ---------------------------------------------------------------- Logic
    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            pg = parent.geometry()
            w, h = self.sizeHint().width() or 600, self.sizeHint().height() or 300
            x = pg.x() + (pg.width() - w) // 2
            y = pg.y() + int(pg.height() * 0.18)
            self.move(x, y)

    def _do_search(self):
        query = self.txt_search.text().strip()
        self.result_list.clear()
        self._results.clear()

        if len(query) < 2:
            self.lbl_count.setText("")
            return

        self._results = _search(query)
        self.lbl_count.setText(f"{len(self._results)} résultat(s)")
        colors = ThemeManager.get_colors()

        for category, title, subtitle, module_id, record_id in self._results:
            icon = CATEGORY_ICONS.get(category, "•")
            navigable = module_id is not None

            item_widget = _ResultItemWidget(
                icon, category, title, subtitle, navigable, colors
            )
            list_item = QListWidgetItem(self.result_list)
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, (module_id, record_id))
            self.result_list.setItemWidget(list_item, item_widget)

        if self._results:
            self.result_list.setCurrentRow(0)

        # ajuster la hauteur dynamiquement
        count = min(len(self._results), 8)
        self.result_list.setMaximumHeight(max(60, count * 64))
        self.adjustSize()
        self._center_on_parent()

    def _on_activate(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        module_id, record_id = data
        if module_id:
            self.navigate_to.emit(module_id, record_id)
        self.close()


class _ResultItemWidget(QWidget):
    """Widget personnalisé pour chaque ligne de résultat"""

    def __init__(self, icon, category, title, subtitle, navigable, colors):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(10)

        lbl_icon = QLabel(icon)
        lbl_icon.setFixedWidth(28)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 18px; border: none;")
        lay.addWidget(lbl_icon)

        text_vlay = QVBoxLayout()
        text_vlay.setSpacing(1)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {colors.TEXT_PRIMARY}; border: none;")
        text_vlay.addWidget(lbl_title)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet(f"font-size: 11px; color: {colors.TEXT_SECONDARY}; border: none;")
            text_vlay.addWidget(lbl_sub)

        lay.addLayout(text_vlay, 1)

        lbl_cat = QLabel(category)
        cat_color = {
            "Élève": colors.PRIMARY, "Personnel": colors.SECONDARY,
            "Paiement": colors.SUCCESS, "Audit": colors.WARNING,
        }.get(category, colors.BORDER)
        lbl_cat.setStyleSheet(f"""
            QLabel {{
                background: {cat_color}22; color: {cat_color};
                border: 1px solid {cat_color}55; border-radius: 8px;
                padding: 2px 8px; font-size: 10px; font-weight: bold;
            }}
        """)
        lay.addWidget(lbl_cat)

        if navigable:
            lbl_arrow = QLabel("→")
            lbl_arrow.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 14px; border: none;")
            lay.addWidget(lbl_arrow)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
