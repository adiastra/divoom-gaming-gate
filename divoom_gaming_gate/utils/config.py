# utils/config.py

import json
import os
from .paths import SETTINGS_FILE as USER_SETTINGS_FILE

class Config:
    SETTINGS_FILE = USER_SETTINGS_FILE

    @staticmethod
    def get_device_ip():
        if os.path.exists(Config.SETTINGS_FILE):
            with open(Config.SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                return settings.get("device_ip", "")
        return ""
