"""About dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from ..utils.constants import APP_NAME, APP_VERSION


ABOUT_HTML = f"""
<h2>{APP_NAME}</h2>
<p><b>Version:</b> {APP_VERSION}</p>
<p>Desktop TTS Studio su dung engine <b>Qwen3-TTS</b> cua Alibaba.</p>
<ul>
  <li>10 ngon ngu (Chinese, English, Japanese, Korean, German, French,
      Russian, Portuguese, Spanish, Italian)</li>
  <li>3 che do: CustomVoice (9 preset speakers + instruct),
      VoiceDesign, VoiceClone</li>
  <li>Batch processing, auto join, auto SRT, voice library</li>
  <li>Toi uu GPU bf16 + FlashAttention 2</li>
</ul>
<p>Qwen3-TTS: <a href="https://github.com/QwenLM/Qwen3-TTS">https://github.com/QwenLM/Qwen3-TTS</a></p>
"""


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ve {APP_NAME}")
        self.resize(480, 360)

        layout = QVBoxLayout(self)
        label = QLabel(ABOUT_HTML)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        layout.addWidget(label)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Dong")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
