import os
from appdirs import user_data_dir

APP_NAME = "divoom-gaming-gate"
APP_AUTHOR = "Alec DiAstra"  # Use your GitHub username or org

USER_DATA_DIR = user_data_dir(APP_NAME, APP_AUTHOR)

THEMES_DIR = os.path.join(USER_DATA_DIR, "themes")
CHARACTER_DIR = os.path.join(USER_DATA_DIR, "characters")
SETTINGS_FILE = os.path.join(USER_DATA_DIR, "settings.json")

# Ensure directories exist
os.makedirs(THEMES_DIR, exist_ok=True)
os.makedirs(CHARACTER_DIR, exist_ok=True)