import os
import sys
import subprocess
import shlex
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


try:
    import pyautogui

    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False


@dataclass
class ExecutionResult:
    matched: bool
    action: str
    message: str
    error: Optional[str] = None


class VoiceExecutor:
    def __init__(self):
        self._app_registry: Dict[str, List[str]] = {
            "chrome": ["chrome", "google chrome", "browser"],
            "notepad": ["notepad", "text editor", "note pad"],
            "calculator": ["calculator", "calc", "calculation"],
            "paint": ["paint", "ms paint", "mspaint"],
            "explorer": ["explorer", "file explorer", "files", "my computer"],
            "cmd": ["cmd", "command prompt", "command line", "terminal"],
            "powershell": ["powershell", "powershell terminal"],
            "spotify": ["spotify", "music app"],
            "word": ["word", "microsoft word", "ms word"],
            "excel": ["excel", "microsoft excel", "spreadsheet"],
            "powerpoint": ["powerpoint", "ppt", "presentation"],
            "edge": ["edge", "microsoft edge"],
            "firefox": ["firefox", "mozilla firefox"],
        }
        self._windows_executables: Dict[str, str] = {
            "chrome": "chrome.exe",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "edge": "msedge.exe",
        }
        self._last_result: Optional[ExecutionResult] = None

    @staticmethod
    def _normalize(text: str) -> str:
        if not text:
            return ""
        t = text.strip().lower()
        for ch in ",.!?;:\"'()[]{}":
            t = t.replace(ch, " ")
        return " ".join(t.split())

    def _match_app(self, phrase: str) -> Optional[str]:
        for app_key, aliases in self._app_registry.items():
            for alias in aliases:
                if alias in phrase:
                    return app_key
        return None

    def _open_app(self, app_key: str) -> Tuple[bool, str, Optional[str]]:
        if not sys.platform.startswith("win"):
            return False, "Open app supported only on Windows", None
        exe = self._windows_executables.get(app_key)
        try:
            if exe:
                subprocess.Popen(exe, shell=False)
                return True, f"Opening {app_key}...", None
            if app_key in ("spotify", "word", "excel", "powerpoint", "firefox"):
                subprocess.Popen(
                    ["cmd", "/c", "start", "", app_key],
                    shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return True, f"Opening {app_key}...", None
            os.startfile(app_key)  # type: ignore[attr-defined]
            return True, f"Opening {app_key}...", None
        except Exception as e:
            return False, f"Failed to open {app_key}", str(e)

    def _media(self, action: str) -> Tuple[bool, str, Optional[str]]:
        if not _HAS_PYAUTOGUI:
            return False, "PyAutoGUI not available", None
        key_map = {
            "playpause": "playpause",
            "play": "playpause",
            "pause": "playpause",
            "next": "nexttrack",
            "nexttrack": "nexttrack",
            "previous": "prevtrack",
            "prevtrack": "prevtrack",
            "stop": "stop",
            "volumeup": "volumeup",
            "volumedown": "volumedown",
            "volumemute": "volumemute",
            "mute": "volumemute",
        }
        key = key_map.get(action)
        if not key:
            return False, f"Unknown media action: {action}", None
        try:
            if action in ("volumeup", "volumedown"):
                for _ in range(3):
                    pyautogui.press(key)
            else:
                pyautogui.press(key)
            label = {
                "playpause": "Toggle Play/Pause",
                "nexttrack": "Next Track",
                "prevtrack": "Previous Track",
                "stop": "Stop",
                "volumeup": "Volume Up",
                "volumedown": "Volume Down",
                "volumemute": "Mute",
            }.get(action, action)
            return True, label, None
        except Exception as e:
            return False, f"Media {action} failed", str(e)

    def _scroll_voice(self, direction: str, amount: int = 6) -> Tuple[bool, str, Optional[str]]:
        if not _HAS_PYAUTOGUI:
            return False, "PyAutoGUI not available", None
        try:
            clicks = amount if direction == "up" else -amount
            pyautogui.scroll(clicks)
            return True, f"Scroll {direction} {amount}", None
        except Exception as e:
            return False, f"Scroll {direction} failed", str(e)

    def execute(self, phrase: str) -> ExecutionResult:
        norm = self._normalize(phrase)
        if not norm:
            self._last_result = ExecutionResult(False, "", "Empty phrase")
            return self._last_result

        if any(w in norm for w in ["open ", "launch ", "start ", "run "]):
            app = self._match_app(norm)
            if app:
                ok, msg, err = self._open_app(app)
                self._last_result = ExecutionResult(ok, f"open:{app}", msg, err)
                return self._last_result

        if any(w in norm for w in ["play", "pause"]):
            if "next" in norm or "skip" in norm:
                ok, msg, err = self._media("nexttrack")
            elif ("previous" in norm) or ("prev" in norm) or ("back" in norm):
                ok, msg, err = self._media("prevtrack")
            elif "stop" in norm:
                ok, msg, err = self._media("stop")
            else:
                ok, msg, err = self._media("playpause")
            self._last_result = ExecutionResult(ok, "media", msg, err)
            return self._last_result

        if "mute" in norm:
            ok, msg, err = self._media("volumemute")
            self._last_result = ExecutionResult(ok, "mute", msg, err)
            return self._last_result
        if any(w in norm for w in ["volume up", "volume louder", "turn it up", "louder"]):
            ok, msg, err = self._media("volumeup")
            self._last_result = ExecutionResult(ok, "volumeup", msg, err)
            return self._last_result
        if any(w in norm for w in ["volume down", "quieter", "lower volume", "softer"]):
            ok, msg, err = self._media("volumedown")
            self._last_result = ExecutionResult(ok, "volumedown", msg, err)
            return self._last_result

        scroll_amounts = [("a lot", 15), ("lot", 12), ("little", 4), ("bit", 4), ("slight", 3)]
        amt = 8
        for label, n in scroll_amounts:
            if label in norm:
                amt = n
                break
        if any(w in norm for w in ["scroll up", "scroll page up", "page up", "scroll up page"]):
            ok, msg, err = self._scroll_voice("up", amt)
            self._last_result = ExecutionResult(ok, "scroll:up", msg, err)
            return self._last_result
        if any(w in norm for w in ["scroll down", "scroll page down", "page down", "scroll down page"]):
            ok, msg, err = self._scroll_voice("down", amt)
            self._last_result = ExecutionResult(ok, "scroll:down", msg, err)
            return self._last_result

        self._last_result = ExecutionResult(False, "", "No command matched")
        return self._last_result

    @property
    def last_result(self) -> Optional[ExecutionResult]:
        return self._last_result
