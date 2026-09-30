from typing import Optional, Tuple

try:
    import pyautogui

    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False

from ..utils.smoothing import EMASmoother
from .config import CONFIG, GESTURE_CONFIG


class CursorController:
    def __init__(self):
        self._smoother = EMASmoother(alpha=GESTURE_CONFIG.CURSOR_SMOOTHING_FACTOR)
        self._screen_w: Optional[int] = None
        self._screen_h: Optional[int] = None
        self._margin_ratio = 0.08
        self._dragging = False
        self._deadzone = CONFIG.CURSOR_DEADZONE
        self._init_screen_size()

    def _init_screen_size(self) -> None:
        if not _HAS_PYAUTOGUI:
            self._screen_w = 1920
            self._screen_h = 1080
            return
        try:
            size = pyautogui.size()
            self._screen_w = int(size.width)
            self._screen_h = int(size.height)
        except Exception:
            self._screen_w = 1920
            self._screen_h = 1080

    def set_smoothing(self, alpha: float) -> None:
        self._smoother.set_alpha(alpha)

    def reset(self) -> None:
        self._smoother.reset()
        self.release_drag()

    def release_drag(self) -> None:
        if not _HAS_PYAUTOGUI:
            self._dragging = False
            return
        try:
            if self._dragging:
                pyautogui.mouseUp()
        except Exception:
            pass
        self._dragging = False

    @property
    def available(self) -> bool:
        return _HAS_PYAUTOGUI

    def _map_camera_to_screen(
        self, norm_x: float, norm_y: float
    ) -> Tuple[int, int]:
        assert self._screen_w is not None
        assert self._screen_h is not None
        m = self._margin_ratio
        clipped_x = max(0.0, min(1.0, float(norm_x)))
        clipped_y = max(0.0, min(1.0, float(norm_y)))
        inner_w = 1.0 - 2.0 * m
        inner_h = 1.0 - 2.0 * m
        if inner_w <= 0:
            inner_w = 1.0
        if inner_h <= 0:
            inner_h = 1.0
        local_x = (clipped_x - m) / inner_w
        local_y = (clipped_y - m) / inner_h
        local_x = max(0.0, min(1.0, local_x))
        local_y = max(0.0, min(1.0, local_y))
        sx = int(round(local_x * float(self._screen_w - 1)))
        sy = int(round(local_y * float(self._screen_h - 1)))
        return sx, sy

    def compute_position(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """Compute smoothed screen coordinates without calling pyautogui (thread-safe)."""
        smooth_x, smooth_y = self._smoother.smooth(norm_x, norm_y)
        sx, sy = self._map_camera_to_screen(smooth_x, smooth_y)
        sx = max(0, min(sx, self._screen_w - 1))
        sy = max(0, min(sy, self._screen_h - 1))
        return sx, sy

    def move(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        sx, sy = self.compute_position(norm_x, norm_y)
        self._do_pyautogui_move(sx, sy)
        return sx, sy

    def _do_pyautogui_move(self, sx: int, sy: int) -> None:
        """Call pyautogui.moveTo() - must be invoked from the main thread."""
        if not _HAS_PYAUTOGUI:
            return
        try:
            pyautogui.moveTo(sx, sy, _pause=False)
        except Exception:
            pass

    def left_click(self) -> None:
        if not _HAS_PYAUTOGUI:
            return
        try:
            pyautogui.click(button="left")
        except Exception:
            pass

    def right_click(self) -> None:
        if not _HAS_PYAUTOGUI:
            return
        try:
            pyautogui.click(button="right")
        except Exception:
            pass

    def start_drag(self) -> None:
        if not _HAS_PYAUTOGUI:
            self._dragging = True
            return
        try:
            pyautogui.mouseDown(button="left")
            self._dragging = True
        except Exception:
            self._dragging = False

    def stop_drag(self) -> None:
        self.release_drag()

    def scroll(self, clicks: float) -> None:
        if not _HAS_PYAUTOGUI:
            return
        c = int(round(clicks))
        if c == 0:
            return
        try:
            pyautogui.scroll(c)
        except Exception:
            pass
