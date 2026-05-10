# File: libs/draggable_list.py
from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QAbstractItemView,
    QWidget, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal
from typing import Any, Callable, Optional


class CustomItemWidget(QWidget):
    delete_requested = Signal(object)  # emits item_ref

    def __init__(
        self,
        text: str,
        show_delete: bool = False,
        item_ref=None,
        delete_label: str = "✕",
        data: Any = None,
    ):
        super().__init__()
        self.item_ref = item_ref
        self._data = data  # arbitrary user data

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        self.label = QLabel(text)
        layout.addWidget(self.label)

        if show_delete:
            self.delete_btn = QPushButton(delete_label)
            self.delete_btn.setFixedWidth(50)
            self.delete_btn.clicked.connect(
                lambda: self.delete_requested.emit(self.item_ref)
            )
            layout.addWidget(self.delete_btn)

    # ── data accessors ──────────────────────────────────────────────
    def get_data(self) -> Any:
        return self._data

    def set_data(self, data: Any) -> None:
        self._data = data

    def get_text(self) -> str:
        return self.label.text()

    def set_text(self, text: str) -> None:
        self.label.setText(text)


class DraggableListManager(QListWidget):
    """
    Enhanced QListWidget wrapper.

    New in v2
    ---------
    * clear()                – remove all items
    * add_custom_item()      – accepts `data`, `delete_label`, `on_delete` callback
    * get_all_data()         – returns list[str] (text) — unchanged
    * get_all_json()         – returns list[dict] with "text" + "data" keys
    * get_item_data(row)     – returns the user-supplied data for a row
    * set_item_data(row, v)  – update stored data for a row
    * get_item_text(row)     – get label text by row index
    * set_item_text(row, v)  – update label text by row index
    * remove_item(row)       – remove by row index (public)
    * item_count             – property alias for count()
    """

    # ── init ────────────────────────────────────────────────────────
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    # ── add ─────────────────────────────────────────────────────────
    def add_custom_item(
        self,
        text: str,
        can_delete: bool = True,
        delete_label: str = "✕",
        data: Any = None,
        on_delete: Optional[Callable[[Any], None]] = None,
    ) -> QListWidgetItem:
        """
        Parameters
        ----------
        text          : display text
        can_delete    : show delete button
        delete_label  : button label (default "✕")
        data          : arbitrary python object stored with item (dict, int, …)
        on_delete     : optional callback(data) called BEFORE item is removed

        Returns
        -------
        The QListWidgetItem created.
        """
        item = QListWidgetItem(self)
        widget = CustomItemWidget(
            text,
            show_delete=can_delete,
            item_ref=item,
            delete_label=delete_label,
            data=data,
        )

        def _handle_delete(item_ref):
            if on_delete is not None:
                w = self.itemWidget(item_ref)
                on_delete(w.get_data() if w else None)
            self.remove_item_by_ref(item_ref)

        widget.delete_requested.connect(_handle_delete)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        return item

    # ── remove ──────────────────────────────────────────────────────
    def remove_item_by_ref(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        if row >= 0:
            self.takeItem(row)

    def remove_item(self, row: int) -> None:
        """Remove item at given row index."""
        if 0 <= row < self.count():
            self.takeItem(row)

    def clear(self) -> None:
        """Remove all items (override for explicitness; super() works too)."""
        super().clear()

    # ── read ────────────────────────────────────────────────────────
    def _widget(self, row: int) -> Optional[CustomItemWidget]:
        item = self.item(row)
        if item is None:
            return None
        return self.itemWidget(item)  # type: ignore[return-value]

    def get_item_text(self, row: int) -> Optional[str]:
        w = self._widget(row)
        return w.get_text() if w else None

    def get_item_data(self, row: int) -> Any:
        w = self._widget(row)
        return w.get_data() if w else None

    # ── write ───────────────────────────────────────────────────────
    def set_item_text(self, row: int, text: str) -> None:
        w = self._widget(row)
        if w:
            w.set_text(text)

    def set_item_data(self, row: int, data: Any) -> None:
        w = self._widget(row)
        if w:
            w.set_data(data)

    # ── bulk export ─────────────────────────────────────────────────
    def get_all_data(self) -> list[str]:
        """Return list of display texts (legacy-compatible)."""
        return [self._widget(i).get_text() for i in range(self.count())]

    def get_all_json(self) -> list[dict]:
        """
        Return list of dicts: {"text": str, "data": any}.
        'data' is whatever was passed as the `data=` kwarg.
        """
        result = []
        for i in range(self.count()):
            w = self._widget(i)
            if w:
                result.append({"text": w.get_text(), "data": w.get_data()})
        return result

    # ── helpers ─────────────────────────────────────────────────────
    @property
    def item_count(self) -> int:
        return self.count()