# utils/config.py

import json, os

class Config:
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '..', 'settings', 'settings.json')

    @staticmethod
    def get_device_ip():
        if os.path.exists(Config.SETTINGS_FILE):
            with open(Config.SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                return settings.get("device_ip", "")
        return ""
