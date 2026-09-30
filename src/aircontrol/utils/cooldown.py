import time
from typing import Dict, Optional


class CooldownManager:
    def __init__(self):
        self._last_trigger: Dict[str, float] = {}

    def can_trigger(self, action: str, cooldown_ms: int) -> bool:
        now = time.monotonic()
        last = self._last_trigger.get(action)
        if last is None:
            return True
        elapsed_ms = (now - last) * 1000.0
        return elapsed_ms >= cooldown_ms

    def mark_triggered(self, action: str) -> None:
        self._last_trigger[action] = time.monotonic()

    def try_trigger(self, action: str, cooldown_ms: int) -> bool:
        if self.can_trigger(action, cooldown_ms):
            self.mark_triggered(action)
            return True
        return False

    def reset(self, action: Optional[str] = None) -> None:
        if action is None:
            self._last_trigger.clear()
        else:
            self._last_trigger.pop(action, None)

    def remaining_ms(self, action: str, cooldown_ms: int) -> float:
        now = time.monotonic()
        last = self._last_trigger.get(action)
        if last is None:
            return 0.0
        elapsed_ms = (now - last) * 1000.0
        remaining = cooldown_ms - elapsed_ms
        return max(0.0, remaining)
