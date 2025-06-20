from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QSizePolicy
from .screen_control import ScreenControl
from PyQt5.QtCore import Qt

class ScreensTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")

        # Main horizontal layout, matching CharactersTab
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        for i in range(5):
            box = QGroupBox(f"Screen {i+1}")
            box.setMinimumWidth(260)
            box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

            ctrl = ScreenControl(i)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignTop)
            v.addWidget(ctrl)
            box.setLayout(v)

            main_layout.addWidget(box)

        main_layout.addStretch()
