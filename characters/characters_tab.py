from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout
from .character_control import CharacterControl
from PyQt5.QtCore import Qt

class CharactersTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        for i in range(5):
            box = QGroupBox(f"Character {i+1}")
            ctrl = CharacterControl(i)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignTop)
            v.addWidget(ctrl)
            box.setLayout(v)
            layout.addWidget(box)
        self.setLayout(layout)