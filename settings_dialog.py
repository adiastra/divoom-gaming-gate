from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout
from utils.config import Config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(300, 100)

        self.ip_edit = QLineEdit(Config.IP_ADDRESS)
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("Device IP:"))
        ip_row.addWidget(self.ip_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(ip_row)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def accept(self):
        Config.IP_ADDRESS = self.ip_edit.text().strip()
        Config.save()
        super().accept()
