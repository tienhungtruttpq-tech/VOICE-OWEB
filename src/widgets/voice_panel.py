"""Voice panel — chon mode, ngon ngu, speaker, speed, device, instruct."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLabel,
    QSlider, QDoubleSpinBox, QPlainTextEdit, QPushButton, QGroupBox,
    QFileDialog,
)

from ..utils.constants import (
    LANGUAGES, DEFAULT_LANGUAGE,
    QWEN3_CUSTOM_SPEAKERS, get_speakers_for_language,
    TTS_MODES, DEFAULT_MODE,
    MODEL_SIZES, DEFAULT_MODEL_SIZE,
    DEVICES, DEFAULT_DEVICE,
    INSTRUCT_PRESETS,
    DEFAULT_SPEED, MIN_SPEED, MAX_SPEED,
)


class VoicePanel(QWidget):
    modeChanged = pyqtSignal(str)
    languageChanged = pyqtSignal(str)
    voiceChanged = pyqtSignal(str)
    speedChanged = pyqtSignal(float)
    deviceChanged = pyqtSignal(str)
    modelSizeChanged = pyqtSignal(str)
    instructChanged = pyqtSignal(str)
    referenceChanged = pyqtSignal(str, str)  # ref_audio, ref_text

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._wire()
        self._on_mode_changed()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # --- Mode + Model size ---
        mode_box = QGroupBox("Che do")
        mode_form = QFormLayout(mode_box)
        self.mode_combo = QComboBox()
        for key, label in TTS_MODES.items():
            self.mode_combo.addItem(label, key)
        self.mode_combo.setCurrentIndex(list(TTS_MODES.keys()).index(DEFAULT_MODE))

        self.size_combo = QComboBox()
        for key, label in MODEL_SIZES.items():
            self.size_combo.addItem(label, key)
        self.size_combo.setCurrentIndex(list(MODEL_SIZES.keys()).index(DEFAULT_MODEL_SIZE))

        mode_form.addRow("Mode:", self.mode_combo)
        mode_form.addRow("Model size:", self.size_combo)
        root.addWidget(mode_box)

        # --- Language + Speaker ---
        voice_box = QGroupBox("Giong noi")
        voice_form = QFormLayout(voice_box)

        self.lang_combo = QComboBox()
        for key, label in LANGUAGES.items():
            self.lang_combo.addItem(label, key)
        self.lang_combo.setCurrentIndex(list(LANGUAGES.keys()).index(DEFAULT_LANGUAGE))

        self.voice_combo = QComboBox()
        self._refresh_speakers(DEFAULT_LANGUAGE)

        voice_form.addRow("Ngon ngu:", self.lang_combo)
        voice_form.addRow("Speaker:", self.voice_combo)
        root.addWidget(voice_box)

        # --- Speed + Device ---
        perf_box = QGroupBox("Hieu nang & Toc do")
        perf_form = QFormLayout(perf_box)

        speed_row = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(int(MIN_SPEED * 100))
        self.speed_slider.setMaximum(int(MAX_SPEED * 100))
        self.speed_slider.setValue(int(DEFAULT_SPEED * 100))

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(MIN_SPEED, MAX_SPEED)
        self.speed_spin.setSingleStep(0.05)
        self.speed_spin.setValue(DEFAULT_SPEED)
        self.speed_spin.setDecimals(2)

        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(self.speed_spin, 0)
        speed_widget = QWidget()
        speed_widget.setLayout(speed_row)

        self.device_combo = QComboBox()
        for key, label in DEVICES.items():
            self.device_combo.addItem(label, key)
        self.device_combo.setCurrentIndex(list(DEVICES.keys()).index(DEFAULT_DEVICE))

        perf_form.addRow("Toc do:", speed_widget)
        perf_form.addRow("Device:", self.device_combo)
        root.addWidget(perf_box)

        # --- Instruct (cho custom + design) ---
        self.instruct_box = QGroupBox("Instruct (natural-language)")
        inst_layout = QVBoxLayout(self.instruct_box)
        self.instruct_preset = QComboBox()
        for key in INSTRUCT_PRESETS.keys():
            self.instruct_preset.addItem(key)
        self.instruct_edit = QPlainTextEdit()
        self.instruct_edit.setPlaceholderText(
            'VD: "Speak warmly, like telling a bedtime story, slow pace."'
        )
        self.instruct_edit.setMaximumHeight(80)
        inst_layout.addWidget(self.instruct_preset)
        inst_layout.addWidget(self.instruct_edit)
        root.addWidget(self.instruct_box)

        # --- Reference (cho clone) ---
        self.ref_box = QGroupBox("Reference audio (Voice Clone)")
        ref_layout = QVBoxLayout(self.ref_box)
        ref_row = QHBoxLayout()
        self.ref_path_label = QLabel("(chua chon file)")
        self.ref_path_label.setWordWrap(True)
        self.ref_browse_btn = QPushButton("Browse audio...")
        ref_row.addWidget(self.ref_path_label, 1)
        ref_row.addWidget(self.ref_browse_btn)
        ref_layout.addLayout(ref_row)

        self.ref_text_edit = QPlainTextEdit()
        self.ref_text_edit.setPlaceholderText(
            "Transcript cua reference audio (nen chinh xac → clone chat luong cao)"
        )
        self.ref_text_edit.setMaximumHeight(80)
        ref_layout.addWidget(self.ref_text_edit)
        root.addWidget(self.ref_box)

        root.addStretch(1)

    def _wire(self) -> None:
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.size_combo.currentIndexChanged.connect(
            lambda: self.modelSizeChanged.emit(self.size_combo.currentData())
        )
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.voice_combo.currentIndexChanged.connect(
            lambda: self.voiceChanged.emit(self.voice_combo.currentData() or self.voice_combo.currentText())
        )
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_spin.setValue(v / 100.0)
        )
        self.speed_spin.valueChanged.connect(self._on_speed_spin)
        self.device_combo.currentIndexChanged.connect(
            lambda: self.deviceChanged.emit(self.device_combo.currentData())
        )
        self.instruct_preset.currentTextChanged.connect(self._on_preset_changed)
        self.instruct_edit.textChanged.connect(
            lambda: self.instructChanged.emit(self.instruct_edit.toPlainText().strip())
        )
        self.ref_browse_btn.clicked.connect(self._browse_reference)
        self.ref_text_edit.textChanged.connect(self._on_ref_text_changed)

    def _refresh_speakers(self, lang_code: str) -> None:
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        speakers = get_speakers_for_language(lang_code)
        for sp in speakers:
            info = QWEN3_CUSTOM_SPEAKERS.get(sp, {})
            label = f"{sp} ({info.get('gender', '?')})"
            self.voice_combo.addItem(label, sp)
        self.voice_combo.blockSignals(False)

    def _on_mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        show_instruct = mode in ('custom', 'design')
        show_ref = mode == 'clone'
        show_speaker = mode == 'custom'

        self.instruct_box.setVisible(show_instruct)
        self.ref_box.setVisible(show_ref)
        self.voice_combo.setEnabled(show_speaker)
        self.modeChanged.emit(mode)

    def _on_language_changed(self) -> None:
        lang = self.lang_combo.currentData()
        self._refresh_speakers(lang)
        self.languageChanged.emit(lang)

    def _on_speed_spin(self, v: float) -> None:
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(int(v * 100))
        self.speed_slider.blockSignals(False)
        self.speedChanged.emit(float(v))

    def _on_preset_changed(self, name: str) -> None:
        val = INSTRUCT_PRESETS.get(name, '')
        if val:
            self.instruct_edit.setPlainText(val)
        elif name == 'None':
            self.instruct_edit.clear()

    def _browse_reference(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chon reference audio", "", "Audio (*.wav *.mp3 *.flac *.ogg)"
        )
        if path:
            self.ref_path_label.setText(path)
            self._emit_reference()

    def _on_ref_text_changed(self) -> None:
        self._emit_reference()

    def _emit_reference(self) -> None:
        path = self.ref_path_label.text()
        if path == "(chua chon file)":
            path = ''
        text = self.ref_text_edit.toPlainText().strip()
        self.referenceChanged.emit(path, text)

    # Public getters
    def current_mode(self) -> str:
        return self.mode_combo.currentData()

    def current_language(self) -> str:
        return self.lang_combo.currentData()

    def current_voice(self) -> str:
        return self.voice_combo.currentData() or self.voice_combo.currentText()

    def current_speed(self) -> float:
        return float(self.speed_spin.value())

    def current_device(self) -> str:
        return self.device_combo.currentData()

    def current_model_size(self) -> str:
        return self.size_combo.currentData()

    def current_instruct(self) -> str:
        return self.instruct_edit.toPlainText().strip()

    def current_reference(self) -> tuple[str, str]:
        p = self.ref_path_label.text()
        if p == "(chua chon file)":
            p = ''
        return p, self.ref_text_edit.toPlainText().strip()
