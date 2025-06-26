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

from importlib.metadata import version, PackageNotFoundError

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")
        self.ip_edit = QLineEdit()
        self.loading_settings = False  # Add this flag

        # Main layout for the tab
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # Group box for settings
        group = QGroupBox("Device Settings")
        group.setMaximumWidth(400)
        group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        for layout_widget in group.findChildren(QLabel):
            layout_widget.setStyleSheet("color:white")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)  # No spacing for flush positioning of IP/help

        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(0)
        ip_layout.setContentsMargins(0, 0, 0, 0)
        ip_layout.addWidget(QLabel("Device IP:"))
        ip_layout.addWidget(self.ip_edit)
        # --- Add Find button ---
        find_btn = QPushButton("Find")
        find_btn.setFixedWidth(50)
        find_btn.setContentsMargins(0, 0, 0, 0)
        find_btn.clicked.connect(self.find_lan_device)
        ip_layout.addWidget(find_btn)
        layout.addLayout(ip_layout)

        # --- Instruction label directly under IP section, flush ---
        ip_help_label = QLabel('Click "Find" to locate a device or enter the IP manually')
        ip_help_label.setStyleSheet("color: #aaa; font-size: 12px; margin: 0; padding: 0;")
        ip_help_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(ip_help_label)

        # --- Device name label (initially empty) ---
        self.device_name_label = QLabel("")
        self.device_name_label.setStyleSheet("color: #8ecfff; font-size: 12px; margin-left: 4px;")
        layout.addWidget(self.device_name_label)

        # Restore normal spacing for the rest of the controls
        layout.setSpacing(14)

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

        # --- Screens On/Off slider ---
        screens_layout = QHBoxLayout()
        screens_label = QLabel("Screens:")
        screens_layout.addWidget(screens_label)

        self.screens_slider = QSlider(Qt.Horizontal)
        self.screens_slider.setMinimum(0)
        self.screens_slider.setMaximum(1)
        self.screens_slider.setValue(1)  # Default is ON
        self.screens_slider.setTickPosition(QSlider.TicksBelow)
        self.screens_slider.setTickInterval(1)
        self.screens_slider.setSingleStep(1)
        self.screens_slider.setFixedWidth(80)
        self.screens_slider.valueChanged.connect(self.toggle_screens_off)
        screens_layout.addWidget(QLabel("Off"))
        screens_layout.addWidget(self.screens_slider)
        screens_layout.addWidget(QLabel("On"))
        screens_layout.addStretch()
        layout.addLayout(screens_layout)

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
        self.hour_mode_combo.addItems(["12-hour", "24-hour"])
        self.hour_mode_combo.currentIndexChanged.connect(self.set_hour_mode)
        hour_layout.addWidget(self.hour_mode_combo)
        layout.addLayout(hour_layout)

        # --- Tenor API Key input and link ---
        tenor_vlayout = QVBoxLayout()
        tenor_vlayout.setSpacing(0)  # Remove extra space between widgets

        tenor_hlayout = QHBoxLayout()
        tenor_hlayout.addWidget(QLabel("Tenor API Key:"))
        self.tenor_api_edit = QLineEdit()
        self.tenor_api_edit.setPlaceholderText("Enter your Tenor API Key")
        # Make font smaller and less bright
        self.tenor_api_edit.setStyleSheet("""
            margin-bottom:0px;
            font-size: 12px;
            color: #b0b0b0;
            background: #232323;
        """)
        tenor_hlayout.addWidget(self.tenor_api_edit)
        tenor_vlayout.addLayout(tenor_hlayout)

        # Centered link directly under the textbox, no top margin
        tenor_link = QLabel('<a href="https://developers.google.com/tenor/guides/quickstart">Get a Tenor API Key</a>')
        tenor_link.setOpenExternalLinks(True)
        tenor_link.setStyleSheet("color: #8ecfff; font-size: 11px; margin-top:0px;")
        tenor_link.setAlignment(Qt.AlignHCenter)
        tenor_vlayout.addWidget(tenor_link)

        # --- Tenor Content Filter dropdown ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Tenor Content Filter:"))
        self.tenor_filter_combo = QComboBox()
        self.tenor_filter_combo.addItems(["off", "low", "medium", "high"])
        self.tenor_filter_combo.setCurrentText("medium")  # Default
        filter_layout.addWidget(self.tenor_filter_combo)
        tenor_vlayout.addLayout(filter_layout)

        layout.addLayout(tenor_vlayout)

        # --- Pixellab.ai API Key input and link ---
        pixellab_vlayout = QVBoxLayout()
        pixellab_vlayout.setSpacing(0)

        pixellab_hlayout = QHBoxLayout()
        pixellab_hlayout.addWidget(QLabel("Pixellab.ai API Key:"))
        self.pixellab_api_edit = QLineEdit()
        self.pixellab_api_edit.setPlaceholderText("Enter your Pixellab.ai API Key")
        self.pixellab_api_edit.setStyleSheet("""
            margin-bottom:0px;
            font-size: 12px;
            color: #b0b0b0;
            background: #232323;
        """)
        pixellab_hlayout.addWidget(self.pixellab_api_edit)
        pixellab_vlayout.addLayout(pixellab_hlayout)

        # Centered link under the textbox
        pixellab_link = QLabel('<a href="https://api.pixellab.ai/v1/docs">Get a Pixellab.ai API Key</a>')
        pixellab_link.setOpenExternalLinks(True)
        pixellab_link.setStyleSheet("color: #8ecfff; font-size: 11px; margin-top:0px;")
        pixellab_link.setAlignment(Qt.AlignHCenter)
        pixellab_vlayout.addWidget(pixellab_link)

        layout.addLayout(pixellab_vlayout)

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

        # Reboot button
        reboot_btn = QPushButton("Reboot Device")
        reboot_btn.clicked.connect(self.reboot_device)
        reboot_btn.setStyleSheet("QPushButton:hover { background: #222; }")
        layout.addWidget(reboot_btn)


        # Now that all widgets exist, load settings
        self.load_settings()

    def load_settings(self):
        self.loading_settings = True
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            self.ip_edit.setText(settings.get("device_ip", ""))
            city = settings.get("timezone_city")
            if city and city in self.city_timezones:
                self.tz_combo.setCurrentText(city)
            self.dst_checkbox.setChecked(settings.get("dst", False))
            self.hour_mode_combo.setCurrentIndex(settings.get("hour_mode", 0))
            self.tenor_api_edit.setText(settings.get("tenor_api_key", ""))
            self.tenor_filter_combo.setCurrentText(settings.get("tenor_filter", "medium"))
            self.pixellab_api_edit.setText(settings.get("pixellab_api_key", ""))
        else:
            self.ip_edit.setText("")
            self.tenor_api_edit.setText("")
            self.pixellab_api_edit.setText("")
        self.loading_settings = False

    def save_settings(self):
        settings = {
            "device_ip": self.ip_edit.text().strip(),
            "timezone_city": self.tz_combo.currentText(),
            "dst": self.dst_checkbox.isChecked(),
            "hour_mode": self.hour_mode_combo.currentIndex(),
            "tenor_api_key": self.tenor_api_edit.text().strip(),
            "tenor_filter": self.tenor_filter_combo.currentText(),
            "pixellab_api_key": self.pixellab_api_edit.text().strip()  # <-- Add this line
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        QMessageBox.information(self, "Settings", "Settings saved.")

    def set_brightness(self, value):
        if self.loading_settings:
            return
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
        if self.loading_settings:
            return
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
        if self.loading_settings:
            return
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
        except Exception:
            pass  # Silently ignore errors for now

    def set_hour_mode(self, index):
        if self.loading_settings:
            return
        ip = self.ip_edit.text().strip()
        if not ip:
            return
        payload = {
            "Command": "Device/SetTime24Flag",
            "Mode": index  # 0 for 12-hour, 1 for 24-hour
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

    def find_lan_device(self):
        if self.loading_settings:
            return
        try:
            resp = requests.post(
                "https://app.divoom-gz.com/Device/ReturnSameLANDevice",
                json={},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            devices = data.get("DeviceList", [])
            if not devices:
                QMessageBox.information(self, "Find Device", "No Divoom devices found on your LAN.")
                return
            # Use the first device found
            device = devices[0]
            ip = device.get("DevicePrivateIP", "")
            name = device.get("DeviceName", "Unknown")
            self.ip_edit.setText(ip)
            self.device_name_label.setText(f"Device: {name}")
        except Exception as e:
            QMessageBox.warning(self, "Find Device", f"Error: {e}")

    def reboot_device(self):
        if self.loading_settings:
            return
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "Reboot", "Please enter the device IP.")
            return
        payload = {"Command": "Device/SysReboot"}
        try:
            resp = requests.post(f"http://{ip}/post", json=payload, timeout=5)
            if resp.ok:
                QMessageBox.information(self, "Reboot", "Reboot command sent to device.")
            else:
                QMessageBox.warning(self, "Reboot", f"HTTP error: {resp.status_code}")
        except Exception as e:
            QMessageBox.warning(self, "Reboot", f"Error: {e}")

    def toggle_screens_off(self, value):
        if self.loading_settings:
            return
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "Screens", "Please enter the device IP.")
            return
        payload = {
            "Command": "Channel/OnOffScreen",
            "OnOff": value  # 0 = Off, 1 = On
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=4)
        except Exception as e:
            QMessageBox.warning(self, "Screens", f"Error: {e}")
