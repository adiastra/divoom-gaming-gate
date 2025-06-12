import io, base64, time, requests
from PIL import Image
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSpinBox, QPushButton,
    QVBoxLayout, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from utils.image import compose_character_image

DEVICE_IP    = "10.10.10.122"
SCREEN_COUNT = 5
IMG_SIZE     = 128

class CharacterControl(QWidget):
    def __init__(self, slot):
        super().__init__()
        self.slot = slot
        self.char = {
            "name": f"Char {slot+1}",
            "stats": {s: 1 for s in ["Brawn","Agility","Intellect","Cunning","Willpower","Presence"]},
            "background": "", "portrait": ""
        }

        # Name field
        self.name_edit = QLineEdit(self.char["name"])
        self.name_edit.setPlaceholderText("Name")
        self.name_edit.textChanged.connect(self.update_preview)

        # Preview label
        self.preview = QLabel()
        self.preview.setFixedSize(IMG_SIZE, IMG_SIZE)
        self.preview.setStyleSheet("border:1px solid white;")
        self.preview.setAlignment(Qt.AlignCenter)

        # Center the preview horizontally
        preview_box = QHBoxLayout()
        preview_box.addStretch()
        preview_box.addWidget(self.preview)
        preview_box.addStretch()

        # Stat spinboxes
        self.stat_boxes = {}
        stat_layout = QVBoxLayout()
        for stat in self.char["stats"]:
            h = QHBoxLayout()
            lbl = QLabel(stat)
            sb = QSpinBox()
            sb.setRange(1, 10)
            sb.setValue(self.char["stats"][stat])
            sb.valueChanged.connect(self.update_preview)
            self.stat_boxes[stat] = sb
            h.addWidget(lbl)
            h.addWidget(sb)
            stat_layout.addLayout(h)

        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send)

        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self.name_edit)
        layout.addLayout(preview_box)
        layout.addLayout(stat_layout)
        layout.addWidget(self.send_btn)
        self.setLayout(layout)

        # Initial render
        self.update_preview()

    def update_preview(self):
        stats = {s: self.stat_boxes[s].value() for s in self.stat_boxes}
        name = self.name_edit.text()
        img = compose_character_image(
            self.char["background"], self.char["portrait"], name, stats
        )
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def send(self):
        stats = {s: self.stat_boxes[s].value() for s in self.stat_boxes}
        name = self.name_edit.text()
        img = compose_character_image(
            self.char["background"], self.char["portrait"], name, stats
        )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        pid = int(time.time())
        payload = {
            "Command":   "Draw/SendHttpGif",
            "LcdArray":  [1 if i == self.slot else 0 for i in range(SCREEN_COUNT)],
            "PicNum":    1,
            "PicOffset": 0,
            "PicID":     pid,
            "PicSpeed":  100,
            "PicWidth":  IMG_SIZE,
            "PicData":   b64
        }
        requests.post(f"http://{DEVICE_IP}/post", json=payload)
