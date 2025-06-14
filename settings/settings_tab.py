# settings/settings_tab.py

import json, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox
)

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'settings.json')

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.ip_edit = QLineEdit()
        self.load_settings()

        layout = QVBoxLayout(self)

        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("Device IP:"))
        ip_layout.addWidget(self.ip_edit)
        layout.addLayout(ip_layout)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            self.ip_edit.setText(settings.get("device_ip", ""))
        else:
            self.ip_edit.setText("")

    def save_settings(self):
        settings = {"device_ip": self.ip_edit.text().strip()}
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        QMessageBox.information(self, "Settings", "Settings saved.")
