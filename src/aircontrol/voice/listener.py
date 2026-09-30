import time
from threading import Event
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker
from typing import Optional

from ..core.config import VOICE_CONFIG
from ..utils.cooldown import CooldownManager

_HAS_SR = False
try:
    import speech_recognition as sr  # type: ignore

    _HAS_SR = True
except Exception:
    sr = None  # type: ignore


class VoiceListener(QThread):
    phrase_recognized = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    partial_status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._stop_requested = Event()
        self._mutex = QMutex()
        self._recognizer = None
        self._microphone = None
        self._cooldowns = CooldownManager()
        self._last_phrase: Optional[str] = None

    def available(self) -> bool:
        return _HAS_SR

    def start(self, priority=QThread.InheritPriority) -> None:
        self._stop_requested.clear()
        with QMutexLocker(self._mutex):
            self._running = True
        super().start(priority)

    def _init(self) -> Optional[str]:
        if not _HAS_SR or sr is None:
            return "SpeechRecognition library not installed"
        try:
            self._recognizer = sr.Recognizer()
            self._recognizer.operation_timeout = 4.0
            self._recognizer.energy_threshold = VOICE_CONFIG.ENERGY_THRESHOLD
            self._recognizer.pause_threshold = VOICE_CONFIG.PAUSE_THRESHOLD
            self._recognizer.dynamic_energy_threshold = VOICE_CONFIG.DYNAMIC_ENERGY
            self._recognizer.non_speaking_duration = VOICE_CONFIG.NON_SPEAKING_DURATION
            self._microphone = sr.Microphone()
            return None
        except Exception as e:
            return f"Failed to open microphone: {e}"

    def _calibrate(self) -> Optional[str]:
        if self._microphone is None or self._recognizer is None:
            return "Mic not initialized"
        try:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(
                    source, duration=VOICE_CONFIG.AMBIENT_DURATION
                )
            return None
        except Exception as e:
            return f"Ambient calibration failed: {e}"

    def run(self):
        if self._stop_requested.is_set():
            return
        if not _HAS_SR:
            self._running = False
            self.error_occurred.emit(
                "SpeechRecognition/PyAudio unavailable. Install PyAudio via `pipwin install pyaudio`."
            )
            self.status_changed.emit("Voice: Unavailable")
            return

        err = self._init()
        if err:
            self.error_occurred.emit(err)
            self.status_changed.emit("Voice: Error")
            return

        self.status_changed.emit("Voice: Calibrating...")
        cal_err = self._calibrate()
        if cal_err:
            self.error_occurred.emit(cal_err)
            self.status_changed.emit("Voice: Error (mic)")
        else:
            self.status_changed.emit("Voice: Listening")

        assert self._recognizer is not None
        assert self._microphone is not None

        while True:
            with QMutexLocker(self._mutex):
                if not self._running or self._stop_requested.is_set():
                    break
            try:
                with self._microphone as source:
                    self.partial_status.emit("Voice: Hearing...")
                    audio = self._recognizer.listen(
                        source,
                        timeout=1.0,
                        phrase_time_limit=VOICE_CONFIG.PHRASE_TIME_LIMIT,
                    )
                    self.partial_status.emit("Voice: Recognizing...")
            except Exception as e:
                self.partial_status.emit("Voice: Listening")
                time.sleep(0.1)
                continue

            try:
                text = self._recognizer.recognize_google(
                    audio, language=VOICE_CONFIG.LANGUAGE
                )
                text = (text or "").strip()
                if text and self._cooldowns.try_trigger(
                    "phrase", VOICE_CONFIG.COMMAND_COOLDOWN_MS
                ):
                    self._last_phrase = text
                    self.phrase_recognized.emit(text)
                self.partial_status.emit("Voice: Listening")
            except sr.WaitTimeoutError:
                self.partial_status.emit("Voice: Listening")
            except sr.UnknownValueError:
                self.partial_status.emit("Voice: Listening")
            except sr.RequestError as e:
                self.error_occurred.emit(f"Google API error: {e}")
                self.partial_status.emit("Voice: API error")
                time.sleep(1.0)
            except Exception as e:
                self.error_occurred.emit(f"Recognition error: {e}")
                self.partial_status.emit("Voice: Error")
                time.sleep(0.5)

        with QMutexLocker(self._mutex):
            self._running = False
        self.status_changed.emit("Voice: Stopped")

    @property
    def last_phrase(self) -> Optional[str]:
        return self._last_phrase

    def stop(self):
        self._stop_requested.set()
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(6000)
