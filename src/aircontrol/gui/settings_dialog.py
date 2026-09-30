from dataclasses import asdict
from typing import Any, Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSlider,
    QComboBox,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QDialogButtonBox,
    QGraphicsDropShadowEffect,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtGui import QColor

from ..core.config import (
    AppConfig,
    GestureConfig,
    VoiceConfig,
    CONFIG,
    GESTURE_CONFIG,
    VOICE_CONFIG,
)


LABEL_FONT = QFont("Segoe UI", 10)
VALUE_FONT = QFont("Segoe UI", 10, QFont.DemiBold)
TITLE_FONT = QFont("Segoe UI", 13, QFont.Bold)


def _make_group(title: str) -> QGroupBox:
    box = QGroupBox(title)
    box.setFont(TITLE_FONT)
    box.setStyleSheet(
        "QGroupBox { background-color: #0f3460; border: 1px solid #16213e;"
        "border-radius: 12px; margin-top: 14px; color: #64ffda; padding: 10px; }"
        "QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }"
    )
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(10)
    shadow.setColor(QColor(0, 0, 0, 80))
    shadow.setOffset(0, 2)
    box.setGraphicsEffect(shadow)
    return box


class SliderRow(QFrame):
    def __init__(
        self,
        label: str,
        min_v: int,
        max_v: int,
        value: int,
        unit: str = "",
        scale: float = 1.0,
        decimals: int = 0,
    ):
        super().__init__()
        self._scale = scale
        self._decimals = decimals
        self._unit = unit
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        self.label_w = QLabel(label)
        self.label_w.setFont(LABEL_FONT)
        self.label_w.setStyleSheet("color: #ccd6f6; background: transparent;")
        self.label_w.setFixedWidth(220)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min_v)
        self.slider.setMaximum(max_v)
        self.slider.setValue(value)
        self.slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #16213e; height: 6px; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #53d397; border: 1px solid #16213e;"
            "width: 16px; margin: -6px 0; border-radius: 8px; }"
            "QSlider::sub-page:horizontal { background: #533483; border-radius: 3px; }"
        )

        self.value_lbl = QLabel(self._fmt(value))
        self.value_lbl.setFont(VALUE_FONT)
        self.value_lbl.setFixedWidth(90)
        self.value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_lbl.setStyleSheet("color: #64ffda; background: transparent;")

        self.slider.valueChanged.connect(self._on_change)

        layout.addWidget(self.label_w)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_lbl)

    def _fmt(self, val: int) -> str:
        actual = val * self._scale
        if self._decimals == 0:
            s = f"{actual:.0f}"
        else:
            s = f"{actual:.{self._decimals}f}"
        if self._unit:
            s = f"{s} {self._unit}"
        return s

    def _on_change(self, val: int) -> None:
        self.value_lbl.setText(self._fmt(val))

    def value(self) -> int:
        return self.slider.value()


class SettingsDialog(QDialog):
    settings_applied = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AirControl OS — Settings")
        self.resize(760, 780)
        self.setMinimumSize(680, 680)
        self.setStyleSheet("SettingsDialog, QDialog { background-color: #16213e; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(18)

        header = QLabel("Settings")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet("color: #ccd6f6;")

        sub = QLabel(
            "Tune detection feel, cursor smoothness, and voice sensitivity. "
            "Click Apply to save changes — they take effect immediately and persist between launches."
        )
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #8892b0;")
        sub.setWordWrap(True)

        root.addWidget(header)
        root.addWidget(sub)

        # ====== Gesture Group ======
        gesture_group = _make_group("Gesture Recognition")
        gform = QFormLayout(gesture_group)
        gform.setSpacing(10)
        gform.setContentsMargins(16, 18, 16, 12)

        self.pinch_slider = SliderRow(
            "Pinch distance threshold",
            10, 200, int(round(CONFIG.PINCH_DISTANCE_THRESHOLD * 1000)),
            scale=0.001, decimals=3, unit="",
        )
        self.cooldown_slider = SliderRow(
            "Click cooldown",
            50, 1500, int(CONFIG.PINCH_CLICK_COOLDOWN_MS),
            unit="ms",
        )
        self.drag_hold_slider = SliderRow(
            "Drag hold duration",
            30, 1000, int(CONFIG.DRAG_HOLD_DURATION_MS),
            unit="ms",
        )
        self.fist_hold_slider = SliderRow(
            "Fist hold for pause",
            100, 3000, int(GESTURE_CONFIG.FIST_HOLD_MS_FOR_PAUSE),
            unit="ms",
        )
        self.pause_cd_slider = SliderRow(
            "Pause toggle cooldown",
            200, 5000, int(GESTURE_CONFIG.PAUSE_TOGGLE_COOLDOWN_MS),
            unit="ms",
        )
        self.right_cd_slider = SliderRow(
            "Right click cooldown",
            100, 3000, int(GESTURE_CONFIG.RIGHT_CLICK_COOLDOWN_MS),
            unit="ms",
        )
        self.scroll_sens_slider = SliderRow(
            "Scroll sensitivity",
            1, 80, int(CONFIG.SCROLL_SENSITIVITY),
            unit="",
        )
        self.scroll_cd_slider = SliderRow(
            "Scroll frame cooldown",
            0, 400, int(GESTURE_CONFIG.SCROLL_COOLDOWN_MS),
            unit="ms",
        )

        for row in [
            self.pinch_slider, self.cooldown_slider, self.drag_hold_slider,
            self.fist_hold_slider, self.pause_cd_slider, self.right_cd_slider,
            self.scroll_sens_slider, self.scroll_cd_slider,
        ]:
            gform.addRow(row)

        # ====== Cursor Group ======
        cursor_group = _make_group("Cursor & Camera")
        cform = QFormLayout(cursor_group)
        cform.setSpacing(10)
        cform.setContentsMargins(16, 18, 16, 12)

        self.smooth_slider = SliderRow(
            "Cursor smoothing factor",
            5, 95, int(round(GESTURE_CONFIG.CURSOR_SMOOTHING_FACTOR * 100)),
            scale=0.01, decimals=2, unit="",
        )
        self.cam_w_slider = SliderRow(
            "Camera width",
            320, 1920, int(CONFIG.CAMERA_WIDTH), unit="px",
        )
        self.cam_h_slider = SliderRow(
            "Camera height",
            240, 1080, int(CONFIG.CAMERA_HEIGHT), unit="px",
        )
        self.cam_fps_slider = SliderRow(
            "Camera FPS target",
            15, 60, int(CONFIG.CAMERA_FPS), unit="fps",
        )

        cam_idx_row = QHBoxLayout()
        cam_idx_row.setSpacing(12)
        self.cam_idx_label = QLabel("Camera index")
        self.cam_idx_label.setFont(LABEL_FONT)
        self.cam_idx_label.setStyleSheet("color: #ccd6f6;")
        self.cam_idx_label.setFixedWidth(220)
        self.cam_idx_combo = QComboBox()
        self.cam_idx_combo.addItems([str(i) for i in range(6)])
        self.cam_idx_combo.setCurrentText(str(int(CONFIG.CAMERA_INDEX)))
        self.cam_idx_combo.setStyleSheet(
            "QComboBox { background-color: #16213e; color: #ccd6f6;"
            "padding: 6px 10px; border-radius: 6px; border: 1px solid #533483; }"
            "QComboBox QAbstractItemView { background-color: #0f3460; color: #ccd6f6;"
            "selection-background-color: #533483; }"
        )
        self.cam_idx_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        cam_idx_row.addWidget(self.cam_idx_label)
        cam_idx_row.addWidget(self.cam_idx_combo, 1)

        self.mp_det_slider = SliderRow(
            "Detection confidence",
            30, 100, int(round(CONFIG.MP_MIN_DETECTION_CONFIDENCE * 100)),
            scale=0.01, decimals=2, unit="",
        )
        self.mp_trk_slider = SliderRow(
            "Tracking confidence",
            30, 100, int(round(CONFIG.MP_MIN_TRACKING_CONFIDENCE * 100)),
            scale=0.01, decimals=2, unit="",
        )

        for row in [self.smooth_slider, self.cam_w_slider, self.cam_h_slider,
                    self.cam_fps_slider, self.mp_det_slider, self.mp_trk_slider]:
            cform.addRow(row)
        cam_idx_wrap = QWidget()
        QVBoxLayout(cam_idx_wrap).addLayout(cam_idx_row)
        cam_idx_wrap.layout().setContentsMargins(0, 0, 0, 0)
        cform.addRow(cam_idx_wrap)

        # ====== Voice Group ======
        voice_group = _make_group("Voice Recognition")
        vform = QFormLayout(voice_group)
        vform.setSpacing(10)
        vform.setContentsMargins(16, 18, 16, 12)

        self.energy_slider = SliderRow(
            "Energy threshold",
            10, 4000, int(VOICE_CONFIG.ENERGY_THRESHOLD), unit="",
        )
        self.dyn_energy_cb = QCheckBox("Dynamic energy adjustment")
        self.dyn_energy_cb.setChecked(bool(VOICE_CONFIG.DYNAMIC_ENERGY))
        self.dyn_energy_cb.setFont(LABEL_FONT)
        self.dyn_energy_cb.setStyleSheet("color: #ccd6f6; padding: 4px 0;")

        self.pause_thr_slider = SliderRow(
            "End-of-phrase pause",
            10, 300, int(round(VOICE_CONFIG.PAUSE_THRESHOLD * 100)),
            scale=0.01, decimals=2, unit="s",
        )
        self.phrase_limit_slider = SliderRow(
            "Max phrase length",
            2, 15, int(VOICE_CONFIG.PHRASE_TIME_LIMIT), unit="s",
        )
        self.ambient_slider = SliderRow(
            "Ambient calibration time",
            0, 50, int(round(VOICE_CONFIG.AMBIENT_DURATION * 10)),
            scale=0.1, decimals=1, unit="s",
        )
        self.voice_cd_slider = SliderRow(
            "Voice command cooldown",
            100, 4000, int(VOICE_CONFIG.COMMAND_COOLDOWN_MS), unit="ms",
        )

        lang_row = QHBoxLayout()
        lang_row.setSpacing(12)
        self.lang_label = QLabel("Recognition language")
        self.lang_label.setFont(LABEL_FONT)
        self.lang_label.setStyleSheet("color: #ccd6f6;")
        self.lang_label.setFixedWidth(220)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "en-US (English US)", "en-GB (English UK)",
            "es-ES (Spanish)", "fr-FR (French)",
            "de-DE (German)", "it-IT (Italian)",
            "pt-BR (Portuguese BR)", "ja-JP (Japanese)",
            "ko-KR (Korean)", "zh-CN (Chinese)",
        ])
        current_lang = VOICE_CONFIG.LANGUAGE or "en-US"
        matched_idx = 0
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemText(i).startswith(current_lang):
                matched_idx = i
                break
        self.lang_combo.setCurrentIndex(matched_idx)
        self.lang_combo.setStyleSheet(
            "QComboBox { background-color: #16213e; color: #ccd6f6;"
            "padding: 6px 10px; border-radius: 6px; border: 1px solid #533483; }"
            "QComboBox QAbstractItemView { background-color: #0f3460; color: #ccd6f6;"
            "selection-background-color: #533483; }"
        )
        self.lang_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.lang_combo, 1)
        lang_wrap = QWidget()
        QVBoxLayout(lang_wrap).addLayout(lang_row)
        lang_wrap.layout().setContentsMargins(0, 0, 0, 0)

        for row in [self.energy_slider, self.pause_thr_slider,
                    self.phrase_limit_slider, self.ambient_slider,
                    self.voice_cd_slider]:
            vform.addRow(row)
        vform.addRow(self.dyn_energy_cb)
        vform.addRow(lang_wrap)

        # Wrap everything into scroll via VBox in main root
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        inner_lay.setSpacing(14)
        inner_lay.addWidget(gesture_group)
        inner_lay.addWidget(cursor_group)
        inner_lay.addWidget(voice_group)
        inner_lay.addStretch(1)

        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #0f3460; width: 10px; border-radius: 5px; }"
            "QScrollBar::handle:vertical { background: #533483; border-radius: 5px; min-height: 40px; }"
        )
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Buttons
        defaults_btn = QPushButton("Restore Defaults")
        defaults_btn.setCursor(Qt.PointingHandCursor)
        defaults_btn.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        defaults_btn.setStyleSheet(
            "QPushButton { background-color: #16213e; color: #ffb86c;"
            "border: 1px solid #533483; border-radius: 8px; padding: 8px 14px; }"
            "QPushButton:hover { background-color: #1f2e5c; }"
        )
        defaults_btn.clicked.connect(self._restore_defaults)

        button_box = QDialogButtonBox()
        apply_btn = button_box.addButton("Apply", QDialogButtonBox.AcceptRole)
        cancel_btn = button_box.addButton("Cancel", QDialogButtonBox.RejectRole)
        for b in [apply_btn, cancel_btn]:
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
            b.setMinimumHeight(36)
        apply_btn.setStyleSheet(
            "QPushButton { background-color: #53d397; color: #0f3460;"
            "border-radius: 8px; padding: 8px 22px; }"
            "QPushButton:hover { background-color: #44b882; }"
        )
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #533483; color: #ccd6f6;"
            "border-radius: 8px; padding: 8px 22px; }"
            "QPushButton:hover { background-color: #5f3e9a; }"
        )
        apply_btn.clicked.connect(self._apply_and_save)
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(defaults_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(button_box)

        root.addWidget(scroll, 1)
        root.addLayout(btn_row)

    def _collect_payload(self) -> Dict[str, Dict[str, Any]]:
        return {
            "app": {
                "CAMERA_INDEX": int(self.cam_idx_combo.currentText()),
                "CAMERA_WIDTH": int(self.cam_w_slider.value()),
                "CAMERA_HEIGHT": int(self.cam_h_slider.value()),
                "CAMERA_FPS": int(self.cam_fps_slider.value()),
                "MP_MIN_DETECTION_CONFIDENCE": float(self.mp_det_slider.value() * 0.01),
                "MP_MIN_TRACKING_CONFIDENCE": float(self.mp_trk_slider.value() * 0.01),
                "PINCH_DISTANCE_THRESHOLD": float(self.pinch_slider.value() * 0.001),
                "PINCH_CLICK_COOLDOWN_MS": int(self.cooldown_slider.value()),
                "DRAG_HOLD_DURATION_MS": int(self.drag_hold_slider.value()),
                "SCROLL_SENSITIVITY": int(self.scroll_sens_slider.value()),
            },
            "gesture": {
                "CURSOR_SMOOTHING_FACTOR": float(self.smooth_slider.value() * 0.01),
                "PAUSE_TOGGLE_COOLDOWN_MS": int(self.pause_cd_slider.value()),
                "RIGHT_CLICK_COOLDOWN_MS": int(self.right_cd_slider.value()),
                "SCROLL_COOLDOWN_MS": int(self.scroll_cd_slider.value()),
                "FIST_HOLD_MS_FOR_PAUSE": int(self.fist_hold_slider.value()),
            },
            "voice": {
                "ENERGY_THRESHOLD": int(self.energy_slider.value()),
                "PAUSE_THRESHOLD": float(self.pause_thr_slider.value() * 0.01),
                "PHRASE_TIME_LIMIT": int(self.phrase_limit_slider.value()),
                "DYNAMIC_ENERGY": bool(self.dyn_energy_cb.isChecked()),
                "AMBIENT_DURATION": float(self.ambient_slider.value() * 0.1),
                "COMMAND_COOLDOWN_MS": int(self.voice_cd_slider.value()),
                "LANGUAGE": self.lang_combo.currentText().split(" ", 1)[0],
            },
        }

    def _apply_to_memory(self) -> None:
        payload = self._collect_payload()
        for section, values in payload.items():
            if section == "app":
                for k, v in values.items():
                    setattr(CONFIG, k, v)
            elif section == "gesture":
                for k, v in values.items():
                    setattr(GESTURE_CONFIG, k, v)
            elif section == "voice":
                for k, v in values.items():
                    setattr(VOICE_CONFIG, k, v)

    def _apply_and_save(self) -> None:
        self._apply_to_memory()
        try:
            from ..core.persistence import save_settings
            path = save_settings()
            self.settings_applied.emit()
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Save failed", f"Could not write settings file:\n{e}")

    def _restore_defaults(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Restore defaults?",
            "This will reset every setting in this dialog to its factory default.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        from ..core.persistence import reset_defaults
        reset_defaults()
        # Reset each control to dataclass default values:
        self.pinch_slider.slider.setValue(int(round(CONFIG.PINCH_DISTANCE_THRESHOLD * 1000)))
        self.cooldown_slider.slider.setValue(int(CONFIG.PINCH_CLICK_COOLDOWN_MS))
        self.drag_hold_slider.slider.setValue(int(CONFIG.DRAG_HOLD_DURATION_MS))
        self.fist_hold_slider.slider.setValue(int(GESTURE_CONFIG.FIST_HOLD_MS_FOR_PAUSE))
        self.pause_cd_slider.slider.setValue(int(GESTURE_CONFIG.PAUSE_TOGGLE_COOLDOWN_MS))
        self.right_cd_slider.slider.setValue(int(GESTURE_CONFIG.RIGHT_CLICK_COOLDOWN_MS))
        self.scroll_sens_slider.slider.setValue(int(CONFIG.SCROLL_SENSITIVITY))
        self.scroll_cd_slider.slider.setValue(int(GESTURE_CONFIG.SCROLL_COOLDOWN_MS))
        self.smooth_slider.slider.setValue(int(round(GESTURE_CONFIG.CURSOR_SMOOTHING_FACTOR * 100)))
        self.cam_w_slider.slider.setValue(int(CONFIG.CAMERA_WIDTH))
        self.cam_h_slider.slider.setValue(int(CONFIG.CAMERA_HEIGHT))
        self.cam_fps_slider.slider.setValue(int(CONFIG.CAMERA_FPS))
        self.cam_idx_combo.setCurrentText(str(int(CONFIG.CAMERA_INDEX)))
        self.mp_det_slider.slider.setValue(int(round(CONFIG.MP_MIN_DETECTION_CONFIDENCE * 100)))
        self.mp_trk_slider.slider.setValue(int(round(CONFIG.MP_MIN_TRACKING_CONFIDENCE * 100)))
        self.energy_slider.slider.setValue(int(VOICE_CONFIG.ENERGY_THRESHOLD))
        self.dyn_energy_cb.setChecked(bool(VOICE_CONFIG.DYNAMIC_ENERGY))
        self.pause_thr_slider.slider.setValue(int(round(VOICE_CONFIG.PAUSE_THRESHOLD * 100)))
        self.phrase_limit_slider.slider.setValue(int(VOICE_CONFIG.PHRASE_TIME_LIMIT))
        self.ambient_slider.slider.setValue(int(round(VOICE_CONFIG.AMBIENT_DURATION * 10)))
        self.voice_cd_slider.slider.setValue(int(VOICE_CONFIG.COMMAND_COOLDOWN_MS))
        self.lang_combo.setCurrentIndex(0)
