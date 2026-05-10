"""
dialogs.py - all dialog window
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton
)
from PySide6.QtCore import QCoreApplication
from i18n import tr

class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(420, 240)
        self.setModal(True)

        self.setup_ui()
        self.retranslate_ui()

    def setup_ui(self):

        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()

        # icon_label = QLabel()
        # pix = QPixmap("icon.png")   # path icon
        # icon_label.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # icon_label.setAlignment(Qt.AlignTop)

        # top_layout.addWidget(icon_label)

        # ----- info -----
        info_layout = QVBoxLayout()

        lbl_title = QLabel("TK-Tagger")
        lbl_title.setStyleSheet("font-size:20px; font-weight:bold;")
        info_layout.addWidget(lbl_title)

        self._lbl_author = QLabel()
        info_layout.addWidget(self._lbl_author)

        url = "https://github.com/Quocraft1436/TKtagger"
        lbl_link = QLabel(f'<a href="{url}">{url}</a>')
        lbl_link.setOpenExternalLinks(True)
        info_layout.addWidget(lbl_link)

        self._lbl_version = QLabel()
        info_layout.addWidget(self._lbl_version)

        self._lbl_license = QLabel()
        self._lbl_license.setStyleSheet("font-style: italic;")
        info_layout.addWidget(self._lbl_license)

        self._lbl_copy = QLabel()
        self._lbl_copy.setWordWrap(True)
        info_layout.addWidget(self._lbl_copy)

        info_layout.addStretch()

        top_layout.addLayout(info_layout)

        main_layout.addLayout(top_layout)

        # ===== button =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._close_btn = QPushButton()
        self._close_btn.setFixedWidth(80)
        self._close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self._close_btn)

        main_layout.addLayout(btn_layout)

    def retranslate_ui(self):
        self.setWindowTitle(tr("about_title"))
        self._lbl_author.setText(tr("about_author"))
        version = QCoreApplication.applicationVersion()
        self._lbl_version.setText(tr("about_version", version=version))
        self._lbl_license.setText(tr("about_license"))
        self._lbl_copy.setText(tr("about_copy"))
        self._close_btn.setText(tr("about_close"))
