from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout
from .screen_control import ScreenControl
from PyQt5.QtCore import Qt

class ScreensTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        for i in range(5):
            box = QGroupBox(f"Screen {i+1}")
            ctrl = ScreenControl(i)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignTop)
            v.addWidget(ctrl)
            box.setLayout(v)
            layout.addWidget(box)
        self.setLayout(layout)