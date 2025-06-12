from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QSizePolicy
from .character_control import CharacterControl
from PyQt5.QtCore import Qt

class CharactersTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        for i in range(5):
            box = QGroupBox(f"Character {i+1}")
            # Keep each character panel at least 300px wide
            box.setMinimumWidth(300)
            box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

            ctrl = CharacterControl(i)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignTop)
            v.addWidget(ctrl)
            box.setLayout(v)

            layout.addWidget(box)

        layout.addStretch()
        self.setLayout(layout)
