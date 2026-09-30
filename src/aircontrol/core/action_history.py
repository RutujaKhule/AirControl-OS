import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Deque, List, Optional


class ActionCategory(Enum):
    GESTURE = "Gesture"
    VOICE = "Voice"
    SYSTEM = "System"
    ERROR = "Error"
    INFO = "Info"


@dataclass
class HistoryEntry:
    timestamp: float
    category: ActionCategory
    action: str
    detail: str
    success: bool = True

    def time_label(self, local: bool = True) -> str:
        t = time.localtime(self.timestamp) if local else time.gmtime(self.timestamp)
        return time.strftime("%H:%M:%S", t)


class ActionHistory:
    def __init__(self, max_size: int = 200):
        self._max_size = max_size
        self._entries: Deque[HistoryEntry] = deque(maxlen=max_size)
        self._listeners: List[Callable[[HistoryEntry], None]] = []

    def add_listener(self, cb: Callable[[HistoryEntry], None]) -> None:
        if cb not in self._listeners:
            self._listeners.append(cb)

    def remove_listener(self, cb: Callable[[HistoryEntry], None]) -> None:
        try:
            self._listeners.remove(cb)
        except ValueError:
            pass

    def add(
        self,
        category: ActionCategory,
        action: str,
        detail: str = "",
        success: bool = True,
        ts: Optional[float] = None,
    ) -> HistoryEntry:
        entry = HistoryEntry(
            timestamp=ts if ts is not None else time.monotonic(),
            category=category,
            action=action,
            detail=detail,
            success=success,
        )
        self._entries.append(entry)
        for cb in list(self._listeners):
            try:
                cb(entry)
            except Exception:
                pass
        return entry

    def gesture(self, action: str, detail: str = "", success: bool = True) -> HistoryEntry:
        return self.add(ActionCategory.GESTURE, action, detail, success)

    def voice(self, action: str, detail: str = "", success: bool = True) -> HistoryEntry:
        return self.add(ActionCategory.VOICE, action, detail, success)

    def system(self, action: str, detail: str = "", success: bool = True) -> HistoryEntry:
        return self.add(ActionCategory.SYSTEM, action, detail, success)

    def error(self, action: str, detail: str = "") -> HistoryEntry:
        return self.add(ActionCategory.ERROR, action, detail, False)

    def info(self, action: str, detail: str = "") -> HistoryEntry:
        return self.add(ActionCategory.INFO, action, detail, True)

    def recent(self, limit: Optional[int] = None) -> List[HistoryEntry]:
        entries = list(reversed(self._entries))
        if limit is None:
            return entries
        return entries[: max(0, int(limit))]

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def max_size(self) -> int:
        return self._max_size


HISTORY = ActionHistory(max_size=200)
