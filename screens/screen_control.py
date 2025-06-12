import time, io, base64, requests
from PIL import Image, ImageSequence
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QSlider, QComboBox, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

DEVICE_IP       = "10.10.10.122"
SCREEN_COUNT    = 5
IMG_SIZE        = 128
DEFAULT_SPEED   = 100
DEFAULT_QUALITY = 85
MAX_SKIP        = 10

class ScreenControl(QWidget):
    def __init__(self, screen_index):
        super().__init__()
        self.screen_index = screen_index

        # Raw & processed frames
        self.raw_frames = []
        self.frames     = []

        # Settings
        self.speed   = DEFAULT_SPEED
        self.quality = DEFAULT_QUALITY
        self.skip    = 1

        # UI Widgets
        self.label     = QLabel(f"Screen {screen_index+1}")
        self.preview   = QLabel()
        self.preview.setFixedSize(IMG_SIZE, IMG_SIZE)
        self.preview.setStyleSheet("border:1px solid white;")
        self.preview.setAlignment(Qt.AlignCenter)

        # center preview
        preview_box = QHBoxLayout()
        preview_box.addStretch()
        preview_box.addWidget(self.preview)
        preview_box.addStretch()

        self.mode_combo  = QComboBox()
        self.mode_combo.addItems(["Stretch","Fit","Crop"])
        self.mode_combo.currentIndexChanged.connect(self.apply_mode)

        self.load_btn    = QPushButton("Load")
        self.send_btn    = QPushButton("Send")

        self.speed_box   = QSpinBox()
        self.speed_box.setRange(10,2000)
        self.speed_box.setValue(self.speed)
        self.speed_box.setSuffix(" ms")
        self.speed_box.valueChanged.connect(lambda v: setattr(self, "speed", v))

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(40,95)
        self.quality_slider.setValue(self.quality)
        self.quality_slider.valueChanged.connect(lambda v: setattr(self, "quality", v))

        self.skip_box = QSpinBox()
        self.skip_box.setRange(1,MAX_SKIP)
        self.skip_box.setValue(self.skip)
        self.skip_box.valueChanged.connect(lambda v: setattr(self, "skip", v))

        # Main Layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self.label)
        layout.addLayout(preview_box)

        # Mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        mode_row.addWidget(self.mode_combo)
        layout.addLayout(mode_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.load_btn)
        btn_row.addWidget(self.send_btn)
        layout.addLayout(btn_row)

        # Options
        opt_row = QHBoxLayout()
        opt_row.addWidget(self.speed_box)
        opt_row.addWidget(self.quality_slider)
        opt_row.addWidget(self.skip_box)
        layout.addLayout(opt_row)

        self.setLayout(layout)

        # Signals
        self.load_btn.clicked.connect(self.load_image)
        self.send_btn.clicked.connect(self.send_to_screen)

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image or GIF", "", "Images (*.png *.jpg *.jpeg *.gif)"
        )
        if not path:
            return

        raw = Image.open(path)
        self.raw_frames = []
        if getattr(raw, "is_animated", False):
            for fr in ImageSequence.Iterator(raw):
                self.raw_frames.append(fr.convert("RGB"))
        else:
            self.raw_frames = [raw.convert("RGB")]

        self.label.setText(f"Loaded {len(self.raw_frames)} raw frame(s)")
        self.apply_mode()

    def apply_mode(self):
        mode = self.mode_combo.currentText()
        self.frames = []

        def normalize(img):
            w, h = img.size
            if mode == "Stretch":
                return img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            elif mode == "Fit":
                img.thumbnail((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
                bg = Image.new("RGB", (IMG_SIZE, IMG_SIZE), (0,0,0))
                bg.paste(img, ((IMG_SIZE-img.width)//2, (IMG_SIZE-img.height)//2))
                return bg
            elif mode == "Crop":
                side = min(w, h)
                left = (w - side)//2
                top  = (h - side)//2
                crop = img.crop((left, top, left+side, top+side))
                return crop.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            return img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

        for raw in self.raw_frames:
            self.frames.append(normalize(raw))

        self.label.setText(f"Mode {mode}: {len(self.frames)} frame(s)")
        self.update_preview()

    def update_preview(self):
        if not self.frames:
            return
        img = self.frames[0]
        data = img.tobytes("raw","RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def send_to_screen(self):
        if not self.frames:
            return

        pic_id = int(time.time())
        lcd = [0]*SCREEN_COUNT
        lcd[self.screen_index] = 1
        frames = self.frames[::self.skip]

        for offset, frame in enumerate(frames):
            buf = io.BytesIO()
            frame.save(buf, format="JPEG", quality=self.quality)
            b64 = base64.b64encode(buf.getvalue()).decode()

            payload = {
                "Command":   "Draw/SendHttpGif",
                "LcdArray":  lcd,
                "PicNum":    len(frames),
                "PicOffset": offset,
                "PicID":     pic_id,
                "PicSpeed":  self.speed,
                "PicWidth":  IMG_SIZE,
                "PicData":   b64
            }
            requests.post(f"http://{DEVICE_IP}/post", json=payload)
