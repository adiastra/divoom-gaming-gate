import os, json, base64, io, requests
from PIL import Image
from PyQt5.QtCore import Qt, QUrl, pyqtSlot, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QInputDialog, QMessageBox, QColorDialog, QSpinBox, QDoubleSpinBox, QComboBox, QSizePolicy, QFileDialog, QGroupBox, QLineEdit, QTextEdit
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from ..utils.config import Config
import importlib.resources
import pixellab 
import random

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

        # Root layout for the group box
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
        tbtn1('🖼️', "Import image (gif, jpg, png...)", self._import_image, ref='import')
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

        # --- Stroke Width SpinBox (standalone QGroupBox) ---
        stroke_width_group = QGroupBox("Stroke Width", self)
        stroke_width_layout = QHBoxLayout(stroke_width_group)
        self.stroke_width_spin = QSpinBox(stroke_width_group)
        self.stroke_width_spin.setRange(1, 32)
        self.stroke_width_spin.setValue(2)
        self.stroke_width_spin.valueChanged.connect(self._set_stroke_width)
        stroke_width_layout.addWidget(QLabel("Width:", stroke_width_group))
        stroke_width_layout.addWidget(self.stroke_width_spin)
        prop_layout.addWidget(stroke_width_group)

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
        main_layout.setSpacing(12)
        main_layout.addWidget(editor_group, alignment=Qt.AlignLeft | Qt.AlignTop)

        # --- Pixellab AI Image Generator Group Box ---
        ai_group = QGroupBox("Pixellab AI Image Generator")
        ai_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setContentsMargins(8, 8, 8, 8)
        ai_layout.setSpacing(8)

        # Model (dropdown, at the top, default to pixflux)
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItems([
            "pixflux", "bitforge", "pixart", "stable-diffusion-xl", "stable-diffusion-v1-5", "stable-diffusion-2-1"
        ])
        self.ai_model_combo.setCurrentIndex(0)
        ai_layout.addWidget(QLabel("Model:", styleSheet="color:white;"))
        ai_layout.addWidget(self.ai_model_combo)

        # Prompt
        self.ai_prompt_label = QLabel("Prompt:", styleSheet="color:white;")
        ai_layout.addWidget(self.ai_prompt_label)
        self.ai_prompt_edit = QTextEdit()
        self.ai_prompt_edit.setPlaceholderText("Describe your image...")
        self.ai_prompt_edit.setStyleSheet("color:white;background:#333; font-size:13px;")
        self.ai_prompt_edit.setFixedHeight(60)
        ai_layout.addWidget(self.ai_prompt_edit)

        # Negative Prompt
        self.negative_prompt_widget = QWidget()
        neg_layout = QVBoxLayout(self.negative_prompt_widget)
        neg_layout.setContentsMargins(0, 0, 0, 0)
        neg_layout.addWidget(QLabel("Negative Prompt:", styleSheet="color:white;"))
        self.ai_negative_prompt_edit = QLineEdit()
        self.ai_negative_prompt_edit.setPlaceholderText("What should NOT appear (optional)")
        neg_layout.addWidget(self.ai_negative_prompt_edit)
        ai_layout.addWidget(self.negative_prompt_widget)

        # Style
        self.style_widget = QWidget()
        style_layout = QVBoxLayout(self.style_widget)
        style_layout.setContentsMargins(0, 0, 0, 0)
        self.ai_style_combo = QComboBox()
        self.ai_style_combo.addItems([
            "", "anime", "photographic", "digital-art", "comic-book", "fantasy-art", "line-art", "analog-film", "neon-punk"
        ])
        style_layout.addWidget(QLabel("Style:", styleSheet="color:white;"))
        style_layout.addWidget(self.ai_style_combo)
        ai_layout.addWidget(self.style_widget)

        # Scheduler
        self.scheduler_widget = QWidget()
        scheduler_layout = QVBoxLayout(self.scheduler_widget)
        scheduler_layout.setContentsMargins(0, 0, 0, 0)
        self.ai_scheduler_combo = QComboBox()
        self.ai_scheduler_combo.addItems([
            "", "DDIM", "DPMSolverMultistep", "Euler", "EulerAncestral", "Heun", "KDPM2Ancestral", "KDPM2", "LMS", "PNDM"
        ])
        scheduler_layout.addWidget(QLabel("Scheduler:", styleSheet="color:white;"))
        scheduler_layout.addWidget(self.ai_scheduler_combo)
        ai_layout.addWidget(self.scheduler_widget)

        # Seed (optional)
        self.seed_widget = QWidget()
        seed_layout = QHBoxLayout(self.seed_widget)
        seed_layout.setContentsMargins(0, 0, 0, 0)
        seed_layout.addWidget(QLabel("Seed:", styleSheet="color:white;"))
        self.ai_seed_spin = QSpinBox()
        self.ai_seed_spin.setRange(0, 2**31-1)
        self.ai_seed_spin.setValue(random.randint(0, 2**31-1))  # Randomize on load
        seed_layout.addWidget(self.ai_seed_spin)
        ai_layout.addWidget(self.seed_widget)

        # Status label
        self.ai_status_lbl = QLabel("", styleSheet="color:#8ecfff;")
        ai_layout.addWidget(self.ai_status_lbl)

        # Image preview
        self.ai_img_lbl = QLabel()
        self.ai_img_lbl.setFixedSize(128, 128)
        self.ai_img_lbl.setStyleSheet("background:#222; border:1px solid #444;")
        ai_layout.addWidget(self.ai_img_lbl, alignment=Qt.AlignHCenter)

        # Send to Canvas button
        self.ai_send_canvas_btn = QToolButton(text="Send to Canvas", autoRaise=True)
        self.ai_send_canvas_btn.setStyleSheet("color:white;font-size:14px")
        self.ai_send_canvas_btn.setEnabled(False)
        self.ai_send_canvas_btn.clicked.connect(self.send_ai_image_to_canvas)
        ai_layout.addWidget(self.ai_send_canvas_btn)

        # Generate Image button (at the bottom)
        self.ai_generate_btn = QToolButton(text="Generate Image", autoRaise=True)
        self.ai_generate_btn.setStyleSheet("color:white;font-size:14px")
        self.ai_generate_btn.clicked.connect(self.generate_ai_image)
        ai_layout.addWidget(self.ai_generate_btn)

        # Image Size (Width/Height)
        self.size_widget = QWidget()
        size_layout = QHBoxLayout(self.size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.addWidget(QLabel("Width:", styleSheet="color:white;"))
        self.ai_width_spin = QSpinBox()
        self.ai_width_spin.setRange(64, 1024)
        self.ai_width_spin.setValue(IMG_SIZE)
        size_layout.addWidget(self.ai_width_spin)
        size_layout.addWidget(QLabel("Height:", styleSheet="color:white;"))
        self.ai_height_spin = QSpinBox()
        self.ai_height_spin.setRange(64, 1024)
        self.ai_height_spin.setValue(IMG_SIZE)
        size_layout.addWidget(self.ai_height_spin)
        ai_layout.addWidget(self.size_widget)

        main_layout.addWidget(ai_group, alignment=Qt.AlignLeft | Qt.AlignTop)

        self.ai_model_combo.currentTextChanged.connect(self._update_ai_controls)
        self._update_ai_controls()  # Set initial visibility (now safe)

    def _update_label(self, label, value):
        label.setText(str(value))

    def _js(self, code):
        self.view.page().runJavaScript(code, self._update_frame_lbl)
    def _update_frame_lbl(self, txt):
        if isinstance(txt,str) and '/' in txt: self.frame_lbl.setText(txt)

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
        if getattr(self, 'current_tool', None) == 'draw':
            self._js(f"EditorAPI.setBrushWidth({w});")
        else:
            self._js(f"var o=canvas.getActiveObject();if(o){{o.set('strokeWidth',{w});canvas.renderAll();}}")
    def _set_font       (self,f ): self._js(f"var o=canvas.getActiveObject();if(o){{o.set('fontFamily','{f}');canvas.renderAll();}}")
    def _set_font_size  (self,s ): self._js(f"var o=canvas.getActiveObject();if(o){{o.set('fontSize',{s});canvas.renderAll();}}")

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
                        "PicOffset":idx,
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

        self.view.page().runJavaScript("EditorAPI.exportAllFramesSync();")
        QTimer.singleShot(200, lambda: self.view.page().runJavaScript("window.EXPORTED_FRAMES", process))

    def export_gif(self):
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
            path, _ = QFileDialog.getSaveFileName(self, "Save GIF/PNG", "", "GIF Image (*.gif);;PNG Image (*.png)")
            if not path:
                return
            if path.lower().endswith('.gif') or (len(imgs) > 1 and not path.lower().endswith('.png')):
                imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=100, loop=0, optimize=False)
            else:
                imgs[0].save(path, format="PNG")
            QMessageBox.information(self, "Export", f"Saved: {path}")

        # Use the same export logic as send-to-screen for reliability
        self.view.page().runJavaScript("EditorAPI.exportAllFramesSync();")
        QTimer.singleShot(200, lambda: self.view.page().runJavaScript("window.EXPORTED_FRAMES", process))

    @pyqtSlot(str)
    def selectionChanged(self, obj_type):
        # print("selectionChanged called with:", obj_type)
        is_text = obj_type == 'text'
        self.font_label.setVisible(is_text)
        self.font_combo.setVisible(is_text)
        self.font_size_label.setVisible(is_text)
        self.font_spin.setVisible(is_text)
        self._js("EditorAPI.getSelectedStrokeWidth();")

    @pyqtSlot()
    def highlightPlay(self):
        self.play_btn.setStyleSheet("color:white;font-size:16px;background:#2a8d2a;")

    @pyqtSlot()
    def unhighlightPlay(self):
        self.play_btn.setStyleSheet("color:white;font-size:16px;")

    @pyqtSlot(int, int)
    def updateFrameLabel(self, current, total):
        self.frame_lbl.setText(f"{current+1}/{total}")

    @pyqtSlot(int)
    def update_brush_width(self, val):
        self._js(f"EditorAPI.setBrushWidth({val});")

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        is_ctrl = modifiers & Qt.ControlModifier
        is_cmd = modifiers & Qt.MetaModifier

        if (is_ctrl or is_cmd) and event.key() == Qt.Key_Z:
            self._js("EditorAPI.undo();")
            event.accept()
            return
        if (is_ctrl or is_cmd) and event.key() == Qt.Key_Y:
            self._js("EditorAPI.redo();")
            event.accept()
            return
        if (is_ctrl or is_cmd) and event.key() == Qt.Key_G:
            if modifiers & Qt.ShiftModifier:
                self._js("EditorAPI.ungroup();")
            else:
                self._js("EditorAPI.group();")
            event.accept()
            return
        if (is_ctrl or is_cmd) and event.key() == Qt.Key_C:
            self._js("EditorAPI.copy();")
            event.accept()
            return
        if (is_ctrl or is_cmd) and event.key() == Qt.Key_V:
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
            self.set_tool('select')
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
        self.stroke_width_spin.blockSignals(True)
        self.stroke_width_spin.setValue(width)
        self.stroke_width_spin.blockSignals(False)

    @pyqtSlot()
    def generate_ai_image(self):
        model = self.ai_model_combo.currentText()
        prompt = self.ai_prompt_edit.toPlainText().strip()
        if not prompt:
            self._stop_ai_status("Please enter a prompt.")
            return

        self._start_ai_status("Sent, waiting for response")
        self.ai_generate_btn.setEnabled(False)
        self.ai_img_lbl.clear()
        self.ai_send_canvas_btn.setEnabled(False)

        api_key = ""
        try:
            from ..utils.paths import SETTINGS_FILE
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                api_key = settings.get("pixellab_api_key", "")
        except Exception:
            pass
        if not api_key:
            self._stop_ai_status("No Pixellab.ai API key set in Settings.")
            self.ai_generate_btn.setEnabled(True)
            return

        params = self._collect_pixellab_params(model)
        self._ai_worker = PixellabWorker(api_key, model, params)
        self._ai_worker.finished.connect(self._on_ai_image_generated)
        self._ai_worker.start()

    def send_ai_image_to_canvas(self):
        import base64
        if not hasattr(self, "_last_ai_image_bytes"):
            QMessageBox.warning(self, "No Image", "No AI image to send.")
            return
        b64 = base64.b64encode(self._last_ai_image_bytes).decode()
        self._js(f"EditorAPI.addImageFromDataURL('data:image/png;base64,{b64}');")
        
    def _import_image(self):
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if not file_path:
            return
        with open(file_path, "rb") as f:
            data = f.read()
        import base64, mimetypes
        mime, _ = mimetypes.guess_type(file_path)
        if not mime:
            mime = "image/png"
        b64 = base64.b64encode(data).decode()
        self._js(f"EditorAPI.addImageFromDataURL('data:{mime};base64,{b64}');")    
        
    def _start_ai_status(self, base_text):
        if not hasattr(self, "_ai_status_timer"):
            self._ai_status_timer = QTimer(self)
            self._ai_status_timer.timeout.connect(self._animate_ai_status)
        self._ai_status_base = base_text
        self._ai_status_dot_count = 0
        self.ai_status_lbl.setText(base_text)
        self._ai_status_timer.start(400)

    def _stop_ai_status(self, final_text):
        if hasattr(self, "_ai_status_timer"):
            self._ai_status_timer.stop()
        self.ai_status_lbl.setText(final_text)

    def _animate_ai_status(self):
        self._ai_status_dot_count = (self._ai_status_dot_count + 1) % 4
        dots = '.' * self._ai_status_dot_count
        self.ai_status_lbl.setText(self._ai_status_base + dots)

    def _on_ai_image_generated(self, img_bytes, error):
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        if error:
            self._stop_ai_status(f"Error: {error}")
            self.ai_generate_btn.setEnabled(True)
            return
        pix = QPixmap()
        pix.loadFromData(img_bytes)
        self.ai_img_lbl.setPixmap(pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._last_ai_image_bytes = img_bytes
        self._stop_ai_status("Image generated!")
        self.ai_send_canvas_btn.setEnabled(True)
        self.ai_generate_btn.setEnabled(True)

    def _collect_pixellab_params(self, model):
        prompt = self.ai_prompt_edit.toPlainText().strip()
        negative = self.ai_negative_prompt_edit.text().strip()
        width = self.ai_width_spin.value()
        height = self.ai_height_spin.value()
        seed = self.ai_seed_spin.value()
        scheduler = self.ai_scheduler_combo.currentText().strip()
        
        def clean(d):
            """Remove keys with empty string or None values."""
            return {k: v for k, v in d.items() if v not in ("", None)}

        if model == "pixflux":
            params = {
                "description": prompt,
                "negative_description": negative,
                "image_size": {"width": width, "height": height},
                "seed": seed,
            }
            params = clean(params)
            params["image_size"] = clean(params["image_size"])
            return params
        elif model == "bitforge":
            params = {
                "description": prompt,
                "negative_description": negative,
                "image_size": {"width": width, "height": height},
                "seed": seed,
            }
            params = clean(params)
            params["image_size"] = clean(params["image_size"])
            return params
        elif model == "pixart":
            params = {
                "description": prompt,
                "negative_description": negative,
                "image_size": {"width": width, "height": height},
                "seed": seed,
            }
            params = clean(params)
            params["image_size"] = clean(params["image_size"])
            return params
        elif model == "stable-diffusion-xl":
            params = {
                "prompt": prompt,
                "negative_prompt": negative,
                "width": width,
                "height": height,
                "seed": seed,
                "scheduler": scheduler,
            }
            return clean(params)
        elif model == "stable-diffusion-v1-5":
            params = {
                "prompt": prompt,
                "negative_prompt": negative,
                "width": width,
                "height": height,
                "seed": seed,
                "scheduler": scheduler,
            }
            return clean(params)
        elif model == "stable-diffusion-2-1":
            params = {
                "prompt": prompt,
                "negative_prompt": negative,
                "width": width,
                "height": height,
                "seed": seed,
                "scheduler": scheduler,
            }
            return clean(params)
        else:
            raise Exception("Unsupported model")

    def _update_ai_controls(self):
        model = self.ai_model_combo.currentText()
        # Update prompt/description label and negative label
        if model.startswith("stable-diffusion"):
            self.ai_prompt_label.setText("Prompt:")
            self.negative_prompt_widget.layout().itemAt(0).widget().setText("Negative Prompt:")
            self.scheduler_widget.setVisible(True)
        else:
            self.ai_prompt_label.setText("Description:")
            self.negative_prompt_widget.layout().itemAt(0).widget().setText("Negative Description:")
            self.scheduler_widget.setVisible(False)

        # Set allowed image size ranges
        if model in ("pixflux", "bitforge", "pixart"):
            self.ai_width_spin.setRange(32, 400)
            self.ai_height_spin.setRange(32, 400)
        else:
            self.ai_width_spin.setRange(64, 1024)
            self.ai_height_spin.setRange(64, 1024)

        # Reset to default size
        self.ai_width_spin.setValue(IMG_SIZE)
        self.ai_height_spin.setValue(IMG_SIZE)
        
class PixellabWorker(QThread):
    finished = pyqtSignal(object, object)  # (image_bytes, error)

    def __init__(self, api_key, model, params):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.params = params

    def run(self):
        import pixellab
        import base64
        try:
            client = pixellab.Client(secret=self.api_key)
            if self.model == "pixflux":
                result = client.generate_image_pixflux(**self.params)
            elif self.model == "bitforge":
                result = client.generate_image_bitforge(**self.params)
            elif self.model == "pixart":
                result = client.generate_image_pixart(**self.params)
            elif self.model == "stable-diffusion-xl":
                result = client.generate_image_sdxl(**self.params)
            elif self.model == "stable-diffusion-v1-5":
                result = client.generate_image_sd15(**self.params)
            elif self.model == "stable-diffusion-2-1":
                result = client.generate_image_sd21(**self.params)
            else:
                raise Exception("Unsupported model")
            img_bytes = base64.b64decode(result.image.base64)
            self.finished.emit(img_bytes, None)
        except Exception as e:
            self.finished.emit(None, str(e))