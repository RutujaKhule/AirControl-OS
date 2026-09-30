import cv2
import numpy as np
from typing import Optional, Tuple
from .config import CONFIG


class CameraCapture:
    def __init__(self, camera_index: int = CONFIG.CAMERA_INDEX):
        self.camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_opened = False

    def open(self) -> bool:
        if self._is_opened:
            return True
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            self._is_opened = False
            return False
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG.CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG.CAMERA_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, CONFIG.CAMERA_FPS)
        self._is_opened = True
        return True

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_opened = False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._is_opened or self._cap is None:
            return False, None
        ret, frame = self._cap.read()
        if not ret:
            return False, None
        frame = cv2.flip(frame, 1)
        return True, frame

    def is_opened(self) -> bool:
        return self._is_opened

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
