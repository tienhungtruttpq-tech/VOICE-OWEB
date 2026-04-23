"""QApplication setup."""

from __future__ import annotations

import os
import sys

from PyQt6.QtWidgets import QApplication


def _load_stylesheet(app: QApplication) -> None:
    qss_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'styles.qss'))
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())


def create_app(argv: list[str] | None = None) -> QApplication:
    argv = argv if argv is not None else sys.argv
    app = QApplication(argv)
    app.setApplicationName('Qwen3-TTS Studio')
    app.setOrganizationName('Qwen3-TTS Studio')
    _load_stylesheet(app)
    return app
