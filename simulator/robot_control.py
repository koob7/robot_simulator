import enum
import logging
import time
from PySide6 import QtCore

logger = logging.getLogger(__name__)

class RobotStatus(enum.Enum):
    COMMAND_PENDING     = 0
    READY               = 1
    ERROR               = 2

class ConnectionStatus(enum.Enum):
    READY               = 0
    DISCONNECTED        = 1
    UNKNOWN_POSITION    = 2
    COMMAND_PENDING     = 3
    TIMEOUT             = 4
    USART_ERROR         = 5

class RobotCommands(enum.Enum):
    GET_ANGLES         = 1
    SET_ANGLES         = 2
    GET_STATUS         = 3
    SYNCHRONIZE        = 4 #is a aspecial command where robot does not have to strict to timeout. Robot respond with POSITION_REACHED when is ready
    MOVE_TO_POSITION   = 5
    POSITION_REACHED   = 6

MAX_ANGLE_SINGLE_MOVE = 20
COMMAND_TIMEOUT = 5000
COMMAND_TIMEOUT_GAP = 100

class RobotControl:
    def __init__(self, usart_control):
        self.usart_control = usart_control
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.RobotStatus = RobotStatus.READY
        self.usart_control.connect_status_callback(self.status_changed_callback)
        self.usart_control.connect_received_callback(self.data_received_callback)



        self.home_angles = [0, 90, 90, 0, 0, 0]
        self.current_angles = self.home_angles.copy()
        self.desired_angles = self.home_angles.copy()

        self.timeout_timer = QtCore.QTimer()
        self.timeout_timer.timeout.connect(self.command_timeout_callback)

    def get_connection_status(self):
        return self.connection_status

    def get_current_angles(self):
        return self.current_angles

    def command_timeout_callback(self):
        if self.connection_status == ConnectionStatus.COMMAND_PENDING:
            self.connection_status = ConnectionStatus.TIMEOUT

    def move_to_position(self, target_angles, timeout) -> bool:
        timeout = timeout + COMMAND_TIMEOUT_GAP
        if self.connection_status != ConnectionStatus.READY:
            return False

        oversped = valid_max_angular_speed(self.current_angles, target_angles, timeout)

        if oversped > 1.0:
            logger.info("command speed to high")
            return False

        status =  self.__send_command(timeout, RobotCommands.MOVE_TO_POSITION.value, *(int(val * 1000) for val in target_angles)) #robot stores angles as millidegrees, convert to degrees

        if status:
            self.desired_angles = target_angles
        return status

    def set_default_position(self):
        self.synchronize_to_position(self.home_angles)

    def synchronize_to_position(self, angles) -> bool:
        timeout = 60000

        status = self.__send_command(timeout, RobotCommands.SYNCHRONIZE.value, *(int(val * 1000) for val in angles)) #robot stores angles as millidegrees, convert to degrees

        if status:
            self.desired_angles = angles

        return status

    def get_robot_angles(self):
        self.__send_command(COMMAND_TIMEOUT, RobotCommands.GET_ANGLES.value)

    def data_received_callback(self, data):
        if data.startswith("cmd "):
            self.timeout_timer.stop()
            command = data[3:]
            command_code = int(command.split()[0])
            if command_code == RobotCommands.GET_ANGLES.value:
                angles = list(map(int, command.split()[1:])) #robot stores angles as millidegrees, convert to degrees
                self.current_angles = [angle / 1000 for angle in angles]
                logger.info(f"Received angles: {self.current_angles}")
                self.connection_status = ConnectionStatus.READY

            elif command_code == RobotCommands.GET_STATUS.value: #currently unused
                status_code = int(command.split()[1])
                if status_code not in RobotStatus._value2member_map_:
                    return
                self.RobotStatus = RobotStatus(status_code)
                logger.info(f"Received status: {self.RobotStatus.name}")

            elif command_code == RobotCommands.POSITION_REACHED.value:
                if (i is None for i in self.desired_angles) or self.connection_status != ConnectionStatus.COMMAND_PENDING:
                    self.connection_status = ConnectionStatus.UNKNOWN_POSITION
                    return

                self.current_angles = self.desired_angles.copy()
                self.connection_status = ConnectionStatus.READY


        self.desired_angles = [None] * 6 #if we get POSITTION_REACHED we already used this values and we don't need them anymore
                                         #if we get any other command we can be wchich desired position robot will reach next time

                
    def status_changed_callback(self, new_status):
        if new_status == "READY":
            self.connection_status = ConnectionStatus.UNKNOWN_POSITION
        elif new_status == "DISCONNECTED":
            self.connection_status = ConnectionStatus.DISCONNECTED
            self.timeout_timer.stop()


    def __send_command(self, timeout, command_code: int, param_1 = None: int, param_2 = None: int, param_3 = None: int, param_4 = None: int, param_5 = None: int, param_6 = None: int) -> bool:
        if self.connection_status != ConnectionStatus.DISCONNECTED and self.connection_status != ConnectionStatus.USART_ERROR:
            return

        command = "cmd " + str(command_code) + " " + " ".join([str(param) for param in [param_1, param_2, param_3, param_4, param_5, param_6] if param is not None])

        status = self.usart_control.send_data(command)

        if not status:
            self.connection_status = ConnectionStatus.USART_ERROR
            return False

        self.connection_status = ConnectionStatus.COMMAND_PENDING
        self.timeout_timer.start(timeout)

        return status