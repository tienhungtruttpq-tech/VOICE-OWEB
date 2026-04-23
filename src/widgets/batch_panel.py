"""Batch panel — controls + log."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit,
    QProgressBar, QGroupBox, QLabel,
)


class BatchPanel(QWidget):
    startRequested = pyqtSignal()
    stopRequested = pyqtSignal()
    clearLogRequested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._wire()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start")
        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setEnabled(False)
        self.clear_log_btn = QPushButton("Clear log")
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch(1)
        controls.addWidget(self.clear_log_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat('%v / %m  (%p%)')

        self.eta_label = QLabel("ETA: --")

        log_box = QGroupBox("Batch log")
        log_layout = QVBoxLayout(log_box)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        log_layout.addWidget(self.log)

        root.addLayout(controls)
        root.addWidget(self.progress)
        root.addWidget(self.eta_label)
        root.addWidget(log_box, 1)

    def _wire(self) -> None:
        self.start_btn.clicked.connect(self.startRequested)
        self.stop_btn.clicked.connect(self.stopRequested)
        self.clear_log_btn.clicked.connect(lambda: self.log.clear())

    def set_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def set_progress(self, done: int, total: int, eta: str = '') -> None:
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(done)
        if eta:
            self.eta_label.setText(f"ETA: {eta}")

    def append_log(self, text: str) -> None:
        self.log.appendPlainText(text)
