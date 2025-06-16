import os, json, base64, io, requests
from PIL import Image
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QInputDialog, QMessageBox, QColorDialog, QSpinBox, QComboBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from utils.config import Config

# constants that match the rest of your code-base
IMG_SIZE      = 128
SCREEN_COUNT  = 5
CANVAS_PIX    = IMG_SIZE * 4  # 4× zoomed canvas

class DesignerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")
        self.cfg = Config()

        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ─── Top toolbar ──────────────────────────────────────────────────────
        top = QWidget(); top.setStyleSheet("background:#3c3c3c")
        tlay = QHBoxLayout(top); tlay.setContentsMargins(4,4,4,4); tlay.setSpacing(8)
        def tbtn(txt, tip, cb):
            b = QToolButton(text=txt, toolTip=tip, autoRaise=True)
            b.setStyleSheet("color:white;font-size:18px"); b.clicked.connect(cb); tlay.addWidget(b)
        tbtn('▭', "Add rectangle", lambda: self._js("EditorAPI.newRect();"))
        tbtn('◯', "Add circle", lambda: self._js("EditorAPI.newCircle();"))
        tbtn('⬟', "Add polygon",   lambda: self._js("EditorAPI.newPolygon();")) 
        tbtn('T', "Add text", self._add_text)
        tbtn('🗑', "Clear",    lambda: self._js("EditorAPI.clear();"))
        tbtn('📤', "Send to screen", self._send)
        tlay.addStretch()
        root.addWidget(top)

        # ─── Center area (canvas + properties) ───────────────────────────────
        mid = QHBoxLayout(); mid.setContentsMargins(0,0,0,0); mid.setSpacing(0)

        self.view = QWebEngineView()
        self.view.setFixedSize(CANVAS_PIX, CANVAS_PIX)
        html = os.path.join(os.path.dirname(__file__), "editor.html")
        self.view.load(QUrl.fromLocalFile(os.path.abspath(html)))
        mid.addWidget(self.view, alignment=Qt.AlignLeft | Qt.AlignTop)

        prop = QWidget(); prop.setFixedWidth(200); prop.setStyleSheet("background:#3c3c3c")
        play = QVBoxLayout(prop); play.setContentsMargins(8,8,8,8); play.setSpacing(10)
        play.addWidget(QLabel("Object Properties", alignment=Qt.AlignCenter))

        fbtn = QToolButton(text='Fill Color', toolTip="Fill", autoRaise=True)
        fbtn.setStyleSheet("color:white;font-size:12px"); fbtn.clicked.connect(self._change_fill)
        play.addWidget(fbtn)

        sbtn = QToolButton(text='Stroke Color', toolTip="Stroke", autoRaise=True)
        sbtn.setStyleSheet("color:white;font-size:12px"); sbtn.clicked.connect(self._change_stroke)
        play.addWidget(sbtn)

        wlay = QHBoxLayout()
        wlay.addWidget(QLabel("Width", styleSheet="color:white"))
        self.stroke_spin = QSpinBox(); self.stroke_spin.setRange(1,20)
        self.stroke_spin.valueChanged.connect(self._set_stroke_width)
        wlay.addWidget(self.stroke_spin); play.addLayout(wlay)

        play.addWidget(QLabel("Font", styleSheet="color:white"))
        self.font_combo = QComboBox()
        for fam in ["Arial","Helvetica","Times New Roman","Courier New","Verdana"]:
            self.font_combo.addItem(fam)
        self.font_combo.currentTextChanged.connect(self._set_font)
        play.addWidget(self.font_combo)

        slay = QHBoxLayout()
        slay.addWidget(QLabel("Size", styleSheet="color:white"))
        self.font_spin = QSpinBox(); self.font_spin.setRange(8,72)
        self.font_spin.valueChanged.connect(self._set_font_size)
        slay.addWidget(self.font_spin); play.addLayout(slay)

        play.addStretch()
        mid.addWidget(prop); mid.addStretch()
        root.addLayout(mid, 1)

        # ─── Frame controls (bottom) ─────────────────────────────────────────
        bot = QWidget(); bot.setStyleSheet("background:#3c3c3c")
        bl  = QHBoxLayout(bot); bl.setContentsMargins(4,4,4,4); bl.setSpacing(8)
        def fbtn(txt, tip, cb):
            b = QToolButton(text=txt, toolTip=tip, autoRaise=True)
            b.setStyleSheet("color:white;font-size:16px"); b.clicked.connect(cb); bl.addWidget(b)
        fbtn('＋',"New frame",   lambda: self._js("EditorAPI.addFrame();"))
        fbtn('✎',"Clone",       lambda: self._js("EditorAPI.cloneFrame();"))
        fbtn('←',"Previous",    lambda: self._js("EditorAPI.prevFrame();"))
        self.frame_lbl = QLabel("1/1", styleSheet="color:white"); bl.addWidget(self.frame_lbl)
        fbtn('→',"Next",        lambda: self._js("EditorAPI.nextFrame();"))
        bl.addStretch()
        fbtn('▶',"Play",        lambda: self._js("EditorAPI.playAnimation(500);"))
        fbtn('⏸',"Pause",       lambda: self._js("EditorAPI.stopAnimation();"))
        root.addWidget(bot)

    # ───────────────────── JavaScript helper ────────────────────────────────
    def _js(self, code):
        self.view.page().runJavaScript(code, self._update_frame_lbl)
    def _update_frame_lbl(self, txt):
        if isinstance(txt,str) and '/' in txt: self.frame_lbl.setText(txt)

    # ───────────────────── Toolbar actions ──────────────────────────────────
    def _add_text(self):
        txt, ok = QInputDialog.getText(self,"Insert Text","Text:")
        if ok and txt: self._js(f"EditorAPI.newText({json.dumps(txt)});")

    def _change_fill(self):
        col = QColorDialog.getColor(QColor("white"), self, "Fill")
        if col.isValid(): self._js(f"var o=canvas.getActiveObject();if(o){{o.set('fill','{col.name()}');canvas.renderAll();}}")
    def _change_stroke(self):
        col = QColorDialog.getColor(QColor("white"), self, "Stroke")
        if col.isValid(): self._js(f"var o=canvas.getActiveObject();if(o){{o.set('stroke','{col.name()}');canvas.renderAll();}}")
    def _set_stroke_width(self,w): self._js(f"var o=canvas.getActiveObject();if(o){{o.set('strokeWidth',{w});canvas.renderAll();}}")
    def _set_font       (self,f ): self._js(f"var o=canvas.getActiveObject();if(o){{o.set('fontFamily','{f}');canvas.renderAll();}}")
    def _set_font_size  (self,s ): self._js(f"var o=canvas.getActiveObject();if(o){{o.set('fontSize',{s});canvas.renderAll();}}")

    # ───────────────────── Send to Divoom ───────────────────────────────────

    def _send(self):
        import time
        ip = self.cfg.get_device_ip()
        if not ip:
            QMessageBox.warning(self, "No IP", "Configure the device IP in Settings.")
            return

        def process(frames_js):
            try:
                frames = json.loads(frames_js) if isinstance(frames_js, str) else frames_js
                if not frames:
                    QMessageBox.warning(self, "Export Error", "No frames exported.")
                    return
                if len(frames) > 60:
                    QMessageBox.warning(self, "Too many frames", "Maximum 60 frames allowed.")
                    return

                imgs = []
                for entry in frames:
                    url = entry if isinstance(entry, str) else entry.get("dataURL", "")
                    b64_part = url.split(",", 1)[1] if "," in url else url
                    img = Image.open(io.BytesIO(base64.b64decode(b64_part))).convert("RGB")
                    imgs.append(img.resize((IMG_SIZE, IMG_SIZE)))

                pic_id  = int(time.time())          # unique animation id
                pic_num = len(imgs)

                for idx, img in enumerate(imgs):
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    b64_jpg = base64.b64encode(buf.getvalue()).decode()

                    payload = {
                        "Command":  "Draw/SendHttpGif",
                        "LcdArray": [1,1,1,1,1],      # send to all panels
                        "PicNum":   pic_num,
                        "PicOffset":idx,              # 0 .. pic_num-1
                        "PicID":    pic_id,
                        "PicSpeed": 100,
                        "PicWidth": IMG_SIZE,
                        "PicData":  b64_jpg
                    }
                    requests.post(f"http://{ip}/post", json=payload, timeout=8)

                QMessageBox.information(
                    self, "Send",
                    f"Sent {pic_num} frame(s) animation as JPEG sequence."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to send:\n{exc}")

        self.view.page().runJavaScript("EditorAPI.exportAllFrames();", process)
