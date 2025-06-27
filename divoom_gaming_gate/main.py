# main.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QSplashScreen
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation
import importlib.resources
from .screens.screens_tab import ScreensTab
from .themes.themes_tab import ThemesTab
from .characters.characters_tab import CharactersTab
from .tools.tools_tab import ToolsTab
from .designer.designer_tab import DesignerTab
from .settings.settings_tab import SettingsTab
from importlib.metadata import version, PackageNotFoundError
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Divoom Gaming Gate")
        tabs = QTabWidget()
        tabs.addTab(ScreensTab(),    "Screens")
        tabs.addTab(ThemesTab(),     "Themes")
        tabs.addTab(CharactersTab(), "Characters")
        tabs.addTab(ToolsTab(), "Tools")
        settings_tab = SettingsTab()
        tabs.addTab(DesignerTab(),   "Designer")
        tabs.addTab(settings_tab, "Settings")  
        self.setCentralWidget(tabs)

def get_current_version():
    try:
        return version("divoom-gaming-gate")
    except PackageNotFoundError:
        return "unknown"

def show_splash(app):
    splash_path = os.path.join(os.path.dirname(__file__), "splash.png")
    splash_pix = QPixmap(splash_path)
    version_str = f"v - {get_current_version()}"
    painter = QPainter(splash_pix)
    painter.setPen(QColor("white"))
    font = QFont("Arial", 14)
    painter.setFont(font)
    margin = 16
    rect = splash_pix.rect().adjusted(margin, margin, -margin, -margin)
    painter.drawText(rect, Qt.AlignBottom | Qt.AlignRight, version_str)
    # Draw border (4px white)
    painter.setPen(QColor("white"))
    painter.setBrush(Qt.NoBrush)
    painter.setRenderHint(QPainter.Antialiasing)
    border_rect = splash_pix.rect().adjusted(2, 2, -2, -2)
    painter.drawRect(border_rect)
    painter.end()
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setWindowOpacity(0.0)  # <-- Add this line BEFORE show()
    splash.show()
    splash.raise_()
    splash.activateWindow()
    splash.repaint()
    app.processEvents()
    return splash

def fade_out_splash(splash, on_finished=None):
    anim = QPropertyAnimation(splash, b"windowOpacity")
    anim.setDuration(1000)  # 1 second fade
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    if on_finished:
        anim.finished.connect(on_finished)
    # Keep a reference so it doesn't get garbage collected
    splash._fade_anim = anim
    anim.start()

def fade_in_splash(splash, on_finished=None):
    splash.setWindowOpacity(0.0)
    anim = QPropertyAnimation(splash, b"windowOpacity")
    anim.setDuration(1000)  # 1 second fade in
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    if on_finished:
        anim.finished.connect(on_finished)
    splash._fade_in_anim = anim
    anim.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Gaming Gate")
    # Set window icon
    with importlib.resources.path("divoom_gaming_gate", "GamingGate.ico") as icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
    splash = show_splash(app)

    def start_main():
        global window
        window = MainWindow()
        window.resize(1000, 700)
        window.show()
        fade_out_splash(splash, lambda: splash.finish(window))

    def after_fade_in():
        QTimer.singleShot(3000, start_main)  # 3 seconds after fade-in

    fade_in_splash(splash, after_fade_in)
    sys.exit(app.exec_())
