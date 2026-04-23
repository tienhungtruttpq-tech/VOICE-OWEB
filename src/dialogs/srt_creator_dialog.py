"""SRT creator — tao SRT tu text va duration thuc te cua audio file."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QPlainTextEdit, QLabel, QMessageBox, QSpinBox, QFormLayout, QGroupBox,
)

from ..core.audio_processor import load_wav, duration_ms
from ..core.srt_parser import build_srt_from_durations, export_srt


class SRTCreatorDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tao SRT tu text + audio")
        self.resize(640, 520)
        self._audio_files: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        files_box = QGroupBox("Audio files (dung thu tu)")
        fl = QVBoxLayout(files_box)
        row = QHBoxLayout()
        self.files_label = QLabel("(chua chon)")
        self.files_label.setWordWrap(True)
        self.pick_btn = QPushButton("Chon files .wav...")
        row.addWidget(self.files_label, 1)
        row.addWidget(self.pick_btn)
        fl.addLayout(row)
        root.addWidget(files_box)

        text_box = QGroupBox("Text (moi dong 1 segment, thu tu khop audio files)")
        tl = QVBoxLayout(text_box)
        self.text_edit = QPlainTextEdit()
        tl.addWidget(self.text_edit)
        root.addWidget(text_box)

        opt_box = QGroupBox("Tuy chon")
        form = QFormLayout(opt_box)
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 5000)
        self.gap_spin.setValue(200)
        self.gap_spin.setSuffix(' ms')
        form.addRow("Gap giua segment:", self.gap_spin)
        root.addWidget(opt_box)

        btns = QHBoxLayout()
        self.save_btn = QPushButton("Xuat SRT...")
        self.close_btn = QPushButton("Dong")
        btns.addWidget(self.save_btn)
        btns.addStretch(1)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

        self.pick_btn.clicked.connect(self._pick_files)
        self.save_btn.clicked.connect(self._save)
        self.close_btn.clicked.connect(self.close)

    def _pick_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Chon audio files", "", "Audio (*.wav *.mp3 *.flac *.ogg)"
        )
        if paths:
            self._audio_files = paths
            self.files_label.setText("\n".join(os.path.basename(p) for p in paths))

    def _save(self) -> None:
        if not self._audio_files:
            QMessageBox.warning(self, "Thieu audio", "Chon audio files truoc.")
            return
        texts = [t for t in self.text_edit.toPlainText().splitlines() if t.strip()]
        if len(texts) != len(self._audio_files):
            QMessageBox.warning(
                self,
                "So luong khong khop",
                f"Co {len(self._audio_files)} audio files nhung {len(texts)} dong text."
            )
            return

        durations_ms: list[int] = []
        try:
            for p in self._audio_files:
                audio, sr = load_wav(p)
                durations_ms.append(duration_ms(audio, sr))
        except Exception as e:
            QMessageBox.warning(self, "Loi doc audio", str(e))
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Luu SRT", "output.srt", "SRT (*.srt)"
        )
        if not out_path:
            return
        segs = build_srt_from_durations(texts, durations_ms, gap_ms=self.gap_spin.value())
        export_srt(segs, out_path)
        QMessageBox.information(self, "Da luu", f"Da xuat SRT: {out_path}")
