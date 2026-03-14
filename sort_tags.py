"""
sort_tags.py
Logic sắp xếp tag — tách ra khỏi main_window để dễ test/reuse.

Sử dụng:
    from sort_tags import run_sort_tags
    run_sort_tags(main_window)
"""
from PySide6.QtWidgets import QMessageBox
from dialogs import SortTagsDialog
from i18n import tr


def run_sort_tags(win) -> bool:
    """
    Mở dialog chọn tags + position, sau đó sắp xếp.
    win: MainWindow instance (duck-typed).
    Trả về True nếu đã xử lý, False nếu bỏ qua.
    """
    if not win.images:
        QMessageBox.information(win, tr("notify_no_image"), tr("notify_no_image_msg"))
        return False

    dlg = SortTagsDialog(win.all_folder_tags, win)
    if dlg.exec() != SortTagsDialog.Accepted:
        return False

    chosen = dlg.get_selected_tags()
    if not chosen:
        QMessageBox.information(win, tr("notify_no_tag_selected"),
                                tr("notify_no_tag_selected_msg"))
        return False

    position = dlg.get_position()
    chosen_set = set(chosen)
    before = win._snapshot()
    affected = 0

    for idx, img in enumerate(win.images):
        present   = [t for t in img['tags'] if t in chosen_set]
        if not present:
            continue
        remaining = [t for t in img['tags'] if t not in chosen_set]
        img['tags'] = (present + remaining) if position == "beginning" else (remaining + present)
        img['modified'] = True
        win.image_grid.refresh_card(idx)
        affected += 1

    win._push_history(tr("history_sort_tags", tags=chosen, position=position), before)
    win._reload_tags_panel()
    QMessageBox.information(win, tr("sort_done"), tr("sort_done_msg", count=affected))
    return True
