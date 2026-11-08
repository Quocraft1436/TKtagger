"""
main.py - Entry point of TKtagger (PySide6)
"""
import sys
import argparse
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
from libs.app_paths import resource_path
from libs.settings_manager import settings
from libs.i18n import set_language
from main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="TKtagger")
    parser.add_argument("path", nargs="?", help="The path to the folder to open")
    parser.add_argument('--smoke-test', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("TKtagger")
    app.setWindowIcon(QIcon(str(resource_path("icons", "tktagger.svg"))))
    app.setApplicationVersion("1.5.2")

    # Initialize settings and load language
    initial_lang = settings.language
    set_language(initial_lang)
    
    # Connect language change signal to i18n
    settings.language_changed.connect(set_language)

    window = MainWindow(initial_path=args.path)
    window.show()
    if args.smoke_test:
        from libs.table_icon import ICON_MAP, get_icon
        from libs.settings_manager import SETTINGS_FILE
        if any(get_icon(name).isNull() for name in ICON_MAP):
            raise RuntimeError('Bundled icons failed to load')
        print(f'TKtagger smoke test OK; settings={SETTINGS_FILE}', flush=True)
        QTimer.singleShot(250, app.quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
