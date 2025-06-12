import time, io, base64, requests
from PIL import Image, ImageSequence
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QSlider
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

DEVICE_IP = "10.10.10.122"
SCREEN_COUNT = 5
IMG_SIZE = 128
DEFAULT_SPEED_MS = 100
DEFAULT_QUALITY = 85
MAX_SKIP = 10

class ScreenControl(QWidget):
    def __init__(self, screen_index):
        super().__init__()
        self.screen_index = screen_index
        self.frames = []
        self.speed = DEFAULT_SPEED_MS
        self.quality = DEFAULT_QUALITY
        self.skip = 1

        # Widgets
        self.label = QLabel(f"Screen {screen_index + 1}")
        self.preview = QLabel()
        self.preview.setFixedSize(IMG_SIZE, IMG_SIZE)
        self.preview.setStyleSheet("border:1px solid white;")
        self.preview.setAlignment(Qt.AlignCenter)

        self.load_btn = QPushButton("Load")
        self.send_btn = QPushButton("Send")

        self.speed_box = QSpinBox()
        self.speed_box.setRange(10, 2000)
        self.speed_box.setValue(self.speed)
        self.speed_box.setSuffix(" ms")
        self.speed_box.valueChanged.connect(self.update_speed)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(40, 95)
        self.quality_slider.setValue(self.quality)
        self.quality_slider.valueChanged.connect(self.update_quality)

        self.skip_box = QSpinBox()
        self.skip_box.setRange(1, MAX_SKIP)
        self.skip_box.setValue(self.skip)
        self.skip_box.valueChanged.connect(self.update_skip)

        # Layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self.label)
        layout.addWidget(self.preview)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.load_btn)
        btn_row.addWidget(self.send_btn)
        layout.addLayout(btn_row)

        opt_row = QHBoxLayout()
        opt_row.addWidget(self.speed_box)
        opt_row.addWidget(self.quality_slider)
        opt_row.addWidget(self.skip_box)
        layout.addLayout(opt_row)

        self.setLayout(layout)

        # Signals
        self.load_btn.clicked.connect(self.load_image)
        self.send_btn.clicked.connect(self.send_to_screen)

    def update_speed(self, val):
        self.speed = val

    def update_quality(self, val):
        self.quality = val

    def update_skip(self, val):
        self.skip = val

    def load_image(self):
        # Accept .png, .jpg, .jpeg, .gif
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image or GIF",
            "",
            "Images (*.png *.jpg *.jpeg *.gif)"
        )
        if not path:
            return

        img = Image.open(path)
        self.frames = []

        if getattr(img, 'is_animated', False):
            for frame in ImageSequence.Iterator(img):
                self.frames.append(
                    frame.convert("RGB").resize((IMG_SIZE, IMG_SIZE))
                )
        else:
            self.frames.append(
                img.convert("RGB").resize((IMG_SIZE, IMG_SIZE))
            )

        self.update_preview()
        self.label.setText(f"Loaded {len(self.frames)} frame(s)")

    def update_preview(self):
        if not self.frames:
            return
        img = self.frames[0]
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def send_to_screen(self):
        if not self.frames:
            return

        frames = self.frames[::self.skip]
        pic_id = int(time.time())
        lcd = [0] * SCREEN_COUNT
        lcd[self.screen_index] = 1

        for i, frame in enumerate(frames):
            buf = io.BytesIO()
            frame.save(buf, format="JPEG", quality=self.quality)
            b64 = base64.b64encode(buf.getvalue()).decode()

            payload = {
                "Command": "Draw/SendHttpGif",
                "LcdArray": lcd,
                "PicNum": len(frames),
                "PicOffset": i,
                "PicID": pic_id,
                "PicSpeed": self.speed,
                "PicWidth": IMG_SIZE,
                "PicData": b64
            }

            requests.post(f"http://{DEVICE_IP}/post", json=payload)