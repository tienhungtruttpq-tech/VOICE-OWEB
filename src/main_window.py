"""Main window — ket noi cac panels, toolbar, table, player."""

from __future__ import annotations

import os
from dataclasses import asdict

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFileDialog,
    QMessageBox,
)

from .core.tts_engine import TTSEngine
from .core.batch_processor import BatchProcessor, BatchOptions
from .core.srt_parser import parse_file, Segment, export_srt
from .core.voice_library import VoiceLibrary
from .widgets.voice_panel import VoicePanel
from .widgets.batch_panel import BatchPanel
from .widgets.options_panel import OptionsPanel
from .widgets.toolbar import AppToolbar
from .widgets.subtitle_table import SubtitleTable
from .widgets.audio_player import AudioPlayer
from .widgets.status_bar import AppStatusBar
from .dialogs.voice_design_dialog import VoiceDesignDialog
from .dialogs.voice_clone_dialog import VoiceCloneDialog
from .dialogs.voice_manager_dialog import VoiceManagerDialog
from .dialogs.srt_creator_dialog import SRTCreatorDialog
from .dialogs.about_dialog import AboutDialog
from .utils.constants import APP_NAME, APP_VERSION
from .utils.helpers import export_project, import_project, ensure_dir


class EngineLoader(QThread):
    """Tai/reload engine trong background, khong block UI."""

    loaded = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, engine: TTSEngine) -> None:
        super().__init__()
        self.engine = engine

    def run(self) -> None:
        try:
            self.engine.load()
            self.loaded.emit()
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1400, 860)

        self.engine = TTSEngine()
        self.library = VoiceLibrary(
            data_path=os.path.abspath('data/voices.json'),
            voices_dir=os.path.abspath('voices'),
        )
        self._engine_loader: EngineLoader | None = None
        self._batch: BatchProcessor | None = None

        self._build_ui()
        self._wire()

    # ------------------- UI -------------------

    def _build_ui(self) -> None:
        self.toolbar = AppToolbar(self)
        self.addToolBar(self.toolbar)

        self.voice_panel = VoicePanel()
        self.options_panel = OptionsPanel()
        self.batch_panel = BatchPanel()
        self.subtitle_table = SubtitleTable()
        self.audio_player = AudioPlayer()

        self.status = AppStatusBar(self)
        self.setStatusBar(self.status)

        # Left column (voice/options) + right column (table/batch/player)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        splitter_left = QSplitter(Qt.Orientation.Vertical)
        splitter_left.addWidget(self.voice_panel)
        splitter_left.addWidget(self.options_panel)
        splitter_left.setStretchFactor(0, 2)
        splitter_left.setStretchFactor(1, 1)
        left_layout.addWidget(splitter_left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        splitter_right = QSplitter(Qt.Orientation.Vertical)
        splitter_right.addWidget(self.subtitle_table)
        splitter_right.addWidget(self.batch_panel)
        splitter_right.addWidget(self.audio_player)
        splitter_right.setStretchFactor(0, 4)
        splitter_right.setStretchFactor(1, 2)
        splitter_right.setStretchFactor(2, 0)
        right_layout.addWidget(splitter_right)

        root_split = QSplitter(Qt.Orientation.Horizontal)
        root_split.addWidget(left)
        root_split.addWidget(right)
        root_split.setStretchFactor(0, 1)
        root_split.setStretchFactor(1, 3)

        self.setCentralWidget(root_split)

    def _wire(self) -> None:
        # Toolbar
        self.toolbar.importRequested.connect(self._do_import)
        self.toolbar.clearRequested.connect(self._do_clear)
        self.toolbar.voiceManagerRequested.connect(self._open_voice_manager)
        self.toolbar.voiceDesignRequested.connect(self._open_voice_design)
        self.toolbar.voiceCloneRequested.connect(self._open_voice_clone)
        self.toolbar.srtCreatorRequested.connect(self._open_srt_creator)
        self.toolbar.exportProjectRequested.connect(self._export_project)
        self.toolbar.importProjectRequested.connect(self._import_project)
        self.toolbar.aboutRequested.connect(self._open_about)

        # Voice panel → engine
        self.voice_panel.modeChanged.connect(self._on_mode_changed)
        self.voice_panel.languageChanged.connect(self.engine.set_language)
        self.voice_panel.voiceChanged.connect(self.engine.set_voice)
        self.voice_panel.speedChanged.connect(self.engine.set_speed)
        self.voice_panel.deviceChanged.connect(self._on_device_changed)
        self.voice_panel.modelSizeChanged.connect(self._on_model_size_changed)
        self.voice_panel.instructChanged.connect(self.engine.set_instruct)
        self.voice_panel.referenceChanged.connect(
            lambda ref, text: self.engine.set_reference(ref or None, text)
        )

        # Batch panel
        self.batch_panel.startRequested.connect(self._start_batch)
        self.batch_panel.stopRequested.connect(self._stop_batch)

        # Table row preview → play audio
        self.subtitle_table.rowPreview.connect(self._preview_row)

    # ------------------- actions -------------------

    def _do_import(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import SRT/TXT", "", "Subtitle (*.srt *.txt)"
        )
        if not paths:
            return
        all_segs: list[Segment] = []
        offset = 0
        for p in paths:
            try:
                segs = parse_file(p)
            except Exception as e:
                QMessageBox.warning(self, f"Loi import {p}", str(e))
                continue
            for s in segs:
                s.index += offset
            offset += len(segs)
            all_segs.extend(segs)
        if all_segs:
            self.subtitle_table.load_segments(all_segs)
            self.status.set_message(f"Da nap {len(all_segs)} segments tu {len(paths)} file.")
            self.batch_panel.append_log(f"Da nap {len(all_segs)} segments.")

    def _do_clear(self) -> None:
        if self.subtitle_table.rowCount() == 0:
            return
        if QMessageBox.question(self, "Clear", "Xoa het bang subtitle?") == QMessageBox.StandardButton.Yes:
            self.subtitle_table.clear_all()
            self.status.set_message("Da clear bang.")

    def _on_mode_changed(self, mode: str) -> None:
        self.engine.set_mode(mode)
        self.status.set_model(f"{mode} ({self.voice_panel.current_model_size()})")
        self._reload_engine_async()

    def _on_device_changed(self, device: str) -> None:
        self.engine.set_device(device)
        self.status.set_device(device)
        self._reload_engine_async()

    def _on_model_size_changed(self, size: str) -> None:
        self.engine.model_size = size
        self.engine._loaded = False
        self.engine.model = None
        self._reload_engine_async()

    def _reload_engine_async(self) -> None:
        if self._engine_loader and self._engine_loader.isRunning():
            return
        self.status.set_message("Dang tai engine...")
        self._engine_loader = EngineLoader(self.engine)
        self._engine_loader.loaded.connect(
            lambda: self.status.set_message("Engine san sang.")
        )
        self._engine_loader.failed.connect(
            lambda err: self.status.set_message(f"Loi tai engine: {err}")
        )
        self._engine_loader.start()

    # ------------------- dialogs -------------------

    def _open_voice_manager(self) -> None:
        dlg = VoiceManagerDialog(self.library, self)
        dlg.voiceChosen.connect(self._apply_voice_profile)
        dlg.exec()

    def _open_voice_design(self) -> None:
        dlg = VoiceDesignDialog(self.engine, self.library, self)
        dlg.exec()

    def _open_voice_clone(self) -> None:
        dlg = VoiceCloneDialog(self.engine, self.library, self)
        dlg.exec()

    def _open_srt_creator(self) -> None:
        dlg = SRTCreatorDialog(self)
        dlg.exec()

    def _open_about(self) -> None:
        AboutDialog(self).exec()

    def _apply_voice_profile(self, voice_id: str) -> None:
        p = self.library.get(voice_id)
        if p is None:
            return
        self.engine.set_mode(p.mode)
        self.engine.set_language(p.language)
        if p.mode == 'custom' and p.speaker:
            self.engine.set_voice(p.speaker)
        self.engine.set_instruct(p.instruct or '')
        if p.mode == 'clone':
            self.engine.set_reference(p.ref_audio or None, p.ref_text or '')
        self.status.set_message(f"Da chon voice: {p.name}")

    # ------------------- batch -------------------

    def _start_batch(self) -> None:
        segments = self.subtitle_table.segments()
        if not segments:
            QMessageBox.information(self, "Chua co du lieu", "Import SRT/TXT truoc.")
            return
        output_dir = ensure_dir(self.options_panel.output_dir())
        opts = BatchOptions(
            output_dir=output_dir,
            sample_rate=self.options_panel.sample_rate(),
            output_format=self.options_panel.output_format(),
            normalize=self.options_panel.normalize(),
            join_output=self.options_panel.join_output(),
            auto_generate_srt=self.options_panel.auto_srt(),
            silence_ms=self.options_panel.silence_ms(),
            per_file_subdir=self.options_panel.per_file_subdir(),
        )

        self._batch = BatchProcessor(self.engine, segments, opts, self)
        self._batch.log.connect(self.batch_panel.append_log)
        self._batch.progress.connect(self._on_batch_progress)
        self._batch.segments_done.connect(self.subtitle_table.update_status_batch)
        self._batch.finished_batch.connect(self._on_batch_finished)

        self.batch_panel.set_running(True)
        self.status.set_message(f"Batch bat dau ({len(segments)} segments).")
        self._batch.start()

    def _stop_batch(self) -> None:
        if self._batch and self._batch.isRunning():
            self._batch.stop()
            self.batch_panel.append_log("Da yeu cau dung batch...")

    def _on_batch_progress(self, done: int, total: int, eta: str) -> None:
        self.batch_panel.set_progress(done, total, eta)
        self.status.set_progress(done, total)

    def _on_batch_finished(self, success: bool, msg: str) -> None:
        self.batch_panel.set_running(False)
        self.status.set_message(msg)
        if not success:
            QMessageBox.warning(self, "Batch loi", msg)

    # ------------------- project export/import -------------------

    def _export_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export project", "project.json", "JSON (*.json)")
        if not path:
            return
        segs = self.subtitle_table.segments()
        payload = {
            'app': APP_NAME,
            'version': APP_VERSION,
            'mode': self.voice_panel.current_mode(),
            'language': self.voice_panel.current_language(),
            'voice': self.voice_panel.current_voice(),
            'speed': self.voice_panel.current_speed(),
            'instruct': self.voice_panel.current_instruct(),
            'segments': [
                {
                    'index': s.index, 'start_ms': s.start_ms, 'end_ms': s.end_ms,
                    'text': s.text, 'source_file': s.source_file,
                    'status': s.status, 'audio_path': s.audio_path,
                }
                for s in segs
            ],
        }
        export_project(path, payload)
        self.status.set_message(f"Da export project: {path}")

    def _import_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import project", "", "JSON (*.json)")
        if not path:
            return
        try:
            data = import_project(path)
        except Exception as e:
            QMessageBox.warning(self, "Loi import", str(e))
            return
        segs = [
            Segment(
                index=s.get('index', i + 1),
                start_ms=s.get('start_ms', 0),
                end_ms=s.get('end_ms', 0),
                text=s.get('text', ''),
                source_file=s.get('source_file', ''),
                status=s.get('status', 'pending'),
                audio_path=s.get('audio_path', ''),
            )
            for i, s in enumerate(data.get('segments', []))
        ]
        self.subtitle_table.load_segments(segs)
        self.status.set_message(f"Da import project: {path}")

    def _preview_row(self, row: int) -> None:
        seg = self.subtitle_table.segment_at_row(row)
        if seg and seg.audio_path and os.path.exists(seg.audio_path):
            self.audio_player.load(seg.audio_path)
