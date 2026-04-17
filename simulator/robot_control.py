import enum
import logging
from PySide6 import QtCore, QtWidgets
from kinematic_helper import valid_max_angular_speed
import math

logger = logging.getLogger(__name__)

class RobotStatus(enum.Enum):
    COMMAND_PENDING     = 0
    READY               = 1
    UNKNOWN_POSITION    = 2
    TIMEOUT             = 3

class ConnectionStatus(enum.Enum):
    USART_READY         = 0
    USART_DISCONNECTED  = 1
    USART_ERROR         = 2

class RobotCommands(enum.Enum):
    GET_ANGLES          = 1
    SET_ANGLES          = 2
    GET_STATUS          = 3
    RESET               = 4
    STOP                = 5

MAX_ANGLE_SINGLE_MOVE = 20
COMMAND_TIMEOUT = 100 #ms
COMMAND_TIMEOUT_GAP = 20 #ms

class robot_control(QtCore.QObject):
    status_updated = QtCore.Signal()
    _data_received_signal = QtCore.Signal(str)
    _usart_status_changed_signal = QtCore.Signal(str)

    def __init__(self, usart_control):
        super().__init__()
        self.usart_control = usart_control
        self.connection_status = ConnectionStatus.USART_DISCONNECTED
        self.robot_status = RobotStatus.UNKNOWN_POSITION

        self.usart_control.connect_status_callback(self.usart_status_changed_callback)
        self._usart_status_changed_signal.connect(self._process_usart_status_changed, QtCore.Qt.ConnectionType.QueuedConnection)

        self.usart_control.connect_received_callback(self.data_received_callback)
        self._data_received_signal.connect(self._process_data_received, QtCore.Qt.ConnectionType.QueuedConnection)

        self.home_angles = [0, 90, 90, 0, 0, 0]
        self.current_angles = [None] * 6
        self.desired_angles = [None] * 6
        self.status_updated.emit()

        self.timeout_timer = QtCore.QTimer()
        self.timeout_timer.timeout.connect(self.command_timeout_callback)

        # USART callbacks can come from a Python worker thread.
        # Route them into this QObject's thread before touching Qt objects.

    def connect_synchronization_callback(self, func):
        self.synchronization_callback = func

    def usart_status_changed_callback(self, new_status):
        self._usart_status_changed_signal.emit(new_status)

    def data_received_callback(self, data):
        self._data_received_signal.emit(data)

    def robot_desynchronized(self):
        self.robot_status = RobotStatus.UNKNOWN_POSITION
        self.desired_angles = [None] * 6
        self.current_angles = [None] * 6
        self.status_updated.emit()

    def get_connection_status(self):
        return self.connection_status

    def get_robot_status(self):
        return self.robot_status

    def get_current_angles(self):
        return self.current_angles

    def command_timeout_callback(self):
        self.robot_status = RobotStatus.TIMEOUT
        self.timeout_timer.stop()
        self.status_updated.emit()

    def move_to_position(self, target_angles, timeout) -> bool:
        status = False

        if self.connection_status != ConnectionStatus.USART_READY:
            logger.debug("unknown position 0")
            status |= True

        if self.robot_status != RobotStatus.READY:
            logger.debug("unknown position 1")
            status |= True

        if any(angle is None for angle in self.current_angles):
            logger.debug("unknown position 2")
            status |= True

        if status:
            self.robot_desynchronized()
            return False
        
        int_target_angles = [int(math.trunc(angle * 1000)) for angle in target_angles] #były jakieś dziwne problemy z zaokrąglaniem
        
        # oversped = valid_max_angular_speed(self.current_angles, target_angles, timeout/1000) # ms -> s

        # if oversped > 1.0:
        #     logger.info("command speed to high")
        #     #return False

        status =  self.__send_command(timeout, RobotCommands.SET_ANGLES.value, *int_target_angles) #robot stores angles as millidegrees, convert to degrees
        
        if status:
            self.desired_angles = [angle / 1000 for angle in int_target_angles]
            self.status_updated.emit()

        return status

    def reset_robot(self):
        #TODO - useless command - what to do?
        self.robot_desynchronized()

    def synchronize_position(self):
        self.robot_desynchronized()
        self.__send_command(COMMAND_TIMEOUT, RobotCommands.GET_ANGLES.value) #robot stores angles as millidegrees, convert to degrees

    def _process_data_received(self, data):
        if data.startswith("cmd "):
            self.connection_status = ConnectionStatus.USART_READY
            self.timeout_timer.stop()

            command = data[3:]
            command_code = int(command.split()[0])

            if command_code == RobotCommands.SET_ANGLES.value:
                angles = list(map(int, command.split()[1:])) #robot stores angles as millidegrees, convert to degrees
                angles = [angle / 1000 for angle in angles]
                self.current_angles = angles
                if all(self.desired_angles[i] is not None and angles[i] == self.desired_angles[i] for i in range(6)):
                    self.robot_status = RobotStatus.READY
                else:
                    logger.info(f"desired: {self.desired_angles}, current: {angles}")

            elif command_code == RobotCommands.RESET.value:
                self.robot_desynchronized()
            
            elif command_code == RobotCommands.GET_ANGLES.value:
                angles = list(map(int, command.split()[1:7])) #robot stores angles as millidegrees, convert to degrees
                angles = [angle / 1000 for angle in angles]
                
                self.current_angles = angles
                self.robot_status = RobotStatus.READY

                if hasattr(self, 'synchronization_callback'):
                    self.synchronization_callback(angles)

            #TODO - usunąć w niczym nie pomaga a nie wiadomo co robi
            elif command_code == RobotCommands.GET_STATUS.value: #robot internal status
                status_code = int(command.split()[1])
                logger.info(f"Received status: {status_code}")

            self.status_updated.emit()

    def emergency_stop(self):
        self.__send_command(0, RobotCommands.STOP.value)
        self.robot_desynchronized()

    def _process_usart_status_changed(self, new_status):
        if new_status == "CONNECTED":
            self.connection_status = ConnectionStatus.USART_READY
        elif new_status == "DISCONNECTED":
            self.connection_status = ConnectionStatus.USART_DISCONNECTED
            self.timeout_timer.stop()
        else:
            self.connection_status = ConnectionStatus.USART_ERROR

        self.robot_desynchronized()

    def __send_command(self, timeout, command_code: int, param_1: int = None, param_2: int = None, param_3: int = None, param_4: int = None, param_5: int = None, param_6: int = None) -> bool:
        if self.connection_status != ConnectionStatus.USART_READY:
            return False

        command = "cmd " + str(command_code) + " " + " ".join([str(param)if param is not None else "0" for param in [param_1, param_2, param_3, param_4, param_5, param_6]]) + " " + str(int(timeout*1000)) + " 0x37373737" # time passed in us

        status = self.usart_control.send_data(command)

        if not status:
            self.connection_status = ConnectionStatus.USART_ERROR
            self.robot_status = RobotStatus.UNKNOWN_POSITION
            self.status_updated.emit()
            return False

        if status:
            self.robot_status = RobotStatus.COMMAND_PENDING
            self.timeout_timer.start(timeout)
        else:
            self.robot_desynchronized()


        return status


class ROBOT_STATUS_TAB(QtWidgets.QWidget):
    def __init__(self, robot_control: robot_control, parent=None):
        super().__init__(parent)
        self.robot_control = robot_control

        self.emergency_button = QtWidgets.QPushButton("Emergency Stop")
        self.emergency_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.emergency_button.setFixedHeight(50)

        self.sync_button = QtWidgets.QPushButton("Synchronize")
        self.reset_button = QtWidgets.QPushButton("Reset Robot")

        self.usart_status_label = QtWidgets.QLabel("USART: DISCONNECTED")
        self.robot_status_label = QtWidgets.QLabel("Robot: UNKNOWN")

        self.axis_value_labels = []

        main_layout = QtWidgets.QVBoxLayout(self)

        main_layout.addWidget(self.emergency_button)
        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.sync_button)
        button_row.addWidget(self.reset_button)
        button_row.addStretch(1)
        main_layout.addLayout(button_row)

        status_group = QtWidgets.QGroupBox("Robot Status")
        status_layout = QtWidgets.QVBoxLayout(status_group)
        status_layout.addWidget(self.usart_status_label)
        status_layout.addWidget(self.robot_status_label)
        main_layout.addWidget(status_group)

        axes_group = QtWidgets.QGroupBox("Current Axis Positions [deg]")
        axes_layout = QtWidgets.QGridLayout(axes_group)

        for idx in range(6):
            axis_name = QtWidgets.QLabel(f"Axis {idx + 1}")
            axis_value = QtWidgets.QLabel("-")
            axes_layout.addWidget(axis_name, idx, 0)
            axes_layout.addWidget(axis_value, idx, 1)
            self.axis_value_labels.append(axis_value)

        main_layout.addWidget(axes_group)
        main_layout.addStretch(1)

        self.emergency_button.clicked.connect(self.robot_control.emergency_stop)
        self.sync_button.clicked.connect(self.robot_control.synchronize_position)
        self.reset_button.clicked.connect(self.robot_control.reset_robot)

        self.robot_control.status_updated.connect(self.refresh_display)
        self.refresh_display()

    def refresh_display(self):
        connection_status = self.robot_control.get_connection_status()
        robot_status = self.robot_control.get_robot_status()
        current_angles = self.robot_control.get_current_angles()

        if connection_status == ConnectionStatus.USART_READY:
            self.usart_status_label.setText("USART: CONNECTED")
        elif connection_status == ConnectionStatus.USART_ERROR:
            self.usart_status_label.setText("USART: ERROR")
        else:
            self.usart_status_label.setText("USART: DISCONNECTED")

        self.robot_status_label.setText(f"Robot: {robot_status.name}")

        for idx, label in enumerate(self.axis_value_labels):
            angle = current_angles[idx]
            if angle is None:
                label.setText("-")
            else:
                label.setText(f"{angle:.3f}")