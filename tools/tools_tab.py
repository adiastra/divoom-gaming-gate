import requests
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QSpinBox, QToolButton, QMessageBox
)
from utils.config import Config

class ToolsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#2b2b2b;")
        self.cfg = Config()

        # Use a horizontal layout for side-by-side tools
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # --- Scoreboard Tool Group Box ---
        scoreboard_group = QGroupBox("Scoreboard")
        scoreboard_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        scoreboard_layout = QVBoxLayout(scoreboard_group)
        scoreboard_layout.setContentsMargins(8, 8, 8, 8)
        scoreboard_layout.setSpacing(8)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Blue Score:", styleSheet="color:white"))
        self.blue_score = QSpinBox()
        self.blue_score.setRange(0, 999)
        row2.addWidget(self.blue_score)
        row2.addWidget(QLabel("Red Score:", styleSheet="color:white"))
        self.red_score = QSpinBox()
        self.red_score.setRange(0, 999)
        row2.addWidget(self.red_score)
        scoreboard_layout.addLayout(row2)

        # Automatically send scoreboard on score change
        self.blue_score.valueChanged.connect(self.send_scoreboard)
        self.red_score.valueChanged.connect(self.send_scoreboard)

        # Remove the manual send button for scoreboard
        # send_btn = QToolButton(text="Send Scoreboard", autoRaise=True)
        # send_btn.setStyleSheet("color:white;font-size:14px")
        # send_btn.clicked.connect(self.send_scoreboard)
        # scoreboard_layout.addWidget(send_btn, alignment=Qt.AlignRight)

        # --- Countdown Timer Tool Group Box ---
        timer_group = QGroupBox("Countdown Timer")
        timer_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        timer_layout = QVBoxLayout(timer_group)
        timer_layout.setContentsMargins(8, 8, 8, 8)
        timer_layout.setSpacing(8)

        # Time input (minutes and seconds)
        time_lay = QHBoxLayout()
        time_lay.addWidget(QLabel("Minutes:", styleSheet="color:white"))
        self.timer_minutes = QSpinBox()
        self.timer_minutes.setRange(0, 99)
        time_lay.addWidget(self.timer_minutes)
        time_lay.addWidget(QLabel("Seconds:", styleSheet="color:white"))
        self.timer_seconds = QSpinBox()
        self.timer_seconds.setRange(0, 59)
        time_lay.addWidget(self.timer_seconds)
        timer_layout.addLayout(time_lay)

        # Start button
        start_btn = QToolButton(text="Start Countdown", autoRaise=True)
        start_btn.setStyleSheet("color:white;font-size:14px")
        start_btn.clicked.connect(self.send_countdown)
        timer_layout.addWidget(start_btn, alignment=Qt.AlignRight)

        # --- Stopwatch Tool Group Box ---
        stopwatch_group = QGroupBox("Stopwatch")
        stopwatch_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        stopwatch_layout = QVBoxLayout(stopwatch_group)
        stopwatch_layout.setContentsMargins(8, 8, 8, 8)
        stopwatch_layout.setSpacing(8)

        btn_lay = QHBoxLayout()
        start_btn = QToolButton(text="Start", autoRaise=True)
        start_btn.setStyleSheet("color:white;font-size:14px")
        start_btn.clicked.connect(lambda: self.send_stopwatch(1))
        btn_lay.addWidget(start_btn)

        stop_btn = QToolButton(text="Stop", autoRaise=True)
        stop_btn.setStyleSheet("color:white;font-size:14px")
        stop_btn.clicked.connect(lambda: self.send_stopwatch(0))
        btn_lay.addWidget(stop_btn)

        reset_btn = QToolButton(text="Reset", autoRaise=True)
        reset_btn.setStyleSheet("color:white;font-size:14px")
        reset_btn.clicked.connect(lambda: self.send_stopwatch(2))
        btn_lay.addWidget(reset_btn)

        stopwatch_layout.addLayout(btn_lay)

        # --- Buzzer Tool Group Box ---
        buzzer_group = QGroupBox("Buzzer")
        buzzer_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        buzzer_layout = QVBoxLayout(buzzer_group)
        buzzer_layout.setContentsMargins(8, 8, 8, 8)
        buzzer_layout.setSpacing(8)

        # ActiveTimeInCycle
        active_lay = QHBoxLayout()
        active_lay.addWidget(QLabel("Active Time (ms):", styleSheet="color:white"))
        self.buzzer_active = QSpinBox()
        self.buzzer_active.setRange(1, 10000)
        self.buzzer_active.setValue(500)
        active_lay.addWidget(self.buzzer_active)
        buzzer_layout.addLayout(active_lay)

        # OffTimeInCycle
        off_lay = QHBoxLayout()
        off_lay.addWidget(QLabel("Off Time (ms):", styleSheet="color:white"))
        self.buzzer_off = QSpinBox()
        self.buzzer_off.setRange(0, 10000)
        self.buzzer_off.setValue(500)
        off_lay.addWidget(self.buzzer_off)
        buzzer_layout.addLayout(off_lay)

        # PlayTotalTime
        total_lay = QHBoxLayout()
        total_lay.addWidget(QLabel("Total Play Time (ms):", styleSheet="color:white"))
        self.buzzer_total = QSpinBox()
        self.buzzer_total.setRange(1, 60000)
        self.buzzer_total.setValue(3000)
        total_lay.addWidget(self.buzzer_total)
        buzzer_layout.addLayout(total_lay)

        # Play button
        play_btn = QToolButton(text="Play Buzzer", autoRaise=True)
        play_btn.setStyleSheet("color:white;font-size:14px")
        play_btn.clicked.connect(self.send_buzzer)
        buzzer_layout.addWidget(play_btn, alignment=Qt.AlignRight)

        # --- Noise Tool Group Box ---
        noise_group = QGroupBox("Noise Meter")
        noise_group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; border: 1px inset #666; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
        )
        noise_layout = QVBoxLayout(noise_group)
        noise_layout.setContentsMargins(8, 8, 8, 8)
        noise_layout.setSpacing(8)

        btn_lay = QHBoxLayout()
        start_btn = QToolButton(text="Start", autoRaise=True)
        start_btn.setStyleSheet("color:white;font-size:14px")
        start_btn.clicked.connect(lambda: self.send_noise(1))
        btn_lay.addWidget(start_btn)

        stop_btn = QToolButton(text="Stop", autoRaise=True)
        stop_btn.setStyleSheet("color:white;font-size:14px")
        stop_btn.clicked.connect(lambda: self.send_noise(0))
        btn_lay.addWidget(stop_btn)

        noise_layout.addLayout(btn_lay)

        # Add all group boxes to the horizontal layout
        main_layout.addWidget(scoreboard_group, alignment=Qt.AlignTop | Qt.AlignLeft)
        main_layout.addWidget(timer_group, alignment=Qt.AlignTop | Qt.AlignLeft)
        main_layout.addWidget(stopwatch_group, alignment=Qt.AlignTop | Qt.AlignLeft)
        main_layout.addWidget(buzzer_group, alignment=Qt.AlignTop | Qt.AlignLeft)
        main_layout.addWidget(noise_group, alignment=Qt.AlignTop | Qt.AlignLeft)
        main_layout.addStretch()

    def send_scoreboard(self):
        ip = self.cfg.get_device_ip()
        blue = self.blue_score.value()
        red = self.red_score.value()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetScoreBoard",
            "BlueScore": blue,
            "RedScore": red
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_countdown(self):
        ip = self.cfg.get_device_ip()
        minutes = self.timer_minutes.value()
        seconds = self.timer_seconds.value()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetTimer",
            "Minute": minutes,
            "Second": seconds,
            "Status": 1  # 1 = start, 0 = stop
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_stopwatch(self, status):
        ip = self.cfg.get_device_ip()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetStopWatch",
            "Status": status  # 2:reset; 1: start; 0: stop
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_buzzer(self):
        ip = self.cfg.get_device_ip()
        if not ip:
            return
        payload = {
            "Command": "Device/PlayBuzzer",
            "ActiveTimeInCycle": self.buzzer_active.value(),
            "OffTimeInCycle": self.buzzer_off.value(),
            "PlayTotalTime": self.buzzer_total.value()
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass

    def send_noise(self, status):
        ip = self.cfg.get_device_ip()
        if not ip:
            return
        payload = {
            "Command": "Tools/SetNoiseStatus",
            "NoiseStatus": status  # 1 = start, 0 = stop
        }
        try:
            requests.post(f"http://{ip}/post", json=payload, timeout=8)
        except Exception:
            pass