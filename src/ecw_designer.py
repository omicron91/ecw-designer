import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='output.log',
    filemode="w",
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%d-%m-%Y %I:%M:%S',
    encoding='utf-8',
    level=logging.DEBUG
)

import sys

def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    from PyQt5.QtWidgets import QMessageBox

    logging.critical("Unhandled exception caught!", exc_info=(exc_type, exc_value, exc_traceback))

    QMessageBox.critical(
        None,
        "Critical Error",
        "An unhandled exception occurred!"
    )

    sys.exit(0)

sys.excepthook = handle_unhandled_exception

import os
from PyQt5 import QtCore, QtWidgets, QtGui

from app.core import BASE_DIR, ECWDesigner

try:
    import pyi_splash
except ModuleNotFoundError:
    pass

import ctypes

myappid = "app.ecw-designer"    # Arbitrary and unique ID for your system
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(
        BASE_DIR,
        "assets", 
        "icons",
        "designer.ico"
    )))
    
    if getattr(sys, "frozen", False):
        import time
        for i in range(101):
            pyi_splash.update_text("Loading: {}%".format(i))
            time.sleep(0.01)

        pyi_splash.close()

    designer = ECWDesigner()

    scr_center = QtWidgets.QApplication.desktop().screen().rect().center()
    designer.setGeometry(QtCore.QRect(scr_center.x() - 600, scr_center.y() - 300, 1200, 600))
    
    designer.show()

    sys.exit(app.exec())
