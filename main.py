"""Entry point — Qwen3-TTS Studio."""

from __future__ import annotations

import sys

from src.app import create_app
from src.main_window import MainWindow


def main() -> int:
    app = create_app(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
