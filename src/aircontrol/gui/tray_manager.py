from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QPainter,
    QPixmap,
    QFont,
    QBrush,
    QLinearGradient,
    QCursor,
    QShortcut,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QMenu,
    QSystemTrayIcon,
    QWidget,
    QApplication,
)


def _make_tray_icon(color: str = "#53d397") -> QIcon:
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#533483"))
    grad.setColorAt(1.0, QColor(color))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Segoe UI", 28, QFont.Bold))
    p.drawText(pm.rect(), Qt.AlignCenter, "✋")
    p.end()
    return QIcon(pm)


class TrayManager(QObject):
    toggle_pause_requested = Signal()
    toggle_voice_requested = Signal()
    show_main_requested = Signal()
    hide_main_requested = Signal()
    open_settings_requested = Signal()
    open_log_requested = Signal()
    open_help_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._icon_active = _make_tray_icon("#53d397")
        self._icon_paused = _make_tray_icon("#e94560")

        self._tray = QSystemTrayIcon(self._icon_active, parent)
        self._tray.setToolTip("AirControl OS — Active")
        self._menu: Optional[QMenu] = None
        self._build_menu()
        self._tray.activated.connect(self._on_activated)

        self._global_shortcuts: list = []

    @staticmethod
    def supported() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def install_global_shortcuts(
        self,
        context_widget: QWidget,
        pause_seq: str = "Ctrl+Alt+P",
        voice_seq: str = "Ctrl+Alt+V",
        show_seq: str = "Ctrl+Alt+S",
    ) -> None:
        if context_widget is None:
            return
        for sc in self._global_shortcuts:
            try:
                sc.setEnabled(False)
                sc.deleteLater()
            except Exception:
                pass
        self._global_shortcuts.clear()

        def add(seq_str: str, cb: Callable[[], None]) -> None:
            sc = QShortcut(QKeySequence(seq_str), context_widget)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(cb)
            self._global_shortcuts.append(sc)

        try:
            add(pause_seq, lambda: self.toggle_pause_requested.emit())
            add(voice_seq, lambda: self.toggle_voice_requested.emit())
            add(show_seq, lambda: self.show_main_requested.emit())
        except Exception:
            pass

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background-color: #0f3460; color: #ccd6f6; border: 1px solid #533483;"
            "border-radius: 8px; padding: 6px; font-family: Segoe UI; font-size: 10pt; }"
            "QMenu::item { padding: 8px 22px; border-radius: 5px; }"
            "QMenu::item:selected { background: #533483; color: #ccd6f6; }"
            "QMenu::separator { height: 1px; background: #16213e; margin: 5px 5px; }"
        )

        act_show = QAction("Show / Hide Window", menu)
        act_show.triggered.connect(self._toggle_show_hide)
        menu.addAction(act_show)

        act_pause = QAction("Toggle Pause (Ctrl+Alt+P)", menu)
        act_pause.triggered.connect(lambda: self.toggle_pause_requested.emit())
        menu.addAction(act_pause)

        act_voice = QAction("Toggle Voice (Ctrl+Alt+V)", menu)
        act_voice.triggered.connect(lambda: self.toggle_voice_requested.emit())
        menu.addAction(act_voice)

        menu.addSeparator()
        act_settings = QAction("Settings... (Ctrl+,)", menu)
        act_settings.triggered.connect(lambda: self.open_settings_requested.emit())
        menu.addAction(act_settings)

        act_log = QAction("Activity Log", menu)
        act_log.triggered.connect(lambda: self.open_log_requested.emit())
        menu.addAction(act_log)

        act_help = QAction("Help & Cheatsheet (F1)", menu)
        act_help.triggered.connect(lambda: self.open_help_requested.emit())
        menu.addAction(act_help)

        menu.addSeparator()
        act_quit = QAction("Quit AirControl", menu)
        act_quit.triggered.connect(lambda: self.quit_requested.emit())
        menu.addAction(act_quit)

        self._menu = menu
        self._tray.setContextMenu(self._menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        try:
            from PySide6.QtWidgets import QSystemTrayIcon as _T

            if reason in (_T.Trigger, _T.DoubleClick):
                self._toggle_show_hide()
        except Exception:
            pass

    def _toggle_show_hide(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        top = None
        for w in app.topLevelWidgets():
            if hasattr(w, "_start_worker"):
                top = w
                break
        if top is None:
            self.show_main_requested.emit()
            return
        if top.isVisible() and top.isWindow():
            try:
                if top.isMinimized():
                    top.showNormal()
                    top.raise_()
                    top.activateWindow()
                else:
                    self.hide_main_requested.emit()
            except Exception:
                self.show_main_requested.emit()
        else:
            self.show_main_requested.emit()

    def show(self) -> None:
        if self.supported():
            self._tray.show()

    def hide(self) -> None:
        try:
            self._tray.hide()
        except Exception:
            pass

    def show_message(
        self,
        title: str,
        body: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information,
        timeout_ms: int = 4000,
    ) -> None:
        if not self.supported():
            return
        try:
            self._tray.showMessage(title, body, icon, timeout_ms)
        except Exception:
            pass

    def set_active(self, active: bool) -> None:
        if active:
            self._tray.setIcon(self._icon_active)
            self._tray.setToolTip("AirControl OS — Active")
        else:
            self._tray.setIcon(self._icon_paused)
            self._tray.setToolTip("AirControl OS — PAUSED")

    def set_voice_status(self, text: str) -> None:
        try:
            tip = f"AirControl OS — Voice: {text}"
            cur = self._tray.toolTip()
            if cur.startswith("AirControl OS — PAUSED"):
                tip = f"AirControl OS — PAUSED  •  Voice: {text}"
            self._tray.setToolTip(tip)
        except Exception:
            pass
