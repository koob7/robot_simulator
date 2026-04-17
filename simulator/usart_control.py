import serial
import threading


class USARTControl:
    def __init__(self):
        self.serial_port = None
        self.read_thread = None
        self.stop_thread = threading.Event()

        self.receive_callbacks = []
        self.data_sent_callbacks = []

    def connect(self, port_name, baud_rate):
        if self.serial_port and self.serial_port.is_open:
            return -1

        if port_name is None or port_name == "":
            return 0

        try:
            self.serial_port = serial.Serial(port_name, baud_rate, timeout=1, write_timeout=1)
            self.stop_thread.clear()
            self.read_thread = threading.Thread(target=self.receive_data, daemon=True)
            self.read_thread.start()
            if hasattr(self, 'status_changed_callback'):
                self.status_changed_callback("CONNECTED")
            return 1
        except serial.SerialException as e:
            return 0

    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.stop_thread.set()
            self.read_thread.join()
            self.serial_port.close()
            if hasattr(self, 'status_changed_callback'):
                self.status_changed_callback("DISCONNECTED")
            return True
        return False

    def send_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write((data + "\n").encode('utf-8'))
                if hasattr(self, 'data_sent_callbacks'):
                    for cb in self.data_sent_callbacks:
                        cb(data)
                return True
            except serial.SerialException as e:
                return False
        else:
            return False
        
    

    def connect_received_callback(self, callback):
        self.receive_callbacks.append(callback)

    def connect_data_sent_callback(self, callback):
        self.data_sent_callbacks.append(callback)

    def connect_status_callback(self, callback):
        self.status_changed_callback = callback

    def receive_data(self):
        while not self.stop_thread.is_set():
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        if hasattr(self, 'receive_callbacks'):
                            for cb in self.receive_callbacks:
                                cb(line)
            except serial.SerialException as e:
                break
        