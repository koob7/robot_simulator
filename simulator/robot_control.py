import enum
import logging
from PySide6 import QtCore, QtWidgets
from kinematic_helper import valid_max_angular_speed

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
    SYNCHRONIZE         = 4 #is a aspecial version of SET_ANGLES command where robot almost does not have to strict to timeout
    MOVE_TO_POSITION    = 5
    RESET               = 6
    #POSITION_REACHED    = 6 #nie wspieram żeby zapewnić maksymalną synchronizację 

MAX_ANGLE_SINGLE_MOVE = 20
COMMAND_TIMEOUT = 5000
COMMAND_TIMEOUT_GAP = 10

class robot_control(QtCore.QObject):
    status_updated = QtCore.Signal()

    def __init__(self, usart_control):
        super().__init__()
        self.usart_control = usart_control
        self.connection_status = ConnectionStatus.USART_DISCONNECTED
        self.robot_status = RobotStatus.UNKNOWN_POSITION
        self.usart_control.connect_status_callback(self.usart_status_changed_callback)
        self.usart_control.connect_received_callback(self.data_received_callback)

        self.home_angles = [0, 90, 90, 0, 0, 0]
        self.current_angles = [None] * 6
        self.desired_angles = [None] * 6

        self.timeout_timer = QtCore.QTimer()
        self.timeout_timer.timeout.connect(self.command_timeout_callback)

    def get_connection_status(self):
        return self.connection_status

    def get_robot_status(self):
        return self.robot_status

    def get_current_angles(self):
        return self.current_angles

    def command_timeout_callback(self):
        self.robot_status = RobotStatus.TIMEOUT
        self.status_updated.emit()

    def move_to_position(self, target_angles, timeout) -> bool:
        timeout = timeout + COMMAND_TIMEOUT_GAP

        status = False

        if self.robot_status != RobotStatus.READY:
            logger.debug("unknown position 1")
            status |= True

        if any(angle is None for angle in self.current_angles):
            logger.debug("unknown position 2")
            status |= True
        
        if any(angle_1 != angle_2 for angle_1, angle_2 in zip(self.current_angles, self.desired_angles)):
            logger.debug("unknown position 3")
            status |= True

        if status:
            self.robot_status = RobotStatus.UNKNOWN_POSITION
            self.desired_angles = [None] * 6
            self.status_updated.emit()
            return False

        oversped = valid_max_angular_speed(self.current_angles, target_angles, timeout)

        if oversped > 1.0:
            logger.info("command speed to high")
            return False

        status =  self.__send_command(timeout, RobotCommands.MOVE_TO_POSITION.value, *(int(val * 1000) for val in target_angles)) #robot stores angles as millidegrees, convert to degrees

        if status:
            self.desired_angles = target_angles
            self.status_updated.emit()

        return status

    def set_default_position(self):
        self.robot_status = RobotStatus.UNKNOWN_POSITION
        self.status_updated.emit()
        self.synchronize_to_position(self.home_angles)

    def reset_robot(self):
        self.robot_status = RobotStatus.UNKNOWN_POSITION
        timeout = 60000 + COMMAND_TIMEOUT_GAP
        status = self.__send_command(timeout, RobotCommands.RESET.value)

        self.desired_angles = [None] * 6
        self.current_angles = [None] * 6
        self.status_updated.emit()

        return status

    def synchronize_to_position(self, angles) -> bool:
        self.robot_status = RobotStatus.UNKNOWN_POSITION
        timeout = 60000

        status = self.__send_command(timeout, RobotCommands.SYNCHRONIZE.value, *(int(val * 1000) for val in angles)) #robot stores angles as millidegrees, convert to degrees

        if status:
            self.desired_angles = angles
            self.status_updated.emit()

        return status

    def get_robot_angles(self):
        self.__send_command(COMMAND_TIMEOUT, RobotCommands.GET_ANGLES.value)

    def poll_robot_state(self):
        if self.connection_status != ConnectionStatus.USART_READY:
            return

        if self.robot_status == RobotStatus.COMMAND_PENDING:
            return

        self.get_robot_angles()

    def data_received_callback(self, data):
        if data.startswith("cmd "):
            self.connection_status = ConnectionStatus.USART_READY
            self.timeout_timer.stop()
            command = data[3:]
            command_code = int(command.split()[0])
            if command_code == RobotCommands.GET_ANGLES.value:
                angles = list(map(int, command.split()[1:])) #robot stores angles as millidegrees, convert to degrees
                angles = [angle / 1000 for angle in angles]
                self.current_angles = angles

                if all(self.desired_angles[i] is not None and angles[i] == self.desired_angles[i] for i in range(6)):
                    self.robot_status = RobotStatus.READY

            elif command_code == RobotCommands.GET_STATUS.value: #robot internal status
                status_code = int(command.split()[1])
                logger.info(f"Received status: {status_code}")

            self.status_updated.emit()

                
    def usart_status_changed_callback(self, new_status):
        if new_status == "CONNECTED":
            self.connection_status = ConnectionStatus.USART_READY
        elif new_status == "DISCONNECTED":
            self.connection_status = ConnectionStatus.USART_DISCONNECTED
            self.timeout_timer.stop()
        else:
            self.connection_status = ConnectionStatus.USART_ERROR

        self.desired_angles = [None] * 6
        self.current_angles = [None] * 6
        self.robot_status = RobotStatus.UNKNOWN_POSITION
        self.status_updated.emit()

    def __send_command(self, timeout, command_code: int, param_1: int = None, param_2: int = None, param_3: int = None, param_4: int = None, param_5: int = None, param_6: int = None) -> bool:
        if self.connection_status != ConnectionStatus.USART_READY:
            return False

        command = "cmd " + str(command_code) + " " + " ".join([str(param) for param in [param_1, param_2, param_3, param_4, param_5, param_6] if param is not None])

        status = self.usart_control.send_data(command)

        if not status:
            self.connection_status = ConnectionStatus.USART_ERROR
            self.robot_status = RobotStatus.UNKNOWN_POSITION
            self.status_updated.emit()
            return False

        self.robot_status = RobotStatus.COMMAND_PENDING
        self.timeout_timer.start(timeout)
        self.status_updated.emit()

        return status


class ROBOT_STATUS_TAB(QtWidgets.QWidget):
    def __init__(self, robot_control: robot_control, parent=None):
        super().__init__(parent)
        self.robot_control = robot_control

        self.sync_button = QtWidgets.QPushButton("Synchronize")
        self.reset_button = QtWidgets.QPushButton("Reset Robot")

        self.usart_status_label = QtWidgets.QLabel("USART: DISCONNECTED")
        self.robot_status_label = QtWidgets.QLabel("Robot: UNKNOWN")

        self.axis_value_labels = []

        main_layout = QtWidgets.QVBoxLayout(self)

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

        self.sync_button.clicked.connect(self.robot_control.set_default_position)
        self.reset_button.clicked.connect(self.robot_control.reset_robot)

        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.robot_control.poll_robot_state)
        self.refresh_timer.timeout.connect(self.refresh_display)
        self.refresh_timer.start()

        self.robot_control.status_updated.connect(self.refresh_display)
        self.refresh_display()

    def refresh_display(self):
        connection_status = self.robot_control.get_connection_status()
        robot_status = self.robot_control.get_robot_status()
        current_angles = self.robot_control.get_current_angles()

        if connection_status == ConnectionStatus.USART_READY:
            self.usart_status_label.setText("USART: CONNECTED")
            self.robot_status_label.setText(f"Robot: {robot_status.name}")
        elif connection_status == ConnectionStatus.USART_ERROR:
            self.usart_status_label.setText("USART: ERROR")
            self.robot_status_label.setText("Robot: UNKNOWN")
        else:
            self.usart_status_label.setText("USART: DISCONNECTED")
            self.robot_status_label.setText("Robot: N/A")

        for idx, label in enumerate(self.axis_value_labels):
            angle = current_angles[idx]
            if angle is None:
                label.setText("-")
            else:
                label.setText(f"{angle:.3f}")