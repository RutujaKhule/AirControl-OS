import cv2
import mediapipe as mp
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
from ..core.config import CONFIG


@dataclass
class HandLandmark:
    x: float
    y: float
    z: float
    visibility: float


@dataclass
class DetectionResult:
    success: bool
    landmarks: List[HandLandmark]
    handedness: str
    confidence: float
    num_hands_detected: int


class HandDetector:
    def __init__(self):
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=CONFIG.MP_MAX_NUM_HANDS,
            model_complexity=CONFIG.MP_MODEL_COMPLEXITY,
            min_detection_confidence=CONFIG.MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=CONFIG.MP_MIN_TRACKING_CONFIDENCE,
        )
        self._last_result: Optional[DetectionResult] = None

    def close(self) -> None:
        self._hands.close()

    def detect(self, frame: np.ndarray) -> DetectionResult:
        if frame is None:
            return DetectionResult(False, [], "", 0.0, 0)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self._hands.process(rgb_frame)
        rgb_frame.flags.writeable = True

        if not results.multi_hand_landmarks:
            self._last_result = DetectionResult(False, [], "", 0.0, 0)
            return self._last_result

        num_hands = len(results.multi_hand_landmarks)
        # Always use the first (largest/most prominent) hand for control.
        # Multi-hand situations are handled safely by only using index 0.
        hand_landmarks = results.multi_hand_landmarks[0]

        landmarks: List[HandLandmark] = []
        for lm in hand_landmarks.landmark:
            landmarks.append(
                HandLandmark(
                    x=float(lm.x),
                    y=float(lm.y),
                    z=float(lm.z),
                    visibility=float(getattr(lm, "visibility", 1.0)),
                )
            )

        handedness = "Right"
        confidence = 0.0
        if results.multi_handedness:
            classification = results.multi_handedness[0].classification[0]
            handedness = classification.label
            confidence = float(classification.score)

        self._last_result = DetectionResult(
            success=True,
            landmarks=landmarks,
            handedness=handedness,
            confidence=confidence,
            num_hands_detected=num_hands,
        )
        return self._last_result

    def draw_landmarks(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        if frame is None:
            return frame
        output = frame.copy()
        if not result.success or not result.landmarks:
            return output

        h, w, _ = output.shape
        landmark_points = []
        for lm in result.landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            landmark_points.append((cx, cy))

        connections = self._mp_hands.HAND_CONNECTIONS
        for conn in connections:
            pt1 = landmark_points[conn[0]]
            pt2 = landmark_points[conn[1]]
            cv2.line(
                output,
                pt1,
                pt2,
                CONFIG.CONNECTION_COLOR,
                CONFIG.CONNECTION_THICKNESS,
            )

        for (cx, cy) in landmark_points:
            cv2.circle(
                output,
                (cx, cy),
                CONFIG.LANDMARK_RADIUS,
                CONFIG.LANDMARK_COLOR,
                CONFIG.LANDMARK_THICKNESS,
            )

        if len(result.landmarks) > 0:
            index = result.landmarks[8]
            ix, iy = int(index.x * w), int(index.y * h)
            cv2.circle(output, (ix, iy), 12, (255, 255, 0), 2)

            thumb = result.landmarks[4]
            tx, ty = int(thumb.x * w), int(thumb.y * h)
            cv2.circle(output, (tx, ty), 12, (0, 255, 255), 2)

        return output

    def get_landmark_px(self, result: DetectionResult, idx: int, frame_shape: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        if not result.success or idx >= len(result.landmarks):
            return None
        h, w = frame_shape
        lm = result.landmarks[idx]
        return int(lm.x * w), int(lm.y * h)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
