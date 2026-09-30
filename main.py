from PySide6.QtCore import Qt, QTimer
import sys
import os

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from aircontrol.gui.main_window import MainWindow
from aircontrol.gui.onboarding_wizard import OnboardingWizard
from aircontrol.gui.tray_manager import TrayManager
from aircontrol.gui.log_dialog import LogDialog
from aircontrol.gui.help_dialog import HelpDialog
from aircontrol.gui.settings_dialog import SettingsDialog
from aircontrol.core.config import CONFIG
from aircontrol.core.persistence import load_and_apply, save_settings


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(CONFIG.APP_NAME)
    app.setApplicationVersion(CONFIG.APP_VERSION)
    app.setQuitOnLastWindowClosed(False)

    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)

    load_and_apply()
    CONFIG.FRAME_SKIP_EVERY_N = 1

    launch_minimized = False
    if not CONFIG.ONBOARDING_DONE:
        wizard = OnboardingWizard()
        accepted = wizard.exec()
        if accepted != OnboardingWizard.Accepted:
            CONFIG.ONBOARDING_DONE = False
        else:
            CONFIG.ONBOARDING_DONE = True
            launch_minimized = bool(getattr(wizard, "launch_minimized_to_tray", False))
        try:
            save_settings()
        except Exception:
            pass

    tray = TrayManager()
    if tray.supported():
        tray.show()

    window = MainWindow()
    window.set_tray_manager(tray)

    _log_dialog = None
    _help_dialog = None
    _settings_dialog = None

    def show_window() -> None:
        if not window.isVisible():
            window.show()
        if window.isMinimized():
            window.showNormal()
        window.raise_()
        window.activateWindow()

    def hide_window() -> None:
        if CONFIG.CLOSE_TO_TRAY and tray.supported():
            tray.show_message(
                f"{CONFIG.APP_NAME} still running",
                f"Minimized to tray. Use {'Ctrl+Alt+S' if tray.supported() else 'the tray menu.'}",
                timeout_ms=3000,
            )
            window.hide()
        else:
            window.showMinimized()

    def quit_app() -> None:
        if not window.close():
            QTimer.singleShot(250, quit_app)
            return
        try:
            window._save_window_geometry()
            save_settings()
        except Exception:
            pass
        app.quit()

    tray.toggle_pause_requested.connect(window._toggle_pause)
    tray.toggle_voice_requested.connect(window._toggle_voice)
    tray.show_main_requested.connect(show_window)
    tray.hide_main_requested.connect(hide_window)
    tray.quit_requested.connect(quit_app)

    def open_settings() -> None:
        nonlocal _settings_dialog
        show_window()
        if _settings_dialog is None or not _settings_dialog.isVisible():
            _settings_dialog = SettingsDialog(window)
            _settings_dialog.settings_applied.connect(window._on_settings_applied)
        _settings_dialog.show()
        _settings_dialog.raise_()
        _settings_dialog.activateWindow()

    def open_log() -> None:
        nonlocal _log_dialog
        show_window()
        if _log_dialog is None or not _log_dialog.isVisible():
            from aircontrol.core.action_history import HISTORY

            _log_dialog = LogDialog(HISTORY, window)
        _log_dialog.show()
        _log_dialog.raise_()
        _log_dialog.activateWindow()

    def open_help() -> None:
        nonlocal _help_dialog
        show_window()
        if _help_dialog is None or not _help_dialog.isVisible():
            _help_dialog = HelpDialog(window)
        _help_dialog.show()
        _help_dialog.raise_()
        _help_dialog.activateWindow()

    tray.open_settings_requested.connect(open_settings)
    tray.open_log_requested.connect(open_log)
    tray.open_help_requested.connect(open_help)

    window.request_open_settings.connect(open_settings)
    window.request_open_log.connect(open_log)
    window.request_open_help.connect(open_help)

    window.request_hide.connect(hide_window)
    window.request_quit.connect(quit_app)

    window.settings_applied_signal.connect(lambda: tray.show_message(
        "Settings saved", "Camera and voice have been restarted.",
        timeout_ms=2500,
    ))

    def update_tray_active(gesture_label: str, is_active: bool, gesture_name: str) -> None:
        tray.set_active(bool(is_active))

    window._worker_state_active = True

    window.gesture_state_toggled.connect(update_tray_active)

    if CONFIG.TRAY_GLOBAL_HOTKEYS:
        try:
            tray.install_global_shortcuts(window)
        except Exception:
            pass

    if launch_minimized and tray.supported():
        tray.show_message(
            f"Welcome to {CONFIG.APP_NAME}",
            "Launched in tray. Double-click the tray icon to open the window.",
            timeout_ms=4000,
        )
        window.hide()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
