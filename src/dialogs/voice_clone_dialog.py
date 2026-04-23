"""Voice Clone dialog — clone giong tu reference audio + transcript."""

from __future__ import annotations

import os
import tempfile

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLabel,
    QPlainTextEdit, QPushButton, QGroupBox, QMessageBox, QLineEdit,
    QFileDialog, QCheckBox,
)

from ..core.tts_engine import TTSEngine
from ..core.audio_processor import save_wav
from ..core.voice_library import VoiceProfile
from ..utils.constants import LANGUAGES, DEFAULT_LANGUAGE


class _CloneWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        engine: TTSEngine,
        ref_audio: str,
        ref_text: str,
        test_text: str,
        lang: str,
        x_vector_only: bool,
        out_path: str,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.ref_audio = ref_audio
        self.ref_text = ref_text
        self.test_text = test_text
        self.lang = lang
        self.x_vector_only = x_vector_only
        self.out_path = out_path

    def run(self) -> None:
        try:
            self.engine.set_mode('clone')
            self.engine.set_language(self.lang)
            self.engine.set_reference(self.ref_audio, self.ref_text)
            if not self.engine.is_loaded:
                self.engine.load()
            self.engine.create_clone_prompt(x_vector_only=self.x_vector_only)
            audio = self.engine.generate(self.test_text)
            save_wav(self.out_path, audio, self.engine.OUTPUT_SAMPLE_RATE)
            self.done.emit(self.out_path)
        except Exception as e:
            self.failed.emit(str(e))


class VoiceCloneDialog(QDialog):
    profileSaved = pyqtSignal(VoiceProfile)

    def __init__(self, engine: TTSEngine | None = None, library=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Voice Clone — clone tu reference audio")
        self.resize(680, 620)
        self.engine = engine
        self.library = library
        self._worker: _CloneWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        cfg_box = QGroupBox("Thong tin")
        form = QFormLayout(cfg_box)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ten giong (vd: me_calm_en)")

        self.lang_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.lang_combo.addItem(label, code)
        self.lang_combo.setCurrentIndex(list(LANGUAGES.keys()).index(DEFAULT_LANGUAGE))

        form.addRow("Ten:", self.name_edit)
        form.addRow("Ngon ngu:", self.lang_combo)
        root.addWidget(cfg_box)

        ref_box = QGroupBox("Reference audio (3+ giay, ro net)")
        rl = QVBoxLayout(ref_box)
        row1 = QHBoxLayout()
        self.ref_path_edit = QLineEdit()
        self.ref_path_edit.setPlaceholderText("Chon file .wav hoac nhap URL/path")
        self.ref_browse_btn = QPushButton("Browse...")
        row1.addWidget(self.ref_path_edit, 1)
        row1.addWidget(self.ref_browse_btn)
        rl.addLayout(row1)

        self.ref_text_edit = QPlainTextEdit()
        self.ref_text_edit.setPlaceholderText(
            "Transcript chinh xac cua reference audio (sai → clone kem)."
        )
        self.ref_text_edit.setMaximumHeight(100)
        rl.addWidget(self.ref_text_edit)

        self.x_vec_chk = QCheckBox(
            "x_vector_only_mode (khong can transcript — chat luong thap hon)"
        )
        rl.addWidget(self.x_vec_chk)
        root.addWidget(ref_box)

        test_box = QGroupBox("Cau test (text moi de clone sang)")
        tl = QVBoxLayout(test_box)
        self.test_edit = QPlainTextEdit()
        self.test_edit.setPlainText("This is a cloned voice saying some new text.")
        tl.addWidget(self.test_edit)
        root.addWidget(test_box)

        btns = QHBoxLayout()
        self.preview_btn = QPushButton("Preview clone")
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

        self.ref_browse_btn.clicked.connect(self._browse_ref)
        self.preview_btn.clicked.connect(self._do_preview)
        self.save_btn.clicked.connect(self._do_save)
        self.close_btn.clicked.connect(self.close)

    def _browse_ref(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chon reference audio", "", "Audio (*.wav *.mp3 *.flac *.ogg)"
        )
        if path:
            self.ref_path_edit.setText(path)

    def _do_preview(self) -> None:
        ref_audio = self.ref_path_edit.text().strip()
        ref_text = self.ref_text_edit.toPlainText().strip()
        test_text = self.test_edit.toPlainText().strip()
        x_vec_only = self.x_vec_chk.isChecked()

        if not ref_audio:
            QMessageBox.warning(self, "Thieu reference", "Chon file reference audio truoc.")
            return
        if not x_vec_only and not ref_text:
            QMessageBox.warning(
                self,
                "Thieu transcript",
                "Nhap transcript hoac tick 'x_vector_only_mode'."
            )
            return
        if not test_text:
            QMessageBox.warning(self, "Thieu text", "Nhap cau test.")
            return
        if self.engine is None:
            QMessageBox.warning(self, "Chua co engine", "Engine chua duoc gan vao dialog.")
            return
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Dang xu ly", "Preview dang chay.")
            return

        out_path = os.path.join(tempfile.gettempdir(), f"voice_clone_preview_{os.getpid()}.wav")
        self.status_label.setText("Dang tao clone prompt + generate...")
        self.preview_btn.setEnabled(False)
        self._worker = _CloneWorker(
            self.engine, ref_audio, ref_text, test_text,
            self.lang_combo.currentData(), x_vec_only, out_path,
        )
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, path: str) -> None:
        self.status_label.setText(f"Preview luu tai: {path}")
        self.preview_btn.setEnabled(True)
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PyQt6.QtCore import QUrl
            if not hasattr(self, '_pl'):
                self._pl = QMediaPlayer(self)
                self._out = QAudioOutput(self)
                self._pl.setAudioOutput(self._out)
            self._pl.setSource(QUrl.fromLocalFile(path))
            self._pl.play()
        except Exception:
            pass

    def _on_failed(self, err: str) -> None:
        self.status_label.setText(f"Loi: {err}")
        self.preview_btn.setEnabled(True)
        QMessageBox.warning(self, "Loi clone", err)

    def _do_save(self) -> None:
        name = self.name_edit.text().strip()
        ref_audio = self.ref_path_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Thieu ten", "Nhap ten.")
            return
        if not ref_audio:
            QMessageBox.warning(self, "Thieu reference", "Chon reference audio.")
            return
        if self.library is None:
            QMessageBox.information(self, "Chua co library", "Voice library chua san sang.")
            return
        profile = VoiceProfile(
            id=f"clone_{name}",
            name=name,
            mode='clone',
            language=self.lang_combo.currentData(),
            ref_audio=ref_audio,
            ref_text=self.ref_text_edit.toPlainText().strip(),
        )
        self.library.add(profile, copy_ref_audio=True)
        self.profileSaved.emit(profile)
        QMessageBox.information(self, "Da luu", f"Da luu clone '{name}'.")
