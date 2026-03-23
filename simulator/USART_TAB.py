import threading
import time
import serial
from PySide6 import QtWidgets
from PySide6.QtWidgets import QComboBox
from serial.tools import list_ports

class RefreshableComboBox(QComboBox):
    def showPopup(self):
        # Refresh the ports before showing the popup
        self.refresh_callback()
        super().showPopup()  # Calls the original QComboBox.showPopup

class SendLineEdit(QtWidgets.QWidget):
    def __init__(self,  parent=None, send_callback=None):

        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setPlaceholderText("Type a command and press Enter")
        self.line_edit.returnPressed.connect(self.send_command)
        self.sendButton = QtWidgets.QPushButton("Send", self)
        self.clearButton = QtWidgets.QPushButton("Clear", self)
        self.layout.addWidget(self.line_edit, stretch=1)
        self.layout.addWidget(self.sendButton)
        self.layout.addWidget(self.clearButton)
        self.sendButton.clicked.connect(self.send_command)
        self.clearButton.clicked.connect(self.clear_command)
        self.send_data = send_callback

    def send_command(self):
        command = self.line_edit.text()
        self.line_edit.clear()
        self.send_data(command)

    def clear_command(self):
        self.line_edit.clear()


class USART_TAB(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.serial_port = None
        self.read_thread = None
        self.stop_thread = threading.Event()

        self.text_area = QtWidgets.QTextEdit(self)
        self.text_area.setReadOnly(True)

        self.available_ports_combo = RefreshableComboBox(self)
        self.available_ports_combo.refresh_callback = self.refresh_available_ports

        self.baudrate_combo = QComboBox(self)
        self.baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combo.setCurrentText("115200")

        self.connect_button = QtWidgets.QPushButton("Connect", self)
        self.connect_button.clicked.connect(self.handle_connect)

        self.disconnect_button = QtWidgets.QPushButton("Disconnect", self)
        self.disconnect_button.clicked.connect(self.handle_disconnect)

        self.clear_button = QtWidgets.QPushButton("Clear", self)
        self.clear_button.clicked.connect(self.text_area.clear)

        self.send_line_edit = SendLineEdit(self, self.send_data)


        layout = QtWidgets.QVBoxLayout(self)
        horizontal_layout = QtWidgets.QHBoxLayout()
        horizontal_layout.addWidget(self.available_ports_combo)
        horizontal_layout.addWidget(self.baudrate_combo)
        horizontal_layout.addWidget(self.connect_button)
        horizontal_layout.addWidget(self.disconnect_button)
        horizontal_layout.addWidget(self.clear_button)
        layout.addLayout(horizontal_layout)
        layout.addWidget(self.text_area)
        layout.addWidget(self.send_line_edit)

    def send_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write((data + "\n").encode('utf-8'))
                self.text_area.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} >> {data}")
            except serial.SerialException as e:
                self.text_area.append(f"Error sending data: {e}")
        else:
            self.text_area.append("Serial port is not connected.")



    def refresh_available_ports(self):
        self.available_ports_combo.clear()

        ports = list_ports.comports()
        for port in ports:
            self.available_ports_combo.addItem(port.device + " - " + port.description, port.device)

    def connect_serial(self, port_name, baud_rate=115200):
        try:
            self.serial_port = serial.Serial(port_name, baud_rate, timeout=1, write_timeout=1)
            self.stop_thread.clear()
            self.read_thread = threading.Thread(target=self.read_from_serial)
            self.read_thread.start()
            self.text_area.append(f"Connected to {port_name} at {baud_rate} baud.")
        except serial.SerialException as e:
            self.text_area.append(f"Error connecting to serial port: {e}")

    def disconnect_serial(self):
        if self.serial_port and self.serial_port.is_open:
            self.stop_thread.set()
            self.read_thread.join()
            self.serial_port.close()
            self.text_area.append("Serial port disconnected.")

    def handle_connect(self):
        port_name = self.available_ports_combo.currentData()
        baud_rate = int(self.baudrate_combo.currentText())
        if port_name:
            self.connect_serial(port_name, baud_rate)

    def handle_disconnect(self):
        self.disconnect_serial()

    def read_from_serial(self):
        while not self.stop_thread.is_set():
            if self.serial_port and self.serial_port.is_open:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        self.text_area.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} << {line}")
                except serial.SerialException as e:
                    self.text_area.append(f"Error reading from serial port: {e}")
                    break