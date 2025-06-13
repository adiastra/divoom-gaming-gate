from utils.config import Config
import time, io, base64, requests
from PIL import Image, ImageSequence
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QSlider, QComboBox
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer

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

        # Raw/processed frames and preview index
        self.raw_frames = []
        self.frames     = []
        self.preview_idx = 0

        # Settings
        self.speed   = DEFAULT_SPEED
        self.quality = DEFAULT_QUALITY
        self.skip    = 1

        # UI setup
        self.label = QLabel(f"Screen {screen_index+1}")
        self.preview = QLabel()
        self.preview.setFixedSize(IMG_SIZE, IMG_SIZE)
        self.preview.setStyleSheet("border:1px solid white;")
        self.preview.setAlignment(Qt.AlignCenter)

        # Timer for animation
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._advance_preview)

        # Controls
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Stretch","Fit","Crop"])
        self.mode_combo.currentIndexChanged.connect(self.apply_mode)

        self.load_btn = QPushButton("Load")
        self.send_btn = QPushButton("Send")

        self.speed_box = QSpinBox()
        self.speed_box.setRange(10, 2000)
        self.speed_box.setValue(self.speed)
        self.speed_box.setSuffix(" ms")
        self.speed_box.valueChanged.connect(self._on_speed_changed)

        self.skip_box = QSpinBox()
        self.skip_box.setRange(1, MAX_SKIP)
        self.skip_box.setValue(self.skip)
        self.skip_box.valueChanged.connect(self._on_skip_changed)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(40, 95)
        self.quality_slider.setValue(self.quality)
        self.quality_slider.valueChanged.connect(lambda v: setattr(self, "quality", v))

        # Layout
        main = QVBoxLayout()
        main.setAlignment(Qt.AlignTop)
        main.addWidget(self.label)

        pv_box = QHBoxLayout()
        pv_box.addStretch(); pv_box.addWidget(self.preview); pv_box.addStretch()
        main.addLayout(pv_box)

        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Import Mode:")); mrow.addWidget(self.mode_combo)
        main.addLayout(mrow)

        brow = QHBoxLayout()
        brow.addWidget(self.load_btn); brow.addWidget(self.send_btn)
        main.addLayout(brow)

        main.addLayout(self._labeled_row("Frame Speed:", self.speed_box))
        main.addLayout(self._labeled_row("Frame Skip:",  self.skip_box))
        main.addLayout(self._labeled_row("Image Quality:", self.quality_slider))

        self.setLayout(main)

        # Signals
        self.load_btn.clicked.connect(self.load_image)
        self.send_btn.clicked.connect(self.send_to_screen)

    def _labeled_row(self, text, widget):
        row = QHBoxLayout()
        row.addWidget(QLabel(text))
        row.addWidget(widget)
        return row

    def _on_speed_changed(self, v):
        self.speed = v
        if self.anim_timer.isActive():
            self.anim_timer.start(self.speed)

    def _on_skip_changed(self, v):
        self.skip = v
        self.apply_mode()  # rebuild self.frames with new skip

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image or GIF", "", "Images (*.png *.jpg *.jpeg *.gif)"
        )
        if not path:
            return

        img = Image.open(path)
        if getattr(img, "is_animated", False):
            self.raw_frames = [fr.convert("RGB") for fr in ImageSequence.Iterator(img)]
        else:
            self.raw_frames = [img.convert("RGB")]

        self.label.setText(f"Loaded {len(self.raw_frames)} frame(s)")
        self.apply_mode()
        self._start_animation()

    def apply_mode(self):
        mode = self.mode_combo.currentText()
        proc = []
        for img in self.raw_frames:
            w,h = img.size
            if mode == "Stretch":
                norm = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            elif mode == "Fit":
                thumb = img.copy()
                thumb.thumbnail((IMG_SIZE,IMG_SIZE), Image.LANCZOS)
                bg = Image.new("RGB",(IMG_SIZE,IMG_SIZE),(0,0,0))
                bg.paste(thumb, ((IMG_SIZE-thumb.width)//2,(IMG_SIZE-thumb.height)//2))
                norm = bg
            elif mode == "Crop":
                side = min(w,h)
                left = (w-side)//2; top=(h-side)//2
                crop = img.crop((left,top,left+side,top+side))
                norm = crop.resize((IMG_SIZE,IMG_SIZE),Image.LANCZOS)
            else:
                norm = img.resize((IMG_SIZE,IMG_SIZE), Image.LANCZOS)
            proc.append(norm)
        # apply skip
        self.frames = proc[::self.skip] or proc[:1]
        self.preview_idx = 0
        self.update_preview()

    def _start_animation(self):
        if len(self.frames) > 1:
            self.anim_timer.start(self.speed)
        else:
            self.anim_timer.stop()

    def _advance_preview(self):
        if not self.frames:
            return
        self.preview_idx = (self.preview_idx + 1) % len(self.frames)
        self.update_preview()

    def update_preview(self):
        if not self.frames:
            return
        img = self.frames[self.preview_idx]
        data = img.tobytes("raw","RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def send_to_screen(self):
        # Refresh IP
        global DEVICE_IP
        DEVICE_IP = Config.IP_ADDRESS

        if not self.frames:
            return

        frames_to_send = self.frames
        pic_id = int(time.time())
        lcd = [0]*SCREEN_COUNT
        lcd[self.screen_index] = 1

        for offset, frame in enumerate(frames_to_send):
            buf = io.BytesIO()
            frame.save(buf, format="JPEG", quality=self.quality)
            b64 = base64.b64encode(buf.getvalue()).decode()

            payload = {
                "Command":   "Draw/SendHttpGif",
                "LcdArray":  lcd,
                "PicNum":    len(frames_to_send),
                "PicOffset": offset,
                "PicID":     pic_id,
                "PicSpeed":  self.speed,
                "PicWidth":  IMG_SIZE,
                "PicData":   b64
            }
            requests.post(f"http://{DEVICE_IP}/post", json=payload)
