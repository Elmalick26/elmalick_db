from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ui_styles import ThemeManager, apply_shadow_to_widget, get_card_style, get_table_style


def create_card(
    title: str | None = None,
    min_height: int = 0,
    layout_class=QVBoxLayout,
    with_shadow: bool = False,
) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setStyleSheet(get_card_style())
    if min_height > 0:
        frame.setMinimumHeight(min_height)

    layout = layout_class(frame)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)

    if with_shadow:
        apply_shadow_to_widget(frame)

    if title:
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-weight: bold; font-size: 13px;")
        lbl.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(lbl)

    return frame, layout


def card_frame(with_shadow: bool = False, min_height: int = 0) -> QFrame:
    """Styled card frame with NO pre-attached layout.
    Use this when calling code will set its own QHBoxLayout/QGridLayout on the frame."""
    frame = QFrame()
    frame.setStyleSheet(get_card_style())
    if min_height > 0:
        frame.setMinimumHeight(min_height)
    if with_shadow:
        apply_shadow_to_widget(frame)
    return frame


def styled_input(
    placeholder: str = "",
    min_height: int = 42,
    read_only: bool = False,
) -> QLineEdit:
    le = QLineEdit()
    le.setPlaceholderText(placeholder)
    le.setMinimumHeight(min_height)
    le.setReadOnly(read_only)
    colors = ThemeManager.get_colors()
    le.setStyleSheet(
        f"QLineEdit {{ padding: 10px 14px; border: 1.5px solid {colors.INPUT_BORDER};"
        f" border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-size: 13px; }}"
        f" QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}"
        f" QLineEdit:read-only {{ background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; }}"
    )
    return le


def styled_combo(min_height: int = 42) -> QComboBox:
    combo = QComboBox()
    combo.setMinimumHeight(min_height)
    colors = ThemeManager.get_colors()
    combo.setStyleSheet(
        f"QComboBox {{ padding: 10px 14px; border: 1.5px solid {colors.INPUT_BORDER};"
        f" border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-size: 13px; }}"
        f" QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; }}"
        f" QComboBox::drop-down {{ border: none; width: 26px; }}"
        f" QComboBox QAbstractItemView {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER};"
        f" selection-background-color: {colors.PRIMARY_LIGHT}; color: {colors.TEXT_PRIMARY}; }}"
    )
    return combo


def styled_date_edit(date_format: str = "yyyy-MM-dd", min_height: int = 42) -> QDateEdit:
    de = QDateEdit()
    de.setCalendarPopup(True)
    de.setDisplayFormat(date_format)
    de.setMinimumDate(de.minimumDate())
    de.setMaximumDate(de.maximumDate())
    de.setMinimumHeight(min_height)
    colors = ThemeManager.get_colors()
    de.setStyleSheet(
        f"QDateEdit {{ padding: 10px 14px; border: 1.5px solid {colors.INPUT_BORDER};"
        f" border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
        f" QDateEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; }}"
    )
    return de


def styled_spinbox(
    prefix: str = "",
    min_height: int = 42,
    max_value: float = 10000000,
    show_buttons: bool = False,
    read_only: bool = False,
) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(0, max_value)
    sb.setPrefix(prefix)
    sb.setButtonSymbols(
        QDoubleSpinBox.ButtonSymbols.NoButtons if not show_buttons else QDoubleSpinBox.ButtonSymbols.UpDownArrows
    )
    sb.setMinimumHeight(min_height)
    sb.setReadOnly(read_only)
    colors = ThemeManager.get_colors()
    sb.setStyleSheet(
        f"QDoubleSpinBox {{ padding: 10px 14px; border: 1.5px solid {colors.INPUT_BORDER};"
        f" border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-weight: bold; font-size: 13px; }}"
        f" QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}"
    )
    return sb


def style_table(table: QTableWidget) -> QTableWidget:
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.setStyleSheet(get_table_style())
    return table


def styled_time_edit(time_format: str = "HH:mm", min_height: int = 42) -> QTimeEdit:
    """Styled QTimeEdit matching the common input style."""
    te = QTimeEdit()
    te.setDisplayFormat(time_format)
    te.setMinimumHeight(min_height)
    colors = ThemeManager.get_colors()
    te.setStyleSheet(
        f"QTimeEdit {{ padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER};"
        f" border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-size: 13px; }}"
        f" QTimeEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}"
    )
    return te


def styled_text_edit(placeholder: str = "", min_height: int = 120) -> QTextEdit:
    editor = QTextEdit()
    if placeholder:
        editor.setPlaceholderText(placeholder)
    editor.setMinimumHeight(min_height)
    colors = ThemeManager.get_colors()
    editor.setStyleSheet(
        f"QTextEdit {{ padding: 10px 14px; border: 1.5px solid {colors.INPUT_BORDER};"
        f" border-radius: 8px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
        f" QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}"
    )
    return editor


def styled_button(
    label: str,
    bg_color: str | None = None,
    text_color: str = "white",
    hover_color: str | None = None,
    min_height: int = 42,
    object_name: str | None = None,
) -> QPushButton:
    btn = QPushButton(label)
    if object_name:
        btn.setObjectName(object_name)
    btn.setMinimumHeight(min_height)
    colors = ThemeManager.get_colors()
    bg = bg_color or colors.PRIMARY
    hover = hover_color or colors.PRIMARY_HOVER
    btn.setStyleSheet(
        f"QPushButton {{ background-color: {bg}; color: {text_color}; border-radius: 8px;"
        f" border: 2px solid transparent; padding: 10px 14px; }}"
        f"QPushButton:hover {{ background-color: {hover}; }}"
        f"QPushButton:focus {{ border: 2px solid {colors.BORDER_FOCUS}; outline: none; }}"
        f"QPushButton:pressed {{ background-color: {hover}; }}"
    )
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def compact_icon_btn(icon: str, tooltip: str, size: int = 32) -> QPushButton:
    """Icon-only button for secondary toolbar actions (print, export, import…)."""
    btn = QPushButton(icon)
    btn.setFixedSize(size, size)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    colors = ThemeManager.get_colors()
    btn.setStyleSheet(
        f"QPushButton {{ background:transparent; color:{colors.TEXT_SECONDARY};"
        f" border:1.5px solid {colors.BORDER}; border-radius:7px; font-size:15px; }}"
        f"QPushButton:hover {{ background:{colors.BG_MAIN}; color:{colors.TEXT_PRIMARY};"
        f" border-color:{colors.BORDER_FOCUS}; }}"
        f"QPushButton:pressed {{ background:{colors.PRIMARY_LIGHT}; }}"
    )
    return btn


class BaseWindow(QMainWindow):
    def __init__(self, title: str = "", min_width: int = 1100, min_height: int = 700, parent=None):
        super().__init__(parent)
        if title:
            self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)
        ThemeManager.apply_theme(self)

    @property
    def dialog_parent(self):
        return self.central_widget if getattr(self, "central_widget", None) is not None else self


def dialog_button_row(
    ok_text: str,
    ok_slot,
    cancel_slot,
    ok_name: str = "ok_btn",
    cancel_name: str = "cancel_btn",
    cancel_text: str = "Annuler",
) -> QHBoxLayout:
    colors = ThemeManager.get_colors()
    row = QHBoxLayout()
    row.setSpacing(8)

    cancel_btn = QPushButton(cancel_text)
    cancel_btn.setObjectName(cancel_name)
    cancel_btn.setMinimumHeight(38)
    cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    cancel_btn.setStyleSheet(
        f"QPushButton {{ background:transparent; color:{colors.TEXT_SECONDARY}; font-weight:600;"
        f" font-size:13px; border-radius:8px; border:1.5px solid {colors.BORDER}; padding:8px 18px; }}"
        f"QPushButton:hover {{ background:{colors.BG_MAIN}; color:{colors.TEXT_PRIMARY}; }}"
    )
    cancel_btn.clicked.connect(cancel_slot)

    ok_btn = QPushButton(ok_text)
    ok_btn.setObjectName(ok_name)
    ok_btn.setMinimumHeight(38)
    ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    ok_btn.setStyleSheet(
        f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f" stop:0 {colors.SUCCESS} stop:1 #16A34A);"
        f" color:white; font-weight:700; font-size:13px; border-radius:8px; border:none; padding:8px 20px; }}"
        f"QPushButton:hover {{ background:{colors.SUCCESS_HOVER}; }}"
    )
    ok_btn.setDefault(True)
    ok_btn.clicked.connect(ok_slot)
    cancel_btn.setAutoDefault(False)

    row.addStretch()
    row.addWidget(cancel_btn)
    row.addWidget(ok_btn)
    return row


def dialog_error_label(text: str = "") -> QLabel:
    """Red inline validation error label — hide when empty, show on validation failure."""
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setVisible(bool(text))
    colors = ThemeManager.get_colors()
    lbl.setStyleSheet(
        f"color: {colors.DANGER}; background: {colors.DANGER_LIGHT};"
        f" border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: 600;"
    )
    return lbl


class BaseDialog(QDialog):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        if title:
            self.setWindowTitle(title)
        ThemeManager.apply_theme(self)
        self.setMinimumWidth(420)
        self.setLayout(QVBoxLayout())
        self.dialog_layout = self.layout()
        if self.dialog_layout is not None:
            self.dialog_layout.setContentsMargins(20, 20, 20, 16)
            self.dialog_layout.setSpacing(14)

    def add_widget(self, widget):
        if self.dialog_layout is not None:
            self.dialog_layout.addWidget(widget)
        return widget

    def showEvent(self, event):
        super().showEvent(event)
        # Auto-focus the first editable input so keyboard users don't have to Tab first.
        QTimer.singleShot(0, self._focus_first_input)

    def _focus_first_input(self):
        for widget in self.findChildren((QLineEdit, QComboBox, QDateEdit, QTimeEdit, QDoubleSpinBox)):
            if not widget.isEnabled():
                continue
            if isinstance(widget, QLineEdit) and widget.isReadOnly():
                continue
            widget.setFocus()
            break


# ---------------------------------------------------------------------------
# Section label (used as form-group header inside dialogs)
# ---------------------------------------------------------------------------


def section_label(icon: str, text: str) -> QLabel:
    """Styled section header label — colored left-border badge.

    Example::
        lbl = section_label("👤", "المعلومات الشخصية")
    """
    colors = ThemeManager.get_colors()
    lbl = QLabel(f"{icon}  {text}" if icon else text)
    lbl.setStyleSheet(
        f"color: {colors.PRIMARY}; font-weight: 700; font-size: 12px;"
        f" padding: 6px 12px; border-radius: 8px;"
        f" background: {colors.PRIMARY_LIGHT};"
        f" border-left: 3px solid {colors.PRIMARY}; margin-top: 4px;"
    )
    return lbl


# ---------------------------------------------------------------------------
# FormSection — labeled group container
# ---------------------------------------------------------------------------


class FormSection(QFrame):
    """A vertically stacked form group with an optional section header.

    Usage::
        sec = FormSection("👤", "المعلومات الشخصية")
        sec.add_row("الاسم", styled_input("أدخل الاسم"))
        layout.addWidget(sec)
    """

    def __init__(self, icon: str = "", title: str = "", parent=None):
        super().__init__(parent)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(8)
        if title:
            self._outer.addWidget(section_label(icon, title))
        self._grid_widget = QWidget()
        self._grid = QVBoxLayout(self._grid_widget)
        self._grid.setContentsMargins(4, 0, 4, 0)
        self._grid.setSpacing(10)
        self._outer.addWidget(self._grid_widget)

    def add_row(self, label_text: str, widget, required: bool = False) -> None:
        """Add a label + widget pair as a form row."""
        colors = ThemeManager.get_colors()
        row = QVBoxLayout()
        row.setSpacing(4)
        text = f"{label_text} *" if required else label_text
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        row.addWidget(lbl)
        row.addWidget(widget)
        self._grid.addLayout(row)

    def add_widget(self, widget) -> None:
        """Add a widget directly without a label."""
        self._grid.addWidget(widget)


# ---------------------------------------------------------------------------
# Horizontal separator
# ---------------------------------------------------------------------------


def horizontal_separator() -> QFrame:
    """Thin horizontal rule for visual separation inside dialogs/forms."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    colors = ThemeManager.get_colors()
    sep.setStyleSheet(f"color: {colors.BORDER}; background: {colors.BORDER};")
    sep.setFixedHeight(1)
    return sep


def vertical_separator() -> QFrame:
    """Thin vertical rule for toolbar separation."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    colors = ThemeManager.get_colors()
    sep.setStyleSheet(f"color: {colors.BORDER}; background: {colors.BORDER};")
    sep.setFixedWidth(1)
    return sep


def set_tab_order(widgets: list) -> None:
    """Chain tab order for a list of widgets in sequence.

    Call after all widgets are added to the layout::

        set_tab_order([inp_name, inp_email, cmb_role, btn_save])
    """
    for i in range(len(widgets) - 1):
        QWidget.setTabOrder(widgets[i], widgets[i + 1])
