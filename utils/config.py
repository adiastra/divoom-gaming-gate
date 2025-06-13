import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')

class Config:
    IP_ADDRESS = "10.10.10.122"

    @classmethod
    def load(cls):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                cls.IP_ADDRESS = data.get("ip_address", cls.IP_ADDRESS)
        except FileNotFoundError:
            pass

    @classmethod
    def save(cls):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"ip_address": cls.IP_ADDRESS}, f, indent=2)
