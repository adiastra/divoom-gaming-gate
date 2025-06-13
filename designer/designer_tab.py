# designer/designer_tab.py

import os
import json
import requests
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QInputDialog, QMessageBox, QColorDialog, QSpinBox, QComboBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView

from utils.config import Config  # your config module

CANVAS_PIX = 128 * 4  # 4× zoom

class DesignerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #2b2b2b;")
        self._cfg = Config()

        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        # — Top toolbar —
        top = QWidget()
        top.setStyleSheet("background: #3c3c3c;")
        tlay = QHBoxLayout(top)
        tlay.setContentsMargins(4,4,4,4)
        tlay.setSpacing(8)
        def btn(ic, tip, cb):
            b = QToolButton()
            b.setText(ic)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.setStyleSheet("color:white; font-size:18px;")
            b.clicked.connect(cb)
            tlay.addWidget(b)
            return b

        btn('▭',   "Add rectangle",       lambda: self._js("EditorAPI.newRect();"))
        btn('T',   "Add text",            self._add_text)
        btn('🗑',   "Clear",              lambda: self._js("EditorAPI.clear();"))
        btn('💾',   "Export JPEG",        self._export)
        btn('📤',   "Send to screen",     self._send)
        tlay.addStretch()
        root.addWidget(top)

        # — Middle: canvas + properties —
        mid = QHBoxLayout()
        mid.setContentsMargins(0,0,0,0)
        mid.setSpacing(0)

        # Fabric canvas
        self.view = QWebEngineView()
        self.view.setFixedSize(CANVAS_PIX, CANVAS_PIX)
        self.view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.view.page().setBackgroundColor(QColor(0,0,0,0))
        html = os.path.join(os.path.dirname(__file__), "editor.html")
        self.view.load(QUrl.fromLocalFile(os.path.abspath(html)))
        mid.addWidget(self.view)

        # Properties panel
        prop = QWidget()
        prop.setFixedWidth(200)
        prop.setStyleSheet("background: #3c3c3c;")
        play = QVBoxLayout(prop)
        play.setContentsMargins(8,8,8,8)
        play.setSpacing(10)

        play.addWidget(QLabel("Object Properties", alignment=Qt.AlignCenter))

        # Fill
        fbtn = QToolButton(); fbtn.setText('⬤')
        fbtn.setStyleSheet("color:white; font-size:24px;")
        fbtn.setToolTip("Change fill"); fbtn.clicked.connect(self._change_fill)
        play.addWidget(fbtn)

        # Stroke
        sbtn = QToolButton(); sbtn.setText('◯')
        sbtn.setStyleSheet("color:white; font-size:24px;")
        sbtn.setToolTip("Change stroke"); sbtn.clicked.connect(self._change_stroke)
        play.addWidget(sbtn)

        # Stroke width
        wlay = QHBoxLayout()
        wlay.addWidget(QLabel("Width", styleSheet="color:white"))
        self.stroke_spin = QSpinBox(); self.stroke_spin.setRange(1,20)
        self.stroke_spin.valueChanged.connect(self._set_stroke_width)
        wlay.addWidget(self.stroke_spin)
        play.addLayout(wlay)

        # Font family
        play.addWidget(QLabel("Font", styleSheet="color:white"))
        self.font_combo = QComboBox()
        for f in ["Arial","Helvetica","Times New Roman","Courier New","Verdana"]:
            self.font_combo.addItem(f)
        self.font_combo.currentTextChanged.connect(self._set_font)
        play.addWidget(self.font_combo)

        # Font size
        flay = QHBoxLayout()
        flay.addWidget(QLabel("Size", styleSheet="color:white"))
        self.font_spin = QSpinBox(); self.font_spin.setRange(8,72)
        self.font_spin.valueChanged.connect(self._set_font_size)
        flay.addWidget(self.font_spin)
        play.addLayout(flay)

        play.addStretch()
        mid.addWidget(prop)
        mid.addStretch()
        root.addLayout(mid)

        # — Bottom: frame controls —
        bot = QWidget(); bot.setStyleSheet("background: #3c3c3c;")
        bl = QHBoxLayout(bot); bl.setContentsMargins(4,4,4,4); bl.setSpacing(8)
        def ib(ic, tip, cb):
            b = QToolButton(); b.setText(ic); b.setToolTip(tip); b.setAutoRaise(True)
            b.setStyleSheet("color:white; font-size:16px;"); b.clicked.connect(cb)
            bl.addWidget(b); return b

        ib('＋',"New frame",    lambda: self._js("EditorAPI.addFrame();"))
        ib('✎',"Clone frame",  lambda: self._js("EditorAPI.cloneFrame();"))
        self.prev = ib('←',"Prev frame", lambda: self._js("EditorAPI.prevFrame();"))
        self.frame_lbl = QLabel("1/1", styleSheet="color:white"); bl.addWidget(self.frame_lbl)
        self.next = ib('→',"Next frame", lambda: self._js("EditorAPI.nextFrame();"))
        bl.addStretch()
        ib('▶',"Play",         lambda: self._js("EditorAPI.playAnimation(500);"))
        ib('⏸',"Pause",        lambda: self._js("EditorAPI.stopAnimation();"))
        root.addWidget(bot)

    def _js(self, code):
        self.view.page().runJavaScript(code, self._update_frame_label)

    def _add_text(self):
        txt,ok = QInputDialog.getText(self,"Text","Enter:")
        if ok and txt:
            self._js(f"EditorAPI.newText({json.dumps(txt)});")

    def _export(self):
        def cb(data):
            payload = data.split(",",1)[1]
            QMessageBox.information(self,"Export",f"{len(payload)} bytes")
        self.view.page().runJavaScript("EditorAPI.exportFrame();", cb)

    def _send(self):
        """Export the current frame and POST it to the Times Gate."""
        ip = self._cfg.get("device_ip")
        if not ip:
            QMessageBox.warning(self, "No IP",
                "Please configure 'device_ip' in preferences first.")
            return

        def cb(data):
            payload = data.split(",",1)[1]
            # Build the Times Gate JSON command for a static image
            cmd = {
                "Command": "Draw/SendHttpPic",
                "LcdArray": [1,1,1,1,1],
                "PicID": 1,
                "PicData": payload
            }
            try:
                url = f"http://{ip}/postJson"
                resp = requests.post(url, json=cmd, timeout=5)
                resp.raise_for_status()
                QMessageBox.information(self, "Sent",
                    f"Image sent OK (HTTP {resp.status_code}).")
            except Exception as e:
                QMessageBox.critical(self, "Error",
                    f"Failed to send image:\n{e}")

        # run JS and then send
        self.view.page().runJavaScript("EditorAPI.exportFrame();", cb)

    def _change_fill(self):
        col = QColorDialog.getColor(QColor('white'), self, "Fill Color")
        if col.isValid():
            js = (
              "(function(){"
              "var o=canvas.getActiveObject();"
              f"if(o) o.set('fill','{col.name()}');"
              "canvas.requestRenderAll();"
              "})()"
            )
            self._js(js)

    def _change_stroke(self):
        col = QColorDialog.getColor(QColor('white'), self, "Stroke Color")
        if col.isValid():
            js = (
              "(function(){"
              "var o=canvas.getActiveObject();"
              f"if(o) o.set('stroke','{col.name()}');"
              "canvas.requestRenderAll();"
              "})()"
            )
            self._js(js)

    def _set_stroke_width(self, w):
        js = (
          "(function(){"
          "var o=canvas.getActiveObject();"
          f"if(o) o.set('strokeWidth',{w});"
          "canvas.requestRenderAll();"
          "})()"
        )
        self._js(js)

    def _set_font(self, fam):
        js = (
          "(function(){"
          "var o=canvas.getActiveObject();"
          f"if(o) o.set('fontFamily','{fam}');"
          "canvas.requestRenderAll();"
          "})()"
        )
        self._js(js)

    def _set_font_size(self, sz):
        js = (
          "(function(){"
          "var o=canvas.getActiveObject();"
          f"if(o) o.set('fontSize',{sz});"
          "canvas.requestRenderAll();"
          "})()"
        )
        self._js(js)

    def _update_frame_label(self, info):
        if isinstance(info, str) and '/' in info:
            self.frame_lbl.setText(info)
