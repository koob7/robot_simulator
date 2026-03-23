from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QComboBox
from RobotViewport import MovementType

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

        layout = QtWidgets.QVBoxLayout(self)

        self.movement_type_combo = QComboBox()
        self.movement_type_combo.addItem("Linear", MovementType.LINEAR)
        self.movement_type_combo.addItem("PTP", MovementType.PTP)

        self.x_input = QtWidgets.QDoubleSpinBox()
        self.x_input.setRange(-630, 630)
        self.x_input.setValue(0)
        self.y_input = QtWidgets.QDoubleSpinBox()
        self.y_input.setRange(-630, 630)   
        self.y_input.setValue(0)
        self.z_input = QtWidgets.QDoubleSpinBox()
        self.z_input.setRange(-630, 630)
        self.z_input.setValue(0)
        self.angle_0_input = QtWidgets.QDoubleSpinBox()
        self.angle_0_input.setRange(-180, 180)
        self.angle_0_input.setValue(0)
        self.angle_1_input = QtWidgets.QDoubleSpinBox()
        self.angle_1_input.setRange(-180, 180)
        self.angle_1_input.setValue(0)
        self.angle_2_input = QtWidgets.QDoubleSpinBox()
        self.angle_2_input.setRange(-180, 180)
        self.angle_2_input.setValue(0)

        self.speed_input = QtWidgets.QSpinBox()
        self.speed_input.setRange(10, 100)
        self.speed_input.setValue(50)
        self.acceleration_input = QtWidgets.QSpinBox()
        self.acceleration_input.setRange(10, 100)
        self.acceleration_input.setValue(50)

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
        

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Movement Type:", self.movement_type_combo)
        form_layout.addRow("X:", self.x_input)
        form_layout.addRow("Y:", self.y_input)
        form_layout.addRow("Z:", self.z_input)
        form_layout.addRow("Angle 0:", self.angle_0_input)
        form_layout.addRow("Angle 1:", self.angle_1_input)
        form_layout.addRow("Angle 2:", self.angle_2_input)
        form_layout.addRow("Speed:", self.speed_input)
        form_layout.addRow("Acceleration:", self.acceleration_input)
        layout.addLayout(form_layout)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

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


        self.speed_input = QtWidgets.QSpinBox()
        self.speed_input.setRange(10, 100)
        self.speed_input.setValue(50)

        self.acceleration_input = QtWidgets.QSpinBox()
        self.acceleration_input.setRange(10, 100)
        self.acceleration_input.setValue(50)

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
        self.command_list = QtWidgets.QListWidget()
        self.command_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.command_list)

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
        self.command_list.clear()
        for cmd in self.commands:
            self.command_list.addItem(str(cmd))

    def handle_add(self):
        movement_type = self.RobotViewport.get_current_movement_type()
        speed = self.speed_input.value()
        acceleration = self.acceleration_input.value()
        position = self.ik_tab.get_values()
        command = Command(movement_type, *position, speed, acceleration)

        selected_item = self.command_list.currentRow()
        if selected_item != -1:
            self.commands.insert(selected_item, command)
            self.command_list.insertItem(selected_item, str(command))
            self.command_list.setCurrentRow(selected_item)
            return

        self.command_list.addItem(str(command))
        self.commands.append(command)
        

    def handle_remove(self):
        selected_item = self.command_list.currentItem()
        if selected_item is None:
            return

        row = self.command_list.row(selected_item)
        self.command_list.takeItem(row)
        if 0 <= row < len(self.commands):
            self.commands.pop(row)

    def handle_edit(self):
        selected_items = self.command_list.currentItem()
        if not selected_items:
            return

        row = self.command_list.row(selected_items)
        if not (0 <= row < len(self.commands)):
            return

        popup = EditPopup(self, command=self.commands[row])
        if popup.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            command = popup.get_command()
            selected_items.setText(str(command))
            self.commands[row] = command

        
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
        self.command_list.setCurrentRow(index)
        x, y, z = self.commands[index].x, self.commands[index].y, self.commands[index].z
        angle_0, angle_1, angle_2 = self.commands[index].angle_0, self.commands[index].angle_1, self.commands[index].angle_2

        position_touple = (x, y, z, angle_0, angle_1, angle_2)

        speed = self.commands[index].speed
        acceleration = self.commands[index].acceleration

        move_type = self.commands[index].movement_type

        self.kinematic_manager.plan_motion(position_touple, speed=speed, acceleration=acceleration, movement=move_type,set_EDGE_ROBOT = True ,callback=self.handle_next)

        








