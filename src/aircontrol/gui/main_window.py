import cv2
import numpy as np

from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QKeySequence, QAction, QShortcut
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QStatusBar,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QGraphicsDropShadowEffect,
    QMenuBar,
    QMenu,
    QCheckBox,
    QScrollArea,
)
from typing import Optional

from ..core.config import CONFIG, GESTURE_CONFIG
from ..core.persistence import (
    save_settings,
)
from ..core.action_history import (
    ActionHistory,
    HISTORY,
)
from ..core.cursor_controller import CursorController
from ..gesture.hand_detector import DetectionResult
from ..gesture.recognizer import GestureType
from ..voice.executor import VoiceExecutor
from ..voice.listener import VoiceListener
from .video_worker import VideoWorker


_GESTURE_COLORS = {
    GestureType.NONE.name: "#8892b0",
    GestureType.CURSOR_MOVE.name: "#64ffda",
    GestureType.PINCH_CLICK.name: "#53d397",
    GestureType.RIGHT_CLICK.name: "#ffb86c",
    GestureType.DRAGGING.name: "#f1fa8c",
    GestureType.SCROLL_UP.name: "#8be9fd",
    GestureType.SCROLL_DOWN.name: "#8be9fd",
    GestureType.FIST.name: "#bd93f9",
    GestureType.FIST_PAUSED.name: "#e94560",
}


class VideoDisplay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background-color: #1a1a2e; border: 2px solid #16213e; "
            "border-radius: 12px; color: #8892b0; font-size: 16px;"
        )
        self.setText("Initializing camera...")

    def update_frame(self, frame: np.ndarray):
        if frame is None:
            self.setText("Camera Offline")
            self.setStyleSheet(
                "background-color: #2d1117; border: 2px solid #e94560; "
                "border-radius: 12px; color: #e94560; font-size: 16px;"
            )
            return
        self.setText("")
        self.setStyleSheet(
            "background-color: #1a1a2e; border: 2px solid #16213e; "
            "border-radius: 12px; color: #8892b0; font-size: 16px;"
        )
        if not frame.flags['C_CONTIGUOUS']:
            frame = np.ascontiguousarray(frame)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        if ch != 3:
            return
        bytes_per_line = w * ch
        qt_image = QImage(
            rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
        ).copy()
        if qt_image.isNull():
            return
        # Scale to fit the label while preserving aspect ratio
        label_size = self.size()
        if label_size.width() > 0 and label_size.height() > 0:
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                label_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.setPixmap(scaled_pixmap)
        else:
            self.setPixmap(QPixmap.fromImage(qt_image))


class InfoCard(QFrame):
    """A status card with a title label and a value label."""

    def __init__(self, title: str, value: str = "-", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background-color: #0f3460; border-radius: 10px; padding: 6px;"
        )
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumHeight(50)
        self.setMinimumWidth(200)
        self.setAutoFillBackground(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        self.setLayout(layout)

        self._title_label = QLabel(title)
        self._title_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self._title_label.setStyleSheet("color: #ffffff;")
        self._title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._title_label.setAutoFillBackground(False)

        self._value_label = QLabel(value)
        self._value_label.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        self._value_label.setStyleSheet("color: #ffffff;")
        self._value_label.setWordWrap(True)
        self._value_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._value_label.setMinimumHeight(24)
        self._value_label.setAutoFillBackground(False)

        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)

    def sizeHint(self):
        return QSize(280, 60)

    def set_value(self, value: str):
        self._value_label.setText(value)

    def set_value_color(self, color: str):
        self._value_label.setStyleSheet(f"color: {color};")


class MainWindow(QMainWindow):
    request_open_settings = Signal()
    request_open_log = Signal()
    request_open_help = Signal()
    request_hide = Signal()
    request_quit = Signal()
    settings_applied_signal = Signal()
    gesture_state_toggled = Signal(str, bool, str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{CONFIG.APP_NAME} v{CONFIG.APP_VERSION}")
        if CONFIG.WINDOW_STATE_MAXIMIZED:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.resize(CONFIG.WINDOW_WIDTH, CONFIG.WINDOW_HEIGHT)
        self.setMinimumSize(QSize(900, 600))

        self._worker: Optional[VideoWorker] = None
        self._voice_listener: Optional[VoiceListener] = None
        self._voice_executor = VoiceExecutor()
        self._cursor = CursorController()
        self._tray = None
        self._voice_enabled = True

        self._last_gesture_identifier: Optional[str] = None
        self._last_voice_label: Optional[str] = None

        self._history: ActionHistory = HISTORY

        self._build_menu()
        self._build_ui()
        self._register_shortcuts()
        self._restore_window_position()
        self._history.system("Startup", f"{CONFIG.APP_NAME} v{CONFIG.APP_VERSION} launched")

        self._start_worker()
        self._start_voice()

    # ================================================================
    # Tray integration (called by main.py right after construction)
    # ================================================================
    def set_tray_manager(self, tray) -> None:
        self._tray = tray

    # ================================================================
    # Menu bar
    # ================================================================
    def _build_menu(self) -> None:
        menu_bar = QMenuBar(self)
        menu_bar.setStyleSheet(
            "QMenuBar { background-color: #0f3460; color: #ccd6f6; padding: 4px 6px;"
            "border-bottom: 1px solid #16213e; font-family: Segoe UI; font-size: 10pt; }"
            "QMenuBar::item { background: transparent; padding: 6px 10px; border-radius: 4px; }"
            "QMenuBar::item:selected { background: #533483; color: #ccd6f6; }"
            "QMenu { background-color: #0f3460; color: #ccd6f6; border: 1px solid #533483;"
            "border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 6px 22px; border-radius: 4px; }"
            "QMenu::item:selected { background: #533483; color: #ccd6f6; }"
            "QMenu::separator { height: 1px; background: #16213e; margin: 4px 4px; }"
        )

        file_menu: QMenu = menu_bar.addMenu("&File")
        act_settings = QAction("Settings...", self)
        act_settings.setShortcut(QKeySequence.Preferences)
        act_settings.triggered.connect(lambda: self.request_open_settings.emit())
        file_menu.addAction(act_settings)
        act_log = QAction("Activity Log", self)
        act_log.setShortcut(QKeySequence("Ctrl+L"))
        act_log.triggered.connect(lambda: self.request_open_log.emit())
        file_menu.addAction(act_log)
        file_menu.addSeparator()

        act_hide_tray = QAction("Hide to Tray", self)
        act_hide_tray.setShortcut(QKeySequence("Ctrl+M"))
        act_hide_tray.triggered.connect(lambda: self.request_hide.emit())
        file_menu.addAction(act_hide_tray)

        act_restore = QAction("Restore Defaults", self)
        act_restore.triggered.connect(self._restore_defaults)
        file_menu.addAction(act_restore)
        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.setShortcut(QKeySequence.Quit)
        act_exit.triggered.connect(lambda: self.request_quit.emit())
        file_menu.addAction(act_exit)

        view_menu: QMenu = menu_bar.addMenu("&View")
        act_fullscreen = QAction("Toggle Fullscreen", self)
        act_fullscreen.setShortcut(QKeySequence(QKeySequence.FullScreen))
        act_fullscreen.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(act_fullscreen)
        act_min_tray_cb = QAction("Close button minimizes to tray", self)
        act_min_tray_cb.setCheckable(True)
        act_min_tray_cb.setChecked(bool(CONFIG.CLOSE_TO_TRAY))
        act_min_tray_cb.toggled.connect(self._set_close_to_tray)
        view_menu.addAction(act_min_tray_cb)
        act_hotkeys_cb = QAction("Enable global (system-wide) hotkeys", self)
        act_hotkeys_cb.setCheckable(True)
        act_hotkeys_cb.setChecked(bool(CONFIG.TRAY_GLOBAL_HOTKEYS))
        act_hotkeys_cb.toggled.connect(self._set_global_hotkeys)
        view_menu.addAction(act_hotkeys_cb)

        help_menu: QMenu = menu_bar.addMenu("&Help")
        act_help = QAction("Help & Cheatsheet", self)
        act_help.setShortcut(QKeySequence(QKeySequence.HelpContents))
        act_help.triggered.connect(lambda: self.request_open_help.emit())
        help_menu.addAction(act_help)
        act_wizard = QAction("First-run Wizard", self)
        act_wizard.setShortcut(QKeySequence("Ctrl+Shift+W"))
        act_wizard.triggered.connect(self._show_onboarding_again)
        help_menu.addAction(act_wizard)
        act_about = QAction("About Settings Location", self)
        act_about.triggered.connect(self._show_settings_location)
        help_menu.addAction(act_about)

        self.setMenuBar(menu_bar)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Space"), self, activated=self._toggle_pause)
        QShortcut(QKeySequence("V"), self, activated=self._toggle_voice)

    # ================================================================
    # Build main UI
    # ================================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background-color: #16213e;")

        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        header = QLabel("AirControl OS — Gesture + Voice Control")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color: #ccd6f6;")

        self._video_display = VideoDisplay()

        left_layout.addWidget(header)
        left_layout.addWidget(self._video_display, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        sys_header = QLabel("System Status")
        sys_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        sys_header.setStyleSheet("color: #ccd6f6;")

        self._status_card = InfoCard("System", "Starting...")
        self._status_card.set_value_color("#ffb86c")

        self._fps_card = InfoCard("Camera", "Starting...")
        self._fps_card.set_value_color("#ffb86c")

        self._detected_card = InfoCard("Hand Tracking", "Waiting...")

        self._handedness_card = InfoCard("Hand", "Left")

        self._confidence_card = InfoCard("Detection", "95%")

        self._gesture_card = InfoCard("Gesture", "Waiting...")
        self._gesture_card._value_label.setFont(QFont("Segoe UI", 12, QFont.DemiBold))

        self._voice_status_card = InfoCard("Voice Control", "Ready")
        self._voice_status_card.set_value_color("#64ffda")

        self._voice_phrase_card = InfoCard("Last Phrase", "—")
        self._voice_phrase_card._value_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))

        self._voice_action_card = InfoCard("Voice Action", "—")
        self._voice_action_card._value_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))

        self._cursor_card = InfoCard("Cursor", "Enabled")
        self._cursor_card.set_value_color("#53d397")

        info_label = QLabel(
            "Gesture controls:\n"
            " • Index finger → move cursor\n"
            " • Thumb + index pinch → left click\n"
            " • Pinch & hold (250ms) → drag\n"
            " • Index + middle V-shape → right click\n"
            " • Hand up/down motion → scroll\n"
            " • Fist held 350ms → Pause/Resume\n\n"
            "Voice commands (say into mic):\n"
            " • 'Open Chrome' / 'Open Notepad' / ...\n"
            " • 'Play' / 'Pause' / 'Next' / 'Previous'\n"
            " • 'Volume up' / 'Volume down' / 'Mute'\n"
            " • 'Scroll up' / 'Scroll down'\n\n"
            "Shortcuts:\n"
            " Ctrl+, = Settings   Ctrl+L = Log\n"
            " F1 = Help   Space = Pause   V = Voice\n"
            " Global: Ctrl+Alt+P/S/V     Ctrl+M = Hide\n\n"
            "Status: Green=Active Red=Paused"
        )
        info_label.setWordWrap(True)
        info_label.setFont(QFont("Segoe UI", 9))
        info_label.setStyleSheet(
            "color: #8892b0; background-color: #0f3460; "
            "border-radius: 10px; padding: 12px;"
        )

        right_layout.addWidget(sys_header)
        right_layout.addWidget(self._status_card)
        right_layout.addWidget(self._fps_card)
        right_layout.addWidget(self._detected_card)
        right_layout.addWidget(self._handedness_card)
        right_layout.addWidget(self._confidence_card)
        right_layout.addWidget(self._gesture_card)
        right_layout.addWidget(self._voice_status_card)
        right_layout.addWidget(self._voice_phrase_card)
        right_layout.addWidget(self._voice_action_card)
        right_layout.addWidget(self._cursor_card)
        right_layout.addStretch()
        right_layout.addWidget(info_label)
        right_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        status_scroll = QScrollArea()
        status_scroll.setWidgetResizable(True)
        status_scroll.setFrameShape(QFrame.NoFrame)
        status_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        status_scroll.setFixedWidth(320)
        status_scroll.setWidget(right_panel)

        root.addWidget(left_panel, 1)
        root.addWidget(status_scroll)

        status_bar = QStatusBar()
        status_bar.setStyleSheet(
            "background-color: #0f3460; color: #8892b0; border-top: 1px solid #16213e;"
        )
        status_bar.showMessage(f"Welcome to {CONFIG.APP_NAME}")
        self.setStatusBar(status_bar)

    # ================================================================
    # Worker + voice lifecycles
    # ================================================================
    def _start_worker(self):
        if self._worker is not None:
            old_worker = self._worker
            try:
                old_worker.stop()
            except Exception:
                pass
            if old_worker.isRunning():
                message = "Previous camera worker is still running; restart skipped."
                self.statusBar().showMessage(message)
                self._history.error("Camera worker lifecycle", message)
                return
            self._worker = None
        self._worker = VideoWorker(self)
        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.detection_updated.connect(self._on_detection_updated)
        self._worker.gesture_updated.connect(self._on_gesture_updated)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.fps_updated.connect(self._on_fps_updated)
        self._worker.cursor_move_requested.connect(self._on_cursor_move)
        self._worker.cursor_click_requested.connect(self._on_cursor_click)
        self._worker.cursor_scroll_requested.connect(self._on_cursor_scroll)
        self._worker.cursor_drag_requested.connect(self._on_cursor_drag)
        self._status_card.set_value("Starting...")
        self._status_card.set_value_color("#ffb86c")
        self._fps_card.set_value("Starting...")
        self._fps_card.set_value_color("#ffb86c")
        self._detected_card.set_value("Waiting...")
        self._worker.start()
        self._history.system("Camera pipeline", "VideoWorker thread started")

    def _start_voice(self):
        if self._voice_listener is not None:
            old_listener = self._voice_listener
            try:
                old_listener.stop()
            except Exception:
                pass
            if old_listener.isRunning():
                message = "Previous voice listener is still stopping; restart skipped."
                self.statusBar().showMessage(message)
                self._history.error("Voice listener lifecycle", message)
                return
            self._voice_listener = None
        self._voice_listener = VoiceListener(self)
        self._voice_listener.phrase_recognized.connect(self._on_voice_phrase)
        self._voice_listener.status_changed.connect(self._on_voice_status)
        self._voice_listener.partial_status.connect(self._on_voice_status)
        self._voice_listener.error_occurred.connect(self._on_voice_error)
        if self._voice_enabled:
            self._voice_listener.start()
            self._history.system("Voice listener", "Microphone listener thread started")
        else:
            self._on_voice_status("Voice: Disabled")

    # ================================================================
    # Window geometry (save + restore)
    # ================================================================
    def _restore_window_position(self) -> None:
        x = int(CONFIG.WINDOW_POS_X)
        y = int(CONFIG.WINDOW_POS_Y)
        if 0 <= x and 0 <= y:
            self.move(x, y)
        w = int(CONFIG.WINDOW_WIDTH)
        h = int(CONFIG.WINDOW_HEIGHT)
        if w > 0 and h > 0 and not CONFIG.WINDOW_STATE_MAXIMIZED:
            self.resize(w, h)
        if CONFIG.WINDOW_STATE_MAXIMIZED:
            self.setWindowState(Qt.WindowMaximized)

    def _save_window_geometry(self) -> None:
        is_max = bool(self.isMaximized())
        CONFIG.WINDOW_STATE_MAXIMIZED = is_max
        if not is_max:
            CONFIG.WINDOW_WIDTH = int(max(640, self.width()))
            CONFIG.WINDOW_HEIGHT = int(max(480, self.height()))
            pos = self.pos()
            CONFIG.WINDOW_POS_X = int(pos.x())
            CONFIG.WINDOW_POS_Y = int(pos.y())
        try:
            save_settings()
        except Exception:
            pass

    # ================================================================
    # Menu actions (state setters)
    # ================================================================
    def _set_close_to_tray(self, on: bool) -> None:
        CONFIG.CLOSE_TO_TRAY = bool(on)
        try:
            save_settings()
        except Exception:
            pass

    def _set_global_hotkeys(self, on: bool) -> None:
        CONFIG.TRAY_GLOBAL_HOTKEYS = bool(on)
        try:
            save_settings()
        except Exception:
            pass
        if on and self._tray is not None:
            try:
                self._tray.install_global_shortcuts(self)
            except Exception:
                pass
        self.statusBar().showMessage(
            f"Global hotkeys {'on' if on else 'off'}; restart app for change to apply fully."
        )

    def _show_onboarding_again(self) -> None:
        CONFIG.ONBOARDING_DONE = False
        try:
            save_settings()
        except Exception:
            pass
        self.statusBar().showMessage(
            "First-run wizard will run next time you launch AirControl OS."
        )

    # ================================================================
    # Toggles
    # ================================================================
    def _toggle_pause(self) -> None:
        w = self._worker
        if w is None:
            return
        w._paused = not getattr(w, "_paused", False)
        paused = w._paused
        label = CONFIG.SYSTEM_STATUS_PAUSED if paused else CONFIG.SYSTEM_STATUS_ACTIVE
        self._status_card.set_value(label)
        self._status_card.set_value_color("#e94560" if paused else "#53d397")
        self.statusBar().showMessage(f"Toggled: {label}")
        try:
            gtype = GestureType.FIST_PAUSED if paused else GestureType.CURSOR_MOVE
            self._gesture_card.set_value(gtype.value)
            self._gesture_card.set_value_color(
                _GESTURE_COLORS.get(gtype.name, "#ccd6f6")
            )
        except Exception:
            pass
        self._history.system(
            "Pause toggle", f"User requested: {label}", success=True
        )
        self.gesture_state_toggled.emit(label, not paused, "SYSTEM")

    def _toggle_voice(self) -> None:
        self._voice_enabled = not self._voice_enabled
        if self._voice_enabled:
            if self._voice_listener is not None and (
                not self._voice_listener.isRunning()
            ):
                self._start_voice()
            else:
                self._on_voice_status("Voice: Enabled")
        else:
            if self._voice_listener is not None:
                self._voice_listener.stop()
            self._on_voice_status("Voice: Disabled")
        self.statusBar().showMessage(
            f"Voice {'on' if self._voice_enabled else 'off'} (V to toggle)"
        )
        self._history.system(
            "Voice toggle", f"User requested voice {'on' if self._voice_enabled else 'off'}"
        )
        if self._tray is not None:
            try:
                self._tray.set_voice_status(
                    "Active" if self._voice_enabled else "Disabled"
                )
            except Exception:
                pass

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _restore_defaults(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        from ..core.persistence import reset_defaults

        confirm = QMessageBox.question(
            self,
            "Restore defaults?",
            "This will clear all saved settings, window geometry, and onboarding state "
            "and restart camera + voice.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        reset_defaults()
        self._start_worker()
        self._start_voice()
        self.resize(CONFIG.WINDOW_WIDTH, CONFIG.WINDOW_HEIGHT)
        self.statusBar().showMessage("Restored defaults. Restarted camera and voice.")
        self._history.system("Restore defaults", "All settings reset to factory defaults.")

    # ================================================================
    # Menubar Help helpers
    # ================================================================
    def _show_settings_location(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        from ..core.persistence import SETTINGS_PATH

        QMessageBox.information(
            self,
            "Settings location",
            f"Your settings are saved in JSON format at:\n\n{SETTINGS_PATH}\n\n"
            "You can edit it by hand, or use the Settings dialog (Ctrl+,).",
        )

    # ================================================================
    # Settings-applied handler
    # ================================================================
    def _on_settings_applied(self) -> None:
        self._cursor.set_smoothing(GESTURE_CONFIG.CURSOR_SMOOTHING_FACTOR)
        try:
            self._start_worker()
        except Exception as e:
            self.statusBar().showMessage(f"Restarting camera failed: {e}")
        try:
            self._start_voice()
        except Exception as e:
            self.statusBar().showMessage(f"Restarting voice failed: {e}")
        try:
            save_settings()
        except Exception:
            pass
        self.statusBar().showMessage(
            "Settings applied and saved. Camera + voice restarted."
        )
        self._history.system("Settings apply", "Saved settings, restarted camera and voice.")
        self.settings_applied_signal.emit()

    # ================================================================
    # Signal slots (from workers)
    # ================================================================
    def _on_frame_ready(self, frame):
        self._video_display.update_frame(frame)
        if frame is not None:
            self._fps_card.set_value("Connected")
            self._fps_card.set_value_color("#64ffda")

    def _on_detection_updated(self, result: DetectionResult):
        if result.success:
            self._detected_card.set_value("Detected")
            self._detected_card.set_value_color("#53d397")
            self._handedness_card.set_value(result.handedness)
            self._confidence_card.set_value(f"{result.confidence * 100:.1f}%")
        else:
            self._detected_card.set_value("No hand")
            self._detected_card.set_value_color("#8892b0")
            self._handedness_card.set_value("-")
            self._confidence_card.set_value("-")

    def _on_gesture_updated(self, gesture_label: str, is_active: bool, gesture_name: str):
        self._status_card.set_value(
            CONFIG.SYSTEM_STATUS_ACTIVE if is_active else CONFIG.SYSTEM_STATUS_PAUSED
        )
        self._status_card.set_value_color(
            "#53d397" if is_active else "#e94560"
        )
        color = _GESTURE_COLORS.get(gesture_name, "#ccd6f6")
        self._gesture_card.set_value(gesture_label)
        self._gesture_card.set_value_color(color)

        identifier = f"{gesture_name}:{is_active}"
        if identifier != self._last_gesture_identifier:
            self._last_gesture_identifier = identifier
            if gesture_name not in (GestureType.NONE.name, GestureType.CURSOR_MOVE.name):
                detail = ""
                if gesture_name == GestureType.PINCH_CLICK.name:
                    detail = "Left click (pinch)"
                    self._history.gesture("Left click", detail, True)
                elif gesture_name == GestureType.RIGHT_CLICK.name:
                    detail = "Right click (V-shape)"
                    self._history.gesture("Right click", detail, True)
                elif gesture_name == GestureType.DRAGGING.name:
                    detail = "Held pinch → mouseDown drag active"
                    self._history.gesture("Drag start", detail, True)
                elif gesture_name in (GestureType.SCROLL_UP.name, GestureType.SCROLL_DOWN.name):
                    direction = "up" if "Up" in gesture_name else "down"
                    self._history.gesture(f"Scroll {direction}", "Hand vertical motion", True)
                elif gesture_name == GestureType.FIST.name:
                    self._history.gesture("Pause toggle request", "Fist detected", True)
                elif gesture_name == GestureType.FIST_PAUSED.name:
                    self._history.gesture("Paused", "Fist paused", True)

        self.gesture_state_toggled.emit(gesture_label, bool(is_active), gesture_name)
        if self._tray is not None:
            try:
                self._tray.set_active(bool(is_active))
            except Exception:
                pass

    def _on_voice_phrase(self, phrase: str):
        self._voice_phrase_card.set_value(f'"{phrase}"')
        self._voice_phrase_card.set_value_color("#64ffda")
        result = self._voice_executor.execute(phrase)
        if result.matched:
            self._voice_action_card.set_value(result.message)
            self._voice_action_card.set_value_color("#53d397")
            self.statusBar().showMessage(f"Voice: {result.message}")
            self._history.voice(result.action or "voice:matched", f"{phrase} → {result.message}", True)
        else:
            self._voice_action_card.set_value(result.message)
            self._voice_action_card.set_value_color("#ffb86c")
            self._history.voice("Unmatched", f"Heard: {phrase}", False)
        if self._tray is not None:
            try:
                self._tray.show_message(
                    "Voice command",
                    phrase + (" → " + result.message if result.matched else " (no match)"),
                    timeout_ms=2500,
                )
            except Exception:
                pass

    def _on_voice_status(self, status: str):
        text = status.replace("Voice: ", "") if status.startswith("Voice:") else status
        self._voice_status_card.set_value(text)
        color = "#64ffda"
        if "Error" in text:
            color = "#e94560"
        elif "Unavailable" in text or "Stopped" in text or "Disabled" in text:
            color = "#8892b0"
        elif "Calibr" in text:
            color = "#ffb86c"
        elif "Hearing" in text or "Recognizing" in text:
            color = "#f1fa8c"
        self._voice_status_card.set_value_color(color)
        if self._last_voice_label != text:
            self._last_voice_label = text
            if text in ("Listening", "Calibrating...", "Hearing...", "Recognizing..."):
                pass
            elif text in ("Error", "Unavailable", "Stopped", "Disabled"):
                self._history.system("Voice state", f"Voice status: {text}", success=("Error" not in text and "Unavailable" not in text))
        if self._tray is not None:
            try:
                self._tray.set_voice_status(text)
            except Exception:
                pass

    def _on_voice_error(self, msg: str):
        self.statusBar().showMessage(msg)
        self._voice_status_card.set_value("Error")
        self._voice_status_card.set_value_color("#e94560")
        self._history.error("Voice listener error", msg)

    def _on_fps_updated(self, fps: int):
        self._fps_card.set_value(f"Connected | {fps} FPS")
        self._fps_card.set_value_color("#64ffda")

    def _on_error(self, msg: str):
        self.statusBar().showMessage(msg)
        lowered = msg.lower()
        if "failed to open camera" in lowered or "camera error" in lowered:
            self._video_display.update_frame(None)
            self._fps_card.set_value("Offline")
            self._fps_card.set_value_color("#e94560")
            self._detected_card.set_value("Unavailable")
            self._detected_card.set_value_color("#e94560")
            self._status_card.set_value("Camera Offline")
            self._status_card.set_value_color("#e94560")
        else:
            self._status_card.set_value("Tracking Error")
            self._status_card.set_value_color("#ffb86c")
        self._history.error("Camera pipeline", msg)

    def _on_cursor_move(self, norm_x: float, norm_y: float) -> None:
        if self._cursor.available:
            self._cursor.move(norm_x, norm_y)

    def _on_cursor_click(self, button: str) -> None:
        if button == "left":
            self._cursor.left_click()
        else:
            self._cursor.right_click()

    def _on_cursor_scroll(self, delta: int) -> None:
        self._cursor.scroll(delta)

    def _on_cursor_drag(self, started: bool) -> None:
        if started:
            self._cursor.start_drag()
        else:
            self._cursor.stop_drag()

    # ================================================================
    # Close event
    # ================================================================
    def closeEvent(self, event) -> None:
        close_to_tray = bool(CONFIG.CLOSE_TO_TRAY)
        if close_to_tray and event.spontaneous():
            self._save_window_geometry()
            try:
                save_settings()
            except Exception:
                pass
            self.request_hide.emit()
            event.ignore()
            return
        try:
            self._save_window_geometry()
            save_settings()
        except Exception:
            pass
        if self._worker is not None:
            self._worker.stop()
            if self._worker.isRunning():
                self.statusBar().showMessage(
                    "Waiting for the camera worker to stop before closing."
                )
                event.ignore()
                return
        if self._voice_listener is not None:
            self._voice_listener.stop()
            if self._voice_listener.isRunning():
                self.statusBar().showMessage(
                    "Waiting for the voice listener to stop before closing."
                )
                event.ignore()
                return
        self._history.system("Shutdown", "Main window closed", True)
        try:
            save_settings()
        except Exception:
            pass
        super().closeEvent(event)
        event.accept()
