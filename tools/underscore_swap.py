# tools/underscore_swap.py

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt

from i18n import tr

class UnderscoreSwapDialog(QDialog):
    """Dialog chọn kiểu đổi dấu cách <-> underscore."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.choice = None

        self.setWindowTitle(tr("underscore_dialog_title"))
        self.setModal(True)
        self.resize(360, 150)

        layout = QVBoxLayout(self)

        label = QLabel(tr("underscore_dialog_desc"))
        label.setWordWrap(True)
        layout.addWidget(label)

        button_layout = QHBoxLayout()

        self.space_to_underscore_btn = QPushButton(tr("underscore_space_to_btn"))
        self.underscore_to_space_btn = QPushButton(tr("underscore_to_space_btn"))

        self.space_to_underscore_btn.clicked.connect(
            lambda: self._select("space_to_underscore")
        )
        self.underscore_to_space_btn.clicked.connect(
            lambda: self._select("underscore_to_space")
        )

        button_layout.addWidget(self.space_to_underscore_btn)
        button_layout.addWidget(self.underscore_to_space_btn)

        layout.addLayout(button_layout)

    def _select(self, choice):
        self.choice = choice
        self.accept()


def run_underscore_swap(parent):
    if not parent.images:
        QMessageBox.information(
            parent,
            tr("underscore_dialog_title"),
            tr("underscore_no_folder")
        )
        return

    dialog = UnderscoreSwapDialog(parent)

    if dialog.exec() != QDialog.Accepted:
        return

    choice = dialog.choice
    if not choice:
        return

    before = parent._snapshot()
    affected_images = 0
    changed_tags = 0

    for img in parent.images:
        old_tags = img.get("tags", [])
        new_tags = []
        image_changed = False

        for tag in old_tags:
            new_tag = tag

            if choice == "space_to_underscore":
                new_tag = "_".join(tag.split())
            elif choice == "underscore_to_space":
                new_tag = tag.replace("_", " ")

            new_tag = new_tag.strip()

            if new_tag != tag:
                image_changed = True
                changed_tags += 1

            if new_tag and new_tag not in new_tags:
                new_tags.append(new_tag)

        if image_changed:
            img["tags"] = new_tags
            img["modified"] = True
            affected_images += 1

    if changed_tags == 0:
        parent.statusBar().showMessage(tr("underscore_no_changes"))
        return

    if choice == "space_to_underscore":
        action = tr("underscore_action_space_to", count=affected_images)
    else:
        action = tr("underscore_action_to_space", count=affected_images)

    parent._push_history(action, before)
    parent._refresh_after_tag_change()

    parent.statusBar().showMessage(
        tr("underscore_success_status", action=action, changed_tags=changed_tags)
    )

def run_underscore_swap(parent):
    """
    Hiện dialog và đổi separator của toàn bộ tag
    trong folder hiện tại.
    """

    if not parent.images:
        return

    dialog = UnderscoreSwapDialog(parent)

    if dialog.exec() != QDialog.Accepted:
        return

    choice = dialog.choice
    if not choice:
        return

    # Snapshot để Undo
    before = parent._snapshot()

    affected_images = 0
    changed_tags = 0

    for img in parent.images:
        old_tags = img.get("tags", [])
        new_tags = []

        image_changed = False

        for tag in old_tags:
            new_tag = tag

            if choice == "space_to_underscore":
                # Đổi mọi whitespace thành _
                new_tag = "_".join(tag.split())

            elif choice == "underscore_to_space":
                # Đổi _ thành space
                new_tag = tag.replace("_", " ")

            # Không để tag rỗng
            new_tag = new_tag.strip()

            if new_tag != tag:
                image_changed = True
                changed_tags += 1

            # Tránh tạo duplicate tag trong cùng image
            if new_tag and new_tag not in new_tags:
                new_tags.append(new_tag)

        if image_changed:
            img["tags"] = new_tags
            img["modified"] = True
            affected_images += 1

    if changed_tags == 0:
        parent.statusBar().showMessage(tr("underscore_no_changes"))
        return

    # Push history
    if choice == "space_to_underscore":
        action = f"Space → Underscore ({affected_images} images)"
    else:
        action = f"Underscore → Space ({affected_images} images)"

    parent._push_history(action, before)

    # Refresh toàn bộ UI
    parent._refresh_after_tag_change()

    parent.statusBar().showMessage(
        tr("underscore_success_status", action=action, changed_tags=changed_tags)
    )
