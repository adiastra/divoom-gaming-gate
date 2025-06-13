import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QScrollArea,
    QToolButton
)
from PyQt5.QtCore import Qt
from screens.screens_tab import ScreensTab
from characters.characters_tab import CharactersTab
from settings_dialog import SettingsDialog
from utils.config import Config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Divoom Times Gate – Tabletop Manager")
        self.resize(1323, 650)

        Config.load()

        tabs = QTabWidget()
        for title, widget in [("Screens", ScreensTab()), ("Characters", CharactersTab())]:
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(widget)
            tabs.addTab(area, title)

        self.setCentralWidget(tabs)

        # Gear button with Unicode gear, larger font
        gear_btn = QToolButton(self)
        gear_btn.setText("⚙")
        gear_btn.setToolTip("Preferences")
        gear_btn.setStyleSheet("font-size: 32pt; padding: 4px;")
        gear_btn.clicked.connect(self.open_settings)
        gear_btn.setAutoRaise(True)

        toolbar = self.addToolBar("")  # icon-only toolbar
        toolbar.setMovable(False)
        toolbar.addWidget(gear_btn)
        toolbar.layout().setAlignment(Qt.AlignLeft)  # pin to left

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
