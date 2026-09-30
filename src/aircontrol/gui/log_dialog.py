from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QGraphicsDropShadowEffect,
    QSizePolicy,
)
from ..core.action_history import (
    ActionHistory,
    ActionCategory,
    HistoryEntry,
    HISTORY,
)


_CAT_COLORS = {
    ActionCategory.GESTURE: "#53d397",
    ActionCategory.VOICE: "#64ffda",
    ActionCategory.SYSTEM: "#8be9fd",
    ActionCategory.ERROR: "#e94560",
    ActionCategory.INFO: "#8892b0",
}


class LogDialog(QDialog):
    def __init__(self, history: ActionHistory = HISTORY, parent=None):
        super().__init__(parent)
        self._history = history
        self.setWindowTitle("AirControl OS — Activity Log")
        self.resize(760, 620)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("LogDialog, QDialog { background-color: #16213e; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header = QLabel("Recent Activity")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #ccd6f6;")

        sub = QLabel(
            "Scrollable log of gestures, voice commands, and system events. "
            "Filter by category and clear entries from the toolbar below."
        )
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #8892b0;")
        sub.setWordWrap(True)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        filter_lbl = QLabel("Filter:")
        filter_lbl.setFont(QFont("Segoe UI", 10))
        filter_lbl.setStyleSheet("color: #ccd6f6;")

        self._filter = QComboBox()
        self._filter.addItem("All categories", None)
        for cat in ActionCategory:
            self._filter.addItem(cat.value, cat)
        self._filter.setStyleSheet(
            "QComboBox { background-color: #0f3460; color: #ccd6f6; padding: 6px 10px;"
            "border-radius: 6px; border: 1px solid #533483; }"
            "QComboBox QAbstractItemView { background-color: #0f3460; color: #ccd6f6;"
            "selection-background-color: #533483; }"
        )
        self._filter.currentIndexChanged.connect(self.refresh)

        self._count_lbl = QLabel("0 entries")
        self._count_lbl.setFont(QFont("Segoe UI", 10))
        self._count_lbl.setStyleSheet("color: #8892b0;")
        self._count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        clear_btn = QPushButton("Clear Log")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #16213e; color: #ffb86c; "
            "border: 1px solid #533483; border-radius: 8px; padding: 6px 14px; }"
            "QPushButton:hover { background-color: #1f2e5c; }"
        )
        clear_btn.clicked.connect(self._clear_clicked)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #533483; color: #ccd6f6; "
            "border-radius: 8px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #5f3e9a; }"
        )
        refresh_btn.clicked.connect(self.refresh)

        toolbar.addWidget(filter_lbl)
        toolbar.addWidget(self._filter, 0)
        toolbar.addSpacing(12)
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self._count_lbl)

        list_wrap = QWidget()
        list_wrap.setStyleSheet(
            "background-color: #0f3460; border-radius: 12px;"
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        list_wrap.setGraphicsEffect(shadow)
        list_layout = QVBoxLayout(list_wrap)
        list_layout.setContentsMargins(10, 10, 10, 10)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { background-color: #0f3460; color: #ccd6f6;"
            "border: none; font-family: Segoe UI; font-size: 10pt; }"
            "QListWidget::item { padding: 6px 8px; border-radius: 6px; }"
            "QListWidget::item:selected { background-color: #533483; }"
        )
        self._list.setAlternatingRowColors(False)
        self._list.setSelectionMode(QListWidget.SingleSelection)
        self._list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        list_layout.addWidget(self._list)

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet(
            "QPushButton { background-color: #533483; color: #ccd6f6; "
            "border-radius: 8px; padding: 8px 22px; }"
            "QPushButton:hover { background-color: #5f3e9a; }"
        )
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)

        root.addWidget(header)
        root.addWidget(sub)
        root.addLayout(toolbar)
        root.addWidget(list_wrap, 1)
        root.addLayout(btn_row)

        self.refresh()
        self._history.add_listener(self._on_entry_added)

    def closeEvent(self, event) -> None:
        try:
            self._history.remove_listener(self._on_entry_added)
        except Exception:
            pass
        super().closeEvent(event)

    def _on_entry_added(self, entry: HistoryEntry) -> None:
        self.refresh()

    def _clear_clicked(self) -> None:
        self._history.clear()
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        cat_filter = self._filter.currentData()
        visible = 0
        for entry in self._history.recent(limit=self._history.max_size):
            if cat_filter is not None and entry.category != cat_filter:
                continue
            item = QListWidgetItem()
            color = _CAT_COLORS.get(entry.category, "#ccd6f6")
            success_marker = "" if entry.success else "  ✗"
            label = (
                f"[{entry.time_label()}]  "
                f"<span style='color:{color};font-weight:bold;'>"
                f"[{entry.category.value}]</span>  "
                f"<b>{entry.action}</b>"
                + (f" — <span style='color:#8892b0;'>{entry.detail}</span>" if entry.detail else "")
                + f"<span style='color:#e94560;'>{success_marker}</span>"
            )
            item.setText(label)
            self._list.addItem(item)
            visible += 1
        if visible == 0:
            empty = QListWidgetItem("No entries yet.")
            empty.setForeground(QColor("#8892b0"))
            self._list.addItem(empty)
        self._count_lbl.setText(f"{visible} entries")
