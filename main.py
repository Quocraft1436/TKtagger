"""
main.py - Entry point of TKtagger (PySide6)
"""
import sys
import argparse
from PySide6.QtWidgets import QApplication
from settings_manager import settings
from i18n import set_language
from main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="TKtagger")
    parser.add_argument("path", nargs="?", help="The path to the folder to open")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("TKtagger")
    app.setApplicationVersion("1.4.1")

    # Initialize settings and load language
    initial_lang = settings.language
    set_language(initial_lang)
    
    # Connect language change signal to i18n
    settings.language_changed.connect(set_language)

    window = MainWindow(initial_path=args.path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
