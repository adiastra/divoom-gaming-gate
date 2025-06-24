# settings/settings_tab.py

import json, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QGroupBox, QDateTimeEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import QSlider
import requests
import datetime
import toml

from divoom_gaming_gate.utils.paths import SETTINGS_FILE

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError  # For Python <3.8

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")
        self.ip_edit = QLineEdit()

        # Main layout for the tab
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # Group box for settings
        group = QGroupBox("Device Settings")
        group.setMaximumWidth(400)  # Adjust width as needed
        group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        for layout_widget in group.findChildren(QLabel):
            layout_widget.setStyleSheet("color:white")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("Device IP:"))
        ip_layout.addWidget(self.ip_edit)
        layout.addLayout(ip_layout)

        # Brightness slider
        bright_layout = QHBoxLayout()
        bright_layout.addWidget(QLabel("Brightness:"))
        self.bright_slider = QSlider(Qt.Horizontal)
        self.bright_slider.setRange(0, 100)
        self.bright_slider.setValue(100)
        self.bright_slider.valueChanged.connect(self.set_brightness)
        bright_layout.addWidget(self.bright_slider)
        self.bright_label = QLabel("100")
        self.bright_slider.valueChanged.connect(lambda v: self.bright_label.setText(str(v)))
        bright_layout.addWidget(self.bright_label)
        layout.addLayout(bright_layout)

        # Time zone dropdown
        tz_layout = QHBoxLayout()
        tz_layout.addWidget(QLabel("Time Zone:"))
        self.city_timezones = {
            "Baker Island (GMT-12)": "GMT-12",
            "Honolulu (GMT-10)": "GMT-10",
            "Anchorage (GMT-9)": "GMT-9",
            "Los Angeles (GMT-8)": "GMT-8",
            "Denver (GMT-7)": "GMT-7",
            "Chicago (GMT-6)": "GMT-6",
            "New York (GMT-5)": "GMT-5",
            "Caracas (GMT-4)": "GMT-4",
            "Buenos Aires (GMT-3)": "GMT-3",
            "South Georgia (GMT-2)": "GMT-2",
            "Azores (GMT-1)": "GMT-1",
            "London (GMT+0)": "GMT+0",
            "Berlin (GMT+1)": "GMT+1",
            "Athens (GMT+2)": "GMT+2",
            "Moscow (GMT+3)": "GMT+3",
            "Dubai (GMT+4)": "GMT+4",
            "Karachi (GMT+5)": "GMT+5",
            "Dhaka (GMT+6)": "GMT+6",
            "Bangkok (GMT+7)": "GMT+7",
            "Beijing (GMT+8)": "GMT+8",
            "Tokyo (GMT+9)": "GMT+9",
            "Sydney (GMT+10)": "GMT+10",
            "Noumea (GMT+11)": "GMT+11",
            "Auckland (GMT+12)": "GMT+12",
            "Fakaofo (GMT+13)": "GMT+13",
            "Kiritimati (GMT+14)": "GMT+14"
        }
        self.tz_combo = QComboBox()
        self.tz_combo.addItems(self.city_timezones.keys())
        self.tz_combo.currentIndexChanged.connect(self.set_timezone)
        tz_layout.addWidget(self.tz_combo)

        # DST checkbox
        self.dst_checkbox = QCheckBox("DST")
        self.dst_checkbox.stateChanged.connect(self.set_timezone)
        tz_layout.addWidget(self.dst_checkbox)

        layout.addLayout(tz_layout)

        # System time controls
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("System Time (UTC):"))

        sync_btn = QPushButton("Sync with Internet Time")
        sync_btn.clicked.connect(self.sync_system_time)
        time_layout.addWidget(sync_btn)

        # After creating each button, add this line to give a hover highlight:
        sync_btn.setStyleSheet("""
            QPushButton:hover { background: #222; }
        """)

        layout.addLayout(time_layout)

        # 12/24 hour mode
        hour_layout = QHBoxLayout()
        hour_layout.addWidget(QLabel("Clock Format:"))
        self.hour_mode_combo = QComboBox()
        self.hour_mode_combo.addItems(["24-hour", "12-hour"])
        self.hour_mode_combo.currentIndexChanged.connect(self.set_hour_mode)
        hour_layout.addWidget(self.hour_mode_combo)
        layout.addLayout(hour_layout)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        # After creating each button, add this line to give a hover highlight:
        save_btn.setStyleSheet("""
            QPushButton:hover { background: #222; }
        """)

        layout.addStretch()

        main_layout.addWidget(group)

        # Version display and update button
        version_layout = QHBoxLayout()
        self.version_label = QLabel(f"Version: {self.get_current_version()}")
        self.version_label.setStyleSheet("color: #aaa;")
        version_layout.addWidget(self.version_label)
        update_btn = QPushButton("Check for Updates")
        update_btn.clicked.connect(self.check_for_update)
        update_btn.setStyleSheet("QPushButton:hover { background: #222; }")
        version_layout.addWidget(update_btn)
        layout.addLayout(version_layout)

        # Now that all widgets exist, load settings
        self.load_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            self.ip_edit.setText(settings.get("device_ip", ""))
            city = settings.get("timezone_city")
            if city and city in self.city_timezones:
                self.tz_combo.setCurrentText(city)
            self.dst_checkbox.setChecked(settings.get("dst", False))
            self.hour_mode_combo.setCurrentIndex(settings.get("hour_mode", 0))
        else:
            self.ip_edit.setText("")

    def save_settings(self):
        settings = {
            "device_ip": self.ip_edit.text().strip(),
            "timezone_city": self.tz_combo.currentText(),
            "dst": self.dst_checkbox.isChecked(),
            "hour_mode": self.hour_mode_combo.currentIndex()
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        QMessageBox.information(self, "Settings", "Settings saved.")

    def set_brightness(self, value):
        ip = self.ip_edit.text().strip()
        if not ip:
            return
        payload = {
            "Command": "Channel/SetBrightness",
            "Brightness": value
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=4)
        except Exception:
            pass  # Silently ignore errors for now

    def set_timezone(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            return
        city = self.tz_combo.currentText()
        tz_value = self.city_timezones.get(city)
        if not tz_value:
            return

        # Adjust for DST if checked
        if self.dst_checkbox.isChecked():
            # Parse the GMT offset and add 1
            import re
            m = re.match(r"GMT([+-])(\d+)", tz_value)
            if m:
                sign, hours = m.groups()
                hours = int(hours)
                if sign == '+':
                    hours += 1
                    tz_value = f"GMT+{hours}"
                else:
                    hours -= 1
                    tz_value = f"GMT-{hours}"
            # If GMT+0, becomes GMT+1; if GMT-1, becomes GMT-0, etc.

        payload = {
            "Command": "Sys/TimeZone",
            "TimeZoneValue": tz_value
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=4)
        except Exception:
            pass  # Silently ignore errors for now


    def sync_system_time(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            return
        try:
            # Get current UTC time from worldtimeapi.org
            resp = requests.get("http://worldtimeapi.org/api/timezone/Etc/UTC", timeout=5)
            if resp.ok:
                data = resp.json()
                utc_ts = int(data["unixtime"])
                payload = {
                    "Command": "Device/SetUTC",
                    "Utc": utc_ts
                }
                requests.post(f"http://{ip}/post", json=payload, timeout=4)
            # Optionally, show a message if you want:
            # QMessageBox.information(self, "Time Sync", "Device time synced to UTC.")
        except Exception:
            pass  # Silently ignore errors for now

    def set_hour_mode(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            return
        mode = self.hour_mode_combo.currentIndex()  # 0 = 24-hour, 1 = 12-hour
        payload = {
            "Command": "Device/SetTime24Flag",
            "Mode": mode
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=4)
        except Exception:
            pass  # Silently ignore errors for now

    def get_current_version(self):
        try:
            return version("divoom-gaming-gate")
        except PackageNotFoundError:
            return "unknown"

    def check_for_update(self):
        import sys, tempfile
        GITHUB_REPO = "adiastra/divoom-gaming-gate"
        CURRENT_VERSION = self.get_current_version()
        try:
            resp = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", timeout=10)
            resp.raise_for_status()
            release = resp.json()
            latest_version = release["tag_name"].lstrip("v")
            if latest_version > CURRENT_VERSION:
                # Find asset for this OS
                if sys.platform == "darwin":
                    ext = ".dmg"
                elif sys.platform == "win32":
                    ext = ".msi"
                else:
                    ext = None
                asset_url = None
                for asset in release["assets"]:
                    if ext and asset["name"].endswith(ext):
                        asset_url = asset["browser_download_url"]
                        break
                if asset_url:
                    reply = QMessageBox.question(self, "Update Available",
                        f"Version {latest_version} is available. Download and install?",
                        QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        # Download to temp dir
                        local_path = os.path.join(tempfile.gettempdir(), asset_url.split("/")[-1])
                        with requests.get(asset_url, stream=True) as r:
                            r.raise_for_status()
                            with open(local_path, "wb") as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        # Open installer
                        if sys.platform == "darwin":
                            os.system(f"open '{local_path}'")
                        elif sys.platform == "win32":
                            os.startfile(local_path)
                        else:
                            QMessageBox.information(self, "Update", f"Downloaded to {local_path}")
                else:
                    QMessageBox.information(self, "Update", "No suitable installer found for your OS.")
            else:
                QMessageBox.information(self, "Update", "You are up to date.")
        except Exception as e:
            QMessageBox.warning(self, "Update Error", f"Could not check for updates:\n{e}")
