"""Options panel — sample rate, format, output dir, normalize..."""

from __future__ import annotations

import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QPushButton, QLineEdit, QGroupBox, QSpinBox, QFileDialog,
)

from ..utils.constants import (
    DEFAULT_SAMPLE_RATE, SUPPORTED_SAMPLE_RATES,
    DEFAULT_OUTPUT_FORMAT, SUPPORTED_OUTPUT_FORMATS,
    SILENCE_BETWEEN_JOIN_MS,
)


class OptionsPanel(QWidget):
    outputDirChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Output dir
        out_box = QGroupBox("Thu muc output")
        out_row = QHBoxLayout(out_box)
        self.out_edit = QLineEdit(os.path.abspath('output'))
        self.out_browse_btn = QPushButton("Browse...")
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(self.out_browse_btn)
        root.addWidget(out_box)

        # Audio options
        aud_box = QGroupBox("Audio")
        aud_form = QFormLayout(aud_box)
        self.sr_combo = QComboBox()
        for sr in SUPPORTED_SAMPLE_RATES:
            self.sr_combo.addItem(f"{sr} Hz", sr)
        self.sr_combo.setCurrentIndex(SUPPORTED_SAMPLE_RATES.index(DEFAULT_SAMPLE_RATE))

        self.fmt_combo = QComboBox()
        for f in SUPPORTED_OUTPUT_FORMATS:
            self.fmt_combo.addItem(f.upper(), f)
        self.fmt_combo.setCurrentIndex(SUPPORTED_OUTPUT_FORMATS.index(DEFAULT_OUTPUT_FORMAT))

        self.normalize_chk = QCheckBox("Normalize audio")
        self.normalize_chk.setChecked(True)

        aud_form.addRow("Sample rate:", self.sr_combo)
        aud_form.addRow("Format:", self.fmt_combo)
        aud_form.addRow("", self.normalize_chk)
        root.addWidget(aud_box)

        # Post-process
        post_box = QGroupBox("Hau xu ly")
        post_form = QFormLayout(post_box)
        self.join_chk = QCheckBox("Tu dong ghep audio theo file")
        self.join_chk.setChecked(True)
        self.srt_chk = QCheckBox("Tu dong tao SRT tu duration")
        self.srt_chk.setChecked(True)
        self.subdir_chk = QCheckBox("Thu muc rieng cho moi file")
        self.subdir_chk.setChecked(True)

        self.silence_spin = QSpinBox()
        self.silence_spin.setRange(0, 5000)
        self.silence_spin.setSingleStep(50)
        self.silence_spin.setValue(SILENCE_BETWEEN_JOIN_MS)
        self.silence_spin.setSuffix(' ms')

        post_form.addRow("", self.join_chk)
        post_form.addRow("", self.srt_chk)
        post_form.addRow("", self.subdir_chk)
        post_form.addRow("Silence khi ghep:", self.silence_spin)
        root.addWidget(post_box)

        root.addStretch(1)

        self.out_browse_btn.clicked.connect(self._browse_out)

    def _browse_out(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Chon thu muc output", self.out_edit.text())
        if path:
            self.out_edit.setText(path)
            self.outputDirChanged.emit(path)

    # Getters
    def output_dir(self) -> str:
        return self.out_edit.text().strip() or 'output'

    def sample_rate(self) -> int:
        return int(self.sr_combo.currentData())

    def output_format(self) -> str:
        return self.fmt_combo.currentData()

    def normalize(self) -> bool:
        return self.normalize_chk.isChecked()

    def join_output(self) -> bool:
        return self.join_chk.isChecked()

    def auto_srt(self) -> bool:
        return self.srt_chk.isChecked()

    def per_file_subdir(self) -> bool:
        return self.subdir_chk.isChecked()

    def silence_ms(self) -> int:
        return int(self.silence_spin.value())
