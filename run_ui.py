#!/usr/bin/env python3
"""FaceCat 桌面界面入口。"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui import MainWindow

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('FaceCat')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
