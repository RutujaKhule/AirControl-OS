import cv2
import logging
import numpy as np
import time
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker
from typing import Optional

from ..core.camera import CameraCapture
from ..core.config import CONFIG, GESTURE_CONFIG
from ..core.cursor_controller import CursorController
from ..gesture.hand_detector import HandDetector, DetectionResult
from ..gesture.recognizer import (
    GestureRecognizer,
    GestureResult,
    GestureType,
)
from ..utils.cooldown import CooldownManager

logger = logging.getLogger(__name__)


class VideoWorker(QThread):
    frame_ready = Signal(np.ndarray)
    detection_updated = Signal(object)
    error_occurred = Signal(str)
    fps_updated = Signal(int)
    gesture_updated = Signal(str, bool, str)
    cursor_move_requested = Signal(float, float)
    cursor_click_requested = Signal(str)
    cursor_scroll_requested = Signal(int)
    cursor_drag_requested = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera = CameraCapture()
        self._detector = HandDetector()
        self._recognizer = GestureRecognizer()
        self._cursor = CursorController()
        self._cooldowns = CooldownManager()

        self._running = False
        self._mutex = QMutex()
        self._fps_counter = 0
        self._fps_timer_start = 0.0
        self._frame_skip_counter = 0
        self._paused = False
        self._fist_held_since: Optional[float] = None
        self._fist_toggle_armed = True
        self._last_was_dragging = False
        self._last_right_click_state = False

    def run(self):
        try:
            try:
                camera_opened = self._camera.open()
            except Exception as e:
                logger.exception("VideoWorker failed while opening the camera")
                self.error_occurred.emit(f"Camera error: {e}")
                return
            if not camera_opened:
                logger.error("VideoWorker could not open the camera")
                self.error_occurred.emit(
                    "Failed to open camera. Please check your webcam connection."
                )
                return

            self._running = True
            self._fps_counter = 0
            self._fps_timer_start = time.time()
            self._emit_gesture(GestureType.NONE, is_active=True)
            consecutive_read_failures = 0

            while self._running:
                frame = None
                try:
                    ret, frame = self._camera.read()
                    if not ret or frame is None:
                        consecutive_read_failures += 1
                        if consecutive_read_failures == 1 or consecutive_read_failures % 100 == 0:
                            logger.warning(
                                "Camera read failed (%s consecutive failures)",
                                consecutive_read_failures,
                            )
                        self.msleep(10)
                        continue

                    if consecutive_read_failures:
                        logger.info(
                            "Camera reads recovered after %s failures",
                            consecutive_read_failures,
                        )
                        consecutive_read_failures = 0

                    self._frame_skip_counter += 1
                    if self._frame_skip_counter % CONFIG.FRAME_SKIP_EVERY_N != 0:
                        continue

                    result: DetectionResult = self._detector.detect(frame)
                    gesture: GestureResult = self._recognizer.recognize(
                        result, paused=self._paused
                    )

                    self._handle_pause_toggle(gesture)
                    self._handle_cursor_actions(gesture)
                    self._handle_scroll(gesture)

                    display_frame = self._detector.draw_landmarks(frame, result)
                    display_frame = self._overlay_gesture_label(display_frame, gesture)

                    self.detection_updated.emit(result)
                    self.frame_ready.emit(display_frame)
                    self._emit_gesture(gesture.gesture)

                    self._fps_counter += 1
                    elapsed = time.time() - self._fps_timer_start
                    if elapsed >= 1.0:
                        fps = int(self._fps_counter / elapsed)
                        self.fps_updated.emit(fps)
                        self._fps_counter = 0
                        self._fps_timer_start = time.time()

                except Exception as e:
                    logger.exception("VideoWorker frame processing failed; continuing")
                    if frame is not None:
                        self.frame_ready.emit(frame)
                    self.error_occurred.emit(f"Processing error: {e}")
                    self.msleep(50)
                    continue

                self.msleep(2)
        except Exception as e:
            logger.exception("VideoWorker terminated unexpectedly")
            self.error_occurred.emit(f"Camera worker stopped unexpectedly: {e}")
        finally:
            self._running = False
            try:
                self._cursor.release_drag()
            except Exception:
                logger.exception("Failed to release cursor drag during worker shutdown")
            try:
                self._camera.close()
            except Exception:
                logger.exception("Failed to close camera during worker shutdown")
            try:
                self._detector.close()
            except Exception:
                logger.exception("Failed to close hand detector during worker shutdown")
            logger.info("VideoWorker stopped")

    def _handle_pause_toggle(self, gesture: GestureResult) -> None:
        now = time.monotonic()
        if not gesture.is_fist:
            self._fist_held_since = None
            self._fist_toggle_armed = True
            return
        if not self._fist_toggle_armed:
            return

        if gesture.is_fist:
            if self._fist_held_since is None:
                self._fist_held_since = now
            held_ms = (now - self._fist_held_since) * 1000.0
            if (
                held_ms >= GESTURE_CONFIG.FIST_HOLD_MS_FOR_PAUSE
                and self._cooldowns.try_trigger(
                    "pause_toggle", GESTURE_CONFIG.PAUSE_TOGGLE_COOLDOWN_MS
                )
            ):
                self._paused = not self._paused
                self._fist_held_since = None
                self._fist_toggle_armed = False
                if self._paused:
                    self._cursor.release_drag()
                self._recognizer.reset_state()

    def _handle_cursor_actions(self, gesture: GestureResult) -> None:
        if self._paused:
            if self._last_was_dragging:
                self._cursor.stop_drag()
                self._last_was_dragging = False
            return

        if gesture.cursor_position is not None:
            nx, ny = gesture.cursor_position
            self.cursor_move_requested.emit(float(nx), float(ny))

        is_dragging = gesture.gesture == GestureType.DRAGGING
        if is_dragging and not self._last_was_dragging:
            self._cursor.start_drag()
            self.cursor_drag_requested.emit(True)
        elif not is_dragging and self._last_was_dragging:
            self._cursor.stop_drag()
            self.cursor_drag_requested.emit(False)
        self._last_was_dragging = is_dragging

        if (
            gesture.gesture == GestureType.PINCH_CLICK
            and not is_dragging
            and self._cooldowns.try_trigger("click", CONFIG.PINCH_CLICK_COOLDOWN_MS)
        ):
            self.cursor_click_requested.emit("left")

        if gesture.gesture == GestureType.RIGHT_CLICK and self._cooldowns.try_trigger(
            "right_click", GESTURE_CONFIG.RIGHT_CLICK_COOLDOWN_MS
        ):
            self.cursor_click_requested.emit("right")

    def _handle_scroll(self, gesture: GestureResult) -> None:
        if self._paused:
            return
        delta = gesture.scroll_delta
        if abs(delta) < 1.0:
            return
        if not self._cooldowns.can_trigger("scroll", GESTURE_CONFIG.SCROLL_COOLDOWN_MS):
            return
        self._cooldowns.mark_triggered("scroll")
        self.cursor_scroll_requested.emit(int(delta))

    def _emit_gesture(self, gtype: GestureType, is_active: Optional[bool] = None) -> None:
        active = (not self._paused) if is_active is None else is_active
        self.gesture_updated.emit(gtype.value, active, gtype.name)

    def _overlay_gesture_label(
        self, frame: np.ndarray, gesture: GestureResult
    ) -> np.ndarray:
        if frame is None:
            return frame
        out = frame.copy()
        h, w = out.shape[:2]
        label = gesture.gesture.value
        if self._paused:
            label = "PAUSED — hold fist to resume"
            color = (80, 80, 255)
        else:
            color = (0, 255, 170)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
        pad = 14
        x = 18
        y = 18
        cv2.rectangle(
            out,
            (x - 2, y - 2),
            (x + tw + pad, y + th + pad),
            (15, 33, 62),
            -1,
        )
        cv2.rectangle(
            out,
            (x - 2, y - 2),
            (x + tw + pad, y + th + pad),
            (15, 52, 96),
            2,
        )
        cv2.putText(
            out,
            label,
            (x + pad // 2, y + th + pad // 2 - 2),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )
        return out

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(2000)
