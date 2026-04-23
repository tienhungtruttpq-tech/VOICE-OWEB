"""Subtitle table — hien thi SRT segments + status."""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
)

from ..core.srt_parser import Segment
from ..utils.constants import UI_REFRESH_INTERVAL_MS, UI_ROWS_PER_TICK


_STATUS_COLORS = {
    'pending':    QColor('#444'),
    'processing': QColor('#b58900'),
    'done':       QColor('#4caf50'),
    'error':      QColor('#e74c3c'),
    '__file__':   QColor('#3a3f52'),
}


def _ms_to_ts(ms: int) -> str:
    if ms < 0:
        ms = 0
    h = ms // 3_600_000
    m = (ms // 60_000) % 60
    s = (ms // 1000) % 60
    ms_part = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms_part:03d}"


class SubtitleTable(QTableWidget):
    """Bang subtitle voi UI throttling de xu ly hang van rows khong do."""

    rowPreview = pyqtSignal(int)  # request play preview of row

    COL_INDEX = 0
    COL_START = 1
    COL_END = 2
    COL_TEXT = 3
    COL_STATUS = 4
    COL_AUDIO = 5
    HEADERS = ['#', 'Start', 'End', 'Text', 'Status', 'Audio']

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        h = self.horizontalHeader()
        h.setSectionResizeMode(self.COL_TEXT, QHeaderView.ResizeMode.Stretch)
        for c in (self.COL_INDEX, self.COL_START, self.COL_END, self.COL_STATUS, self.COL_AUDIO):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cellDoubleClicked.connect(lambda r, c: self.rowPreview.emit(r))

        self._segments: list[Segment] = []
        self._row_to_seg: dict[int, int] = {}   # row → segment index
        self._dirty_rows: set[int] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(UI_REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._flush_dirty)
        self._timer.start()

    # ------------------- population -------------------

    def load_segments(self, segments: list[Segment]) -> None:
        self.setRowCount(0)
        self._segments = list(segments)
        self._row_to_seg = {}

        # Group headers khi nhieu file
        sources: list[str] = []
        for s in self._segments:
            if s.source_file not in sources:
                sources.append(s.source_file)

        show_headers = len(sources) > 1

        row = 0
        for source in sources:
            if show_headers:
                self.insertRow(row)
                header_item = QTableWidgetItem(f"▸ {source}")
                header_item.setBackground(QBrush(_STATUS_COLORS['__file__']))
                header_item.setForeground(QBrush(QColor('#fff')))
                self.setItem(row, 0, header_item)
                self.setSpan(row, 0, 1, len(self.HEADERS))
                row += 1
            for i, seg in enumerate(self._segments):
                if seg.source_file != source:
                    continue
                self.insertRow(row)
                self._row_to_seg[row] = i
                seg.extras['row_index'] = row
                self._populate_row(row, seg)
                row += 1

    def _populate_row(self, row: int, seg: Segment) -> None:
        self.setItem(row, self.COL_INDEX, QTableWidgetItem(str(seg.index)))
        self.setItem(row, self.COL_START, QTableWidgetItem(_ms_to_ts(seg.start_ms)))
        self.setItem(row, self.COL_END, QTableWidgetItem(_ms_to_ts(seg.end_ms)))
        self.setItem(row, self.COL_TEXT, QTableWidgetItem(seg.text))
        self.setItem(row, self.COL_STATUS, self._status_item(seg.status))
        self.setItem(row, self.COL_AUDIO, QTableWidgetItem(seg.audio_path or ''))

    def _status_item(self, status: str) -> QTableWidgetItem:
        item = QTableWidgetItem(status)
        item.setForeground(QBrush(_STATUS_COLORS.get(status, QColor('#ccc'))))
        return item

    def segments(self) -> list[Segment]:
        return list(self._segments)

    # ------------------- updates (throttled) -------------------

    def update_status_batch(self, updates: Iterable[tuple[int, str, str]]) -> None:
        """Batch update: list of (row, audio_path, status)."""
        for row, audio_path, status in updates:
            if row < 0 or row >= self.rowCount():
                continue
            # Reuse item neu co, khong tao moi
            status_item = self.item(row, self.COL_STATUS)
            if status_item is None:
                status_item = QTableWidgetItem()
                self.setItem(row, self.COL_STATUS, status_item)
            status_item.setText(status)
            status_item.setForeground(QBrush(_STATUS_COLORS.get(status, QColor('#ccc'))))

            audio_item = self.item(row, self.COL_AUDIO)
            if audio_item is None:
                audio_item = QTableWidgetItem()
                self.setItem(row, self.COL_AUDIO, audio_item)
            if audio_path:
                audio_item.setText(audio_path)

            # Update Segment state
            seg_idx = self._row_to_seg.get(row)
            if seg_idx is not None:
                seg = self._segments[seg_idx]
                seg.status = status
                if audio_path:
                    seg.audio_path = audio_path

            self._dirty_rows.add(row)

    def _flush_dirty(self) -> None:
        if not self._dirty_rows:
            return
        # Limit rows repainted per tick
        to_repaint = list(self._dirty_rows)[:UI_ROWS_PER_TICK]
        for row in to_repaint:
            self._dirty_rows.discard(row)
            for c in range(self.columnCount()):
                item = self.item(row, c)
                if item is not None:
                    # No-op set triggers repaint
                    item.setText(item.text())

    def clear_all(self) -> None:
        self.setRowCount(0)
        self._segments = []
        self._row_to_seg = {}
        self._dirty_rows.clear()

    def segment_at_row(self, row: int) -> Segment | None:
        idx = self._row_to_seg.get(row)
        if idx is None:
            return None
        return self._segments[idx]
