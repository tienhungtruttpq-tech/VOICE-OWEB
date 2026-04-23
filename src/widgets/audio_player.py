"""Mini audio player."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel, QFileDialog,
)

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    _HAS_MEDIA = True
except ImportError:
    _HAS_MEDIA = False


class AudioPlayer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        if _HAS_MEDIA:
            self._init_player()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.play_btn = QPushButton("▶")
        self.pause_btn = QPushButton("❚❚")
        self.stop_btn = QPushButton("■")
        self.open_btn = QPushButton("Open...")

        for b in (self.play_btn, self.pause_btn, self.stop_btn, self.open_btn):
            b.setFixedWidth(40)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)

        self.time_label = QLabel("00:00 / 00:00")
        self.file_label = QLabel("(no file)")
        self.file_label.setStyleSheet("color: #888;")

        layout.addWidget(self.play_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.time_label)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.file_label, 2)

    def _init_player(self) -> None:
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._audio.setVolume(0.9)

        self.play_btn.clicked.connect(self._player.play)
        self.pause_btn.clicked.connect(self._player.pause)
        self.stop_btn.clicked.connect(self._player.stop)
        self.open_btn.clicked.connect(self._open_file)

        self._player.positionChanged.connect(self._on_pos)
        self._player.durationChanged.connect(self._on_dur)
        self.slider.sliderMoved.connect(self._player.setPosition)

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Mo audio", "", "Audio (*.wav *.mp3 *.flac *.ogg)")
        if path:
            self.load(path)

    def load(self, path: str) -> None:
        if not _HAS_MEDIA:
            return
        self._player.setSource(QUrl.fromLocalFile(path))
        self.file_label.setText(path)
        self._player.play()

    def _fmt(self, ms: int) -> str:
        s = ms // 1000
        return f"{s // 60:02d}:{s % 60:02d}"

    def _on_pos(self, ms: int) -> None:
        dur = self._player.duration()
        if dur > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(int(ms * 1000 / dur))
            self.slider.blockSignals(False)
        self.time_label.setText(f"{self._fmt(ms)} / {self._fmt(dur)}")

    def _on_dur(self, dur: int) -> None:
        self.time_label.setText(f"00:00 / {self._fmt(dur)}")
