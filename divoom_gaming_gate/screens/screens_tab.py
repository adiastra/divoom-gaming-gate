from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QSizePolicy, QPushButton, QInputDialog, QMessageBox, QFileDialog
from .screen_control import ScreenControl
from PyQt5.QtCore import Qt
import os
import json
import base64
import io
from PIL import Image

from divoom_gaming_gate.utils.paths import THEMES_DIR

def save_theme_file(theme_name, screen_controls, parent=None):
    theme_path = os.path.join(THEMES_DIR, f"{theme_name}.theme")
    if os.path.exists(theme_path):
        # Ask user if they want to overwrite
        reply = QMessageBox.question(
            parent,
            "Overwrite Theme?",
            f"A theme named '{theme_name}' already exists. Overwrite?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False  # Cancel save

    theme_data = {
        "name": theme_name,
        "screens": []
    }

    for sc in screen_controls:
        if hasattr(sc, "frames") and sc.frames:
            if len(sc.frames) > 1:
                # Animated: save as GIF in memory
                buf = io.BytesIO()
                sc.frames[0].save(
                    buf,
                    format="GIF",
                    save_all=True,
                    append_images=sc.frames[1:],
                    duration=getattr(sc, "speed", 100),
                    loop=0,
                    optimize=False
                )
                img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                theme_data["screens"].append({
                    "type": "gif",
                    "data": img_b64
                })
            else:
                # Static: save as PNG in memory
                buf = io.BytesIO()
                sc.frames[0].save(buf, format="PNG")
                img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                theme_data["screens"].append({
                    "type": "png",
                    "data": img_b64
                })
        else:
            # Blank image
            buf = io.BytesIO()
            Image.new("RGB", (128, 128), color="black").save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            theme_data["screens"].append({
                "type": "png",
                "data": img_b64
            })

    with open(theme_path, "w") as f:
        json.dump(theme_data, f)
    return True

class ScreensTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")

        # --- Top row with centered Save as Theme, Load Theme, and Clear All buttons ---
        top_row = QHBoxLayout()
        top_row.addStretch()

        load_theme_btn = QPushButton("Load Theme")
        load_theme_btn.clicked.connect(self.load_theme)
        top_row.addWidget(load_theme_btn)

        save_theme_btn = QPushButton("Save as Theme")
        save_theme_btn.clicked.connect(self.save_as_theme)
        top_row.addWidget(save_theme_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_all_screens)
        top_row.addWidget(clear_all_btn)

        top_row.addStretch()

        # --- Main horizontal layout for screens ---
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self.screen_controls = []
        for i in range(5):
            box = QGroupBox(f"Screen {i+1}")
            box.setMinimumWidth(260)
            box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

            ctrl = ScreenControl(i)
            self.screen_controls.append(ctrl)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignTop)
            v.addWidget(ctrl)
            box.setLayout(v)

            main_layout.addWidget(box)
        main_layout.addStretch()

        # --- Outer vertical layout ---
        outer_layout = QVBoxLayout(self)
        outer_layout.addLayout(top_row)
        outer_layout.addLayout(main_layout)
        self.setLayout(outer_layout)

    def save_as_theme(self):
        name, ok = QInputDialog.getText(self, "Save Theme", "Theme Name:")
        if not ok or not name.strip():
            return
        try:
            save_theme_file(name.strip(), self.screen_controls, self)
            QMessageBox.information(self, "Theme Saved", f"Theme '{name}' saved!")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def clear_all_screens(self):
        for ctrl in self.screen_controls:
            ctrl.clear_image()  # You may need to implement this method in ScreenControl

    def load_theme(self):
        theme_path, _ = QFileDialog.getOpenFileName(
            self, "Load Theme", THEMES_DIR, "Theme Files (*.theme)"
        )
        if not theme_path:
            return
        try:
            with open(theme_path, "r") as f:
                theme_data = json.load(f)
            for ctrl, screen in zip(self.screen_controls, theme_data["screens"]):
                ctrl.load_from_theme_data(screen)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load theme:\n{e}")
