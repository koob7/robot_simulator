import threading
import time
import serial
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QComboBox
from serial.tools import list_ports

class RefreshableComboBox(QComboBox):
    def showPopup(self):
        # Refresh the ports before showing the popup
        self.refresh_callback()
        super().showPopup()  # Calls the original QComboBox.showPopup

class SendLineEdit(QtWidgets.QWidget):
    def __init__(self, send_callback,  parent=None):

        super().__init__(parent)
        self.command_history = []
        self.history_index = None

        self.layout = QtWidgets.QHBoxLayout(self)
        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setPlaceholderText("Type a command and press Enter")
        self.line_edit.returnPressed.connect(self.send_command)
        self.line_edit.installEventFilter(self)
        self.sendButton = QtWidgets.QPushButton("Send", self)
        self.layout.addWidget(self.line_edit, stretch=1)
        self.layout.addWidget(self.sendButton)
        self.sendButton.clicked.connect(self.send_command)
        self.send_callback = send_callback

    def eventFilter(self, obj, event):
        if obj is self.line_edit and event.type() == QtCore.QEvent.Type.KeyPress:
            if event.key() == QtCore.Qt.Key.Key_Up:
                self.show_previous_command()
                return True
            if event.key() == QtCore.Qt.Key.Key_Down:
                self.show_next_command()
                return True

        return super().eventFilter(obj, event)

    def show_previous_command(self):
        if not self.command_history:
            return

        if self.history_index is None:
            self.history_index = len(self.command_history) - 1
        elif self.history_index > 0:
            self.history_index -= 1

        self.line_edit.setText(self.command_history[self.history_index])
        self.line_edit.selectAll()

    def show_next_command(self):
        if self.history_index is None:
            return

        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.line_edit.setText(self.command_history[self.history_index])
            self.line_edit.selectAll()
            return

        self.history_index = None
        self.line_edit.clear()

    def send_command(self):
        command = self.line_edit.text()
        if command:
            if not self.command_history or self.command_history[-1] != command:
                self.command_history.append(command)
            self.history_index = None
        self.line_edit.clear()
        self.send_callback(command)

    def clear_command(self):
        self.line_edit.clear()
        self.history_index = None


class USART_TAB(QtWidgets.QWidget):
    log_message_signal = QtCore.Signal(str)
    connection_status_signal = QtCore.Signal(str)

    def __init__(self, usart_interface, parent=None):
        super().__init__()

        self.log_message_signal.connect(self.append_log)
        self.connection_status_signal.connect(self.apply_status_changed)

        self.usart_interface = usart_interface
        self.usart_interface.connect_received_callback(self.data_received_callback)
        self.usart_interface.connect_status_callback(self.handle_status_changed)
        self.is_connected = False

        self.text_area = QtWidgets.QPlainTextEdit(self)
        self.text_area.setReadOnly(True)

        self.available_ports_combo = RefreshableComboBox(self)
        self.available_ports_combo.refresh_callback = self.refresh_available_ports

        self.baudrate_combo = QComboBox(self)
        self.baudrate_combo.addItems(["9600", "115200", "3125000", "6250000", "7500000"])
        self.baudrate_combo.setCurrentText("7500000")

        self.connection_button = QtWidgets.QPushButton("Connect", self)
        self.connection_button.clicked.connect(self.handle_connection_toggle)

        self.clear_button = QtWidgets.QPushButton("Clear", self)
        self.clear_button.clicked.connect(self.text_area.clear)

        self.auto_scroll_checkbox = QtWidgets.QCheckBox("Auto-scroll", self)
        self.auto_scroll_checkbox.setChecked(True)

        self.send_line_edit = SendLineEdit( send_callback=self.send_data)


        layout = QtWidgets.QVBoxLayout(self)
        horizontal_layout = QtWidgets.QHBoxLayout()
        horizontal_layout.addWidget(self.available_ports_combo)
        horizontal_layout.addWidget(self.baudrate_combo)
        horizontal_layout.addWidget(self.connection_button)
        horizontal_layout.addWidget(self.clear_button)
        horizontal_layout.addWidget(self.auto_scroll_checkbox)
        layout.addLayout(horizontal_layout)
        layout.addWidget(self.text_area)
        layout.addWidget(self.send_line_edit)

    def append_log(self, message):
        self.text_area.appendPlainText(message)
        if self.auto_scroll_checkbox.isChecked():
            scrollbar = self.text_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def send_data(self, data):
        if self.usart_interface.send_data(data):
            self.append_log(f"{time.strftime('%Y-%m-%d %H:%M:%S')} >> {data}")
        else:
            self.append_log("Serial port is not connected.")

    def refresh_available_ports(self):
        self.available_ports_combo.clear()

        ports = list_ports.comports()
        for port in ports:
            self.available_ports_combo.addItem(port.device + " - " + port.description, port.device)

    def handle_connection_toggle(self):
        if self.is_connected:
            self.handle_disconnect()
        else:
            self.handle_connect()

    def handle_connect(self):
        port_name = self.available_ports_combo.currentData()
        baud_rate = int(self.baudrate_combo.currentText())

        result = self.usart_interface.connect(port_name, baud_rate)

        if result == 1:
            self.is_connected = True
            self.connection_button.setText("Disconnect")
            self.append_log(f"Connected to {port_name} at {baud_rate} baud.")
        elif result == 0:
            self.append_log(f"Error connecting to serial port: {port_name}.")
        elif result == -1:
            self.append_log("Already connected to a serial port.")

    def handle_disconnect(self):
        if self.usart_interface.disconnect():
            self.is_connected = False
            self.connection_button.setText("Connect")
            self.append_log("Serial port disconnected.")

    def handle_status_changed(self, status):
        self.connection_status_signal.emit(status)

    def apply_status_changed(self, status):
        if status == "READY":
            self.is_connected = True
            self.connection_button.setText("Disconnect")
        elif status == "DISCONNECTED":
            self.is_connected = False
            self.connection_button.setText("Connect")

    def data_received_callback(self, data):
        self.log_message_signal.emit(f"{time.strftime('%Y-%m-%d %H:%M:%S')} << {data}")

