from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class AppConfig:
    APP_NAME: str = "AirControl OS"
    APP_VERSION: str = "0.1.0"

    CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 1280
    CAMERA_HEIGHT: int = 720
    CAMERA_FPS: int = 30

    MP_MAX_NUM_HANDS: int = 1
    MP_MODEL_COMPLEXITY: int = 1
    MP_MIN_DETECTION_CONFIDENCE: float = 0.5
    MP_MIN_TRACKING_CONFIDENCE: float = 0.5

    LANDMARK_COLOR: Tuple[int, int, int] = (0, 255, 0)
    CONNECTION_COLOR: Tuple[int, int, int] = (255, 0, 0)
    LANDMARK_RADIUS: int = 6
    LANDMARK_THICKNESS: int = 2
    CONNECTION_THICKNESS: int = 2

    # Frame processing
    FRAME_SKIP_EVERY_N: int = 1  # Process every frame for smooth cursor tracking
    MIN_FPS_TARGET: int = 15  # Minimum FPS to maintain

    # Cursor
    CURSOR_SMOOTHING_FACTOR: float = 0.55
    CURSOR_DEADZONE: float = 0.002  # Very small deadzone for responsive tracking

    # Gesture tuning
    PINCH_DISTANCE_THRESHOLD: float = 0.06
    PINCH_CLICK_COOLDOWN_MS: int = 400
    V_GESTURE_SPREAD_THRESHOLD: float = 0.12  # Relaxed from 0.15
    FIST_THUMB_DISTANCE_THRESHOLD: float = 0.20  # Relaxed from 0.18
    FIST_REQUIRE_ALL_FINGERS_DOWN: bool = True  # Stricter fist detection
    SCROLL_DEADZONE: float = 0.012  # Relaxed from 0.008
    SCROLL_SENSITIVITY: int = 15  # Reduced from 20
    DRAG_HOLD_DURATION_MS: int = 250  # Slightly longer for reliability
    PAUSE_TOGGLE_COOLDOWN_MS: int = 1500  # Longer cooldown
    RIGHT_CLICK_COOLDOWN_MS: int = 1000  # Longer cooldown
    GESTURE_COOLDOWN_MS: int = 350  # Slightly longer

    # Window state
    WINDOW_WIDTH: int = 1100
    WINDOW_HEIGHT: int = 750
    WINDOW_STATE_MAXIMIZED: bool = False
    WINDOW_POS_X: int = -1
    WINDOW_POS_Y: int = -1
    ONBOARDING_DONE: bool = False
    MINIMIZE_TO_TRAY: bool = True
    CLOSE_TO_TRAY: bool = True
    TRAY_GLOBAL_HOTKEYS: bool = True
    SYSTEM_STATUS_PAUSED: str = "PAUSED"
    SYSTEM_STATUS_ACTIVE: str = "ACTIVE"


@dataclass
class GestureConfig:
    GESTURE_COOLDOWN_MS: int = 300
    PINCH_DISTANCE_THRESHOLD: float = 0.05
    CURSOR_SMOOTHING_FACTOR: float = 0.6
    SCROLL_SENSITIVITY: int = 20
    DRAG_HOLD_DURATION_MS: int = 200
    PAUSE_TOGGLE_COOLDOWN_MS: int = 1200
    RIGHT_CLICK_COOLDOWN_MS: int = 800
    SCROLL_COOLDOWN_MS: int = 60
    FIST_HOLD_MS_FOR_PAUSE: int = 350


@dataclass
class VoiceConfig:
    ENERGY_THRESHOLD: int = 300
    PAUSE_THRESHOLD: float = 0.8
    PHRASE_TIME_LIMIT: int = 5
    NON_SPEAKING_DURATION: float = 0.5
    DYNAMIC_ENERGY: bool = True
    AMBIENT_DURATION: float = 1.0
    COMMAND_COOLDOWN_MS: int = 600
    LANGUAGE: str = "en-US"


CONFIG = AppConfig()
GESTURE_CONFIG = GestureConfig()
VOICE_CONFIG = VoiceConfig()
