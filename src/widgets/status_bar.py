"""Status bar — tien trinh + thong tin."""

from __future__ import annotations

from PyQt6.QtWidgets import QStatusBar, QLabel, QProgressBar


class AppStatusBar(QStatusBar):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.msg_label = QLabel("San sang.")
        self.model_label = QLabel("Model: chua load")
        self.device_label = QLabel("Device: auto")

        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.addWidget(self.msg_label, 1)
        self.addPermanentWidget(self.model_label)
        self.addPermanentWidget(self.device_label)
        self.addPermanentWidget(self.progress)

    def set_message(self, text: str) -> None:
        self.msg_label.setText(text)

    def set_model(self, text: str) -> None:
        self.model_label.setText(f"Model: {text}")

    def set_device(self, text: str) -> None:
        self.device_label.setText(f"Device: {text}")

    def set_progress(self, done: int, total: int) -> None:
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(done)
