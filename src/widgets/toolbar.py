"""Toolbar — cac nut action chinh."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QToolBar, QWidget


class AppToolbar(QToolBar):
    importRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    voiceManagerRequested = pyqtSignal()
    voiceDesignRequested = pyqtSignal()
    voiceCloneRequested = pyqtSignal()
    srtCreatorRequested = pyqtSignal()
    exportProjectRequested = pyqtSignal()
    importProjectRequested = pyqtSignal()
    aboutRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Main", parent)
        self.setMovable(False)

        self.a_import = self.addAction("Import SRT/TXT")
        self.a_clear = self.addAction("Clear")
        self.addSeparator()
        self.a_voice_mgr = self.addAction("Voice Manager")
        self.a_voice_design = self.addAction("Voice Design")
        self.a_voice_clone = self.addAction("Voice Clone")
        self.addSeparator()
        self.a_srt_creator = self.addAction("Tao SRT")
        self.addSeparator()
        self.a_export = self.addAction("Export project")
        self.a_import_proj = self.addAction("Import project")
        self.addSeparator()
        self.a_about = self.addAction("About")

        self.a_import.triggered.connect(self.importRequested)
        self.a_clear.triggered.connect(self.clearRequested)
        self.a_voice_mgr.triggered.connect(self.voiceManagerRequested)
        self.a_voice_design.triggered.connect(self.voiceDesignRequested)
        self.a_voice_clone.triggered.connect(self.voiceCloneRequested)
        self.a_srt_creator.triggered.connect(self.srtCreatorRequested)
        self.a_export.triggered.connect(self.exportProjectRequested)
        self.a_import_proj.triggered.connect(self.importProjectRequested)
        self.a_about.triggered.connect(self.aboutRequested)


Toolbar = AppToolbar
