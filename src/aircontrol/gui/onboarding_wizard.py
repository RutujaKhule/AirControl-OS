import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QLinearGradient, QBrush
from PySide6.QtWidgets import (
    QWizard,
    QWizardPage,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QWidget,
    QGraphicsDropShadowEffect,
    QFrame,
)

from ..core.config import CONFIG


def _make_hero_pixmap(size: int = 140) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#533483"))
    grad.setColorAt(1.0, QColor("#53d397"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    r = 18
    p.drawRoundedRect(4, 4, size - 8, size - 8, r, r)
    p.setPen(QColor("#ffffff"))
    f = QFont("Segoe UI", 56, QFont.Bold)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, "✋")
    p.end()
    return pm


def _make_card(title: str, body: str, color: str = "#64ffda") -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"background-color: #0f3460; border: 1px solid #533483; border-radius: 12px;"
    )
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(10)
    shadow.setColor(QColor(0, 0, 0, 80))
    shadow.setOffset(0, 2)
    card.setGraphicsEffect(shadow)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(6)
    t = QLabel(title)
    t.setFont(QFont("Segoe UI", 12, QFont.Bold))
    t.setStyleSheet(f"color: {color}; background: transparent;")
    b = QLabel(body)
    b.setFont(QFont("Segoe UI", 10))
    b.setStyleSheet("color: #ccd6f6; background: transparent;")
    b.setWordWrap(True)
    layout.addWidget(t)
    layout.addWidget(b)
    return card


class OnboardingWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Welcome to {CONFIG.APP_NAME}")
        self.resize(820, 680)
        self.setMinimumSize(720, 600)
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)
        self.setButtonText(QWizard.FinishButton, "Launch AirControl")
        self.setButtonText(QWizard.NextButton, "Continue")
        self.setButtonText(QWizard.BackButton, "Back")

        self.setStyleSheet(
            "QWizard { background-color: #16213e; }"
            "QWizardPage { background-color: #16213e; }"
            "QDialogButtonBox QPushButton { background-color: #533483; color: #ccd6f6;"
            "padding: 8px 20px; border-radius: 8px; min-width: 88px; font-family: Segoe UI;"
            "font-weight: 600; }"
            "QDialogButtonBox QPushButton:hover { background-color: #5f3e9a; }"
            "QDialogButtonBox QPushButton:default { background-color: #53d397; color: #0f3460; }"
            "QDialogButtonBox QPushButton:default:hover { background-color: #44b882; }"
            "QDialogButtonBox QPushButton:disabled { color: #8892b0; background-color: #0f3460; }"
            "QWizard QLabel { color: #ccd6f6; }"
        )

        self.addPage(self._page_intro())
        self.addPage(self._page_permissions())
        self.addPage(self._page_gestures())
        self.addPage(self._page_voice())

    def _page_intro(self) -> QWizardPage:
        p = QWizardPage()
        p.setTitle("Welcome to AirControl OS")
        p.setSubTitle("Hands-free control of your computer using gestures and voice.")
        root = QVBoxLayout(p)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(18)
        icon = QLabel()
        icon.setPixmap(_make_hero_pixmap(150))
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        h = QLabel(f"{CONFIG.APP_NAME} v{CONFIG.APP_VERSION}")
        h.setFont(QFont("Segoe UI", 22, QFont.Bold))
        h.setStyleSheet("color: #ccd6f6;")
        s = QLabel(
            "AirControl OS uses your webcam to track your hand and translate gestures into "
            "real cursor control and clicks, while your microphone listens for voice commands "
            "like 'Open Chrome', 'Play', and 'Scroll up'."
        )
        s.setFont(QFont("Segoe UI", 11))
        s.setStyleSheet("color: #8892b0;")
        s.setWordWrap(True)
        title_box.addWidget(h)
        title_box.addWidget(s)
        title_box.addStretch(1)
        top.addWidget(icon, 0)
        top.addLayout(title_box, 1)
        root.addLayout(top)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        cards_row.addWidget(
            _make_card(
                "Webcam Tracking",
                "MediaPipe tracks 21 landmarks on your hand in real time, mirrored to match your movement.",
                "#64ffda",
            )
        )
        cards_row.addWidget(
            _make_card(
                "Gesture Control",
                "Pinch to click, hold to drag, raise hand to scroll, make a fist to pause.",
                "#53d397",
            )
        )
        root.addLayout(cards_row)
        cards_row2 = QHBoxLayout()
        cards_row2.setSpacing(14)
        cards_row2.addWidget(
            _make_card(
                "Voice Commands",
                "Say 'Open Notepad', 'Play', 'Volume up', 'Scroll down' and more — hands-free.",
                "#ffb86c",
            )
        )
        cards_row2.addWidget(
            _make_card(
                "Tunable & Persistent",
                "Every setting (sensitivity, camera index, voice language) is saved between launches.",
                "#bd93f9",
            )
        )
        root.addLayout(cards_row2)
        return p

    def _page_permissions(self) -> QWizardPage:
        p = QWizardPage()
        p.setTitle("Check Permissions & Hardware")
        p.setSubTitle(
            "Before you start, confirm the following are available so control is smooth on first launch."
        )
        root = QVBoxLayout(p)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)

        items = [
            ("Webcam available", "The default camera (index 0) is free and not blocked by another app. You can change index later in Settings."),
            ("Microphone available", "Default mic works and Windows privacy settings allow Python to listen."),
            ("Desktop control (PyAutoGUI)", "If your desktop displays the UAC prompt, clicks work normally from your user session."),
            ("Internet for voice", "Speech recognition uses Google's free API; keep connectivity for voice to work."),
        ]
        self._perm_checks = []
        for title, detail in items:
            row = QVBoxLayout()
            row.setSpacing(2)
            cb = QCheckBox(title)
            cb.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
            cb.setStyleSheet(
                "QCheckBox { color: #ccd6f6; padding: 4px 0; }"
                "QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px;"
                "border: 1px solid #533483; background: #0f3460; }"
                "QCheckBox::indicator:checked { background: #53d397; border: 1px solid #53d397; }"
            )
            desc = QLabel(detail)
            desc.setFont(QFont("Segoe UI", 9))
            desc.setStyleSheet("color: #8892b0;")
            desc.setWordWrap(True)
            row.addWidget(cb)
            row.addWidget(desc)
            wrap = QWidget()
            QVBoxLayout(wrap).addLayout(row)
            wrap.layout().setContentsMargins(0, 0, 0, 0)
            root.addWidget(wrap)
            self._perm_checks.append(cb)
        root.addStretch(1)
        tip = QLabel(
            "Tip: you can always unblock later in Settings (Ctrl+,). Voice will gracefully disable itself if mic is unavailable."
        )
        tip.setFont(QFont("Segoe UI", 10, -1, True))
        tip.setStyleSheet("color: #64ffda;")
        tip.setWordWrap(True)
        root.addWidget(tip)
        return p

    def _page_gestures(self) -> QWizardPage:
        p = QWizardPage()
        p.setTitle("Gesture Guide")
        p.setSubTitle("After setup, hold your hand up to the camera. Try these gestures in order:")
        root = QVBoxLayout(p)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)
        steps = [
            ("1. Move cursor", "Point your index finger (yellow ring) at the camera. Watch your real mouse cursor move smoothly."),
            ("2. Left click", "Pinch your thumb (cyan ring) and index finger together quickly and release."),
            ("3. Drag", "Pinch and hold for ~250 ms, then move your hand. Release the pinch to drop."),
            ("4. Right click", "Hold only index and middle fingers in a V-shape, with ring + pinky folded."),
            ("5. Scroll", "Raise your whole hand up to scroll up, lower it to scroll down."),
            ("6. Pause/Resume", "Make a closed fist and hold ~350 ms. Status turns red. Fist again to resume."),
        ]
        for title, detail in steps:
            row = QHBoxLayout()
            row.setSpacing(14)
            badge = QLabel()
            badge.setFixedSize(QSize(46, 46))
            badge.setAlignment(Qt.AlignCenter)
            badge.setFont(QFont("Segoe UI", 14, QFont.Bold))
            badge.setStyleSheet(
                "background-color: #533483; color: #ccd6f6; border-radius: 23px;"
            )
            badge.setText(title.split(".", 1)[0].strip())
            text_box = QVBoxLayout()
            text_box.setSpacing(2)
            t = QLabel(title)
            t.setFont(QFont("Segoe UI", 11, QFont.Bold))
            t.setStyleSheet("color: #64ffda;")
            d = QLabel(detail)
            d.setFont(QFont("Segoe UI", 10))
            d.setStyleSheet("color: #ccd6f6;")
            d.setWordWrap(True)
            text_box.addWidget(t)
            text_box.addWidget(d)
            row.addWidget(badge, 0)
            row.addLayout(text_box, 1)
            wrap = QWidget()
            QVBoxLayout(wrap).addLayout(row)
            wrap.layout().setContentsMargins(0, 0, 0, 0)
            root.addWidget(wrap)
        return p

    def _page_voice(self) -> QWizardPage:
        p = QWizardPage()
        p.setTitle("Voice Commands & Next Steps")
        p.setSubTitle("Speak naturally into your mic. Some phrases to try first:")
        root = QVBoxLayout(p)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        apps = "Chrome · Notepad · Calculator · Paint · Explorer · cmd · PowerShell · Spotify · Word · Excel · PowerPoint · Edge · Firefox"
        r1 = QHBoxLayout(); r1.setSpacing(12)
        r1.addWidget(_make_card("Open apps", f"\"Open Chrome\", \"Launch Notepad\"\n\nTargets: {apps}", "#64ffda"))
        r1.addWidget(_make_card("Media", "\"Play\", \"Pause\", \"Next\", \"Previous\", \"Stop\"", "#53d397"))
        root.addLayout(r1)
        r2 = QHBoxLayout(); r2.setSpacing(12)
        r2.addWidget(_make_card("Volume", "\"Volume up\", \"Louder\", \"Mute\", \"Quieter\"", "#ffb86c"))
        r2.addWidget(_make_card("Scroll", "\"Scroll up\", \"Page down a lot\", \"Scroll down little\"", "#bd93f9"))
        root.addLayout(r2)

        self._startup_cb = QCheckBox("Launch AirControl OS minimized to system tray next time")
        self._startup_cb.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self._startup_cb.setStyleSheet(
            "QCheckBox { color: #ccd6f6; padding: 4px 0; }"
            "QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px;"
            "border: 1px solid #533483; background: #0f3460; }"
            "QCheckBox::indicator:checked { background: #53d397; border: 1px solid #53d397; }"
        )
        root.addSpacing(6)
        root.addWidget(self._startup_cb)

        fin = QLabel(
            "Click Finish to launch the main window. You can revisit this guide anytime from Help → First-run Guide."
        )
        fin.setFont(QFont("Segoe UI", 10, -1, True))
        fin.setStyleSheet("color: #64ffda;")
        fin.setWordWrap(True)
        root.addStretch(1)
        root.addWidget(fin)
        return p

    @property
    def launch_minimized_to_tray(self) -> bool:
        return self._startup_cb.isChecked() if hasattr(self, "_startup_cb") else False
