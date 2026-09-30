import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .hand_detector import HandLandmark, DetectionResult
from ..core.config import CONFIG


class GestureType(Enum):
    NONE = "No hand detected"
    CURSOR_MOVE = "Cursor Move"
    PINCH_CLICK = "Left Click"
    RIGHT_CLICK = "Right Click"
    DRAGGING = "Dragging"
    SCROLL_UP = "Scroll Up"
    SCROLL_DOWN = "Scroll Down"
    FIST = "Fist (Pause Toggle)"
    FIST_PAUSED = "Paused (fist to resume)"


@dataclass
class GestureResult:
    gesture: GestureType
    is_pinched: bool
    is_fist: bool
    is_right_click: bool
    scroll_delta: float
    cursor_position: Optional[Tuple[float, float]]
    cursor_landmark_px: Optional[Tuple[int, int]]


class GestureRecognizer:
    def __init__(self):
        self._pinch_threshold = CONFIG.PINCH_DISTANCE_THRESHOLD
        self._scroll_sensitivity = CONFIG.SCROLL_SENSITIVITY
        self._drag_hold_ms = CONFIG.DRAG_HOLD_DURATION_MS
        self._v_spread_threshold = CONFIG.V_GESTURE_SPREAD_THRESHOLD
        self._fist_thumb_dist = CONFIG.FIST_THUMB_DISTANCE_THRESHOLD

        self._pinch_started_at: Optional[float] = None
        self._is_dragging = False

        self._last_gesture = GestureType.NONE

        self._cursor_anchor_y: Optional[float] = None
        self._cursor_anchor_last_ts: Optional[float] = None

    @staticmethod
    def _distance(a: HandLandmark, b: HandLandmark) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        dz = a.z - b.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @staticmethod
    def _landmark_distance(
        a: HandLandmark, b: HandLandmark, landmarks: List[HandLandmark]
    ) -> float:
        wrist = landmarks[0]
        ref_mcp = landmarks[5]
        palm_ref = math.sqrt(
            (wrist.x - ref_mcp.x) ** 2
            + (wrist.y - ref_mcp.y) ** 2
            + (wrist.z - ref_mcp.z) ** 2
        )
        if palm_ref < 1e-6:
            palm_ref = 0.1
        raw = math.sqrt(
            (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2
        )
        return raw / palm_ref

    @staticmethod
    def _finger_up(tip: HandLandmark, pip: HandLandmark, mcp: HandLandmark) -> bool:
        return tip.y < pip.y and pip.y < mcp.y

    def _is_pinch(self, landmarks: List[HandLandmark]) -> bool:
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        dist = self._landmark_distance(thumb_tip, index_tip, landmarks)
        return dist < self._pinch_threshold

    def _is_fist(self, landmarks: List[HandLandmark]) -> bool:
        index_up = self._finger_up(landmarks[8], landmarks[6], landmarks[5])
        middle_up = self._finger_up(landmarks[12], landmarks[10], landmarks[9])
        ring_up = self._finger_up(landmarks[16], landmarks[14], landmarks[13])
        pinky_up = self._finger_up(landmarks[20], landmarks[18], landmarks[17])
        if CONFIG.FIST_REQUIRE_ALL_FINGERS_DOWN:
            if any([index_up, middle_up, ring_up, pinky_up]):
                return False
        else:
            up_count = sum([index_up, middle_up, ring_up, pinky_up])
            if up_count >= 2:
                return False
        for tip_index, mcp_index in ((8, 5), (12, 9), (16, 13), (20, 17)):
            pip_index = mcp_index + 1
            tip_distance = self._distance(
                landmarks[tip_index], landmarks[mcp_index]
            )
            pip_distance = self._distance(landmarks[pip_index], landmarks[mcp_index])
            if tip_distance > pip_distance * 1.5:
                return False

        thumb_tip = landmarks[4]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]
        palm_mid_x = (index_mcp.x + pinky_mcp.x) / 2.0
        palm_mid_y = (index_mcp.y + pinky_mcp.y) / 2.0
        dx = thumb_tip.x - palm_mid_x
        dy = thumb_tip.y - palm_mid_y
        thumb_near = math.sqrt(dx * dx + dy * dy) < self._fist_thumb_dist
        return thumb_near

    def _is_right_click_gesture(self, landmarks: List[HandLandmark]) -> bool:
        index_up = self._finger_up(landmarks[8], landmarks[6], landmarks[5])
        middle_up = self._finger_up(landmarks[12], landmarks[10], landmarks[9])
        ring_up = self._finger_up(landmarks[16], landmarks[14], landmarks[13])
        pinky_up = self._finger_up(landmarks[20], landmarks[18], landmarks[17])
        if not (index_up and middle_up and not ring_up and not pinky_up):
            return False
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        spread = self._landmark_distance(index_tip, middle_tip, landmarks)
        return spread > self._v_spread_threshold

    def _scroll_delta(self, landmarks: List[HandLandmark], index_visible: bool) -> float:
        index_y = landmarks[8].y
        now = time.monotonic()
        if not index_visible:
            self._cursor_anchor_y = None
            self._cursor_anchor_last_ts = None
            return 0.0
        if self._cursor_anchor_y is None:
            self._cursor_anchor_y = index_y
            self._cursor_anchor_last_ts = now
            return 0.0
        anchor_age = now - (self._cursor_anchor_last_ts or 0.0)
        if anchor_age > 0.6:
            self._cursor_anchor_y = index_y
            self._cursor_anchor_last_ts = now
            return 0.0
        dy = self._cursor_anchor_y - index_y
        self._cursor_anchor_y = 0.5 * float(index_y) + 0.5 * float(self._cursor_anchor_y)
        self._cursor_anchor_last_ts = now
        dead = CONFIG.SCROLL_DEADZONE
        if abs(dy) < dead:
            return 0.0
        delta = dy * self._scroll_sensitivity * 40.0
        clamped = max(-30.0, min(30.0, delta))
        return clamped

    def reset_state(self) -> None:
        self._pinch_started_at = None
        self._is_dragging = False
        self._cursor_anchor_y = None
        self._cursor_anchor_last_ts = None
        self._fist_held_since = None
        self._right_click_held_since = None

    def recognize(
        self,
        result: DetectionResult,
        paused: bool = False,
    ) -> GestureResult:
        if not result.success or not result.landmarks:
            self.reset_state()
            self._last_gesture = GestureType.NONE
            return GestureResult(
                gesture=GestureType.NONE,
                is_pinched=False,
                is_fist=False,
                is_right_click=False,
                scroll_delta=0.0,
                cursor_position=None,
                cursor_landmark_px=None,
            )

        landmarks = result.landmarks
        index_tip = landmarks[8]
        middle_tip = landmarks[12]

        cursor_norm = (index_tip.x, index_tip.y)
        cursor_mid_norm = (
            (index_tip.x + middle_tip.x) / 2.0,
            (index_tip.y + middle_tip.y) / 2.0,
        )

        is_pinched = self._is_pinch(landmarks)
        is_fist = self._is_fist(landmarks)
        is_right_click = self._is_right_click_gesture(landmarks)

        now = time.monotonic()
        if is_pinched:
            if self._pinch_started_at is None:
                self._pinch_started_at = now
            held_ms = (now - self._pinch_started_at) * 1000.0
            if held_ms >= self._drag_hold_ms:
                self._is_dragging = True
        else:
            self._pinch_started_at = None
            self._is_dragging = False

        scroll_delta = self._scroll_delta(landmarks, index_visible=True)

        if paused:
            gesture = GestureType.FIST_PAUSED
        elif self._is_dragging:
            gesture = GestureType.DRAGGING
        elif is_fist:
            gesture = GestureType.FIST
        elif is_right_click:
            gesture = GestureType.RIGHT_CLICK
        elif is_pinched:
            gesture = GestureType.PINCH_CLICK
        elif scroll_delta > 1.0:
            gesture = GestureType.SCROLL_UP
        elif scroll_delta < -1.0:
            gesture = GestureType.SCROLL_DOWN
        else:
            gesture = GestureType.CURSOR_MOVE

        cursor_use = cursor_mid_norm if self._is_dragging else cursor_norm

        self._last_gesture = gesture
        return GestureResult(
            gesture=gesture,
            is_pinched=is_pinched,
            is_fist=is_fist,
            is_right_click=is_right_click,
            scroll_delta=scroll_delta,
            cursor_position=cursor_use,
            cursor_landmark_px=None,
        )
