import enum
import logging
import time
from PySide6 import QtCore

logger = logging.getLogger(__name__)

class RobotStatus(enum.Enum):
    READY               = 0
    DISCONNECTED        = 1
    NOT_SYNCHRONIZED    = 2
    COMMAND_PENDING     = 3
    TIMEOUT             = 4
    ERROR               = 5

class RobotCommands(enum.Enum):
    GET_ANGLES         = 1
    SET_ANGLES         = 2
    GET_STATUS         = 3
    SYNCHRONIZE        = 4
    MOVE_TO_POSITION   = 5

MAX_ANGLE_SINGLE_MOVE = 20
COMMAND_TIMEOUT = 5000
COMMAND_TIMEOTU_GAP = 100

class RobotControl:
    def __init__(self, usart_control):
        self.usart_control = usart_control
        self.status = RobotStatus.DISCONNECTED
        self.usart_control.connect_status_callback(self.status_changed_callback)
        self.usart_control.connect_received_callback(self.data_received_callback)



        self.home_angles = [0, 90, 90, 0, 0, 0]
        self.current_angles = self.home_angles.copy()

        self.timeout_timer = QtCore.QTimer()
        self.timeout_timer.timeout.connect(self.command_timeout_callback)

    def command_timeout_callback(self):
        if self.status == RobotStatus.COMMAND_PENDING:
            self.status = RobotStatus.TIMEOUT

    def move_to_position(self, target_angles, timeout) -> bool:
        timeout = timeout + COMMAND_TIMEOTU_GAP
        if self.status != RobotStatus.READY:
            return False

        for angle in target_angles:
            if abs(angle)>MAX_ANGLE_SINGLE_MOVE:
                return False

        return self.__send_command(str(RobotCommands.MOVE_TO_POSITION.value) + " ".join([str(int(val * 1000)) for val in target_angles]), timeout) #robot stores angles as millidegrees, convert to degrees

    def synchronize_to_position(self, angles, timeout):
        self.current_angles = angles
        if timeout is None:
            timeout = COMMAND_TIMEOUT

        self.__send_command(str(RobotCommands.SYNCHRONIZE.value) + " ".join([str(int(val * 1000)) for val in self.current_angles])), timeout) #robot stores angles as millidegrees, convert to degrees

    def set_default_position(self):
        self.synchronize_to_position(self.home_angles, 30000)

    def get_current_status(self):
        return self.status

    def get_robot_angles(self):
        self.__send_command(str(RobotCommands.GET_ANGLES.value))

    def data_received_callback(self, data):
        if data.startswith("cmd "):
            command = data[3:]
            command_code = int(command.split()[0])
            if command_code == RobotCommands.GET_ANGLES.value:
                angles = list(map(int, command.split()[1:])) #robot stores angles as millidegrees, convert to degrees
                self.current_angles = [angle / 1000 for angle in angles]
                logger.info(f"Received angles: {self.current_angles}")
                self.status = RobotStatus.READY

            elif command_code == RobotCommands.GET_STATUS.value:
                status_code = int(command.split()[1])
                if status_code not in RobotStatus._value2member_map_:
                    return
                self.status = RobotStatus(status_code)
                logger.info(f"Received status: {self.status.name}")

                
            

    def status_changed_callback(self, new_status):
        if new_status == "READY":
            self.status = RobotStatus.NOT_SYNCHRONIZED
            self.set_default_position()
        elif new_status == "DISCONNECTED":
            self.status = RobotStatus.DISCONNECTED
            self.get_robot_angles()

    def __send_command(self, command: str, timeout = COMMAND_TIMEOUT) -> bool:
        if self.status != RobotStatus.READY and self.status != RobotStatus.NOT_SYNCHRONIZED:
            return

        command = "cmd " + command

        status = self.usart_control.send_data(command)

        if not status:
            self.status = RobotStatus.ERROR
        else:
            self.status = RobotStatus.COMMAND_PENDING
            self.timeout_timer.start(timeout)

        return status