"""
main.py - Entry point of TKtagger (PySide6)
"""
import sys
import argparse
from PySide6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="TKtagger")
    parser.add_argument("path", nargs="?", help="The path to the folder to open")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("TKtagger")
    app.setApplicationVersion("1.4.0")

    window = MainWindow(initial_path=args.path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
