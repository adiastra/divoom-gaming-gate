from ..utils.config import Config
import time, io, base64, json as json_lib, requests
from PIL import Image, ImageSequence
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QSlider, QComboBox, QDialog, QLineEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QTimer, QSize
from io import BytesIO
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot, QObject
from ..utils.device_api import post_device_command
from ..utils.klipy import get_klipy_settings, klipy_search_gifs
DEVICE_IP = Config.get_device_ip()

from ..utils.constants import SCREEN_COUNT, IMG_SIZE, DEFAULT_SPEED, DEFAULT_QUALITY
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
        self.gif_browser_btn = QPushButton("Klipy")

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
        """Send the current frame set to this screen slot on the device."""
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
                post_device_command(payload, ip=DEVICE_IP, timeout=8)
            except Exception as e:
                QMessageBox.warning(self, "Network Error", f"Failed to send to device:\n{e}")
                break

    def open_gif_browser(self):
        """Open KLIPY GIF search; selected GIF loads into this screen."""
        api_key, rating = get_klipy_settings()
        if not api_key:
            msg = QMessageBox(self)
            msg.setWindowTitle("KLIPY API Key Required")
            msg.setText("Go to the Settings tab and add your KLIPY API key.")
            msg.addButton("OK", QMessageBox.AcceptRole)
            get_btn = msg.addButton("Get API Key", QMessageBox.ActionRole)
            msg.exec_()
            if msg.clickedButton() == get_btn:
                import webbrowser
                webbrowser.open("https://partner.klipy.com/api-keys")
            return

        dlg = KlipyGifBrowserDialog(self, api_key=api_key, rating=rating)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_url:
            self.load_gif_from_url(dlg.selected_url)

    def load_gif_from_url(self, url):
        """Download a GIF (or image) URL and replace the current screen frames."""
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content))
            if getattr(img, "is_animated", False):
                self.raw_frames = [fr.convert("RGB") for fr in ImageSequence.Iterator(img)]
            else:
                self.raw_frames = [img.convert("RGB")]
            self.label.setText(f"Loaded {len(self.raw_frames)} frame(s) from Klipy")
            self.apply_mode()
            self._start_animation()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load GIF from Klipy:\n{e}")

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
    """Qt WebChannel bridge so the embedded results page can call back into Python."""

    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog

    @pyqtSlot(str)
    def gifSelected(self, url):
        """Called from JS when the user clicks a GIF thumbnail."""
        self.dialog.selected_url = url
        self.dialog.accept()

    @pyqtSlot()
    def loadMore(self):
        """Called from JS when the user scrolls near the bottom (infinite scroll)."""
        self.dialog.load_more_images()

class KlipyGifBrowserDialog(QDialog):
    """Modal browser that searches KLIPY and returns one selected GIF URL."""

    def __init__(self, parent=None, api_key=None, rating="pg"):
        super().__init__(parent)
        self.api_key = api_key or ""
        self.rating = rating or "pg"
        self.setWindowTitle("Klipy GIF Browser")
        self.setMinimumSize(500, 500)
        self.selected_url = None
        self._next_page = None
        self._klipy_append_busy = False

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search Klipy…")
        self.search_edit.returnPressed.connect(lambda: self.do_search())
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(lambda: self.do_search())
        search_row.addWidget(self.search_edit)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        self.results = QWebEngineView()
        # setHtml() loads from an opaque local origin; allow remote GIF thumbnails.
        rs = self.results.settings()
        rs.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        rs.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
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
        self.search_timer.timeout.connect(lambda: self.do_search())
        self.search_edit.textChanged.connect(self._on_search_text_changed)

    def _on_search_text_changed(self, text):
        self._next_page = None
        self.search_timer.start(400)

    def do_search(self, page=None, append=False):
        """Run a KLIPY search; append=True loads the next results page into the table."""
        q = self.search_edit.text().strip()
        if not q:
            return
        if not append:
            page = page or 1
            self._next_page = None
        else:
            page = page or self._next_page
            if not page:
                return
            self._klipy_append_busy = True
        try:
            gif_urls, next_page = klipy_search_gifs(
                self.api_key, q, page=page, rating=self.rating, per_page=20
            )
            rows = []
            row = ""
            for i, gif_url in enumerate(gif_urls):
                safe = json_lib.dumps(gif_url)
                row += (
                    f"<td><img src={safe} width=\"100\" height=\"100\" "
                    f"onclick='selectGif({safe})'></td>"
                )
                if (i + 1) % 4 == 0:
                    rows.append(f"<tr>{row}</tr>")
                    row = ""
            if row:
                rows.append(f"<tr>{row}</tr>")
            rows_html = "".join(rows)

            more_results = next_page is not None
            self._next_page = next_page

            if append:
                # Embed HTML as a JS string literal (json.dumps output), not JSON.parse(dumps(...)):
                # JSON.parse("<tr>...") fails because the parser sees raw '<' at position 0.
                rows_js_literal = json_lib.dumps(rows_html)
                js = f"""
                var tbl = document.querySelector('table');
                if (tbl) {{
                  var html = {rows_js_literal};
                  tbl.insertAdjacentHTML('beforeend', html);
                }}
                window._klipyHasMore = {str(more_results).lower()};
                window._klipyMoreLoading = false;
                """
                self.results.page().runJavaScript(js)
            else:
                empty_note = (
                    "<tr><td colspan=\"4\" style=\"color:#aaa;padding:12px;\">No GIFs found. "
                    "Try another search.</td></tr>"
                    if not rows_html.strip()
                    else ""
                )
                html = f"""
                <html>
                  <head>
                    <meta charset="utf-8">
                    <style>
                      body {{ background: #232323; margin: 0; pointer-events: none; }}
                      td {{ padding: 6px; }}
                    </style>
                    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
                  </head>
                  <body>
                    <table>
                      {rows_html if rows_html.strip() else empty_note}
                    </table>
                    <script>
                      var pyBridge = null;
                      var _klipyHasMore = {str(more_results).lower()};
                      window._klipyMoreLoading = false;
                      function selectGif(url) {{
                        if (pyBridge) pyBridge.gifSelected(url);
                      }}
                      window.onscroll = function() {{
                        if (!_klipyHasMore || window._klipyMoreLoading) return;
                        if (!pyBridge || !pyBridge.loadMore) return;
                        var nearBottom = (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 120;
                        if (!nearBottom) return;
                        window._klipyMoreLoading = true;
                        pyBridge.loadMore();
                      }};
                      new QWebChannel(qt.webChannelTransport, function(channel) {{
                        pyBridge = channel.objects.pyBridge;
                        document.body.style.pointerEvents = 'auto';
                      }});
                    </script>
                  </body>
                </html>
                """
                self.results.setHtml(html)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to search Klipy:\n{e}")
        finally:
            if append:
                self._klipy_append_busy = False
                self.results.page().runJavaScript("window._klipyMoreLoading = false;")

    def use_selected(self):
        """Accept the dialog if a thumbnail was already chosen via ``gifSelected``."""
        if self.selected_url:
            self.accept()
        else:
            QMessageBox.information(self, "Select GIF", "Click a GIF thumbnail to select it.")

    def load_more_images(self):
        """Infinite-scroll hook: request the next KLIPY page."""
        if self._klipy_append_busy or not self._next_page:
            return
        self.do_search(page=self._next_page, append=True)
