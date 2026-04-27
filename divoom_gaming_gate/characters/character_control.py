from ..utils.config import Config
import io, base64, time
import json
import os
from PIL import Image
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSpinBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QInputDialog, QComboBox, QSizePolicy, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from ..utils.image import compose_character_image
import shutil
from functools import partial
from ..utils.constants import SCREEN_COUNT, IMG_SIZE, DEFAULT_QUALITY, DEFAULT_SPEED
from ..utils.device_api import post_device_command

# IP from config 
from ..utils.config import Config
DEVICE_IP = Config.get_device_ip()

from divoom_gaming_gate.utils.paths import CHARACTER_DIR
ASSIGNMENTS_FILE = os.path.join(CHARACTER_DIR, "screen_assignments.json")
PRESETS_FILE = os.path.join(CHARACTER_DIR, "system_presets.json")

def load_system_presets():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            # File is empty or invalid, treat as no presets
            return {}
    return {}

def save_system_presets(presets):
    with open(PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)

def get_slot_path(slot):
    return os.path.join(CHARACTER_DIR, f"slot_{slot}.json")

def get_character_path(name):
    safe = "".join(c for c in name if c.isalnum() or c in (' ','_','-')).rstrip()
    return os.path.join(CHARACTER_DIR, f"{safe}.json")

def load_assignments():
    if os.path.exists(ASSIGNMENTS_FILE):
        with open(ASSIGNMENTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_assignments(assignments):
    with open(ASSIGNMENTS_FILE, "w") as f:
        json.dump(assignments, f, indent=2)
class PresetSignalEmitter(QObject):
    presets_updated = pyqtSignal()

preset_signals = PresetSignalEmitter()

class CharacterControl(QWidget):

    def __init__(self, slot):
        super().__init__()
        self.slot = slot
        self.char = {
            "name": f"Char {slot+1}",
            "stats": {"Brawn": 1, "Agility": 1, "Intellect": 1, "Cunning": 1, "Willpower": 1, "Presence": 1},
            "background": "",
            "portrait": ""
        }

        # Name field
        self.name_edit = QLineEdit(self.char["name"])
        self.name_edit.setPlaceholderText("Name")
        self.name_edit.textChanged.connect(self.update_preview)

        # System combo box
        self.system_box = QComboBox()
        self.system_box.addItem("----- Presets -----")
        # Don't connect yet!

        # Preview
        self.preview = QLabel()
        self.preview.setFixedSize(IMG_SIZE, IMG_SIZE)
        self.preview.setStyleSheet("border:1px solid white;")
        self.preview.setAlignment(Qt.AlignCenter)
        pv_box = QHBoxLayout()
        pv_box.addStretch()
        pv_box.addWidget(self.preview)
        pv_box.addStretch()

        # Dynamic stats
        self.stat_boxes = {}
        self.stat_layout = QVBoxLayout()
        self._rebuild_stats_ui()

        # Now connect!
        self.system_box.currentIndexChanged.connect(self.apply_system_preset)
        self.update_system_box()

        # Add Stat button
        self.add_stat_btn = QPushButton("Add Stat")
        self.add_stat_btn.clicked.connect(self.add_stat)
        self.add_stat_btn.setStyleSheet("QPushButton:hover { background: #222; }")

        # Send
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send)
        self.send_btn.setStyleSheet("QPushButton:hover { background: #222; }")

        # Background button
        self.bg_btn = QPushButton("Add Background")
        self.bg_btn.clicked.connect(self.load_background)
        self.bg_btn.setStyleSheet("QPushButton:hover { background: #222; }")

        # Load button
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self.load_character_dialog)
        self.load_btn.setStyleSheet("QPushButton:hover { background: #222; }")

        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_character)
        self.save_btn.setStyleSheet("QPushButton:hover { background: #222; }")

        # Save as Preset button
        self.save_preset_btn = QPushButton("Save Preset")
        self.save_preset_btn.clicked.connect(self.save_as_preset)
        self.save_preset_btn.setStyleSheet("QPushButton:hover { background: #222; }")

        # --- Stats Section ---
        stats_btn_row = QHBoxLayout()
        stats_btn_row.setSpacing(self.style().layoutSpacing(
            QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
        ))
        stats_btn_row.addWidget(self.add_stat_btn)
        stats_btn_row.addWidget(self.save_preset_btn)

        # --- Character Section ---
        char_btn_row = QHBoxLayout()
        char_btn_row.setSpacing(self.style().layoutSpacing(
            QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
        ))
        char_btn_row.addWidget(self.load_btn)
        char_btn_row.addWidget(self.save_btn)

        # --- Background Section ---
        bg_btn_row = QHBoxLayout()
        bg_btn_row.setSpacing(self.style().layoutSpacing(
            QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
        ))
        bg_btn_row.addWidget(self.bg_btn)

        # --- Action Section ---
        action_btn_row = QHBoxLayout()
        action_btn_row.setSpacing(self.style().layoutSpacing(
            QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
        ))
        action_btn_row.addWidget(self.send_btn)

        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(2)  
        layout.addWidget(self.system_box)
        layout.addWidget(self.name_edit)
        layout.addLayout(pv_box)
        layout.addLayout(self.stat_layout)
        layout.addLayout(stats_btn_row)
        layout.addLayout(char_btn_row)
        layout.addLayout(bg_btn_row)
        layout.addLayout(action_btn_row)
        self.setLayout(layout)

        self.load_character()
        self.update_preview()

        preset_signals.presets_updated.connect(self.update_system_box)

    def _rebuild_stats_ui(self):
        # Clear old widgets
        for i in reversed(range(self.stat_layout.count())):
            item = self.stat_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w:
                        w.deleteLater()
                item.layout().deleteLater()
            self.stat_layout.removeItem(item)
        self.stat_boxes = {}
        self.stat_layout.setSpacing(0)
        self.stat_layout.setContentsMargins(0, 0, 0, 0)
        # Add stat rows
        for stat, value in self.char["stats"].items():
            # Ensure value is always a dict
            if not isinstance(value, dict):
                value = {"base": value}
                self.char["stats"][stat] = value
            h = QHBoxLayout()
            h.setSpacing(0)  # No space between widgets in the row
            h.setContentsMargins(0, 0, 0, 0)  # No margins around the row

            name_edit = QLineEdit(stat)
            name_edit.setMinimumWidth(20)
            name_edit.setMaximumWidth(60)

            base_edit = QLineEdit(str(value.get("base", value.get("current", value.get("total", "")))))
            base_edit.setFixedWidth(28)

            current_edit = QLineEdit(str(value.get("current", "")))
            current_edit.setFixedWidth(28)

            slash_label = QLabel("/")
            slash_label.setFixedWidth(10)
            slash_label.setAlignment(Qt.AlignCenter)

            mod_btn = QPushButton("±")            
            mod_btn.setFixedWidth(22)
            #mod_btn.setFixedHeight(22)
            mod_btn.setStyleSheet("""
                QPushButton { color: #0f0; padding: 0px; margin: 0px; border-radius: 0px; }
                QPushButton:hover { background: #222; }
            """)
            mod_btn.setFlat(False)
            mod_btn.setFont(QFont("Arial", 16))

            modifier_edit = QLineEdit(str
            (value.get("modifier", "")))
            modifier_edit.setFixedWidth(28)
            modifier_edit.setVisible(bool(value.get("modifier", "")))

            def toggle_modifier_field(edit=modifier_edit):
                edit.setVisible(not edit.isVisible())
            mod_btn.clicked.connect(partial(toggle_modifier_field, modifier_edit))

            remove_btn = QPushButton("X")
            remove_btn.setFixedWidth(22)
            remove_btn.setFlat(False)
            remove_btn.setStyleSheet("""
                QPushButton { color: #c00; padding: 0px; margin: 0px; border-radius: 0px; }
                QPushButton:hover { background: #222; }
            """)
            remove_btn.clicked.connect(lambda _, s=stat: self.remove_stat(s))

            name_edit.textChanged.connect(lambda new_name, old=stat: self.rename_stat(old, new_name))
            base_edit.textChanged.connect(self.update_preview)
            current_edit.textChanged.connect(self.update_preview)
            modifier_edit.textChanged.connect(self.update_preview)

            h.addWidget(name_edit)
            h.addWidget(base_edit)
            h.addWidget(slash_label)
            h.addWidget(current_edit)
            h.addWidget(modifier_edit)
            h.addWidget(mod_btn)
            h.addWidget(remove_btn)

            row_widget = QWidget()
            row_widget.setLayout(h)
            row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row_widget.setContentsMargins(0, 0, 0, 0)  # No margins for the row widget
            self.stat_layout.addWidget(row_widget)
            self.stat_boxes[stat] = (name_edit, base_edit, current_edit, modifier_edit)
        self.update_preview()

    def add_stat(self):
        stat, ok = QInputDialog.getText(self, "Add Stat", "Stat abbreviation(e.g. STR, DEX)")
        stat = stat.strip().upper()
        if ok and stat and stat not in self.char["stats"]:
            self.char["stats"][stat] = {"current": 0, "total": 0}
            self._rebuild_stats_ui()
            self.update_preview()

    def remove_stat(self, stat):
        if stat in self.char["stats"]:
            del self.char["stats"][stat]
            self._rebuild_stats_ui()
            self.update_preview()

    def rename_stat(self, old, new):
        new = new.strip().upper()
        if old != new and new and new not in self.char["stats"]:
            self.char["stats"][new] = self.char["stats"].pop(old)
            self._rebuild_stats_ui()
            self.update_preview()

    def _collect_stats_from_ui(self):
        stats = {}
        for _, (name_edit, base_edit, current_edit, modifier_edit) in self.stat_boxes.items():
            stat_name = name_edit.text()
            if not stat_name:
                continue

            base = base_edit.text()
            current = current_edit.text()
            modifier = modifier_edit.text()
            stat_dict = {}

            try:
                stat_dict["base"] = int(base)
            except ValueError:
                stat_dict["base"] = base

            if current:
                try:
                    stat_dict["current"] = int(current)
                except ValueError:
                    stat_dict["current"] = current

            if modifier:
                stat_dict["modifier"] = modifier

            stats[stat_name] = stat_dict
        return stats

    def save_character(self):
        self.char["name"] = self.name_edit.text()
        self.char["stats"] = self._collect_stats_from_ui()
        with open(get_character_path(self.char["name"]), "w") as f:
            json.dump(self.char, f, indent=2)

    def load_character(self, name=None):
        if name is None:
            assignments = load_assignments()
            name = assignments.get(str(self.slot))
        if name:
            try:
                with open(get_character_path(name), "r") as f:
                    self.char = json.load(f)
            except Exception:
                self.char = {
                    "name": name,
                    "stats": {},
                    "background": "",
                    "portrait": ""
                }
        else:
            self.char = {
                "name": f"Char {self.slot+1}",
                "stats": {},
                "background": "",
                "portrait": ""
            }
        self.name_edit.setText(self.char.get("name", f"Char {self.slot+1}"))
        self._rebuild_stats_ui()

    def update_preview(self):
        stats = self._collect_stats_from_ui()
        name = self.name_edit.text()
        img = compose_character_image(
            self.char["background"], self.char["portrait"], name, stats
        )
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def send(self):
        """Render the current character card and send it to this slot."""
        global DEVICE_IP
        DEVICE_IP = (Config.get_device_ip() or "").strip()
        if not DEVICE_IP:
            QMessageBox.warning(
                self,
                "No IP Set",
                "Please set and save the Divoom device IP in Settings before sending."
            )
            return

        stats = self._collect_stats_from_ui()

        name  = self.name_edit.text()
        img   = compose_character_image(
            self.char["background"], self.char["portrait"], name, stats
        )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=DEFAULT_QUALITY)
        b64 = base64.b64encode(buf.getvalue()).decode()
        pid = int(time.time())

        payload = {
            "Command":  "Draw/SendHttpGif",
            "LcdArray": [1 if i==self.slot else 0 for i in range(SCREEN_COUNT)],
            "PicNum":   1,
            "PicOffset":0,
            "PicID":    pid,
            "PicSpeed": DEFAULT_SPEED,
            "PicWidth": IMG_SIZE,
            "PicData":  b64
        }
        try:
            post_device_command(payload, ip=DEVICE_IP, timeout=8)
        except Exception as e:
            QMessageBox.warning(self, "Network Error", f"Failed to send to device:\n{e}")

    def load_background(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Background Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            ext = os.path.splitext(path)[1]
            dest = os.path.join(CHARACTER_DIR, f"bg_slot_{self.slot}{ext}")
            shutil.copy2(path, dest)
            self.char["background"] = dest
            self.save_character()
            self.update_preview()

    def load_character_dialog(self):
        # List all .json files in CHARACTER_DIR except screen_assignments.json
        files = [
            f for f in os.listdir(CHARACTER_DIR)
            if f.endswith(".json") and f not in ("screen_assignments.json", "system_presets.json")
        ]
        if not files:
            return
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(self, "Load Character", "Select character:", [os.path.splitext(f)[0] for f in files], 0, False)
        if ok and name:
            # Update assignments
            assignments = load_assignments()
            assignments[str(self.slot)] = name
            save_assignments(assignments)
            self.load_character(name)
            self.save_character()
            self.update_preview()

    def apply_system_preset(self):
        preset = self.system_box.currentText()
        # Check built-in presets first
        if hasattr(self, "builtin_presets") and preset in self.builtin_presets:
            self.char["stats"] = self.builtin_presets[preset]
        else:
            presets = load_system_presets()
            if preset in presets:
                # Ensure all stats are dicts
                stats = {}
                for stat, value in presets[preset].items():
                    if isinstance(value, dict):
                        stats[stat] = value
                    else:
                        stats[stat] = {"base": value}
                self.char["stats"] = stats
        self._rebuild_stats_ui()
        self.update_preview()

    def save_as_preset(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name:
            presets = load_system_presets()
            preset_stats = {}
            for stat, (name_edit, base_edit, _, _) in self.stat_boxes.items():
                try:
                    val = int(base_edit.text())
                except ValueError:
                    val = base_edit.text()
                preset_stats[name_edit.text()] = {"base": val}
            presets[name] = preset_stats
            save_system_presets(presets)
            self.update_system_box()
            preset_signals.presets_updated.emit()  # <-- FIXED LINE

    def update_system_box(self):
        current = self.system_box.currentText()
        self.system_box.clear()
        self.system_box.addItem("----- Presets -----")
        # Add built-in presets
        builtins = {
            "D&D 5e": {
                "STR": {"base": 10},
                "DEX": {"base": 10},
                "CON": {"base": 10},
                "INT": {"base": 10},
                "WIS": {"base": 10},
                "CHA": {"base": 10},
                "HP": {"base": 1},
                "AC": {"base": 10},
                "SPD": {"base": 30}
            },
            "Genesys": {
                "BRN": {"base": 1},
                "AGI": {"base": 1},
                "INT": {"base": 1},
                "CUN": {"base": 1},
                "WIL": {"base": 1},
                "PRE": {"base": 1}
            }
        }
        self.builtin_presets = builtins  # Store for use in apply_system_preset
        for preset in builtins:
            self.system_box.addItem(preset)
        # Load user presets
        presets = load_system_presets()
        for preset in presets:
            self.system_box.addItem(preset)
        # Restore selection if possible
        idx = self.system_box.findText(current)
        if idx >= 0:
            self.system_box.setCurrentIndex(idx)

