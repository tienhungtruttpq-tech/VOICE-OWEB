"""Voice manager — hien thi va quan ly custom voices da luu."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QGroupBox, QFormLayout,
)


class VoiceManagerDialog(QDialog):
    voiceChosen = pyqtSignal(str)  # voice profile id

    def __init__(self, library, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Voice Manager")
        self.resize(600, 480)
        self.library = library
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_select)
        left.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.use_btn = QPushButton("Dung giong nay")
        self.del_btn = QPushButton("Xoa")
        self.refresh_btn = QPushButton("Refresh")
        btn_row.addWidget(self.use_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addWidget(self.refresh_btn)
        left.addLayout(btn_row)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        details = QGroupBox("Chi tiet")
        form = QFormLayout(details)
        self.name_label = QLabel('-')
        self.mode_label = QLabel('-')
        self.lang_label = QLabel('-')
        self.ref_label = QLabel('-')
        self.ref_label.setWordWrap(True)
        self.instruct_label = QLabel('-')
        self.instruct_label.setWordWrap(True)
        form.addRow("Ten:", self.name_label)
        form.addRow("Mode:", self.mode_label)
        form.addRow("Ngon ngu:", self.lang_label)
        form.addRow("Ref audio:", self.ref_label)
        form.addRow("Instruct:", self.instruct_label)
        right.addWidget(details)
        right.addStretch(1)
        root.addLayout(right, 1)

        self.use_btn.clicked.connect(self._on_use)
        self.del_btn.clicked.connect(self._on_delete)
        self.refresh_btn.clicked.connect(self._refresh)

    def _refresh(self) -> None:
        self.list_widget.clear()
        for p in self.library.list():
            item = QListWidgetItem(f"[{p.mode}] {p.name}")
            item.setData(0x0100, p.id)  # UserRole = 256
            self.list_widget.addItem(item)

    def _on_select(self, current, previous) -> None:
        if current is None:
            return
        voice_id = current.data(0x0100)
        p = self.library.get(voice_id)
        if p is None:
            return
        self.name_label.setText(p.name)
        self.mode_label.setText(p.mode)
        self.lang_label.setText(p.language)
        self.ref_label.setText(p.ref_audio or '-')
        self.instruct_label.setText(p.instruct or '-')

    def _on_use(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.voiceChosen.emit(item.data(0x0100))
        self.accept()

    def _on_delete(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        voice_id = item.data(0x0100)
        if QMessageBox.question(self, "Xoa giong", f"Xoa giong '{item.text()}'?") == QMessageBox.StandardButton.Yes:
            self.library.remove(voice_id)
            self._refresh()
