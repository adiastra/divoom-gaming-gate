import sys
from PyQt5.QtWidgets import QApplication, QTabWidget
from screens.screens_tab import ScreensTab
from characters.characters_tab import CharactersTab

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tabs = QTabWidget()
    tabs.setWindowTitle("Divoom Times Gate – Tabletop Manager V8")
    tabs.resize(1000, 600)
    tabs.addTab(ScreensTab(), "Screens")
    tabs.addTab(CharactersTab(), "Characters")
    tabs.show()
    sys.exit(app.exec_())