import os, json, base64, io, requests
from PIL import Image
from PyQt5.QtCore import Qt, QUrl, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QInputDialog, QMessageBox, QColorDialog, QSpinBox, QComboBox, QSizePolicy, QFileDialog
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
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
        tbtn('⬟', "Add polygon", lambda: self._js(f"EditorAPI.newPolygon({self.poly_sides_spin.value()});")) 
        tbtn('／', "Add line", lambda: self._js("EditorAPI.newLine();"))
        tbtn('T', "Add text", self._add_text)
        tbtn('🗑', "Clear",    lambda: self._js("EditorAPI.clear();"))
        tbtn('📤', "Send to screen", self._send)
        tlay.addStretch()
        root.addWidget(top)

        # ─── Center area (canvas + properties) ───────────────────────────────
        mid = QHBoxLayout(); mid.setContentsMargins(0,0,0,0); mid.setSpacing(0)

        # --- Left: Canvas + Frame Controls ---
        canvas_col = QVBoxLayout()
        canvas_col.setContentsMargins(0,0,0,0)
        canvas_col.setSpacing(0)

        self.view = QWebEngineView()
        self.view.setFixedSize(CANVAS_PIX, CANVAS_PIX)
        self.view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        html = os.path.join(os.path.dirname(__file__), "editor.html")
        self.channel = QWebChannel()
        self.channel.registerObject('pyObj', self)
        self.view.page().setWebChannel(self.channel)
        self.view.load(QUrl.fromLocalFile(os.path.abspath(html)))
        canvas_col.addWidget(self.view, alignment=Qt.AlignLeft | Qt.AlignTop)

        # --- Frame controls (directly under canvas, all in one row) ---
        bot = QWidget(); bot.setStyleSheet("background:#3c3c3c")
        bot.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        bl  = QHBoxLayout(bot); bl.setContentsMargins(4,4,4,4); bl.setSpacing(8)
        def fbtn(txt, tip, cb, ref=None):
            b = QToolButton(text=txt, toolTip=tip, autoRaise=True)
            b.setStyleSheet("color:white;font-size:16px")
            b.clicked.connect(cb)
            bl.addWidget(b)
            if ref is not None:
                setattr(self, ref, b)
            return b

        fbtn('＋', "New frame", lambda: self._js("EditorAPI.addFrame();"))
        fbtn('－', "Remove selected frame", lambda: self._js("EditorAPI.removeFrame();"))
        fbtn('✎',"Clone",       lambda: self._js("EditorAPI.cloneFrame();"))
        fbtn('←',"Previous",    lambda: self._js("EditorAPI.prevFrame();"))
        self.frame_lbl = QLabel("1/1", styleSheet="color:white")
        bl.addWidget(self.frame_lbl)
        fbtn('→',"Next",        lambda: self._js("EditorAPI.nextFrame();"))
        fbtn('▶',"Play", lambda: self._js("EditorAPI.playAnimation(500);"), ref="play_btn")
        fbtn('⏸',"Pause",       lambda: self._js("EditorAPI.stopAnimation();"), ref="pause_btn")
        canvas_col.addWidget(bot)

        canvas_widget = QWidget()
        canvas_widget.setLayout(canvas_col)
        mid.addWidget(canvas_widget, alignment=Qt.AlignTop)

        # --- Right: Properties panel ---
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

        self.font_label = QLabel("Font", styleSheet="color:white")
        play.addWidget(self.font_label)
        self.font_combo = QComboBox()
        for fam in ["Arial","Helvetica","Times New Roman","Courier New","Verdana"]:
            self.font_combo.addItem(fam)
        self.font_combo.currentTextChanged.connect(self._set_font)
        play.addWidget(self.font_combo)

        self.font_size_lay = QHBoxLayout()
        self.font_size_label = QLabel("Font Size", styleSheet="color:white")
        self.font_size_lay.addWidget(self.font_size_label)
        self.font_spin = QSpinBox(); self.font_spin.setRange(8,72)
        self.font_spin.valueChanged.connect(self._set_font_size)
        self.font_size_lay.addWidget(self.font_spin)
        play.addLayout(self.font_size_lay)

        # Hide font controls by default
        self.font_label.setVisible(False)
        self.font_combo.setVisible(False)
        self.font_size_label.setVisible(False)
        self.font_spin.setVisible(False)

        # --- Polygon sides control ---
        polysides_lay = QHBoxLayout()
        polysides_lay.addWidget(QLabel("Polygon Sides", styleSheet="color:white"))
        self.poly_sides_spin = QSpinBox()
        self.poly_sides_spin.setRange(3, 12)
        self.poly_sides_spin.setValue(6)
        polysides_lay.addWidget(self.poly_sides_spin)
        play.addLayout(polysides_lay)

        # --- Z-order controls ---
        zlay = QHBoxLayout()
        self.zup_btn = QToolButton(text='▲', toolTip="Bring Forward", autoRaise=True)
        self.zup_btn.setStyleSheet("color:white;font-size:16px")
        self.zup_btn.clicked.connect(lambda: self._js("EditorAPI.zUp();"))
        zlay.addWidget(self.zup_btn)

        self.zdown_btn = QToolButton(text='▼', toolTip="Send Backward", autoRaise=True)
        self.zdown_btn.setStyleSheet("color:white;font-size:16px")
        self.zdown_btn.clicked.connect(lambda: self._js("EditorAPI.zDown();"))
        zlay.addWidget(self.zdown_btn)

        play.addLayout(zlay)

        del_btn = QToolButton(text='❌', toolTip="Delete selected object", autoRaise=True)
        del_btn.setStyleSheet("color:#ff4444;font-size:18px")
        del_btn.clicked.connect(lambda: self._js("EditorAPI.deleteObject();"))
        play.addWidget(del_btn)

        play.addStretch()
        mid.addWidget(prop); mid.addStretch()

        root.addLayout(mid, 1)

        # --- Export button (added) ---
        export_btn = QToolButton(text='💾', toolTip="Export as GIF/PNG", autoRaise=True)
        export_btn.setStyleSheet("color:white;font-size:16px")
        export_btn.clicked.connect(self.export_gif)
        bl.addWidget(export_btn)

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

    def export_gif(self):
        # Ask JS for all frames as PNG data URLs
        def process(frames_js):
            frames = frames_js if isinstance(frames_js, list) else []
            if not frames:
                QMessageBox.warning(self, "Export Error", "No frames exported.")
                return
            imgs = []
            for url in frames:
                b64_part = url.split(",", 1)[1] if "," in url else url
                img = Image.open(io.BytesIO(base64.b64decode(b64_part))).convert("RGB")
                imgs.append(img.resize((128, 128), Image.NEAREST))
            if not imgs:
                QMessageBox.warning(self, "Export Error", "No images to export.")
                return
            # Ask user for file path
            path, _ = QFileDialog.getSaveFileName(self, "Save GIF/PNG", "", "GIF Image (*.gif);;PNG Image (*.png)")
            if not path:
                return
            if path.lower().endswith('.gif') or (len(imgs) > 1 and not path.lower().endswith('.png')):
                imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=100, loop=0, optimize=False)
            else:
                imgs[0].save(path, format="PNG")
            QMessageBox.information(self, "Export", f"Saved: {path}")

        self.view.page().runJavaScript("EditorAPI.exportAllFrames();", process)

    @pyqtSlot(str)
    def selectionChanged(self, obj_type):
        print("selectionChanged called with:", obj_type)
        is_text = obj_type == 'text'
        self.font_label.setVisible(is_text)
        self.font_combo.setVisible(is_text)
        self.font_size_label.setVisible(is_text)
        self.font_spin.setVisible(is_text)

    @pyqtSlot()
    def highlightPlay(self):
        self.play_btn.setStyleSheet("color:white;font-size:16px;background:#2a8d2a;")

    @pyqtSlot()
    def unhighlightPlay(self):
        self.play_btn.setStyleSheet("color:white;font-size:16px;")

    @pyqtSlot(int, int)
    def updateFrameLabel(self, current, total):
        # Frame numbers are 1-based for display
        self.frame_lbl.setText(f"{current+1}/{total}")
