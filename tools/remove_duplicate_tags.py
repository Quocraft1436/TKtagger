"""
remove_duplicate_tags.py remove duplicate tags from images.
"""
from PySide6.QtWidgets import QMessageBox
from i18n import tr

def run_remove_duplicates(win) -> bool:
    if not win.images:
        QMessageBox.information(win, tr("ldl_no_images"), tr("notify_no_image_msg"))
        return False
    
    if not win.all_folder_tags:
        QMessageBox.information(win, tr("ldl_no_tags"), tr("notify_no_tags_msg"))
        return False

    # Execute removal
    before = win._snapshot()
    for idx, img in enumerate(win.images):
        img['tags'] = list(dict.fromkeys(img['tags']))
        img['modified'] = True
        win.image_grid.refresh_card(idx)

    win._push_history(tr("history_remove_dup"), before)
    win._reload_tags_panel()
    QMessageBox.information(win, tr("remove_dup_done"), tr("remove_dup_done_msg"))
    return True
