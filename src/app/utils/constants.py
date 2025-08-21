from PyQt5 import QtCore


MAX_COMPONENTS_PER_TYPE = 1000


MAP_SIZE_POLICY = {

}


IMAP_SIZE_POLICY = {
    
}

MAP_LABEL_ALIGNMENT = {
    "ha": {
        "left": QtCore.Qt.AlignLeft,
        "center": QtCore.Qt.AlignHCenter,
        "right": QtCore.Qt.AlignRight
    },
    "va": {
        "top": QtCore.Qt.AlignTop,
        "center": QtCore.Qt.AlignVCenter,
        "bottom": QtCore.Qt.AlignBottom
    }
}


MAP_SHAPES = {
    "Rectangle": "rect",
    "Rounded Rectangle": "rounded_rect",
    "Circular": "circular"
}


IMAP_SHAPES = {
    "rect": "Rectangle",
    "rounded_rect": "Rounded Rectangle",
    "circular": "Circular"
}


LIGHT_THEME = """
    QWidget {
        background-color: #f7f7fa;
        color: #222;
    }
    QMainWindow {
        background-color: #f7f7fa;
    }
    QMenuBar, QMenu, QToolBar, QStatusBar {
        background-color: #f7f7fa;
        color: #222;
    }
    QTreeWidget, QTreeView, QTableWidget, QTableView, QListWidget, QListView {
        background-color: #ffffff;
        alternate-background-color: #f2f3f7;
        color: #222;
        selection-background-color: #e3f0fb;
        selection-color: #1a73e8;
        border: 1px solid #d1d5db;
    }
    QHeaderView::section {
        background-color: #f2f3f7;
        color: #222;
        border: 1px solid #d1d5db;
        padding-left: 3px;
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit {
        background-color: #ffffff;
        color: #222;
        border: 1px solid #d1d5db;
        selection-background-color: #e3f0fb;
        selection-color: #1a73e8;
    }
    QPushButton {
        background-color: #e3e7ed;
        color: #222;
        border: 1px solid #d1d5db;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #d1eaff;
        color: #1a73e8;
    }
    QGroupBox {
        margin-top: 22px;
        padding-top: 0px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 3px;
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: #f2f3f7;
        border: 1px solid #d1d5db;
        width: 9px;
        height: 9px;
        margin: 0px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #cfd8dc;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        background: none;
        border: none;
    }
    QTabWidget::pane {
        border: 1px solid #d1d5db;
        background: #f7f7fa;
    }
    QTabBar::tab {
        background: #e3e7ed;
        color: #222;
        border: 1px solid #d1d5db;
        border-bottom: none;
        padding: 6px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        color: #1a73e8;
        border-bottom: 2px solid #1a73e8;
    }
    QCheckBox, QRadioButton {
        color: #222;
    }
    QMessageBox {
        background-color: #f7f7fa;
        color: #222;
    }
    QComboBox {
        border: 1px solid #d1d5db;
        border-radius: 3px;
        padding: 1px 18px 1px 3px;
        min-width: 6em;
    }
    QComboBox::drop-down:button{
        width: 30px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        border: none;
    }
    QComboBox::down-arrow {
        image: url(C:/Users/ecardenas/Desktop/software/python/.pyqt/ecw_designer/src/assets/icons/down_arrow.png);
        border: none;
    }
    QComboBox::down-arrow:on { /* shift the arrow when popup is open */
        top: 1px;
        left: 1px;
    }
"""

DARK_THEME = """
    QWidget {
        background-color: #232629;
        color: #f0f0f0;
    }
    QMainWindow {
        background-color: #232629;
    }
    QMenuBar, QMenu, QToolBar, QStatusBar {
        background-color: #232629;
        color: #f0f0f0;
    }
    QTreeWidget, QTreeView, QTableWidget, QTableView, QListWidget, QListView {
        background-color: #2d2f31;
        alternate-background-color: #232629;
        color: #f0f0f0;
        selection-background-color: #3d4144;
        selection-color: #ffffff;
        border: 1px solid #444;
        border-radius: 3px;
    }
    QHeaderView::section {
        background-color: #232629;
        color: #f0f0f0;
        border: 1px solid #444;
        padding-left: 3px;
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit {
        background-color: #232629;
        color: #f0f0f0;
        border: 1px solid #444;
        selection-background-color: #3d4144;
        selection-color: #ffffff;
    }
    QPushButton {
        background-color: #2d2f31;
        color: #f0f0f0;
        border: 1px solid #444;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #3d4144;
    }
    QGroupBox 
    {
        border: 1px solid;
        border-color: #444;
        margin-top: 22px;
        padding-top: 0px;
    }
    QGroupBox::title  
    {
        background-color: #444;
        color: #ffffff;
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 3px;
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
    }

    QScrollBar:vertical, QScrollBar:horizontal {
        background: #232629;
        border: 1px solid #444;
        height: 9px;
        width: 9px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #444;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        background: none;
        border: none;
    }
    QTabWidget::pane {
        border: 1px solid #444;
        background: #232629;
    }
    QTabBar::tab {
        background: #2d2f31;
        color: #f0f0f0;
        border: 1px solid #444;
    }
    QTabBar::tab:selected {
        background: #3d4144;
        color: #ffffff;
    }
    QCheckBox, QRadioButton {
        color: #f0f0f0;
    }
    QMessageBox {
        background-color: #232629;
        color: #f0f0f0;
    }
    QComboBox {
        border: 1px solid #444;
        border-radius: 3px;
        padding: 1px 18px 1px 3px;
        min-width: 6em;
    }
    QComboBox::drop-down:button{
        width: 30px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        border: none;
    }
    QComboBox::down-arrow {
        image: url(C:/Users/ecardenas/Desktop/software/python/.pyqt/ecw_designer/src/assets/icons/down_arrow_dt.png);
        border: none;
    }
    QComboBox::down-arrow:on { /* shift the arrow when popup is open */
        top: 1px;
        left: 1px;
    }
"""
