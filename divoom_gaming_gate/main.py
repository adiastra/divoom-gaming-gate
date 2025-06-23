# main.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtGui import QIcon
import importlib.resources
from .screens.screens_tab import ScreensTab
from .themes.themes_tab import ThemesTab
from .characters.characters_tab import CharactersTab
from .tools.tools_tab import ToolsTab
from .designer.designer_tab import DesignerTab
from .settings.settings_tab import SettingsTab

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

def main():
    divoom_gaming_gate = QApplication(sys.argv)
    divoom_gaming_gate.setApplicationName("Gaming Gate")         
    # Use importlib.resources to get the icon path
    with importlib.resources.path("divoom_gaming_gate", "GamingGate.ico") as icon_path:
        divoom_gaming_gate.setWindowIcon(QIcon(str(icon_path)))
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    sys.exit(divoom_gaming_gate.exec_())

if __name__ == "__main__":
    main()
