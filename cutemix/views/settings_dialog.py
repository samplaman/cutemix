"""
Preferences and Hardware Configuration Dialog for CuteMix.
Configures OSC endpoints, ports, dialect, Bonjour auto-discovery,
and MOTU PCIe-424 + 24i AudioWire slot settings.
"""

from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from ..model.config import AppConfig
from ..osc.zeroconf_service import CueMixZeroconfPublisher

if is_qt_available():
    class SettingsDialog(QtWidgets.QDialog):
        settingsSaved = Signal()

        def __init__(self, config: AppConfig, parent=None):
            super().__init__(parent)
            self.config = config
            self.setWindowTitle("CuteMix Preferences & OSC Configuration")
            self.setMinimumWidth(480)
            self.setModal(True)

            self._build_ui()
            self._load_values()

        def _build_ui(self):
            root_layout = QtWidgets.QVBoxLayout(self)
            root_layout.setContentsMargins(12, 12, 12, 12)
            root_layout.setSpacing(10)

            # Tabs
            tabs = QtWidgets.QTabWidget()

            # --- Tab 1: OSC Network Settings ---
            tab_osc = QtWidgets.QWidget()
            osc_layout = QtWidgets.QVBoxLayout(tab_osc)

            # Group: Endpoints
            grp_net = QtWidgets.QGroupBox("OSC Endpoints & Ports")
            net_form = QtWidgets.QFormLayout(grp_net)
            net_form.setSpacing(8)

            self.txt_host = QtWidgets.QLineEdit()
            self.txt_host.setPlaceholderText("127.0.0.1 (Local Windows CueMix FX)")
            net_form.addRow("Target Host (CueMix FX PC):", self.txt_host)

            self.spn_target_port = QtWidgets.QSpinBox()
            self.spn_target_port.setRange(1024, 65535)
            self.spn_target_port.setValue(8000)
            net_form.addRow("Target Send Port (CueMix FX In):", self.spn_target_port)

            self.spn_listen_port = QtWidgets.QSpinBox()
            self.spn_listen_port.setRange(1024, 65535)
            self.spn_listen_port.setValue(9000)
            net_form.addRow("Local Listen Port (CuteMix In):", self.spn_listen_port)

            osc_layout.addWidget(grp_net)

            # Group: Dialect
            grp_dialect = QtWidgets.QGroupBox("OSC Protocol Dialect")
            dialect_layout = QtWidgets.QVBoxLayout(grp_dialect)

            self.cmb_dialect = QtWidgets.QComboBox()
            self.cmb_dialect.addItem("TouchOSC (CueMix FX Native Format)", "touchosc")
            self.cmb_dialect.addItem("Hierarchical Direct Matrix (/mix/1/input/1/vol)", "direct")
            self.cmb_dialect.addItem("Dual Broadcast (Send Both Formats)", "both")
            dialect_layout.addWidget(self.cmb_dialect)

            lbl_dialect_tip = QtWidgets.QLabel(
                "Tip: 'TouchOSC' is the native format used by MOTU's shipped CueMixFX-PCI-424 layout. "
                "CueMix FX understands it out of the box."
            )
            lbl_dialect_tip.setWordWrap(True)
            lbl_dialect_tip.setStyleSheet("color: #7d848e; font-size: 10px;")
            dialect_layout.addWidget(lbl_dialect_tip)

            osc_layout.addWidget(grp_dialect)

            # Group: Bonjour / Zeroconf
            grp_bonjour = QtWidgets.QGroupBox("Auto-Discovery (Bonjour / Zeroconf)")
            bonjour_layout = QtWidgets.QVBoxLayout(grp_bonjour)

            self.chk_zeroconf = QtWidgets.QCheckBox("Advertise as TouchOSC surface for CueMix FX auto-discovery")
            bonjour_layout.addWidget(self.chk_zeroconf)

            zc_status = "Available (zeroconf installed)" if CueMixZeroconfPublisher.is_supported() else "Optional (run 'pip install zeroconf' to enable)"
            lbl_zc = QtWidgets.QLabel(f"Bonjour Engine Status: {zc_status}")
            lbl_zc.setStyleSheet("font-size: 10px; color: #4fd6e6;" if CueMixZeroconfPublisher.is_supported() else "font-size: 10px; color: #88909c;")
            bonjour_layout.addWidget(lbl_zc)

            osc_layout.addWidget(grp_bonjour)
            osc_layout.addStretch()
            tabs.addTab(tab_osc, "OSC Network")

            # --- Tab 2: Hardware Profile ---
            tab_hw = QtWidgets.QWidget()
            hw_layout = QtWidgets.QVBoxLayout(tab_hw)

            grp_hw = QtWidgets.QGroupBox("MOTU 424 PCI-Express & AudioWire Setup")
            hw_form = QtWidgets.QFormLayout(grp_hw)

            lbl_card = QtWidgets.QLabel("MOTU PCIe-424")
            lbl_card.setStyleSheet("font-weight: bold; color: #4fd6e6;")
            hw_form.addRow("Host Card:", lbl_card)

            self.cmb_slot = QtWidgets.QComboBox()
            self.cmb_slot.addItems(["Slot A (Primary)", "Slot B", "Slot C", "Slot D"])
            hw_form.addRow("AudioWire Port:", self.cmb_slot)

            lbl_iface = QtWidgets.QLabel("MOTU 24i (24 Analog Line Inputs)")
            lbl_iface.setStyleSheet("font-weight: bold; color: #e4e7ea;")
            hw_form.addRow("Attached Interface:", lbl_iface)

            self.spn_buses = QtWidgets.QSpinBox()
            self.spn_buses.setRange(1, 8)
            self.spn_buses.setValue(4)
            hw_form.addRow("Active Mix Buses:", self.spn_buses)

            hw_layout.addWidget(grp_hw)

            # Channel Names Editor
            grp_names = QtWidgets.QGroupBox("Channel Names")
            names_layout = QtWidgets.QVBoxLayout(grp_names)

            self.table_names = QtWidgets.QTableWidget(24, 2)
            self.table_names.setHorizontalHeaderLabels(["Channel", "Custom Label"])
            self.table_names.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.table_names.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.table_names.verticalHeader().setVisible(False)

            for i in range(24):
                item_ch = QtWidgets.QTableWidgetItem(f"Input {i + 1:02d}")
                item_ch.setFlags(item_ch.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table_names.setItem(i, 0, item_ch)

                item_name = QtWidgets.QTableWidgetItem(self.config.get_channel_name(i))
                self.table_names.setItem(i, 1, item_name)

            names_layout.addWidget(self.table_names)
            hw_layout.addWidget(grp_names)

            tabs.addTab(tab_hw, "Hardware Profile")
            root_layout.addWidget(tabs)

            # Dialog Buttons
            btn_box = QtWidgets.QHBoxLayout()
            btn_box.addStretch()

            btn_cancel = QtWidgets.QPushButton("Cancel")
            btn_cancel.clicked.connect(self.reject)
            btn_box.addWidget(btn_cancel)

            btn_save = QtWidgets.QPushButton("Apply & Save")
            btn_save.setStyleSheet("font-weight: bold; background-color: #1e525c; color: #ffffff;")
            btn_save.clicked.connect(self._on_save_clicked)
            btn_box.addWidget(btn_save)

            root_layout.addLayout(btn_box)

        def _load_values(self):
            self.txt_host.setText(self.config.osc_target_host)
            self.spn_target_port.setValue(self.config.osc_target_port)
            self.spn_listen_port.setValue(self.config.osc_listen_port)

            idx = self.cmb_dialect.findData(self.config.osc_dialect)
            if idx >= 0:
                self.cmb_dialect.setCurrentIndex(idx)

            self.chk_zeroconf.setChecked(self.config.enable_zeroconf)
            self.spn_buses.setValue(self.config.num_buses)

            slot_idx = ["A", "B", "C", "D"].index(self.config.slot_letter) if self.config.slot_letter in "ABCD" else 0
            self.cmb_slot.setCurrentIndex(slot_idx)

        def _on_save_clicked(self):
            self.config.osc_target_host = self.txt_host.text().strip() or "127.0.0.1"
            self.config.osc_target_port = self.spn_target_port.value()
            self.config.osc_listen_port = self.spn_listen_port.value()
            self.config.osc_dialect = self.cmb_dialect.currentData()
            self.config.enable_zeroconf = self.chk_zeroconf.isChecked()
            self.config.num_buses = self.spn_buses.value()
            self.config.slot_letter = "ABCD"[self.cmb_slot.currentIndex()]

            # Save channel names
            for i in range(24):
                item = self.table_names.item(i, 1)
                if item:
                    val = item.text().strip() or f"Analog {i + 1}"
                    self.config.set_channel_name(i, val)

            self.config.save()
            self.settingsSaved.emit()
            self.accept()
