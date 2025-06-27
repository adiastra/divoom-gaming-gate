import requests
import os
import base64
import time
from io import BytesIO
from PIL import Image
from PIL.ImageQt import toqimage
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QSpinBox, QToolButton, QMessageBox,
    QColorDialog, QComboBox, QFileDialog, QPushButton, QSlider, QSizePolicy
)
from ..utils.config import Config

def pil_to_qimage(img):
    """Convert PIL Image to QImage (works with Pillow 10+)"""
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    data = img.tobytes("raw", "RGB")
    return QImage(data, w, h, QImage.Format_RGB888)

class ToolsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")
        self.cfg = Config()

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # --- API Tools Vertical Group Box ---
        api_tools_group = QGroupBox("API Tools")
        api_tools_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 16px; border: 2px solid #888; border-radius: 8px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px 0 6px; }"
        )
        api_tools_layout = QVBoxLayout(api_tools_group)
        api_tools_layout.setContentsMargins(12, 12, 12, 12)
        api_tools_layout.setSpacing(16)

        # --- Scoreboard Tool Group Box ---
        scoreboard_group = QGroupBox("Scoreboard")
        scoreboard_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        scoreboard_layout = QVBoxLayout(scoreboard_group)
        scoreboard_layout.setContentsMargins(8, 8, 8, 8)
        scoreboard_layout.setSpacing(8)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Blue Score:", styleSheet="color:white"))
        self.blue_score = QSpinBox()
        self.blue_score.setRange(0, 999)
        row2.addWidget(self.blue_score)
        row2.addWidget(QLabel("Red Score:", styleSheet="color:white"))
        self.red_score = QSpinBox()
        self.red_score.setRange(0, 999)
        row2.addWidget(self.red_score)
        scoreboard_layout.addLayout(row2)

        # Automatically send scoreboard on score change
        self.blue_score.valueChanged.connect(self.send_scoreboard)
        self.red_score.valueChanged.connect(self.send_scoreboard)

        # --- Countdown Timer Tool Group Box ---
        timer_group = QGroupBox("Countdown Timer")
        timer_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        timer_layout = QVBoxLayout(timer_group)
        timer_layout.setContentsMargins(8, 8, 8, 8)
        timer_layout.setSpacing(8)

        # Time input (minutes and seconds)
        time_lay = QHBoxLayout()
        time_lay.addWidget(QLabel("Minutes:", styleSheet="color:white"))
        self.timer_minutes = QSpinBox()
        self.timer_minutes.setRange(0, 99)
        time_lay.addWidget(self.timer_minutes)
        time_lay.addWidget(QLabel("Seconds:", styleSheet="color:white"))
        self.timer_seconds = QSpinBox()
        self.timer_seconds.setRange(0, 59)
        time_lay.addWidget(self.timer_seconds)
        timer_layout.addLayout(time_lay)

        # Start button
        start_btn = QToolButton(text="Start Countdown")
        start_btn.setStyleSheet("""
            QToolButton { color: white; font-size: 14px; }
            QToolButton:hover { background: #222; }
        """)
        start_btn.clicked.connect(self.send_countdown)
        timer_layout.addWidget(start_btn, alignment=Qt.AlignRight)

        # --- Stopwatch Tool Group Box ---
        stopwatch_group = QGroupBox("Stopwatch")
        stopwatch_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        stopwatch_layout = QVBoxLayout(stopwatch_group)
        stopwatch_layout.setContentsMargins(8, 8, 8, 8)
        stopwatch_layout.setSpacing(8)

        btn_lay = QHBoxLayout()
        start_btn = QToolButton(text="Start")
        start_btn.setStyleSheet("""
            QToolButton { color: white; font-size: 14px; }
            QToolButton:hover { background: #222; }
        """)
        start_btn.clicked.connect(lambda: self.send_stopwatch(1))
        btn_lay.addWidget(start_btn)

        stop_btn = QToolButton(text="Stop")
        stop_btn.setStyleSheet("""
            QToolButton { color: white; font-size: 14px; }
            QToolButton:hover { background: #222; }
        """)
        stop_btn.clicked.connect(lambda: self.send_stopwatch(0))
        btn_lay.addWidget(stop_btn)

        reset_btn = QToolButton(text="Reset")
        reset_btn.setStyleSheet("""
            QToolButton { color: white; font-size: 14px; }
            QToolButton:hover { background: #222; }
        """)
        reset_btn.clicked.connect(lambda: self.send_stopwatch(2))
        btn_lay.addWidget(reset_btn)

        stopwatch_layout.addLayout(btn_lay)

        # --- Buzzer Tool Group Box ---
        buzzer_group = QGroupBox("Buzzer")
        buzzer_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        buzzer_layout = QVBoxLayout(buzzer_group)
        buzzer_layout.setContentsMargins(8, 8, 8, 8)
        buzzer_layout.setSpacing(8)

        # ActiveTimeInCycle
        active_lay = QHBoxLayout()
        active_lay.addWidget(QLabel("Active Time (ms):", styleSheet="color:white"))
        self.buzzer_active = QSpinBox()
        self.buzzer_active.setRange(1, 10000)
        self.buzzer_active.setValue(500)
        active_lay.addWidget(self.buzzer_active)
        buzzer_layout.addLayout(active_lay)

        # OffTimeInCycle
        off_lay = QHBoxLayout()
        off_lay.addWidget(QLabel("Off Time (ms):", styleSheet="color:white"))
        self.buzzer_off = QSpinBox()
        self.buzzer_off.setRange(0, 10000)
        self.buzzer_off.setValue(500)
        off_lay.addWidget(self.buzzer_off)
        buzzer_layout.addLayout(off_lay)

        # PlayTotalTime
        total_lay = QHBoxLayout()
        total_lay.addWidget(QLabel("Total Play Time (ms):", styleSheet="color:white"))
        self.buzzer_total = QSpinBox()
        self.buzzer_total.setRange(1, 60000)
        self.buzzer_total.setValue(3000)
        total_lay.addWidget(self.buzzer_total)
        buzzer_layout.addLayout(total_lay)

        # Play button
        play_btn = QToolButton(text="Play Buzzer")
        play_btn.setStyleSheet("""
            QToolButton { color: white; font-size: 14px; }
            QToolButton:hover { background: #222; }
        """)
        play_btn.clicked.connect(self.send_buzzer)
        buzzer_layout.addWidget(play_btn, alignment=Qt.AlignRight)

        # --- Noise Tool Group Box ---
        noise_group = QGroupBox("Noise Meter")
        noise_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        noise_layout = QVBoxLayout(noise_group)
        noise_layout.setContentsMargins(8, 8, 8, 8)
        noise_layout.setSpacing(8)

        btn_lay = QHBoxLayout()
        start_btn = QToolButton(text="Start")
        start_btn.setStyleSheet("""
            QToolButton { color: white; font-size: 14px; }
            QToolButton:hover { background: #222; }
        """)
        start_btn.clicked.connect(lambda: self.send_noise(1))
        btn_lay.addWidget(start_btn)

        stop_btn = QToolButton(text="Stop")
        stop_btn.setStyleSheet("""
            QToolButton { color: white; font-size: 14px; }
            QToolButton:hover { background: #222; }
        """)
        stop_btn.clicked.connect(lambda: self.send_noise(0))
        btn_lay.addWidget(stop_btn)

        noise_layout.addLayout(btn_lay)

         # Add all tool group boxes to the API Tools vertical layout
        api_tools_layout.addWidget(scoreboard_group)
        api_tools_layout.addWidget(timer_group)
        api_tools_layout.addWidget(stopwatch_group)
        api_tools_layout.addWidget(buzzer_group)
        api_tools_layout.addWidget(noise_group)
        api_tools_layout.addStretch()

        # Add API Tools group to the main layout (left side)
        main_layout.addWidget(api_tools_group, alignment=Qt.AlignTop | Qt.AlignLeft)

        # --- Banner Split & Send Tool ---
        banner_group = QGroupBox("Banner Split & Send")
        banner_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 16px; border: 2px solid #888; border-radius: 8px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px 0 6px; }"
        )
        banner_layout = QVBoxLayout(banner_group)
        banner_layout.setContentsMargins(12, 12, 12, 12)
        banner_layout.setSpacing(8)

        # Image preview and vertical slider side by side
        preview_row = QHBoxLayout()
        self.banner_label = QLabel("No image loaded")
        self.banner_label.setFixedSize(320, 64)  # Scaled preview (half size)
        self.banner_label.setStyleSheet("background: #111; border: 1px solid #444;")
        self.banner_label.setAlignment(Qt.AlignCenter)
        preview_row.addWidget(self.banner_label)

        self.vert_slider = QSlider(Qt.Vertical)
        self.vert_slider.setRange(0, 100)
        self.vert_slider.setValue(50)
        self.vert_slider.setMinimumHeight(120)
        preview_row.addWidget(self.vert_slider)

        banner_layout.addLayout(preview_row)

        # Horizontal position slider under the preview
        self.pos_slider = QSlider(Qt.Horizontal)
        self.pos_slider.setRange(0, 100)
        self.pos_slider.setValue(50)
        banner_layout.addWidget(QLabel("Horizontal Position:", styleSheet="color:white"))
        banner_layout.addWidget(self.pos_slider)


        # Controls row: Import, Resize Mode, Send
        controls_row = QHBoxLayout()

        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_banner_image)
        controls_row.addWidget(import_btn)

        controls_row.addWidget(QLabel("", styleSheet="color:white"))

        self.fit_mode = QComboBox()
        self.fit_mode.addItems(["Fit", "Stretch", "Crop"])
        controls_row.addWidget(self.fit_mode)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_banner_to_screens)
        controls_row.addWidget(send_btn)

        controls_row.addStretch()
        banner_layout.addLayout(controls_row)

        # Zoom slider under the horizontal position slider
        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Zoom:", styleSheet="color:white"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 200)  # 10% to 200%
        self.zoom_slider.setValue(100)      # Default 100%
        self.zoom_slider.setEnabled(False)
        zoom_row.addWidget(self.zoom_slider)
        banner_layout.addLayout(zoom_row)

        # Store loaded image and preview
        self.loaded_banner = None
        self.banner_preview = None

        # Update preview on slider or mode change
        self.fit_mode.currentIndexChanged.connect(self.update_banner_preview)
        self.pos_slider.valueChanged.connect(self.update_banner_preview)
        self.vert_slider.valueChanged.connect(self.update_banner_preview)
        self.zoom_slider.valueChanged.connect(self.update_banner_preview)

        # Add to main layout
        main_layout.addWidget(banner_group, alignment=Qt.AlignTop | Qt.AlignLeft)
        main_layout.addStretch()

        # --- Send Text Tool Group Box ---
        send_text_group = QGroupBox("Send Text to Screen")
        send_text_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        send_text_layout = QVBoxLayout(send_text_group)
        send_text_layout.setContentsMargins(8, 8, 8, 8)
        send_text_layout.setSpacing(8)

        row = QHBoxLayout()
        row.addWidget(QLabel("Screen (LcdId):", styleSheet="color:white"))
        self.lcdid_spin = QSpinBox()
        self.lcdid_spin.setRange(0, 4)  # 0-4 for 5 screens
        self.lcdid_spin.setValue(0)
        row.addWidget(self.lcdid_spin)
        send_text_layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Text:", styleSheet="color:white"))
        self.text_input = QLineEdit()
        row2.addWidget(self.text_input)
        send_text_layout.addLayout(row2)

        # X and Y
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("X:", styleSheet="color:white"))
        self.text_x = QSpinBox()
        self.text_x.setRange(0, 64)      # Max X is 64
        self.text_x.setValue(32)         # Default X is 32 (centered)
        row3.addWidget(self.text_x)
        row3.addWidget(QLabel("Y:", styleSheet="color:white"))
        self.text_y = QSpinBox()
        self.text_y.setRange(0, 64)      # Max Y is 64
        self.text_y.setValue(40)
        row3.addWidget(self.text_y)
        send_text_layout.addLayout(row3)

        # Direction and Font
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Direction:", styleSheet="color:white"))
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["Left", "Right"])  # Only Left(0) and Right(1)
        row4.addWidget(self.dir_combo)
        row4.addWidget(QLabel("Font:", styleSheet="color:white"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(0, 7)
        self.font_spin.setValue(4)
        row4.addWidget(self.font_spin)
        send_text_layout.addLayout(row4)

        # Width and Speed
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Width:", styleSheet="color:white"))
        self.text_width = QSpinBox()
        self.text_width.setRange(1, 64)   # Max width is 64
        self.text_width.setValue(64)      # Default width is 64
        row5.addWidget(self.text_width)
        row5.addWidget(QLabel("Speed:", styleSheet="color:white"))
        self.text_speed = QComboBox()
        self.text_speed.addItems(["Slow", "Medium", "Fast"])
        row5.addWidget(self.text_speed)
        send_text_layout.addLayout(row5)

        # Color picker and Align
        row6 = QHBoxLayout()
        row6.addWidget(QLabel("Color:", styleSheet="color:white"))
        self.text_color = QLineEdit("#FFFF00")
        color_btn = QPushButton("Pick")
        color_btn.setMaximumWidth(40)
        def pick_color():
            color = QColorDialog.getColor(QColor(self.text_color.text()), self, "Pick Text Color")
            if color.isValid():
                self.text_color.setText(color.name())
        color_btn.clicked.connect(pick_color)
        row6.addWidget(self.text_color)
        row6.addWidget(color_btn)
        row6.addWidget(QLabel("Align:", styleSheet="color:white"))
        self.align_combo = QComboBox()
        self.align_combo.addItems(["Left", "Center", "Right"])
        row6.addWidget(self.align_combo)
        send_text_layout.addLayout(row6)

        send_btn = QPushButton("Send Text")
        send_btn.clicked.connect(self.send_text_to_screen)
        send_text_layout.addWidget(send_btn, alignment=Qt.AlignRight)

        main_layout.addWidget(send_text_group, alignment=Qt.AlignTop | Qt.AlignLeft)

    def send_scoreboard(self):
        ip = self.cfg.get_device_ip()
        blue = self.blue_score.value()
        red = self.red_score.value()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetScoreBoard",
            "BlueScore": blue,
            "RedScore": red
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_countdown(self):
        ip = self.cfg.get_device_ip()
        minutes = self.timer_minutes.value()
        seconds = self.timer_seconds.value()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetTimer",
            "Minute": minutes,
            "Second": seconds,
            "Status": 1  # 1 = start, 0 = stop
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_stopwatch(self, status):
        ip = self.cfg.get_device_ip()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetStopWatch",
            "Status": status  # 2:reset; 1: start; 0: stop
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_buzzer(self):
        ip = self.cfg.get_device_ip()
        if not ip:
            return
        payload = {
            "Command": "Device/PlayBuzzer",
            "ActiveTimeInCycle": self.buzzer_active.value(),
            "OffTimeInCycle": self.buzzer_off.value(),
            "PlayTotalTime": self.buzzer_total.value()
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_noise(self, status):
        ip = self.cfg.get_device_ip()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetNoiseStatus",
            "NoiseStatus": status  # 1 = start, 0 = stop
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def import_banner_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Banner Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            img = Image.open(path).convert("RGB")
            self.loaded_banner = img
            self.pos_slider.setEnabled(True)
            self.vert_slider.setEnabled(True)
            self.zoom_slider.setEnabled(True)
            self.update_banner_preview()

    def update_banner_preview(self):
        if not self.loaded_banner:
            self.banner_label.setText("No image loaded")
            return

        img = self.loaded_banner.copy()
        canvas_w, canvas_h = 640, 128

        # Get slider values (0.0 - 1.0)
        h_pos = self.pos_slider.value() / 100
        v_pos = self.vert_slider.value() / 100
        zoom = self.zoom_slider.value() / 100  # 1.0 = 100%

        # Scale image
        zoomed_w = max(1, int(img.width * zoom))
        zoomed_h = max(1, int(img.height * zoom))
        img = img.resize((zoomed_w, zoomed_h), Image.LANCZOS)

        # For both axes, allow full range: image can be fully off any side
        min_left = canvas_w - zoomed_w
        max_left = 0
        img_left = int(min_left + h_pos * (max_left - min_left))

        min_top = canvas_h - zoomed_h
        max_top = 0
        img_top = int(min_top + v_pos * (max_top - min_top))

        # Paste image onto canvas (shows background if image is smaller than canvas)
        bg = Image.new("RGB", (canvas_w, canvas_h), (30, 30, 30))
        bg.paste(img, (img_left, img_top))
        img = bg

        # Save preview and show (scaled down)
        preview = img.resize((320, 64), Image.LANCZOS)
        self.banner_preview = img
        qimg = pil_to_qimage(preview)
        self.banner_label.setPixmap(QPixmap.fromImage(qimg))

    def send_banner_to_screens(self):
        if not self.banner_preview:
            QMessageBox.warning(self, "No Image", "Please import and preview a banner image first.")
            return

        ip = self.cfg.get_device_ip()
        if not ip:
            QMessageBox.warning(self, "No IP", "No device IP set.")
            return

        # Split into 5 sections and send
        for i in range(5):
            section = self.banner_preview.crop((i*128, 0, (i+1)*128, 128))
            buf = BytesIO()
            section.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode()
            payload = {
                "Command": "Draw/SendHttpGif",
                "LcdArray": [1 if j == i else 0 for j in range(5)],
                "PicNum": 1,
                "PicOffset": 0,
                "PicID": int(time.time()) + i,
                "PicSpeed": 100,
                "PicWidth": 128,
                "PicData": b64
            }
            try:
                requests.post(f"http://{ip}/post", json=payload, timeout=8)
            except Exception as e:
                QMessageBox.warning(self, "Send Error", f"Failed to send to screen {i+1}:\n{e}")

    def send_text_to_screen(self):
        ip = self.cfg.get_device_ip()
        if not ip:
            QMessageBox.warning(self, "No IP", "No device IP set.")
            return
        text = self.text_input.text().strip()
        if not text:
            QMessageBox.warning(self, "No Text", "Please enter text to send.")
            return
        if len(text) >= 512:
            QMessageBox.warning(self, "Text Too Long", "Text must be less than 512 characters.")
            return
        lcd_id = self.lcdid_spin.value()
        x = self.text_x.value()
        y = self.text_y.value()
        dir_map = {"Left": 0, "Right": 1}
        direction = dir_map[self.dir_combo.currentText()]
        font = self.font_spin.value()
        text_width = self.text_width.value()
        speed_map = {"Slow": 100, "Medium": 50, "Fast": 1}
        speed = speed_map[self.text_speed.currentText()]
        color = self.text_color.text().strip() or "#FFFF00"
        align_map = {"Left": 0, "Center": 1, "Right": 2}
        align = align_map[self.align_combo.currentText()]
        payload = {
            "Command": "Draw/SendHttpText",
            "LcdId": lcd_id,
            "TextId": 4,
            "x": x,
            "y": y,
            "dir": direction,
            "font": font,
            "TextWidth": text_width,
            "speed": speed,
            "TextString": text,
            "color": color,
            "align": align
        }
        try:
            resp = requests.post(f"http://{ip}/post", json=payload, timeout=8)
            if resp.ok:
                QMessageBox.information(self, "Success", f"Text sent to screen {lcd_id+1}.")
            else:
                QMessageBox.warning(self, "Send Error", f"Device responded with error: {resp.text}")
        except Exception as e:
            QMessageBox.warning(self, "Send Error", f"Failed to send text:\n{e}")

    def reset_position_sliders(self):
        # No enable/disable logic, just keep sliders as-is and update preview
        self.update_banner_preview()

