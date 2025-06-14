# main.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from screens.screens_tab import ScreensTab
from characters.characters_tab import CharactersTab
from designer.designer_tab import DesignerTab
from settings.settings_tab import SettingsTab  # new line

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Divoom Gaming Gate")
        tabs = QTabWidget()
        tabs.addTab(ScreensTab(),    "Screens")
        tabs.addTab(CharactersTab(), "Characters")
        tabs.addTab(DesignerTab(),   "Designer")
        tabs.addTab(SettingsTab(),   "Settings")  # new line
        self.setCentralWidget(tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    sys.exit(app.exec_())
