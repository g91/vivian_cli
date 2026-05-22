"""ESP-IDF / build controls embedded in the status bar.

[ Target: esp32s3 ▲ ] [ ⚙ Build ] [ ⚡ Flash ▾ ] [ ▶ Monitor ] [ ◼ Stop ]
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QMenu, QToolButton, QWidget


# Common ESP32 targets, oldest → newest. Order chosen to match `idf.py set-target`.
ESP_TARGETS = [
    "esp32",
    "esp32s2",
    "esp32s3",
    "esp32c2",
    "esp32c3",
    "esp32c5",
    "esp32c6",
    "esp32c61",
    "esp32h2",
    "esp32h21",
    "esp32p4",
]


class _UpwardCombo(QComboBox):
    """A QComboBox whose popup is forced to open above the widget.

    Qt usually flips automatically when there's no room below, but in a status
    bar at the very bottom of the screen the heuristic sometimes still picks
    'below', so we reposition explicitly.
    """

    def showPopup(self) -> None:
        super().showPopup()
        view = self.view()
        popup = view.parentWidget()
        if popup is None:
            return
        # Reposition popup so its bottom edge sits just above the combo.
        global_pos = self.mapToGlobal(self.rect().topLeft())
        popup.move(global_pos.x(), global_pos.y() - popup.height())


class ESPStatus(QWidget):
    target_changed = pyqtSignal(str)
    build_requested = pyqtSignal()
    flash_requested = pyqtSignal(str)   # "uart" | "jtag" | "dfu"
    monitor_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(4)

        # Target combo
        self.target_combo = _UpwardCombo()
        self.target_combo.addItems(ESP_TARGETS)
        self.target_combo.setCurrentText("esp32s3")
        self.target_combo.setToolTip("ESP-IDF target chip")
        self.target_combo.currentTextChanged.connect(self.target_changed.emit)
        layout.addWidget(self.target_combo)

        # Build
        self.build_btn = QToolButton()
        self.build_btn.setText("⚙ Build")
        self.build_btn.setToolTip("Compile this project (ESP-IDF / make / single file)")
        self.build_btn.clicked.connect(self.build_requested.emit)
        layout.addWidget(self.build_btn)

        # Flash with method dropdown
        self.flash_btn = QToolButton()
        self.flash_btn.setText("⚡ Flash")
        self.flash_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.flash_btn.setToolTip("Flash firmware (click for default UART, dropdown for other methods)")
        flash_menu = QMenu(self.flash_btn)
        uart_act = QAction("UART (serial)", self)
        jtag_act = QAction("JTAG (OpenOCD)", self)
        dfu_act = QAction("DFU (USB)", self)
        uart_act.triggered.connect(lambda: self.flash_requested.emit("uart"))
        jtag_act.triggered.connect(lambda: self.flash_requested.emit("jtag"))
        dfu_act.triggered.connect(lambda: self.flash_requested.emit("dfu"))
        flash_menu.addAction(uart_act)
        flash_menu.addAction(jtag_act)
        flash_menu.addAction(dfu_act)
        self.flash_btn.setMenu(flash_menu)
        # Default click → UART
        self.flash_btn.clicked.connect(lambda: self.flash_requested.emit("uart"))
        layout.addWidget(self.flash_btn)

        # Monitor
        self.monitor_btn = QToolButton()
        self.monitor_btn.setText("▶ Monitor")
        self.monitor_btn.setToolTip("Open serial monitor (idf.py monitor)")
        self.monitor_btn.clicked.connect(self.monitor_requested.emit)
        layout.addWidget(self.monitor_btn)

        # Stop
        self.stop_btn = QToolButton()
        self.stop_btn.setText("◼ Stop")
        self.stop_btn.setToolTip("Stop the running build / flash / monitor")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        layout.addWidget(self.stop_btn)

        for btn in (self.build_btn, self.flash_btn, self.monitor_btn, self.stop_btn):
            btn.setAutoRaise(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_running(self, running: bool) -> None:
        """Toggle button availability while a subprocess is alive."""
        self.build_btn.setEnabled(not running)
        self.flash_btn.setEnabled(not running)
        self.monitor_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def current_target(self) -> str:
        return self.target_combo.currentText()

    # ── context-sensitive visibility ───────────────────────────────────
    def set_esp_mode(self, on: bool) -> None:
        """Show or hide the ESP-only controls (target, flash, monitor)."""
        for w in (self.target_combo, self.flash_btn, self.monitor_btn):
            w.setVisible(on)

    def set_compiler_label(self, label: str) -> None:
        """Set the Build button text — e.g. '⚙ g++' or '⚙ Build'."""
        if label:
            self.build_btn.setText(f"⚙ {label}")
            self.build_btn.setToolTip(f"Compile with {label}")
        else:
            self.build_btn.setText("⚙ Build")
            self.build_btn.setToolTip("Compile this project")

    def set_build_visible(self, on: bool) -> None:
        """Hide the entire build button (e.g. when no compilable file is open)."""
        self.build_btn.setVisible(on)
