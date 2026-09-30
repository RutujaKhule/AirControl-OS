from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QWidget,
    QPushButton,
    QGraphicsDropShadowEffect,
    QSizePolicy,
)


def _make_card(title: str, body_lines: list) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        "background-color: #0f3460; border-radius: 12px;"
    )
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(12)
    shadow.setColor(QColor(0, 0, 0, 100))
    shadow.setOffset(0, 3)
    card.setGraphicsEffect(shadow)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)

    title_lbl = QLabel(title)
    title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
    title_lbl.setStyleSheet("color: #64ffda; background: transparent;")

    body = QLabel("\n".join(body_lines))
    body.setFont(QFont("Segoe UI", 10))
    body.setStyleSheet("color: #ccd6f6; background: transparent;")
    body.setWordWrap(True)

    layout.addWidget(title_lbl)
    layout.addWidget(body)
    return card


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AirControl OS — Help & Cheatsheet")
        self.resize(820, 720)
        self.setMinimumSize(680, 600)
        self.setStyleSheet("background-color: #16213e;")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header = QLabel("AirControl OS — Gesture & Voice Guide")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #ccd6f6;")

        sub = QLabel(
            "Control your computer hands-free using gestures (webcam) and voice commands (microphone). "
            "Use the Settings dialog (Ctrl+,) to tune gesture thresholds, cursor feel, and voice parameters."
        )
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #8892b0;")
        sub.setWordWrap(True)

        cards_row1 = QHBoxLayout()
        cards_row1.setSpacing(14)
        cards_row1.addWidget(
            _make_card(
                "Hand Gestures — Cursor & Clicks",
                [
                    "• Index finger tip → moves the mouse cursor",
                    "• Thumb + Index pinch (quick) → Left Click",
                    "• Pinch and hold 250 ms → Drag; release to drop",
                    "• Index + Middle V-shape → Right Click",
                    "• Move hand vertically up/down → Scroll Up/Down",
                    "• Make a Fist and hold 350 ms → Pause / Resume control",
                ],
            )
        )
        cards_row1.addWidget(
            _make_card(
                "Voice Commands — Apps & Media",
                [
                    "Open / Launch / Start / Run:",
                    "  Chrome, Notepad, Calculator, Paint,",
                    "  Explorer, cmd, PowerShell, Spotify,",
                    "  Word, Excel, PowerPoint, Edge, Firefox",
                    "",
                    "Media: Play / Pause, Next / Skip,",
                    "  Previous / Back, Stop",
                    "",
                    "Volume: Volume up / Louder,",
                    "  Volume down / Quieter, Mute",
                    "",
                    "Scroll: Scroll up / Page up, Scroll down / Page down",
                    "  (+ 'a lot', 'little', 'slight' for amount)",
                ],
            )
        )

        cards_row2 = QHBoxLayout()
        cards_row2.setSpacing(14)
        cards_row2.addWidget(
            _make_card(
                "Keyboard Shortcuts",
                [
                    "Ctrl + ,        Open Settings dialog",
                    "F1              Show this help dialog",
                    "Ctrl + Q        Quit AirControl OS",
                    "Space           Toggle Pause / Resume",
                    "V               Toggle Voice on or off",
                    "F11             Toggle fullscreen",
                ],
            )
        )
        cards_row2.addWidget(
            _make_card(
                "Troubleshooting",
                [
                    "• No landmarks detected → check webcam privacy,",
                    "  lighting, and camera index in settings.",
                    "• Pinch feels too easy/hard → adjust pinch",
                    "  threshold slider in Settings.",
                    "• Cursor jittery → increase cursor smoothing",
                    "  factor (0.7+ = very smooth).",
                    "• Voice not listening → verify mic is available,",
                    "  run `pipwin install pyaudio` if needed.",
                    "• False scrolls → raise scroll sensitivity.",
                    "• Clicks happen twice → raise cooldown ms.",
                ],
            )
        )

        scroll_inner = QWidget()
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)
        scroll_layout.addWidget(header)
        scroll_layout.addWidget(sub)
        temp1 = QWidget(); tmp_lay1 = QHBoxLayout(temp1); tmp_lay1.setContentsMargins(0,0,0,0)
        tmp_lay1.addLayout(cards_row1); scroll_layout.addWidget(temp1)
        temp2 = QWidget(); tmp_lay2 = QHBoxLayout(temp2); tmp_lay2.setContentsMargins(0,0,0,0)
        tmp_lay2.addLayout(cards_row2); scroll_layout.addWidget(temp2)

        scroll = QScrollArea()
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #0f3460; width: 10px; }"
            "QScrollBar::handle:vertical { background: #533483; border-radius: 5px; }"
        )
        scroll.setWidget(scroll_inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet(
            "QPushButton { background-color: #533483; color: #ccd6f6; "
            "border-radius: 8px; padding: 8px 22px; }"
            "QPushButton:hover { background-color: #5f3e9a; }"
        )
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)

        root.addWidget(scroll, 1)
        root.addLayout(btn_row)
