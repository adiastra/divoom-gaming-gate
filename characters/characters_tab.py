from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QSizePolicy
from .character_control import CharacterControl
from PyQt5.QtCore import Qt

class CharactersTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")

        # Main horizontal layout, matching ToolsTab
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        for i in range(5):
            box = QGroupBox(f"Character {i+1}")
            box.setMinimumWidth(260)
            box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

            ctrl = CharacterControl(i)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignTop)
            v.addWidget(ctrl)
            box.setLayout(v)

            main_layout.addWidget(box)

        main_layout.addStretch()
