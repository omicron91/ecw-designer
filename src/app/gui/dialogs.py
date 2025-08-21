from PyQt5 import QtCore, QtWidgets


class ApiKeyDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter API Key")
        self.setModal(True)
        self.setWindowFlags(
            (self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint) |
            QtCore.Qt.CustomizeWindowHint |
            QtCore.Qt.WindowTitleHint 
        )
        
        self.setFixedSize(350, 120)

        layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Please enter your API key:")
        layout.addWidget(self.label)

        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(self.line_edit)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_api_key(self):
        return self.line_edit.text()
    

class LoadingDialog(QtWidgets.QDialog):
    def __init__(self, message="Loading...", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Please Wait")
        self.setModal(True)
        self.setWindowFlags(
            (self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint) |
            QtCore.Qt.CustomizeWindowHint |
            QtCore.Qt.WindowTitleHint 
        )
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(message)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        self.setFixedSize(250, 100)
        