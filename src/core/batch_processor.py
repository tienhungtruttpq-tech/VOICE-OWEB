"""Batch TTS processor — xu ly hang loat voi async I/O + throttled UI updates."""

from __future__ import annotations

import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from .audio_processor import save_wav, duration_ms, normalize_audio, resample
from .srt_parser import Segment, export_srt, build_srt_from_durations


@dataclass
class BatchOptions:
    output_dir: str
    sample_rate: int = 24000
    output_format: str = 'wav'
    normalize: bool = True
    join_output: bool = True
    auto_generate_srt: bool = True
    silence_ms: int = 250
    per_file_subdir: bool = True


class BatchProcessor(QThread):
    """Xu ly batch TTS trong background thread."""

    progress = pyqtSignal(int, int, str)           # done, total, eta_text
    segment_done = pyqtSignal(int, str, str)       # row_index, audio_path, status
    segments_done = pyqtSignal(list)               # batched list of tuples
    log = pyqtSignal(str)
    finished_batch = pyqtSignal(bool, str)         # success, message

    def __init__(
        self,
        engine,
        segments: list[Segment],
        options: BatchOptions,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.segments = segments
        self.options = options
        self._stop = False
        self._io_pool = ThreadPoolExecutor(max_workers=4)
        self._pending_updates: list[tuple[int, str, str]] = []
        self._last_flush = 0.0

    def stop(self) -> None:
        self._stop = True

    def _flush_updates(self, force: bool = False) -> None:
        now = time.time()
        if not self._pending_updates:
            return
        if not force and (now - self._last_flush) < 0.1:
            return
        updates = self._pending_updates
        self._pending_updates = []
        self._last_flush = now
        self.segments_done.emit(updates)

    def _format_eta(self, done: int, total: int, start: float) -> str:
        if done <= 0:
            return '--'
        elapsed = time.time() - start
        per = elapsed / max(1, done)
        remain = per * max(0, total - done)
        m, s = divmod(int(remain), 60)
        return f"ETA {m:02d}:{s:02d} ({per:.2f}s/seg)"

    def run(self) -> None:
        try:
            import torch
        except ImportError:
            torch = None

        total = len(self.segments)
        if total == 0:
            self.finished_batch.emit(False, "Khong co segment nao de xu ly.")
            return

        start_time = time.time()
        self.log.emit(f"Bat dau batch {total} segments, output: {self.options.output_dir}")

        # Setup output structure
        output_dir = self.options.output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Group theo source file neu nhieu file
        by_source: dict[str, list[Segment]] = {}
        for seg in self.segments:
            by_source.setdefault(seg.source_file or '_default', []).append(seg)

        # Nap engine neu chua
        if not self.engine.is_loaded:
            self.log.emit("Loading model...")
            try:
                self.engine.load()
            except Exception as e:
                self.log.emit(f"Loi tai model: {e}")
                self.finished_batch.emit(False, str(e))
                return

        # Uu tien: neu mode clone → cache clone prompt 1 lan
        if getattr(self.engine, 'mode', None) == getattr(self.engine, 'MODE_CLONE', 'clone'):
            try:
                if self.engine._ref_audio is not None and self.engine._clone_prompt is None:
                    self.log.emit("Dang cache voice clone prompt (mot lan cho ca batch)...")
                    self.engine.create_clone_prompt()
            except Exception as e:
                self.log.emit(f"Khong tao duoc clone prompt: {e}")

        done = 0
        success = True
        last_log_pct = -1

        ctx = torch.inference_mode() if torch is not None else _NullCtx()

        try:
            with ctx:
                for source, segs in by_source.items():
                    if self._stop:
                        break

                    file_stem = os.path.splitext(os.path.basename(source))[0] or 'output'
                    if self.options.per_file_subdir:
                        file_out_dir = os.path.join(output_dir, file_stem)
                    else:
                        file_out_dir = output_dir
                    os.makedirs(file_out_dir, exist_ok=True)

                    produced_paths: list[str] = []
                    produced_durations_ms: list[int] = []
                    produced_texts: list[str] = []

                    for seg in segs:
                        if self._stop:
                            break
                        row_idx = seg.extras.get('row_index', seg.index - 1)
                        try:
                            audio = self.engine.generate(seg.text)
                            if self.options.normalize:
                                audio = normalize_audio(audio)
                            target_sr = self.options.sample_rate
                            if target_sr != self.engine.OUTPUT_SAMPLE_RATE:
                                audio = resample(audio, self.engine.OUTPUT_SAMPLE_RATE, target_sr)

                            fname = f"{seg.index:04d}.wav"
                            out_path = os.path.join(file_out_dir, fname)

                            self._io_pool.submit(save_wav, out_path, audio, target_sr)

                            produced_paths.append(out_path)
                            produced_durations_ms.append(duration_ms(audio, target_sr))
                            produced_texts.append(seg.text)

                            seg.audio_path = out_path
                            seg.status = 'done'
                            self._pending_updates.append((row_idx, out_path, 'done'))

                        except Exception as e:
                            success = False
                            err = f"Loi segment {seg.index}: {e}"
                            self.log.emit(err)
                            seg.status = 'error'
                            self._pending_updates.append((row_idx, '', 'error'))

                        done += 1
                        self._flush_updates()

                        pct = int(done * 100 / total)
                        if pct >= last_log_pct + 2 or done == total:
                            last_log_pct = pct
                            eta = self._format_eta(done, total, start_time)
                            self.progress.emit(done, total, eta)
                            self.log.emit(f"Tien do: {done}/{total} ({pct}%) {eta}")

                    # Sau moi file: optional auto-join + auto-srt
                    if self.options.join_output and produced_paths:
                        try:
                            self._io_pool.submit(
                                self._post_file_tasks,
                                file_stem, file_out_dir, produced_paths,
                                produced_texts, produced_durations_ms,
                            )
                        except Exception as e:
                            self.log.emit(f"Khong the schedule post-tasks: {e}")

        except Exception as e:
            success = False
            self.log.emit("Batch error:\n" + traceback.format_exc())
            self._flush_updates(force=True)
            self.finished_batch.emit(False, str(e))
            self._io_pool.shutdown(wait=True)
            return

        self._flush_updates(force=True)
        self._io_pool.shutdown(wait=True)

        elapsed = time.time() - start_time
        msg = f"Hoan thanh {done}/{total} segments trong {elapsed:.1f}s."
        self.log.emit(msg)
        self.finished_batch.emit(success and not self._stop, msg)

    def _post_file_tasks(
        self,
        file_stem: str,
        out_dir: str,
        audio_paths: list[str],
        texts: list[str],
        durations_ms: list[int],
    ) -> None:
        """Join audio + export SRT tu thuc te duration."""
        from .audio_processor import join_audio_files

        joined_path = os.path.join(out_dir, f"{file_stem}.wav")
        try:
            join_audio_files(
                audio_paths,
                joined_path,
                silence_ms=self.options.silence_ms,
                sample_rate=self.options.sample_rate,
            )
            self.log.emit(f"Da ghep audio: {joined_path}")
        except Exception as e:
            self.log.emit(f"Khong ghep duoc audio: {e}")

        if self.options.auto_generate_srt:
            try:
                srt_path = os.path.join(out_dir, f"{file_stem}.srt")
                segs = build_srt_from_durations(
                    texts, durations_ms, gap_ms=self.options.silence_ms,
                )
                export_srt(segs, srt_path)
                self.log.emit(f"Da tao SRT: {srt_path}")
            except Exception as e:
                self.log.emit(f"Khong tao duoc SRT: {e}")


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
