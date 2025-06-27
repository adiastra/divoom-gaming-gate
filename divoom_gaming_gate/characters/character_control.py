from ..utils.config import Config
import io, base64, time, requests
import json
import os
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSpinBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QInputDialog, QComboBox, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from ..utils.image import compose_character_image
import shutil
from functools import partial

# IP from config 
from ..utils.config import Config
DEVICE_IP = Config.get_device_ip()

SCREEN_COUNT = 5
IMG_SIZE     = 128

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
def compose_character_image(background_path, portrait_path, name, stats):
    if background_path and os.path.exists(background_path):
        bg = Image.open(background_path).convert("RGB").resize((128, 128))
    else:
        bg = Image.new("RGB", (128, 128), (0, 0, 0))

    draw = ImageDraw.Draw(bg, "RGBA")
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    # --- Draw name overlay at the top ---
    name_box_height = 22
    draw.rectangle([0, 0, 128, name_box_height], fill=(40, 40, 40, 180))
    try:
        bbox = draw.textbbox((0, 0), name, font=font)
        w = bbox[2] - bbox[0]
    except AttributeError:
        w, _ = font.getsize(name)
    draw.text(((128 - w) // 2, 4), name, fill=(255, 255, 255), font=font)

    # --- Draw stats in two columns ---
    stat_keys = list(stats.keys())
    n = len(stat_keys)
    left_stats = stat_keys[: (n + 1) // 2]
    right_stats = stat_keys[(n + 1) // 2 :]

    stat_box_top = name_box_height + 2
    stat_box_height = max(len(left_stats), len(right_stats)) * 16 + 4
    draw.rectangle([0, stat_box_top, 128, stat_box_top + stat_box_height], fill=(40, 40, 40, 180))

    for col, stat_list in enumerate([left_stats, right_stats]):
        for i, k in enumerate(stat_list):
            y = stat_box_top + 2 + i * 16
            x = 6 if col == 0 else 68  # 68 leaves a gap between columns
            v = stats[k]
            base = str(v.get('base', ''))
            current = str(v.get('current', ''))
            modifier = str(v.get('modifier', ''))
            abbr = k  # Use stat key directly
            try:
                bold_font = ImageFont.truetype("arialbd.ttf", 14)
            except Exception:
                bold_font = font
            draw.text((x, y), f"{abbr}: ", fill=(200, 200, 200), font=font)
            x_offset = x + draw.textlength(f"{abbr}: ", font=font)
            draw.text((x_offset, y), base, fill=(255, 255, 255), font=bold_font)
            x_offset += draw.textlength(base, font=bold_font)
            # Draw current if present
            if current:
                try:
                    base_val = float(base)
                    curr_val = float(current)
                    if curr_val < base_val:
                        pct = curr_val / base_val if base_val else 0
                        if pct >= 0.7:
                            curr_color = (0, 200, 0)
                        elif pct >= 0.3:
                            curr_color = (220, 180, 0)
                        else:
                            curr_color = (220, 0, 0)
                    else:
                        curr_color = (0, 200, 0)
                except Exception:
                    curr_color = (200, 200, 200)
                draw.text((x_offset, y), f" / {current}", fill=curr_color, font=font)
                x_offset += draw.textlength(f" / {current}", font=font)
            # Draw modifier if present
            if modifier:
                mod_color = (200, 200, 200)
                mod_str = modifier.strip()
                # Try to interpret as a number
                try:
                    mod_val = int(mod_str)
                except ValueError:
                    try:
                        mod_val = float(mod_str)
                    except ValueError:
                        mod_val = None

                if mod_val is not None:
                    if mod_val > 0:
                        mod_color = (0, 200, 0)
                        mod_str = f"+{mod_val}"  # Always show plus for positive
                    elif mod_val < 0:
                        mod_color = (220, 0, 0)
                        mod_str = f"{mod_val}"
                    else:
                        mod_color = (200, 200, 200)
                        mod_str = f"{mod_val}"
                else:
                    # Not a number, fallback to string and color by prefix
                    if mod_str.startswith('+'):
                        mod_color = (0, 200, 0)
                    elif mod_str.startswith('-'):
                        mod_color = (220, 0, 0)
                draw.text((x_offset, y), f" ({mod_str})", fill=mod_color, font=font)
    return bg

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

    def save_character(self):
        self.char["name"] = self.name_edit.text()
        stats = {}
        for stat, (name_edit, base_edit, current_edit, modifier_edit) in self.stat_boxes.items():
            base = base_edit.text()
            current = current_edit.text()
            modifier = modifier_edit.text()  # Always get the value, even if hidden
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
            stats[name_edit.text()] = stat_dict
        self.char["stats"] = stats
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
        stats = {}
        for stat, (name_edit, base_edit, current_edit, modifier_edit) in self.stat_boxes.items():
            base = base_edit.text()
            current = current_edit.text()
            modifier = modifier_edit.text()  # Always get the value, even if hidden
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
            stats[name_edit.text()] = stat_dict
        name = self.name_edit.text()
        img = compose_character_image(
            self.char["background"], self.char["portrait"], name, stats
        )
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def send(self):
        global DEVICE_IP
        DEVICE_IP = Config.get_device_ip()

        stats = {}
        for stat, (name_edit, base_edit, current_edit, modifier_edit) in self.stat_boxes.items():
            try:
                base = int(base_edit.text())
            except ValueError:
                base = base_edit.text()
            try:
                current = int(current_edit.text())
            except ValueError:
                current = current_edit.text()
            modifier = modifier_edit.text()  # Always get the value, even if hidden
            stat_dict = {"base": base}
            if current:
                stat_dict["current"] = current
            if modifier:
                stat_dict["modifier"] = modifier
            stats[name_edit.text()] = stat_dict

        name  = self.name_edit.text()
        img   = compose_character_image(
            self.char["background"], self.char["portrait"], name, stats
        )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        pid = int(time.time())

        payload = {
            "Command":  "Draw/SendHttpGif",
            "LcdArray": [1 if i==self.slot else 0 for i in range(SCREEN_COUNT)],
            "PicNum":   1,
            "PicOffset":0,
            "PicID":    pid,
            "PicSpeed": 100,
            "PicWidth": IMG_SIZE,
            "PicData":  b64
        }
        requests.post(f"http://{DEVICE_IP}/post", json=payload)

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

