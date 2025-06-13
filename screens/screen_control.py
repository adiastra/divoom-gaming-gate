from utils.config import Config
import time, io, base64, requests
from PIL import Image, ImageSequence
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QSlider, QComboBox
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

# Now reads from Config.IP_ADDRESS
DEVICE_IP       = Config.IP_ADDRESS
SCREEN_COUNT    = 5
IMG_SIZE        = 128
DEFAULT_SPEED   = 100
DEFAULT_QUALITY = 85
MAX_SKIP        = 10

class ScreenControl(QWidget):
    def __init__(self, screen_index):
        super().__init__()
        self.screen_index = screen_index
        self.raw_frames   = []
        self.frames       = []
        self.speed        = DEFAULT_SPEED
        self.quality      = DEFAULT_QUALITY
        self.skip         = 1

        # Title
        self.label = QLabel(f"Screen {screen_index+1}")

        # Preview
        self.preview = QLabel()
        self.preview.setFixedSize(IMG_SIZE, IMG_SIZE)
        self.preview.setStyleSheet("border:1px solid white;")
        self.preview.setAlignment(Qt.AlignCenter)
        pv_box = QHBoxLayout()
        pv_box.addStretch()
        pv_box.addWidget(self.preview)
        pv_box.addStretch()

        # Mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Stretch","Fit","Crop"])
        self.mode_combo.currentIndexChanged.connect(self.apply_mode)

        # Load / Send
        self.load_btn = QPushButton("Load")
        self.send_btn = QPushButton("Send")

        # Frame Speed
        speed_label = QLabel("Frame Speed:")
        self.speed_box = QSpinBox()
        self.speed_box.setRange(10, 2000)
        self.speed_box.setValue(self.speed)
        self.speed_box.setSuffix(" ms")
        self.speed_box.valueChanged.connect(lambda v: setattr(self, "speed", v))
        speed_row = QHBoxLayout()
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self.speed_box)

        # Frame Skip
        skip_label = QLabel("Frame Skip:")
        self.skip_box = QSpinBox()
        self.skip_box.setRange(1, MAX_SKIP)
        self.skip_box.setValue(self.skip)
        self.skip_box.valueChanged.connect(lambda v: setattr(self, "skip", v))
        skip_row = QHBoxLayout()
        skip_row.addWidget(skip_label)
        skip_row.addWidget(self.skip_box)

        # Image Quality
        quality_label = QLabel("Image Quality:")
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(40, 95)
        self.quality_slider.setValue(self.quality)
        self.quality_slider.valueChanged.connect(lambda v: setattr(self, "quality", v))
        quality_row = QHBoxLayout()
        quality_row.addWidget(quality_label)
        quality_row.addWidget(self.quality_slider)

        # Main layout
        main = QVBoxLayout()
        main.setAlignment(Qt.AlignTop)
        main.addWidget(self.label)
        main.addLayout(pv_box)

        # Mode row
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Import Mode:"))
        mrow.addWidget(self.mode_combo)
        main.addLayout(mrow)

        # Load/Send row
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.load_btn)
        btn_row.addWidget(self.send_btn)
        main.addLayout(btn_row)

        # Controls stacked
        main.addLayout(speed_row)
        main.addLayout(skip_row)
        main.addLayout(quality_row)

        self.setLayout(main)

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
        if getattr(raw, "is_animated", False):
            self.raw_frames = [fr.convert("RGB") for fr in ImageSequence.Iterator(raw)]
        else:
            self.raw_frames = [raw.convert("RGB")]

        self.label.setText(f"Loaded {len(self.raw_frames)} frame(s)")
        self.apply_mode()

    def apply_mode(self):
        mode = self.mode_combo.currentText()
        self.frames = []
        for img in self.raw_frames:
            w, h = img.size
            if mode == "Stretch":
                norm = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            elif mode == "Fit":
                img_thumb = img.copy()
                img_thumb.thumbnail((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
                bg = Image.new("RGB", (IMG_SIZE, IMG_SIZE), (0,0,0))
                bg.paste(img_thumb, ((IMG_SIZE-img_thumb.width)//2, (IMG_SIZE-img_thumb.height)//2))
                norm = bg
            elif mode == "Crop":
                side = min(w, h)
                left = (w-side)//2; top = (h-side)//2
                crop = img.crop((left, top, left+side, top+side))
                norm = crop.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            else:
                norm = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            self.frames.append(norm)
        self.update_preview()

    def update_preview(self):
        if not self.frames:
            return
        img = self.frames[0]
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def send_to_screen(self):
        # Reload the latest IP in case it changed
        global DEVICE_IP
        DEVICE_IP = Config.IP_ADDRESS

        if not self.frames:
            return
        pic_id = int(time.time())
        lcd = [0]*SCREEN_COUNT
        lcd[self.screen_index] = 1

        for offset, frame in enumerate(self.frames[::self.skip]):
            buf = io.BytesIO()
            frame.save(buf, format="JPEG", quality=self.quality)
            b64 = base64.b64encode(buf.getvalue()).decode()

            payload = {
                "Command":"Draw/SendHttpGif",
                "LcdArray": lcd,
                "PicNum": len(self.frames),
                "PicOffset": offset,
                "PicID": pic_id,
                "PicSpeed": self.speed,
                "PicWidth": IMG_SIZE,
                "PicData": b64
            }
            requests.post(f"http://{DEVICE_IP}/post", json=payload)
