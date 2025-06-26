from ..utils.config import Config
import time, io, base64, requests
from PIL import Image, ImageSequence
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QSlider, QComboBox, QDialog, QLineEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QTimer, QSize
from io import BytesIO
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot, QObject
import os
import json
from ..utils.paths import SETTINGS_FILE

# IP from config
from ..utils.config import Config
DEVICE_IP = Config.get_device_ip()

SCREEN_COUNT    = 5
IMG_SIZE        = 128
DEFAULT_SPEED   = 100
DEFAULT_QUALITY = 85
MAX_SKIP        = 10

def get_tenor_api_key():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        return settings.get("tenor_api_key", "").strip()
    return ""

def get_tenor_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        return (
            settings.get("tenor_api_key", "").strip(),
            settings.get("tenor_filter", "medium")
        )
    return "", "medium"

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
        self.gif_browser_btn = QPushButton("Tenor")

        self.load_btn.setStyleSheet("QPushButton:hover { background: #222; }")
        self.send_btn.setStyleSheet("QPushButton:hover { background: #222; }")
        self.gif_browser_btn.setStyleSheet("QPushButton:hover { background: #222; }")

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
        brow.addWidget(self.load_btn)
        brow.addWidget(self.gif_browser_btn)
        brow.addWidget(self.send_btn)
        main.addLayout(brow)

        main.addLayout(self._labeled_row("Frame Speed:", self.speed_box))
        main.addLayout(self._labeled_row("Frame Skip:",  self.skip_box))
        main.addLayout(self._labeled_row("Image Quality:", self.quality_slider))

        self.setLayout(main)

        # Signals
        self.load_btn.clicked.connect(self.load_image)
        self.send_btn.clicked.connect(self.send_to_screen)
        self.gif_browser_btn.clicked.connect(self.open_gif_browser)

        # Search state
        self.current_query = ""
        self.current_pos = None
        self.prev_stack = []

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
        DEVICE_IP = Config.get_device_ip()

        if not self.frames:
            return

        if not DEVICE_IP or DEVICE_IP.strip() == "":
            QMessageBox.warning(self, "No IP Set", "Please set the Divoom device IP in the settings before sending.")
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
            try:
                requests.post(f"http://{DEVICE_IP}/post", json=payload)
            except Exception as e:
                QMessageBox.warning(self, "Network Error", f"Failed to send to device:\n{e}")
                break

    def open_gif_browser(self):
        api_key, tenor_filter = get_tenor_settings()
        if not api_key:
            msg = QMessageBox(self)
            msg.setWindowTitle("Tenor API Key Required")
            msg.setText("Go to the Settings tab to add your Tenor API Key.")
            ok_btn = msg.addButton("OK", QMessageBox.AcceptRole)
            get_btn = msg.addButton("Get API Key", QMessageBox.ActionRole)
            msg.exec_()
            if msg.clickedButton() == get_btn:
                import webbrowser
                webbrowser.open("https://developers.google.com/tenor/guides/quickstart")
            return

        dlg = GifBrowserDialog(self, api_key=api_key, tenor_filter=tenor_filter)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_url:
            self.load_gif_from_url(dlg.selected_url)

    def load_gif_from_url(self, url):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content))
            if getattr(img, "is_animated", False):
                self.raw_frames = [fr.convert("RGB") for fr in ImageSequence.Iterator(img)]
            else:
                self.raw_frames = [img.convert("RGB")]
            self.label.setText(f"Loaded {len(self.raw_frames)} frame(s) from Tenor")
            self.apply_mode()
            self._start_animation()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load GIF from Tenor:\n{e}")

    def clear_image(self):
        self.raw_frames = []
        self.frames = []
        self.preview_idx = 0
        self.label.setText("No image loaded")
        self.preview.clear()  # <-- This line clears the preview area

    def load_from_theme_data(self, screen_data):
        import base64, io
        from PIL import Image, ImageSequence
        img_type = screen_data["type"]
        img_data = base64.b64decode(screen_data["data"])
        if img_type == "gif":
            img = Image.open(io.BytesIO(img_data))
            self.raw_frames = [fr.convert("RGB") for fr in ImageSequence.Iterator(img)]
        else:
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            self.raw_frames = [img]
        self.apply_mode()
        self._start_animation()

from PyQt5.QtCore import QObject, pyqtSlot

class GifBridge(QObject):
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog

    @pyqtSlot(str)
    def gifSelected(self, url):
        self.dialog.selected_url = url
        self.dialog.accept()

    @pyqtSlot()
    def loadMore(self):
        self.dialog.load_more_images()

class GifBrowserDialog(QDialog):
    def __init__(self, parent=None, api_key=None, tenor_filter="medium"):
        super().__init__(parent)
        self.api_key = api_key or ""
        self.tenor_filter = tenor_filter
        self.setWindowTitle("Tenor GIF Browser")
        self.setMinimumSize(500, 500)
        self.selected_url = None

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search Tenor...")
        self.search_edit.returnPressed.connect(self.do_search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.do_search)
        search_row.addWidget(self.search_edit)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        self.results = QWebEngineView()
        layout.addWidget(self.results)

        # Remove navigation buttons for infinite scroll

        # Set initial dark background
        initial_html = """
        <html>
          <head>
            <style>
              body { background: #232323; }
            </style>
          </head>
          <body></body>
        </html>
        """
        self.results.setHtml(initial_html)

        use_btn = QPushButton("Use Selected GIF")
        use_btn.clicked.connect(self.use_selected)
        layout.addWidget(use_btn)

        self.channel = QWebChannel()
        self.bridge = GifBridge(self)
        self.channel.registerObject('pyBridge', self.bridge)
        self.results.page().setWebChannel(self.channel)

        # Live search timer setup (correct place)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.do_search)
        self.search_edit.textChanged.connect(self._on_search_text_changed)

        # Paging state
        self.current_query = ""
        self.current_pos = None
        self.prev_stack = []

    def _on_search_text_changed(self, text):
        self.prev_stack = []
        self.current_pos = None
        self.search_timer.start(400)

    def do_search(self, pos=None, append=False):
        api_key = self.api_key
        tenor_filter = self.tenor_filter
        q = self.search_edit.text().strip()
        if not q:
            return
        url = f"https://tenor.googleapis.com/v2/search?q={q}&key={api_key}&limit=20&media_filter=gif&contentfilter={tenor_filter}"
        if pos:
            url += f"&pos={pos}"
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            # Build <tr>...</tr> rows for every 4 GIFs
            rows = []
            row = ""
            for i, result in enumerate(data["results"]):
                gif_url = result["media_formats"]["gif"]["url"]
                row += f'<td><img src="{gif_url}" width="100" height="100" onclick="selectGif(\'{gif_url}\')"></td>'
                if (i+1) % 4 == 0:
                    rows.append(f"<tr>{row}</tr>")
                    row = ""
            if row:  # Any remaining GIFs
                rows.append(f"<tr>{row}</tr>")
            rows_html = "".join(rows)

            # Track if more results are available
            more_results = data.get("next", None) is not None

            if append:
                js = f"""
                var tbl = document.querySelector('table');
                var html = `{rows_html}`;
                tbl.insertAdjacentHTML('beforeend', html);
                window._tenorHasMore = {str(more_results).lower()};
                """
                self.results.page().runJavaScript(js)
            else:
                html = f"""
                <html>
                  <head>
                    <style>
                      body {{ background: #232323; }}
                      td {{ padding: 6px; }}
                    </style>
                    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
                    <script>
                      var pyBridge = null;
                      var _tenorHasMore = {str(more_results).lower()};
                      new QWebChannel(qt.webChannelTransport, function(channel) {{
                        pyBridge = channel.objects.pyBridge;
                      }});

                      function selectGif(url) {{
                        if (pyBridge) pyBridge.gifSelected(url);
                      }}

                      window.onscroll = function() {{
                        if (_tenorHasMore && (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 2) {{
                          // Reached bottom
                          if (pyBridge && pyBridge.loadMore) pyBridge.loadMore();
                        }}
                      }};
                    </script>
                  </head>
                  <body>
                    <table>
                      {rows_html}
                    </table>
                  </body>
                </html>
                """
                self.results.setHtml(html)

            # --- Fix: Always track previous positions, including first page ---
            if not self.prev_stack or self.prev_stack[-1] != pos:
                self.prev_stack.append(pos)
            self.current_query = q
            self.current_pos = data.get("next", None)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to search Tenor:\n{e}")

    def use_selected(self):
        pass

    def load_more_images(self):
        if self.current_pos:
            self.do_search(self.current_pos, append=True)
