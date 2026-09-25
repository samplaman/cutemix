"""
Live OSC Monitor and Diagnostic Console for CuteMix.
Real-time inspection of incoming and outgoing OSC packets with address filtering,
packet statistics, and a manual OSC command injector for CueMix FX testing.
"""

from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from ..osc.osc_client import OscLogEntry
from ..osc.osc_core import OscMessage

if is_qt_available():
    class OscMonitorWidget(QtWidgets.QWidget):
        manualSendRequested = Signal(str, list)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._paused: bool = False
            self._max_rows: int = 400
            self._entries = []

            self._build_ui()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)

            # 1. Top Statistics Bar
            stats_box = QtWidgets.QHBoxLayout()

            self.lbl_stats = QtWidgets.QLabel("Status: Listening | Packets: 0 In / 0 Out")
            self.lbl_stats.setStyleSheet("font-family: monospace; font-size: 10px; color: #4fd6e6;")
            stats_box.addWidget(self.lbl_stats)

            stats_box.addStretch()

            self.btn_pause = QtWidgets.QPushButton("Pause Log")
            self.btn_pause.setCheckable(True)
            self.btn_pause.setFixedHeight(22)
            self.btn_pause.toggled.connect(self._toggle_pause)
            stats_box.addWidget(self.btn_pause)

            self.btn_clear = QtWidgets.QPushButton("Clear")
            self.btn_clear.setFixedHeight(22)
            self.btn_clear.clicked.connect(self.clear_log)
            stats_box.addWidget(self.btn_clear)

            layout.addLayout(stats_box)

            # 2. Filter Bar
            filter_box = QtWidgets.QHBoxLayout()
            filter_box.setSpacing(6)

            lbl_filter = QtWidgets.QLabel("Filter:")
            lbl_filter.setStyleSheet("font-weight: bold; color: #8c939d;")
            filter_box.addWidget(lbl_filter)

            self.txt_filter = QtWidgets.QLineEdit()
            self.txt_filter.setPlaceholderText("Filter by address pattern (e.g. cdf, pan, trm, /in)...")
            self.txt_filter.textChanged.connect(self._apply_filter)
            filter_box.addWidget(self.txt_filter)

            self.cmb_dir_filter = QtWidgets.QComboBox()
            self.cmb_dir_filter.addItems(["All Directions", "Incoming Only (IN)", "Outgoing Only (OUT)"])
            self.cmb_dir_filter.currentIndexChanged.connect(self._apply_filter)
            filter_box.addWidget(self.cmb_dir_filter)

            layout.addLayout(filter_box)

            # 3. Log Table
            self.table = QtWidgets.QTableWidget()
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["Time", "Dir", "OSC Address", "Type", "Arguments"])
            self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setStyleSheet("""
                QTableWidget {
                    font-family: monospace;
                    font-size: 10px;
                    background-color: #111215;
                    gridline-color: #1c1e22;
                }
            """)
            layout.addWidget(self.table, stretch=1)

            # 4. Manual OSC Command Injector Bar
            inject_group = QtWidgets.QGroupBox("Manual OSC Command Injector (CueMix FX Test)")
            inject_layout = QtWidgets.QHBoxLayout(inject_group)
            inject_layout.setContentsMargins(6, 8, 6, 6)
            inject_layout.setSpacing(6)

            self.txt_send_addr = QtWidgets.QLineEdit("/bin/fvEB+0/fvInCS+0/cdf")
            self.txt_send_addr.setPlaceholderText("OSC Address")
            inject_layout.addWidget(self.txt_send_addr, stretch=3)

            self.txt_send_val = QtWidgets.QLineEdit("0.78")
            self.txt_send_val.setPlaceholderText("Argument (float, int, or text)")
            inject_layout.addWidget(self.txt_send_val, stretch=2)

            self.btn_send = QtWidgets.QPushButton("Send OSC")
            self.btn_send.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #227b87, stop:1 #16565e);
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #2ec4d6;
                }
                QPushButton:hover {
                    background-color: #2ec4d6;
                    color: #0b1a1d;
                }
            """)
            self.btn_send.clicked.connect(self._on_send_clicked)
            inject_layout.addWidget(self.btn_send)

            layout.addWidget(inject_group)

        def append_entry(self, entry: OscLogEntry):
            """Appends an OSC log entry."""
            if self._paused:
                return

            self._entries.append(entry)
            if len(self._entries) > self._max_rows:
                self._entries.pop(0)

            # Check filters
            filter_text = self.txt_filter.text().strip().lower()
            dir_filter_idx = self.cmb_dir_filter.currentIndex()

            if dir_filter_idx == 1 and entry.direction != "IN":
                return
            if dir_filter_idx == 2 and entry.direction != "OUT":
                return
            if filter_text and (filter_text not in entry.address.lower() and filter_text not in str(entry.args).lower()):
                return

            row = self.table.rowCount()
            self.table.insertRow(row)

            # Format items
            time_item = QtWidgets.QTableWidgetItem(entry.formatted_time())
            dir_item = QtWidgets.QTableWidgetItem(entry.direction)
            addr_item = QtWidgets.QTableWidgetItem(entry.address)

            type_tags = "," + "".join(
                "f" if isinstance(a, float) else "i" if isinstance(a, int) else "s"
                for a in entry.args
            )
            type_item = QtWidgets.QTableWidgetItem(type_tags)

            args_str = ", ".join(f"{a:.4f}" if isinstance(a, float) else str(a) for a in entry.args)
            args_item = QtWidgets.QTableWidgetItem(args_str)

            # Colors
            if entry.direction == "IN":
                dir_item.setForeground(QtGui.QColor("#2ec4d6"))
                addr_item.setForeground(QtGui.QColor("#4fd6e6"))
            else:
                dir_item.setForeground(QtGui.QColor("#f0a63a"))
                addr_item.setForeground(QtGui.QColor("#ffc266"))

            self.table.setItem(row, 0, time_item)
            self.table.setItem(row, 1, dir_item)
            self.table.setItem(row, 2, addr_item)
            self.table.setItem(row, 3, type_item)
            self.table.setItem(row, 4, args_item)

            if self.table.rowCount() > self._max_rows:
                self.table.removeRow(0)

            self.table.scrollToBottom()

        def update_stats(self, in_count: int, out_count: int, in_bytes: int, out_bytes: int, is_connected: bool):
            status = "Listening" if is_connected else "Disconnected"
            self.lbl_stats.setText(
                f"Status: {status} | Packets: {in_count} In ({in_bytes / 1024:.1f} KB) / "
                f"{out_count} Out ({out_bytes / 1024:.1f} KB)"
            )

        def clear_log(self):
            self._entries.clear()
            self.table.setRowCount(0)

        def _toggle_pause(self, checked: bool):
            self._paused = checked
            self.btn_pause.setText("Resume Log" if checked else "Pause Log")

        def _apply_filter(self):
            filter_text = self.txt_filter.text().strip().lower()
            dir_filter_idx = self.cmb_dir_filter.currentIndex()

            self.table.setRowCount(0)
            for entry in self._entries:
                if dir_filter_idx == 1 and entry.direction != "IN":
                    continue
                if dir_filter_idx == 2 and entry.direction != "OUT":
                    continue
                if filter_text and (filter_text not in entry.address.lower() and filter_text not in str(entry.args).lower()):
                    continue

                row = self.table.rowCount()
                self.table.insertRow(row)

                time_item = QtWidgets.QTableWidgetItem(entry.formatted_time())
                dir_item = QtWidgets.QTableWidgetItem(entry.direction)
                addr_item = QtWidgets.QTableWidgetItem(entry.address)
                type_tags = "," + "".join("f" if isinstance(a, float) else "i" if isinstance(a, int) else "s" for a in entry.args)
                type_item = QtWidgets.QTableWidgetItem(type_tags)
                args_str = ", ".join(f"{a:.4f}" if isinstance(a, float) else str(a) for a in entry.args)
                args_item = QtWidgets.QTableWidgetItem(args_str)

                if entry.direction == "IN":
                    dir_item.setForeground(QtGui.QColor("#2ec4d6"))
                    addr_item.setForeground(QtGui.QColor("#4fd6e6"))
                else:
                    dir_item.setForeground(QtGui.QColor("#f0a63a"))
                    addr_item.setForeground(QtGui.QColor("#ffc266"))

                self.table.setItem(row, 0, time_item)
                self.table.setItem(row, 1, dir_item)
                self.table.setItem(row, 2, addr_item)
                self.table.setItem(row, 3, type_item)
                self.table.setItem(row, 4, args_item)

            self.table.scrollToBottom()

        def _on_send_clicked(self):
            addr = self.txt_send_addr.text().strip()
            if not addr:
                return
            if not addr.startswith("/"):
                addr = "/" + addr

            raw_val = self.txt_send_val.text().strip()
            args = []
            if raw_val:
                # Try float
                try:
                    args.append(float(raw_val))
                except ValueError:
                    # Try int
                    try:
                        args.append(int(raw_val))
                    except ValueError:
                        # String
                        args.append(raw_val)

            self.manualSendRequested.emit(addr, args)
