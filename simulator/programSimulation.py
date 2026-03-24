from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QComboBox
from RobotViewport import MovementType


COMMAND_INPUT_LIMITS = {
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

    def __str__(self):
        return f"Command(type={self.movement_type}, x={self.x}, y={self.y}, z={self.z}, angle_0={self.angle_0}, angle_1={self.angle_1}, angle_2={self.angle_2}, speed={self.speed}, acceleration={self.acceleration})"

    def to_csv_line(self):
        return (
            f"{self.movement_type.value},{self.x},{self.y},{self.z},"
            f"{self.angle_0},{self.angle_1},{self.angle_2},{self.speed},{self.acceleration}"
        )
    
    def __restore__(self, line):
        try:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 9:
                return None

            self.movement_type = MovementType(int(parts[0]))
            self.x = float(parts[1])
            self.y = float(parts[2])
            self.z = float(parts[3])
            self.angle_0 = float(parts[4])
            self.angle_1 = float(parts[5])
            self.angle_2 = float(parts[6])
            self.speed = float(parts[7])
            self.acceleration = float(parts[8])
            return self
        except (ValueError, IndexError):
            return None

    @classmethod
    def from_csv_line(cls, line):
        cmd = cls(MovementType.LINEAR, 0, 0, 0, 0, 0, 0, 50, 50)
        return cmd.__restore__(line)

    

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

        horizontal_layout2 = QtWidgets.QHBoxLayout()
        horizontal_layout2.addWidget(QtWidgets.QLabel("Speed:"))
        horizontal_layout2.addWidget(self.speed_input)
        horizontal_layout2.addWidget(QtWidgets.QLabel("Acceleration:"))
        horizontal_layout2.addWidget(self.acceleration_input)
        layout.addLayout(horizontal_layout2)

        icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay)

        pixmap = icon.pixmap(32, 32)
        flipped = pixmap.transformed(QtGui.QTransform().scale(-1, 1))  # odbicie poziome

        self.back_button = QtWidgets.QPushButton("Back")
        self.back_button.clicked.connect(self.handle_back)
        self.back_button.setIcon(QtGui.QIcon(flipped))

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.handle_stop)
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaStop))

        self.play_button = QtWidgets.QPushButton("Play")
        self.play_button.clicked.connect(self.handle_play)
        self.play_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay))

        horizontal_layout3 = QtWidgets.QHBoxLayout()
        horizontal_layout3.addWidget(self.back_button)
        horizontal_layout3.addWidget(self.stop_button)
        horizontal_layout3.addWidget(self.play_button)

        layout.addLayout(horizontal_layout3)
        self.commands = []
        self.command_list = QtWidgets.QTableWidget(0, len(COMMAND_TABLE_HEADERS))
        self.command_list.setHorizontalHeaderLabels(COMMAND_TABLE_HEADERS)
        self.command_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.command_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.command_list.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.command_list.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.command_list)

    def _movement_label(self, movement_type: MovementType) -> str:
        if movement_type == MovementType.LINEAR:
            return "Linear"
        if movement_type == MovementType.PTP:
            return "PTP"
        return str(movement_type)

    def _command_row_values(self, command: Command):
        return [
            self._movement_label(command.movement_type),
            str(command.x),
            str(command.y),
            str(command.z),
            str(command.angle_0),
            str(command.angle_1),
            str(command.angle_2),
            str(command.speed),
            str(command.acceleration),
        ]

    def _set_command_row(self, row: int, command: Command):
        for column, value in enumerate(self._command_row_values(command)):
            item = QtWidgets.QTableWidgetItem(value)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.command_list.setItem(row, column, item)

    def _append_command_row(self, command: Command):
        row = self.command_list.rowCount()
        self.command_list.insertRow(row)
        self._set_command_row(row, command)

    def _insert_command_row(self, row: int, command: Command):
        self.command_list.insertRow(row)
        self._set_command_row(row, command)

    def _select_row(self, row: int):
        if row < 0 or row >= self.command_list.rowCount():
            return
        self.command_list.setCurrentCell(row, 0)
        self.command_list.selectRow(row)

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

        loaded_commands = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    cmd = Command.from_csv_line(line)
                    if cmd is not None:
                        loaded_commands.append(cmd)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Open file", f"Failed to open file:\n{exc}")
            return

        self.commands = loaded_commands
        self.command_list.setRowCount(0)
        for cmd in self.commands:
            self._append_command_row(cmd)

    def handle_add(self):
        movement_type = self.RobotViewport.get_current_movement_type()
        speed = self.speed_input.value()
        acceleration = self.acceleration_input.value()
        position = self.ik_tab.get_values()
        command = Command(movement_type, *position, speed, acceleration)

        selected_item = self.command_list.currentRow()
        if selected_item != -1:
            self.commands.insert(selected_item, command)
            self._insert_command_row(selected_item, command)
            self._select_row(selected_item)
            return

        self.commands.append(command)
        self._append_command_row(command)
        

    def handle_remove(self):
        row = self.command_list.currentRow()
        if row == -1:
            return

        self.command_list.removeRow(row)
        if 0 <= row < len(self.commands):
            self.commands.pop(row)

    def handle_edit(self):
        row = self.command_list.currentRow()
        if not (0 <= row < len(self.commands)):
            return

        popup = EditPopup(self, command=self.commands[row])
        if popup.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            command = popup.get_command()
            self.commands[row] = command
            self._set_command_row(row, command)
            self._select_row(row)

        
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
                for cmd in self.commands:
                    f.write(cmd.to_csv_line() + "\n")
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Save file", f"Failed to save file:\n{exc}")

    def handle_back(self):
        if self.command_list.currentRow() != -1:
            self.current_command_index = self.command_list.currentRow()
        else:
            self.current_command_index = 0

        self.direction_factor = -1
        self.move_robot_to_commands(self.current_command_index)


    def handle_stop(self):
        self.kinematic_manager.abort_motion()

    def handle_next(self):
        if self.current_command_index is None:
            return 
        if self.direction_factor == 1 and self.current_command_index < len(self.commands) - 1:
            self.current_command_index += self.direction_factor

        elif self.direction_factor == -1 and self.current_command_index > 0:
            self.current_command_index += self.direction_factor

        self.move_robot_to_commands(self.current_command_index)

    def handle_play(self):
        if self.command_list.currentRow() != -1:
            self.current_command_index = self.command_list.currentRow()
        else:
            self.current_command_index = 0

        self.direction_factor = 1
        self.move_robot_to_commands(self.current_command_index)

    def move_robot_to_commands(self, index):
        self._select_row(index)
        x, y, z = self.commands[index].x, self.commands[index].y, self.commands[index].z
        angle_0, angle_1, angle_2 = self.commands[index].angle_0, self.commands[index].angle_1, self.commands[index].angle_2

        position_touple = (x, y, z, angle_0, angle_1, angle_2)

        speed = self.commands[index].speed
        acceleration = self.commands[index].acceleration

        move_type = self.commands[index].movement_type

        self.kinematic_manager.plan_motion(position_touple, speed=speed, acceleration=acceleration, movement=move_type,set_EDGE_ROBOT = True ,callback=self.handle_next)

        








