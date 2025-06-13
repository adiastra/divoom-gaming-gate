# main.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from screens.screens_tab import ScreensTab
from characters.characters_tab import CharactersTab
from designer.designer_tab import DesignerTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Divoom Gaming Gate")
        self._init_ui()

    def _init_ui(self):
        tabs = QTabWidget()
        tabs.addTab(ScreensTab(),    "Screens")
        tabs.addTab(CharactersTab(), "Characters")
        tabs.addTab(DesignerTab(),   "Designer")
        self.setCentralWidget(tabs)
        # optional: set a reasonable minimum size
        self.resize(1200, 800)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
