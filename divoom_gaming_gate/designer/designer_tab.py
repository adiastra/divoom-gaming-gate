import os, json, base64, io, requests
from PIL import Image
from PyQt5.QtCore import Qt, QUrl, pyqtSlot
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,

    QInputDialog, QMessageBox, QColorDialog, QSpinBox, QComboBox, QSizePolicy, QFileDialog, QSlider, QGroupBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from ..utils.config import Config
import importlib.resources

# constants that match the rest of your code-base
IMG_SIZE      = 128
SCREEN_COUNT  = 5
CANVAS_PIX    = IMG_SIZE * 4  # 4× zoomed canvas

class DesignerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")
        self.cfg = Config()

        # Create the group box and its layout
        editor_group = QGroupBox("")
        editor_group.setStyleSheet(
            """
            QGroupBox {
                color: #444;
                font-size: 12px;
                border: 1px inset #444;
                border-radius: 8px;
                margin-top: 8px;
                background: #232323;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            """
        )
        group_layout = QVBoxLayout(editor_group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)

        # Your original root layout (now for the group box)
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ─── Top toolbar (two rows) ────────────────────────────────────────────────
        top = QWidget(); top.setStyleSheet("background:#3c3c3c")
        top_lay = QVBoxLayout(top); top_lay.setContentsMargins(4,4,4,4); top_lay.setSpacing(2)

        # First row: tools
        row1 = QHBoxLayout(); row1.setSpacing(8)
        def tbtn1(txt_or_icon, tip, cb, ref=None):
            b = QToolButton(toolTip=tip, autoRaise=True)
            if isinstance(txt_or_icon, QIcon):
                b.setIcon(txt_or_icon)
            else:
                b.setText(txt_or_icon)
            b.setStyleSheet("color:white;font-size:18px")
            b.clicked.connect(cb)
            row1.addWidget(b)
            if ref:
                self.tool_buttons[ref] = b
            return b

        self.tool_buttons = {}  # Store references to tool buttons

        tbtn1('↖', "Select/move objects", lambda: self.set_tool('select'), ref='select')
        tbtn1('▭', "Add rectangle", lambda: self.set_tool('rect'), ref='rect')
        tbtn1('◯', "Add circle", lambda: self.set_tool('circle'), ref='circle')
        tbtn1('⬟', "Add polygon", lambda: self.set_tool('polygon'), ref='polygon')
        tbtn1('／', "Add line", lambda: self.set_tool('line'), ref='line')
        tbtn1('T', "Add text", lambda: self.set_tool('text'), ref='text')
        tbtn1('🖌️', "Freehand draw", lambda: self.set_tool('draw'), ref='draw')
        row1.addStretch()

        # Second row: actions
        row2 = QHBoxLayout(); row2.setSpacing(8)
        def tbtn2(txt_or_icon, tip, cb, ref=None):
            b = QToolButton(toolTip=tip, autoRaise=True)
            if isinstance(txt_or_icon, QIcon):
                b.setIcon(txt_or_icon)
            else:
                b.setText(txt_or_icon)
            b.setStyleSheet("color:white;font-size:18px")
            b.clicked.connect(cb)
            row2.addWidget(b)
            if ref:
                self.tool_buttons[ref] = b
            return b

        tbtn2('☒', "Delete selected object", lambda: self._js("EditorAPI.deleteObject();"))
        tbtn2('↶', "Undo (Ctrl+Z)", lambda: self._js("EditorAPI.undo();"))
        tbtn2('↷', "Redo (Ctrl+Y)", lambda: self._js("EditorAPI.redo();"))
        tbtn2('⚭', "Group (Ctrl+G)", lambda: self._js("EditorAPI.group();"))
        tbtn2('⚮', "Ungroup (Ctrl+Shift+G)", lambda: self._js("EditorAPI.ungroup();"))
        tbtn2('⧉', "Copy (Ctrl+C)", lambda: self._js("EditorAPI.copy();"))
        tbtn2('☑', "Paste (Ctrl+V)", lambda: self._js("EditorAPI.paste();"))
        row2.addStretch()

        top_lay.addLayout(row1)
        top_lay.addLayout(row2)
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
        with importlib.resources.path("divoom_gaming_gate.designer", "editor.html") as html_path:
            self.view.load(QUrl.fromLocalFile(str(html_path)))
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
        prop = QWidget()
        prop.setFixedWidth(220)
        prop.setStyleSheet("background:#3c3c3c")
        prop_layout = QVBoxLayout(prop)
        prop_layout.setContentsMargins(8, 8, 8, 8)
        prop_layout.setSpacing(10)

        # --- Object Properties Group Box ---
        obj_group = QGroupBox("Object Properties")
        obj_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        obj_layout = QVBoxLayout(obj_group)
        obj_layout.setContentsMargins(8, 8, 8, 8)
        obj_layout.setSpacing(8)

        fbtn = QToolButton(text='Fill Color', toolTip="Fill", autoRaise=True)
        fbtn.setStyleSheet("color:white;font-size:12px")
        fbtn.clicked.connect(self._change_fill)
        obj_layout.addWidget(fbtn)

        sbtn = QToolButton(text='Stroke Color', toolTip="Stroke", autoRaise=True)
        sbtn.setStyleSheet("color:white;font-size:12px")
        sbtn.clicked.connect(self._change_stroke)
        obj_layout.addWidget(sbtn)

        wlay = QHBoxLayout()
        wlay.addWidget(QLabel("Width", styleSheet="color:white"))
        self.stroke_slider = QSlider(Qt.Horizontal)
        self.stroke_slider.setRange(1, 32)
        self.stroke_slider.setValue(2)
        self.stroke_slider.setFixedWidth(100)
        self.stroke_slider.setToolTip("Stroke width")
        self.stroke_slider.valueChanged.connect(self._set_stroke_width)
        self.stroke_width_label = QLabel("2", styleSheet="color:white")
        self.stroke_slider.valueChanged.connect(
            lambda v: self.stroke_width_label.setText(str(v))
        )
        wlay.addWidget(self.stroke_slider)
        wlay.addWidget(self.stroke_width_label)
        obj_layout.addLayout(wlay)

        self.font_label = QLabel("Font", styleSheet="color:white")
        obj_layout.addWidget(self.font_label)
        self.font_combo = QComboBox()
        for fam in ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"]:
            self.font_combo.addItem(fam)
        self.font_combo.currentTextChanged.connect(self._set_font)
        obj_layout.addWidget(self.font_combo)

        self.font_size_lay = QHBoxLayout()
        self.font_size_label = QLabel("Font Size", styleSheet="color:white")
        self.font_size_lay.addWidget(self.font_size_label)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 72)
        self.font_spin.valueChanged.connect(self._set_font_size)
        self.font_size_lay.addWidget(self.font_spin)
        obj_layout.addLayout(self.font_size_lay)

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
        obj_layout.addLayout(polysides_lay)

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
        obj_layout.addLayout(zlay)

        prop_layout.addWidget(obj_group)

        # --- Send to Screen Group Box ---
        send_group = QGroupBox("Send to Screens")
        send_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        send_layout = QVBoxLayout(send_group)
        send_layout.setContentsMargins(8, 8, 8, 8)
        send_layout.setSpacing(8)

        # Screens label above buttons
        screens_label = QLabel("Select Screens", styleSheet="color:white")
        send_layout.addWidget(screens_label, alignment=Qt.AlignLeft)

        # Screen selection buttons in a row
        screen_btn_lay = QHBoxLayout()
        self.screen_checks = []
        for i in range(SCREEN_COUNT):
            cb = QToolButton(text=str(i+1), checkable=True, autoRaise=True)
            cb.setChecked(True)  # Default: all screens selected
            cb.setStyleSheet("color:white;font-size:14px")
            screen_btn_lay.addWidget(cb)
            self.screen_checks.append(cb)
        send_layout.addLayout(screen_btn_lay)

        # Select All / Select None buttons
        select_lay = QHBoxLayout()
        select_all_btn = QToolButton(text="Select All", autoRaise=True)
        select_all_btn.setStyleSheet("color:white;font-size:12px")
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self.screen_checks])
        select_lay.addWidget(select_all_btn)

        select_none_btn = QToolButton(text="Select None", autoRaise=True)
        select_none_btn.setStyleSheet("color:white;font-size:12px")
        select_none_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in self.screen_checks])
        select_lay.addWidget(select_none_btn)

        send_layout.addLayout(select_lay)

        # Send to screen button
        send_btn = QToolButton(text='Send 📤', toolTip="Send to screen", autoRaise=True)
        send_btn.setStyleSheet("color:white;font-size:18px")
        send_btn.clicked.connect(self._send)
        send_layout.addWidget(send_btn, alignment=Qt.AlignRight)

        prop_layout.addWidget(send_group)
        prop_layout.addStretch()

        mid.addWidget(prop)
        mid.addStretch()

        root.addLayout(mid, 1)

        # --- Export button (added) ---
        export_btn = QToolButton(text='💾', toolTip="Export as GIF/PNG", autoRaise=True)
        export_btn.setStyleSheet("color:white;font-size:16px")
        export_btn.clicked.connect(self.export_gif)
        bl.addWidget(export_btn)
        
        self.setFocusPolicy(Qt.StrongFocus)

        # At the end, add the root layout to the group box
        group_layout.addLayout(root)

        # Now set the main layout of the widget to contain only the group box
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)  # Add some space between group boxes if needed
        main_layout.addWidget(editor_group, alignment=Qt.AlignLeft | Qt.AlignTop)
        # You can add a second group box here later:
        # main_layout.addWidget(other_group_box, alignment=Qt.AlignLeft | Qt.AlignTop)

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
    def _set_stroke_width(self, w):
        # Called when the slider is changed
        if getattr(self, 'current_tool', None) == 'draw':
            self._js(f"EditorAPI.setBrushWidth({w});")
        else:
            self._js(f"var o=canvas.getActiveObject();if(o){{o.set('strokeWidth',{w});canvas.renderAll();}}")
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
                        "LcdArray": [int(cb.isChecked()) for cb in self.screen_checks],
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
        # Get stroke width from JS
        self._js("EditorAPI.getSelectedStrokeWidth();")

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

    @pyqtSlot(int)
    def update_brush_width(self, val):
        self._js(f"EditorAPI.setBrushWidth({val});")

    def keyPressEvent(self, event):
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_Z:
            self._js("EditorAPI.undo();")
            event.accept()
            return
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_Y:
            self._js("EditorAPI.redo();")
            event.accept()
            return
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_G:
            if event.modifiers() & Qt.ShiftModifier:
                self._js("EditorAPI.ungroup();")
            else:
                self._js("EditorAPI.group();")
            event.accept()
            return
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_C:
            self._js("EditorAPI.copy();")
            event.accept()
            return
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_V:
            self._js("EditorAPI.paste();")
            event.accept()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self._js("""
                if (canvas.getActiveObject() && !(canvas.getActiveObject().isEditing)) {
                    EditorAPI.deleteObject();
                }
            """)
            event.accept()
        else:
            super().keyPressEvent(event)

    @pyqtSlot(str)
    def set_tool(self, tool):
        # Only highlight select and draw tools
        for key, btn in self.tool_buttons.items():
            if key in ('select', 'draw') and tool == key:
                btn.setStyleSheet(

                    "color:white;font-size:18px;"
                    "background:#6cf;"
                    "border:2px solid #39f;"
                    "border-radius:6px;"
                )
                btn.setAutoRaise(False)
            else:
                btn.setStyleSheet("color:white;font-size:18px;background:;border:;")
                btn.setAutoRaise(True)

        self.current_tool = tool
        if tool == 'select':
            self._js("EditorAPI.setSelectMode();")
        elif tool == 'draw':
            self._js("EditorAPI.toggleDrawMode(true);")
            self._js("if (pyObj && pyObj.setStrokeWidth) pyObj.setStrokeWidth(canvas.freeDrawingBrush.width);")
        elif tool == 'rect':
            self._js("EditorAPI.newRect();")
            self.set_tool('select')  # <-- Highlight select after action
        elif tool == 'circle':
            self._js("EditorAPI.newCircle();")
            self.set_tool('select')
        elif tool == 'polygon':
            self._js(f"EditorAPI.newPolygon({self.poly_sides_spin.value()});")
            self.set_tool('select')
        elif tool == 'line':
            self._js("EditorAPI.newLine();")
            self.set_tool('select')
        elif tool == 'text':
            self._add_text()
            self.set_tool('select')

    @pyqtSlot(int)
    def setStrokeWidth(self, width):
        self.stroke_slider.blockSignals(True)
        self.stroke_slider.setValue(width)
        self.stroke_width_label.setText(str(width))  # <-- Add this line
        self.stroke_slider.blockSignals(False)


