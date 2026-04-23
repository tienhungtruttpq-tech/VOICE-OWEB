"""Voice Design dialog — thiet ke giong voi instruct natural-language."""

from __future__ import annotations

import os
import tempfile

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLabel,
    QPlainTextEdit, QPushButton, QGroupBox, QMessageBox, QLineEdit,
)

from ..core.tts_engine import TTSEngine
from ..core.audio_processor import save_wav
from ..core.voice_library import VoiceProfile
from ..utils.constants import LANGUAGES, DEFAULT_LANGUAGE, INSTRUCT_PRESETS


class _DesignWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, engine: TTSEngine, text: str, instruct: str, lang: str, out_path: str) -> None:
        super().__init__()
        self.engine = engine
        self.text = text
        self.instruct = instruct
        self.lang = lang
        self.out_path = out_path

    def run(self) -> None:
        try:
            self.engine.set_mode('design')
            self.engine.set_language(self.lang)
            self.engine.set_instruct(self.instruct)
            if not self.engine.is_loaded:
                self.engine.load()
            audio = self.engine.generate(self.text)
            save_wav(self.out_path, audio, self.engine.OUTPUT_SAMPLE_RATE)
            self.done.emit(self.out_path)
        except Exception as e:
            self.failed.emit(str(e))


class VoiceDesignDialog(QDialog):
    profileSaved = pyqtSignal(VoiceProfile)

    def __init__(self, engine: TTSEngine, library=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Voice Design — thiet ke giong")
        self.resize(640, 520)
        self.engine = engine
        self.library = library
        self._worker: _DesignWorker | None = None
        self._last_preview: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        form_box = QGroupBox("Cau hinh")
        form = QFormLayout(form_box)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ten giong (vd: teacher_warm_en)")

        self.lang_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.lang_combo.addItem(label, code)
        self.lang_combo.setCurrentIndex(list(LANGUAGES.keys()).index(DEFAULT_LANGUAGE))

        self.preset_combo = QComboBox()
        for k in INSTRUCT_PRESETS.keys():
            self.preset_combo.addItem(k)
        self.preset_combo.currentTextChanged.connect(self._on_preset)

        form.addRow("Ten:", self.name_edit)
        form.addRow("Ngon ngu:", self.lang_combo)
        form.addRow("Preset:", self.preset_combo)
        root.addWidget(form_box)

        instruct_box = QGroupBox("Instruct (mo ta giong)")
        il = QVBoxLayout(instruct_box)
        self.instruct_edit = QPlainTextEdit()
        self.instruct_edit.setPlaceholderText(
            "VD: 'A young female teacher explaining math, warm and patient, medium pace.'"
        )
        il.addWidget(self.instruct_edit)
        root.addWidget(instruct_box)

        text_box = QGroupBox("Cau test")
        tl = QVBoxLayout(text_box)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText("Hello, this is a voice design preview.")
        tl.addWidget(self.text_edit)
        root.addWidget(text_box)

        btns = QHBoxLayout()
        self.preview_btn = QPushButton("Preview")
        self.save_btn = QPushButton("Luu vao library")
        self.close_btn = QPushButton("Dong")
        btns.addWidget(self.preview_btn)
        btns.addWidget(self.save_btn)
        btns.addStretch(1)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

        self.status_label = QLabel('')
        self.status_label.setStyleSheet("color: #888;")
        root.addWidget(self.status_label)

        self.preview_btn.clicked.connect(self._do_preview)
        self.save_btn.clicked.connect(self._do_save)
        self.close_btn.clicked.connect(self.close)

    def _on_preset(self, name: str) -> None:
        val = INSTRUCT_PRESETS.get(name, '')
        if val:
            self.instruct_edit.setPlainText(val)
        elif name == 'None':
            self.instruct_edit.clear()

    def _do_preview(self) -> None:
        instruct = self.instruct_edit.toPlainText().strip()
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Thieu text", "Vui long nhap text de preview.")
            return
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Dang xu ly", "Preview dang chay, vui long doi.")
            return
        out_path = os.path.join(tempfile.gettempdir(), f"voice_design_preview_{os.getpid()}.wav")
        self.status_label.setText("Dang generate...")
        self.preview_btn.setEnabled(False)
        self._worker = _DesignWorker(
            self.engine, text, instruct, self.lang_combo.currentData(), out_path
        )
        self._worker.done.connect(self._on_preview_done)
        self._worker.failed.connect(self._on_preview_failed)
        self._worker.start()

    def _on_preview_done(self, path: str) -> None:
        self._last_preview = path
        self.status_label.setText(f"Preview luu tai: {path}")
        self.preview_btn.setEnabled(True)
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PyQt6.QtCore import QUrl
            if not hasattr(self, '_preview_player'):
                self._preview_player = QMediaPlayer(self)
                self._preview_audio = QAudioOutput(self)
                self._preview_player.setAudioOutput(self._preview_audio)
            self._preview_player.setSource(QUrl.fromLocalFile(path))
            self._preview_player.play()
        except Exception:
            pass

    def _on_preview_failed(self, err: str) -> None:
        self.status_label.setText(f"Loi: {err}")
        self.preview_btn.setEnabled(True)
        QMessageBox.warning(self, "Loi preview", err)

    def _do_save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Thieu ten", "Nhap ten cho giong nay.")
            return
        if self.library is None:
            QMessageBox.information(self, "Chua co library", "Voice library chua san sang.")
            return
        profile = VoiceProfile(
            id=f"design_{name}",
            name=name,
            mode='design',
            language=self.lang_combo.currentData(),
            instruct=self.instruct_edit.toPlainText().strip(),
        )
        self.library.add(profile, copy_ref_audio=False)
        self.profileSaved.emit(profile)
        QMessageBox.information(self, "Da luu", f"Da luu giong '{name}' vao library.")
