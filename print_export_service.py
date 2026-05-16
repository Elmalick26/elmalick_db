import os
import subprocess
import tempfile
from datetime import datetime
from uuid import uuid4

from PyQt6.QtWidgets import QFileDialog, QMessageBox

try:
    from config_manager import ConfigManager
except Exception:
    ConfigManager = None


VALID_OUTPUT_MODES = {"save", "open", "print"}

STANDARD_SUCCESS_TITLE = "Succès / نجاح"
STANDARD_ERROR_TITLE = "Erreur / خطأ"
STANDARD_SAVE_MESSAGE_AR = "تم إنشاء ملف PDF بنجاح."
STANDARD_PRINT_MESSAGE_AR = "تم إرسال المستند إلى الطابعة بنجاح."
STANDARD_FALLBACK_MESSAGE_AR = "الطباعة المباشرة غير متاحة. تم فتح الملف للطباعة اليدوية."
REPORTS_SECTION = "REPORTS"
LAST_SAVE_DIR_KEY = "last_save_dir"


def normalize_output_mode(mode):
    value = (mode or "save").strip().lower()
    return value if value in VALID_OUTPUT_MODES else "save"


def get_report_output_mode(report_key, fallback="save"):
    fallback_mode = normalize_output_mode(fallback)
    if ConfigManager is None:
        return fallback_mode

    try:
        config = ConfigManager()
        configured = config.get("PRINT", report_key, fallback_mode)
        return normalize_output_mode(configured)
    except Exception:
        return fallback_mode


def open_file(filepath):
    if os.name == "nt":
        os.startfile(filepath)
        return
    subprocess.call(("xdg-open", filepath))


def direct_print_file(filepath):
    if os.name == "nt":
        try:
            os.startfile(filepath, "print")
            return "printed"
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1155:
                try:
                    os.startfile(filepath)
                    return "opened"
                except Exception:
                    raise RuntimeError("Aucune application PDF n'est associée pour l'ouverture/impression.\nلا يوجد تطبيق PDF مرتبط بالفتح/الطباعة.") from exc
            raise
    open_file(filepath)
    return "opened"


def _compose_bilingual_message(fr_message, ar_fallback):
    fr_text = (fr_message or "").strip()
    if not fr_text:
        return ar_fallback
    if "\n" in fr_text and any("\u0600" <= ch <= "\u06FF" for ch in fr_text):
        return fr_text
    return f"{fr_text}\n{ar_fallback}"


def _get_last_save_dir():
    if ConfigManager is None:
        return ""
    try:
        config = ConfigManager()
        return (config.get(REPORTS_SECTION, LAST_SAVE_DIR_KEY, "") or "").strip()
    except Exception:
        return ""


def _set_last_save_dir(file_path):
    if ConfigManager is None:
        return
    directory = os.path.dirname(file_path or "")
    if not directory:
        return
    try:
        config = ConfigManager()
        config.set(REPORTS_SECTION, LAST_SAVE_DIR_KEY, directory)
    except Exception:
        pass


def _build_initial_save_path(default_name):
    last_dir = _get_last_save_dir()
    if last_dir and os.path.isdir(last_dir):
        return os.path.join(last_dir, default_name)
    return default_name


def _ensure_unique_file_path(file_path):
    if not file_path or not os.path.exists(file_path):
        return file_path

    directory, filename = os.path.split(file_path)
    stem, ext = os.path.splitext(filename)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    candidate = os.path.join(directory, f"{stem}_{stamp}{ext}")
    if not os.path.exists(candidate):
        return candidate

    counter = 2
    while True:
        candidate = os.path.join(directory, f"{stem}_{stamp}_{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def output_pdf(
    pdf,
    parent,
    default_name,
    mode="save",
    dialog_title="Enregistrer PDF",
    file_filter="PDF Files (*.pdf)",
    success_title=STANDARD_SUCCESS_TITLE,
    success_save_message="PDF généré.",
    success_print_message="Document envoyé à l'imprimante.",
    success_open_fallback_message="Impression directe indisponible. Le PDF a été ouvert pour impression manuelle.",
):
    selected_mode = normalize_output_mode(mode)
    file_path = None

    try:
        if selected_mode in ("save", "open"):
            initial_path = _build_initial_save_path(default_name)
            file_path, _ = QFileDialog.getSaveFileName(parent, dialog_title, initial_path, file_filter)
            if not file_path:
                return None
            final_path = _ensure_unique_file_path(file_path)
            pdf.output(final_path)
            _set_last_save_dir(final_path)
            if selected_mode == "open":
                open_file(final_path)

            save_message = success_save_message
            if final_path != file_path:
                save_message = f"{success_save_message}\nNom ajusté pour éviter l'écrasement: {os.path.basename(final_path)}"

            QMessageBox.information(
                parent,
                STANDARD_SUCCESS_TITLE,
                _compose_bilingual_message(save_message, STANDARD_SAVE_MESSAGE_AR),
            )
            return final_path

        temp_name = f"print_{uuid4().hex}.pdf"
        temp_path = os.path.join(tempfile.gettempdir(), temp_name)
        pdf.output(temp_path)
        print_status = direct_print_file(temp_path)
        if print_status == "printed":
            QMessageBox.information(
                parent,
                STANDARD_SUCCESS_TITLE,
                _compose_bilingual_message(success_print_message, STANDARD_PRINT_MESSAGE_AR),
            )
        else:
            QMessageBox.information(
                parent,
                STANDARD_SUCCESS_TITLE,
                _compose_bilingual_message(success_open_fallback_message, STANDARD_FALLBACK_MESSAGE_AR),
            )
        return temp_path

    except Exception as exc:
        QMessageBox.critical(parent, STANDARD_ERROR_TITLE, str(exc))
        return None
