from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QSizePolicy
from .screen_control import ScreenControl
from PyQt5.QtCore import Qt

class ScreensTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        for i in range(5):
            box = QGroupBox(f"Screen {i+1}")
            # Ensure the box stays at least 300px wide
            box.setMinimumWidth(300)
            box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

            ctrl = ScreenControl(i)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignTop)
            v.addWidget(ctrl)
            box.setLayout(v)

            layout.addWidget(box)

        # Allow horizontal scroll if the window is narrower
        layout.addStretch()
        self.setLayout(layout)
