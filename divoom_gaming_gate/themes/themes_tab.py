from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QToolButton, QPushButton, QFrame, QMessageBox, QScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QMovie, QIcon
import os
import json
import base64
import tempfile
import requests
import io
import time
from PIL import Image, ImageSequence

from divoom_gaming_gate.utils.paths import THEMES_DIR

class AnimatedLabel(QLabel):
    """A QLabel that can show a static image or an animated GIF from bytes."""
    def set_image(self, img_type, b64data, size):
        data = base64.b64decode(b64data)
        if img_type == "gif":
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
            tmp.write(data)
            tmp.close()
            self.movie = QMovie(tmp.name)
            self.movie.setScaledSize(size)
            self.setMovie(self.movie)
            self.movie.start()
            self._tmpfile = tmp.name
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            pixmap = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(pixmap)
            self.movie = None
            self._tmpfile = None

    def leaveEvent(self, event):
        if hasattr(self, "movie") and self.movie:
            self.movie.stop()
        super().leaveEvent(event)

    def cleanup(self):
        if hasattr(self, "_tmpfile") and self._tmpfile:
            try:
                os.remove(self._tmpfile)
            except Exception:
                pass

class ThemeWidget(QWidget):
    def __init__(self, theme, preview_labels, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.theme = theme
        self.preview_labels = preview_labels

    def enterEvent(self, event):
        for label in self.preview_labels:
            if hasattr(label, "movie") and label.movie:
                label.movie.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        for label in self.preview_labels:
            if hasattr(label, "movie") and label.movie:
                label.movie.stop()
        super().leaveEvent(event)

class ThemesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # --- Add scroll area ---
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        # Container widget for the grid
        self.grid_container = QWidget()
        self.themes_grid = QGridLayout(self.grid_container)
        self.themes_grid.setSpacing(12)
        self.grid_container.setLayout(self.themes_grid)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area)  # Only this, no addStretch()

        self.refresh_themes()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_themes()

    def refresh_themes(self):
        # Clear old widgets
        while self.themes_grid.count():
            item = self.themes_grid.takeAt(0)
            widget = item.widget()
            if widget:
                if hasattr(widget, "cleanup"):
                    widget.cleanup()
                widget.deleteLater()

        # Sort theme files by creation time (oldest first)
        theme_files = [
            os.path.join(THEMES_DIR, fname)
            for fname in os.listdir(THEMES_DIR)
            if fname.endswith(".theme")
        ]
        theme_files.sort(key=lambda f: os.path.getctime(f))

        themes = []
        for path in theme_files:
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                    data["__file"] = os.path.basename(path)
                    themes.append(data)
                except Exception as e:
                    print(f"Failed to load theme {path}: {e}")

        col_count = 3
        for idx, theme in enumerate(themes):
            col = idx % col_count
            row = idx // col_count

            # --- Theme frame (box) ---
            theme_frame = QFrame()
            theme_frame.setFrameShape(QFrame.Box)
            theme_frame.setLineWidth(2)
            theme_frame.setStyleSheet("""
                QFrame {
                    border: none;
                    border-radius: 12px;
                    background: #232323;
                }
            """)
            theme_vbox = QVBoxLayout(theme_frame)
            theme_vbox.setSpacing(4)
            theme_vbox.setContentsMargins(8, 8, 8, 8)

            # Top row: send (left), name (center), delete (right)
            top_row = QHBoxLayout()
            send_btn = QToolButton()
            send_btn.setText('Send to Screens 📤')
            send_btn.setToolTip("Send to Screens")
            send_btn.clicked.connect(lambda _, t=theme: self.send_theme(t))
            top_row.addWidget(send_btn, alignment=Qt.AlignLeft)

            top_row.addStretch()
            name_label = QLabel(theme["name"])
            name_label.setAlignment(Qt.AlignHCenter)
            name_label.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                color: #eee;
                background: transparent;
                border: none;
            """)
            top_row.addWidget(name_label, alignment=Qt.AlignHCenter)
            top_row.addStretch()

            del_btn = QPushButton("Delete Theme")
            del_btn.clicked.connect(lambda _, f=theme["__file"]: self.delete_theme(f))
            top_row.addWidget(del_btn, alignment=Qt.AlignRight)

            theme_vbox.addLayout(top_row)

            # Previews row
            previews_row = QHBoxLayout()
            previews_row.setSpacing(4)
            preview_labels = []
            for screen in theme["screens"]:
                frame = QFrame()
                frame.setFrameShape(QFrame.Box)
                frame.setLineWidth(1)
                frame.setStyleSheet("QFrame { border: 1px solid #555; border-radius: 4px; background: #232323; }")
                frame_layout = QVBoxLayout(frame)
                frame_layout.setContentsMargins(2, 2, 2, 2)
                label = AnimatedLabel()
                label.setFixedSize(64, 64)
                label.set_image(screen["type"], screen["data"], label.size())
                label.leaveEvent(None)  # Stop animation by default
                preview_labels.append(label)
                frame_layout.addWidget(label, alignment=Qt.AlignCenter)
                previews_row.addWidget(frame)
            theme_vbox.addLayout(previews_row)

            theme_frame.setFixedWidth(400)

            # --- Wrap in ThemeWidget for hover effect ---
            theme_widget = ThemeWidget(theme, preview_labels)
            theme_widget.setObjectName("themeCard")
            theme_widget.setStyleSheet("""
                #themeCard {
                    border: 1px solid #aaa;
                    border-radius: 12px;
                    background: transparent;
                }
                #themeCard:hover {
                    border: 1.5px solid #fff;
                    background: #282828;
                }
            """)
            theme_layout = QVBoxLayout(theme_widget)
            theme_layout.setContentsMargins(0, 0, 0, 0)
            theme_layout.setSpacing(0)
            theme_layout.addWidget(theme_frame)

            self.themes_grid.addWidget(theme_widget, row, col, alignment=Qt.AlignTop | Qt.AlignHCenter)

        self.themes_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    def send_theme(self, theme):
        from divoom_gaming_gate.utils.config import Config
        import requests, io, base64, time
        from PIL import Image, ImageSequence

        # These should match your screen_control.py constants
        SCREEN_COUNT = 5
        IMG_SIZE = 128
        DEFAULT_SPEED = 100
        DEFAULT_QUALITY = 85

        DEVICE_IP = Config.get_device_ip()
        if not DEVICE_IP or DEVICE_IP.strip() == "":
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No IP Set", "Please set the Divoom device IP in the settings before sending.")
            return

        pic_id = int(time.time())
        speed = DEFAULT_SPEED
        quality = DEFAULT_QUALITY

        for screen_index, screen in enumerate(theme["screens"]):
            img_type = screen["type"]
            img_data = base64.b64decode(screen["data"])
            if img_type == "gif":
                img = Image.open(io.BytesIO(img_data))
                frames = [fr.convert("RGB") for fr in ImageSequence.Iterator(img)]
            else:
                img = Image.open(io.BytesIO(img_data)).convert("RGB")
                frames = [img]

            lcd = [0] * SCREEN_COUNT
            lcd[screen_index] = 1

            for offset, frame in enumerate(frames):
                buf = io.BytesIO()
                frame.save(buf, format="JPEG", quality=quality)
                b64 = base64.b64encode(buf.getvalue()).decode()

                payload = {
                    "Command":   "Draw/SendHttpGif",
                    "LcdArray":  lcd,
                    "PicNum":    len(frames),
                    "PicOffset": offset,
                    "PicID":     pic_id,
                    "PicSpeed":  speed,
                    "PicWidth":  IMG_SIZE,
                    "PicData":   b64
                }
                try:
                    requests.post(f"http://{DEVICE_IP}/post", json=payload, timeout=2)
                    time.sleep(0.2)  # match per-frame delay
                except Exception as e:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Network Error", f"Failed to send to device:\n{e}")
                    return
            time.sleep(0.3)  # match per-screen delay

    def delete_theme(self, fname):
        path = os.path.join(THEMES_DIR, fname)
        if os.path.exists(path):
            reply = QMessageBox.question(
                self,
                "Delete Theme?",
                f"Are you sure you want to delete the theme '{os.path.splitext(fname)[0]}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            os.remove(path)
        self.refresh_themes()