from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QAbstractTableModel 
from PySide6.QtWidgets import QComboBox, QTableView
from RobotViewport import MovementType
from kinematic_helper import *


COMMAND_INPUT_LIMITS = { # MIN, MAX, DEFAULT
    "x": (-630, 630, 0.0),
    "y": (-630, 630, 0.0),
    "z": (-630, 630, 0.0),
    "angle_0": (-180, 180, 0.0),
    "angle_1": (-180, 180, 0.0),
    "angle_2": (-180, 180, 0.0),
    "speed": (10, 100, 50),
    "acceleration": (10, 100, 50),
}

COMMAND_TABLE_HEADERS = [
    "Movement",
    "X",
    "Y",
    "Z",
    "Angle 0",
    "Angle 1",
    "Angle 2",
    "Speed",
    "Acceleration",
]


def create_double_input(field_name: str) -> QtWidgets.QDoubleSpinBox:
    min_value, max_value, default_value = COMMAND_INPUT_LIMITS[field_name]
    input_widget = QtWidgets.QDoubleSpinBox()
    input_widget.setRange(min_value, max_value)
    input_widget.setValue(default_value)
    return input_widget


def create_int_input(field_name: str) -> QtWidgets.QSpinBox:
    min_value, max_value, default_value = COMMAND_INPUT_LIMITS[field_name]
    input_widget = QtWidgets.QSpinBox()
    input_widget.setRange(min_value, max_value)
    input_widget.setValue(default_value)
    return input_widget

class Command:
    def __init__(self, movement_type: MovementType, x, y, z, angle_0, angle_1, angle_2, speed, acceleration):
        self.movement_type = movement_type
        self.x = x
        self.y = y
        self.z = z
        self.angle_0 = angle_0
        self.angle_1 = angle_1
        self.angle_2 = angle_2
        self.speed = speed
        self.acceleration = acceleration

    def to_csv_line(self):
        return (
            f"{self.movement_type.value},{self.x},{self.y},{self.z},"
            f"{self.angle_0},{self.angle_1},{self.angle_2},{self.speed},{self.acceleration}"
        )

    @classmethod
    def from_csv_line(cls, line):
        try:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 9:
                return None

            return cls(
                movement_type=MovementType(int(parts[0])),
                x=float(parts[1]),
                y=float(parts[2]),
                z=float(parts[3]),
                angle_0=float(parts[4]),
                angle_1=float(parts[5]),
                angle_2=float(parts[6]),
                speed=float(parts[7]),
                acceleration=float(parts[8]),
            )
        except (ValueError, IndexError):
            return None

    

class EditPopup(QtWidgets.QDialog):
    def __init__(self, parent=None, command: Command = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Command")
        self.setMinimumWidth(460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.movement_type_combo = QComboBox()
        self.movement_type_combo.addItem("Linear", MovementType.LINEAR)
        self.movement_type_combo.addItem("PTP", MovementType.PTP)

        self.x_input = create_double_input("x")
        self.y_input = create_double_input("y")
        self.z_input = create_double_input("z")
        self.angle_0_input = create_double_input("angle_0")
        self.angle_1_input = create_double_input("angle_1")
        self.angle_2_input = create_double_input("angle_2")

        self.speed_input = create_int_input("speed")
        self.acceleration_input = create_int_input("acceleration")

        if command:
            self.movement_type_combo.setCurrentIndex(self.movement_type_combo.findData(command.movement_type))
            self.x_input.setValue(command.x)
            self.y_input.setValue(command.y)
            self.z_input.setValue(command.z)
            self.angle_0_input.setValue(command.angle_0)
            self.angle_1_input.setValue(command.angle_1)
            self.angle_2_input.setValue(command.angle_2)
            self.speed_input.setValue(command.speed)
            self.acceleration_input.setValue(command.acceleration)

        general_group = QtWidgets.QGroupBox("General")
        general_layout = QtWidgets.QFormLayout(general_group)
        general_layout.setContentsMargins(12, 12, 12, 12)
        general_layout.setHorizontalSpacing(14)
        general_layout.setVerticalSpacing(8)
        general_layout.addRow("Movement Type:", self.movement_type_combo)
        general_layout.addRow("Speed:", self.speed_input)
        general_layout.addRow("Acceleration:", self.acceleration_input)
        layout.addWidget(general_group)

        position_group = QtWidgets.QGroupBox("Position")
        position_layout = QtWidgets.QFormLayout(position_group)
        position_layout.setContentsMargins(12, 12, 12, 12)
        position_layout.setHorizontalSpacing(14)
        position_layout.setVerticalSpacing(8)
        position_layout.addRow("X:", self.x_input)
        position_layout.addRow("Y:", self.y_input)
        position_layout.addRow("Z:", self.z_input)
        position_layout.addRow("Angle 0:", self.angle_0_input)
        position_layout.addRow("Angle 1:", self.angle_1_input)
        position_layout.addRow("Angle 2:", self.angle_2_input)
        layout.addWidget(position_group)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setContentsMargins(4, 6, 4, 0)
        button_row.addStretch(1)
        button_row.addWidget(button_box)
        layout.addLayout(button_row)

    def get_command(self):
        return Command(
            movement_type=self.movement_type_combo.currentData(),
            x=self.x_input.value(),
            y=self.y_input.value(),
            z=self.z_input.value(),
            angle_0=self.angle_0_input.value(),
            angle_1=self.angle_1_input.value(),
            angle_2=self.angle_2_input.value(),
            speed=self.speed_input.value(),
            acceleration=self.acceleration_input.value()
        )


class SimulationSteps(QAbstractTableModel):
    def __init__(self, commands: list[Command]):
        super().__init__()
        self.commands = commands
        self.headers = COMMAND_TABLE_HEADERS

    def rowCount(self, parent=None):
        return len(self.commands)
    
    def columnCount(self, parent=None):
        return len(self.headers)
    
    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        
        command = self.commands[index.row()]
        column = index.column()

        if column == 0:
            if command.movement_type == MovementType.LINEAR:
                return "LIN"
            if command.movement_type == MovementType.PTP:
                return "PTP"
            return str(command.movement_type)
        elif column == 1:
            return command.x
        elif column == 2:
            return command.y
        elif column == 3:
            return command.z
        elif column == 4:
            return command.angle_0
        elif column == 5:
            return command.angle_1
        elif column == 6:
            return command.angle_2
        elif column == 7:
            return command.speed
        elif column == 8:
            return command.acceleration
        
        return None
    
    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        
        if orientation == QtCore.Qt.Orientation.Horizontal:
            if 0 <= section < len(self.headers):
                return self.headers[section]
        
        return None

    def push_command(self, command: Command):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.commands), len(self.commands))
        self.commands.append(command)
        self.endInsertRows()

    def remove_command(self, index: int):
        if 0 <= index < len(self.commands):
            self.beginRemoveRows(QtCore.QModelIndex(), index, index)
            self.commands.pop(index)
            self.endRemoveRows()

    def update_command(self, index: int, command: Command):
        if 0 <= index < len(self.commands):
            self.commands[index] = command
            self.dataChanged.emit(self.index(index, 0), self.index(index, len(self.headers) - 1))

    def insert_command(self, index: int, command: Command):
        if 0 <= index <= len(self.commands):
            self.beginInsertRows(QtCore.QModelIndex(), index, index)
            self.commands.insert(index, command)
            self.endInsertRows()

    def swap_commands(self, index1: int, index2: int):
        if 0 <= index1 < len(self.commands) and 0 <= index2 < len(self.commands):
            self.commands[index1], self.commands[index2] = self.commands[index2], self.commands[index1]
            self.dataChanged.emit(self.index(min(index1, index2), 0), self.index(max(index1, index2), len(self.headers) - 1))

    def clear_commands(self):
        self.beginResetModel()
        self.commands.clear()
        self.endResetModel()

    def get_length(self):
        return len(self.commands)
    
    def get_command(self, index: int) -> Command | None:
        if 0 <= index < len(self.commands):
            return self.commands[index]
        return None

    def get_all_commands(self) -> list[Command]:
        return self.commands[:]

class ProgramSimulation(QtWidgets.QWidget):
    def __init__(self, ik_tab, RobotViewport):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        self.ik_tab = ik_tab
        self.RobotViewport = RobotViewport

        self.open_file_button = QtWidgets.QPushButton("Open File")
        self.open_file_button.clicked.connect(self.open_file)

        self.add_button = QtWidgets.QPushButton("Add step")
        self.add_button.clicked.connect(self.handle_add)

        self.remove_button = QtWidgets.QPushButton("Remove step")
        self.remove_button.clicked.connect(self.handle_remove)

        self.edit_button = QtWidgets.QPushButton("Edit step")
        self.edit_button.clicked.connect(self.handle_edit)

        self.save_button = QtWidgets.QPushButton("Save file")
        self.save_button.clicked.connect(self.handle_save)

        horizontal_layout = QtWidgets.QHBoxLayout()
        horizontal_layout.addWidget(self.open_file_button)
        horizontal_layout.addWidget(self.remove_button)
        horizontal_layout.addWidget(self.add_button)
        horizontal_layout.addWidget(self.edit_button)
        horizontal_layout.addWidget(self.save_button)
        layout.addLayout(horizontal_layout)


        self.speed_input = create_int_input("speed")

        self.acceleration_input = create_int_input("acceleration")

        self.move_up_button = QtWidgets.QPushButton("Move Up")
        self.move_up_button.clicked.connect(self.handle_move_up)

        self.move_down_button = QtWidgets.QPushButton("Move Down")
        self.move_down_button.clicked.connect(self.handle_move_down)

        horizontal_layout2 = QtWidgets.QHBoxLayout()
        horizontal_layout2.addWidget(QtWidgets.QLabel("Speed:"))
        horizontal_layout2.addWidget(self.speed_input)
        horizontal_layout2.addWidget(QtWidgets.QLabel("Acceleration:"))
        horizontal_layout2.addWidget(self.acceleration_input)
        horizontal_layout2.addWidget(self.move_up_button)
        horizontal_layout2.addWidget(self.move_down_button)
        layout.addLayout(horizontal_layout2)

        icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay)

        pixmap = icon.pixmap(32, 32)
        flipped = pixmap.transformed(QtGui.QTransform().scale(-1, 1))  # odbicie poziome

        self.back_button = QtWidgets.QPushButton("Back")
        self.back_button.clicked.connect(self.handle_play_back)
        self.back_button.setIcon(QtGui.QIcon(flipped))

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.handle_stop)
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaStop))

        self.play_button = QtWidgets.QPushButton("Play")
        self.play_button.clicked.connect(self.handle_play)
        self.play_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay))

        self.continous_play_checkbox = QtWidgets.QCheckBox("Continuous play")
        self.continous_play_checkbox.setChecked(True)

        horizontal_layout3 = QtWidgets.QHBoxLayout()
        horizontal_layout3.addWidget(self.back_button)
        horizontal_layout3.addWidget(self.stop_button)
        horizontal_layout3.addWidget(self.play_button)
        horizontal_layout3.addWidget(self.continous_play_checkbox)

        layout.addLayout(horizontal_layout3)

        self.command_view = QTableView()
        self.command_layout = SimulationSteps([])
        self.command_view.setModel(self.command_layout)
        self.command_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.command_view.setSelectionMode(QTableView.SingleSelection)
        self.command_view.viewport().installEventFilter(self)

        

        layout.addWidget(self.command_view)


    def eventFilter(self, source, event):
        if source == self.command_view.viewport() and event.type() == QtCore.QEvent.MouseButtonPress:
            index = self.command_view.indexAt(event.pos())
            if not index.isValid():
                self.command_view.clearSelection()
                self.command_view.setCurrentIndex(self.command_view.model().index(-1, 0))
        return super().eventFilter(source, event)

    def _movement_label(self, movement_type: MovementType) -> str:
        if movement_type == MovementType.LINEAR:
            return "Linear"
        if movement_type == MovementType.PTP:
            return "PTP"
        return str(movement_type)

    def connect_to_kinematic_manager(self, kinematic_manager):
        self.kinematic_manager = kinematic_manager

    def open_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open program file",
            "",
            "Program files (*.gcode *.txt)",
        )
        if not file_path:
            return

        self.command_view.clearSelection()
        self.command_view.model().clear_commands()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    cmd = Command.from_csv_line(line)
                    if cmd is not None:
                        self.command_view.model().push_command(cmd)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Open file", f"Failed to open file:\n{exc}")
            return

    def handle_add(self):
        movement_type = self.RobotViewport.get_current_movement_type()
        speed = self.speed_input.value()
        acceleration = self.acceleration_input.value()
        position = self.ik_tab.get_values()
        command = Command(movement_type, *position, speed, acceleration)

        selected_item = self.command_view.currentIndex().row()
        if selected_item != -1:
            self.command_view.model().insert_command(selected_item, command)
            return

        self.command_view.model().push_command(command)

    def handle_remove(self):
        row = self.command_view.currentIndex().row()
        if row == -1:
            return

        self.command_view.clearSelection()
        self.command_view.setCurrentIndex(self.command_view.model().index(-1, 0))

        self.command_view.model().remove_command(row)

    def handle_edit(self):

        command = self.command_view.model().get_command(self.command_view.currentIndex().row())

        if command is None:
            return
        
        popup = EditPopup(self, command=command)
        if popup.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            command = popup.get_command()
            self.command_view.model().update_command(self.command_view.currentIndex().row(), command)

        
    def handle_save(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save program file",
            "",
            "Program files (*.gcode)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for cmd in self.command_view.model().get_all_commands():
                    f.write(cmd.to_csv_line() + "\n")
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Save file", f"Failed to save file:\n{exc}")

    def handle_play_back(self):
        if self.command_view.currentIndex().row() != -1:
            self.current_command_index = self.command_view.currentIndex().row()
        else:
            self.current_command_index = self.command_view.model().get_length() - 1

        self.direction_factor = -1
        self.move_robot_to_commands(self.current_command_index)

    def handle_play(self):
        if self.command_view.currentIndex().row() != -1:
            self.current_command_index = self.command_view.currentIndex().row()
        else:
            self.current_command_index = 0

        self.direction_factor = 1
        self.move_robot_to_commands(self.current_command_index)


    def handle_stop(self):
        self.kinematic_manager.abort_motion()

    def handle_next(self):
        if self.current_command_index is None:
            return 
        
        if not self.continous_play_checkbox.isChecked():
            index = self.current_command_index + self.direction_factor
            if index < 0 or index >= self.command_view.model().get_length():
                return
            model_index = self.command_view.model().index(index, 0)
            self.command_view.setCurrentIndex(model_index)
            return
        
        self.current_command_index += self.direction_factor

        self.move_robot_to_commands(self.current_command_index)

    def move_robot_to_commands(self, index):

        if index < 0 or index >= self.command_view.model().get_length():
            return

        model_index = self.command_view.model().index(index, 0)
        self.command_view.setCurrentIndex(model_index)

        desired_command = self.command_view.model().get_command(index)

        if desired_command is None:
            return
        

        x, y, z = desired_command.x, desired_command.y, desired_command.z
        angle_0, angle_1, angle_2 = desired_command.angle_0, desired_command.angle_1, desired_command.angle_2

        position_tuple = (x, y, z, angle_0, angle_1, angle_2)

        speed = desired_command.speed
        acceleration = desired_command.acceleration

        move_type = desired_command.movement_type

        if move_type == MovementType.LINEAR:
            self.kinematic_manager.plan_motion(position_tuple, speed=speed, acceleration=acceleration, movement=move_type,set_EDGE_ROBOT = True ,callback=self.handle_next)

        elif move_type == MovementType.PTP:
            position_tuple = calculate_ik(*position_tuple)
            self.kinematic_manager.plan_motion(position_tuple, speed=speed, acceleration=acceleration, movement=move_type,set_EDGE_ROBOT = True ,callback=self.handle_next)

    def handle_move_up(self):
        current_row = self.command_view.currentIndex().row()
        self.command_view.model().swap_commands(current_row, current_row - 1)

    def handle_move_down(self):
        current_row = self.command_view.currentIndex().row()
        self.command_view.model().swap_commands(current_row, current_row + 1)
