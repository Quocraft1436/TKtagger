"""
remove_duplicate_tags.py
Logic xóa tag trùng — tách ra khỏi main_window để dễ test/reuse.
"""
from PySide6.QtWidgets import QMessageBox
from i18n import tr


def run_remove_duplicates(win) -> bool:

    if not win.current_folder:
        QMessageBox.information(win, tr("notify_no_folder"), tr("notify_no_folder_msg"))
        return False

    if QMessageBox.question(
        win, tr("remove_dup_confirm_title"), tr("remove_dup_confirm_msg"),
        QMessageBox.Yes | QMessageBox.No
    ) != QMessageBox.Yes:
        return False

    before = win._snapshot()
    for idx, img in enumerate(win.images):
        img['tags'] = list(dict.fromkeys(img['tags']))
        img['modified'] = True
        win.image_grid.refresh_card(idx)

    win._push_history(tr("history_remove_dup"), before)
    win._reload_tags_panel()
    QMessageBox.information(win, tr("remove_dup_done"), tr("remove_dup_done_msg"))
    return True
