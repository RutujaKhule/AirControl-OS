from typing import Optional, Tuple


class EMASmoother:
    def __init__(self, alpha: float = 0.4):
        self._alpha = max(0.0, min(1.0, alpha))
        self._last_x: Optional[float] = None
        self._last_y: Optional[float] = None
        self._vel_x: Optional[float] = None
        self._vel_y: Optional[float] = None

    def reset(self) -> None:
        self._last_x = None
        self._last_y = None
        self._vel_x = None
        self._vel_y = None

    def set_alpha(self, alpha: float) -> None:
        self._alpha = max(0.0, min(1.0, alpha))

    def smooth(self, x: float, y: float) -> Tuple[float, float]:
        if self._last_x is None or self._last_y is None:
            self._last_x = float(x)
            self._last_y = float(y)
            self._vel_x = 0.0
            self._vel_y = 0.0
            return self._last_x, self._last_y

        a = self._alpha
        new_x = a * float(x) + (1.0 - a) * self._last_x
        new_y = a * float(y) + (1.0 - a) * self._last_y

        # Very subtle adaptive dampening only for tiny movements
        dx = new_x - self._last_x
        dy = new_y - self._last_y
        speed = (dx * dx + dy * dy) ** 0.5
        if speed < 0.0005:
            new_x = self._last_x + dx * 0.7
            new_y = self._last_y + dy * 0.7

        self._last_x = new_x
        self._last_y = new_y
        self._vel_x = dx
        self._vel_y = dy
        return self._last_x, self._last_y
