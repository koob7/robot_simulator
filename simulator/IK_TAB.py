from PySide6 import QtCore, QtWidgets


class IK_TAB(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.N_ANGLE_SLIDERS = 3
        self.N_POSITION_SLIDERS = 3

        self.sliders = [None] * (self.N_ANGLE_SLIDERS + self.N_POSITION_SLIDERS)
        self.value_labels = [None] * (self.N_ANGLE_SLIDERS + self.N_POSITION_SLIDERS)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Position Control Group
        pos_group = QtWidgets.QGroupBox("Position Control (mm)")
        pos_layout = QtWidgets.QGridLayout(pos_group)
        pos_layout.setSpacing(6)

        labels_pos = ["X", "Y", "Z"]
        for idx in range(self.N_POSITION_SLIDERS):
            self.sliders[idx] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[idx].setMinimum(-400)
            self.sliders[idx].setMaximum(400)
            self.sliders[idx].setSingleStep(1)
            self.sliders[idx].setPageStep(10)
            self.sliders[idx].setValue(0)

            label = QtWidgets.QLabel(f"{labels_pos[idx]} Position:")
            label.setStyleSheet("font-weight: bold;")
            self.value_labels[idx] = QtWidgets.QLabel("0 mm")
            font = self.value_labels[idx].font()
            font.setBold(True)
            self.value_labels[idx].setFont(font)
            self.value_labels[idx].setMinimumWidth(60)
            self.sliders[idx].valueChanged.connect(
                lambda value, idx=idx: self.update_label(idx, value)
            )

            pos_layout.addWidget(label, idx, 0)
            pos_layout.addWidget(self.sliders[idx], idx, 1)
            pos_layout.addWidget(self.value_labels[idx], idx, 2)

        main_layout.addWidget(pos_group)

        # Angle Control Group
        angle_group = QtWidgets.QGroupBox("Angle Control (degrees)")
        angle_layout = QtWidgets.QGridLayout(angle_group)
        angle_layout.setSpacing(6)

        labels_angle = ["Roll", "Pitch", "Yaw"]
        for idx in range(self.N_ANGLE_SLIDERS):
            idx = self.N_POSITION_SLIDERS + idx
            self.sliders[idx] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[idx].setMinimum(-180)
            self.sliders[idx].setMaximum(180)
            self.sliders[idx].setSingleStep(1)
            self.sliders[idx].setPageStep(10)
            self.sliders[idx].setValue(0)

            label = QtWidgets.QLabel(f"{labels_angle[idx - self.N_POSITION_SLIDERS]}:")
            label.setStyleSheet("font-weight: bold;")
            self.value_labels[idx] = QtWidgets.QLabel("0°")
            font = self.value_labels[idx].font()
            font.setBold(True)
            self.value_labels[idx].setFont(font)
            self.value_labels[idx].setMinimumWidth(60)
            self.sliders[idx].valueChanged.connect(
                lambda value, idx=idx: self.update_label(idx, value)
            )

            angle_layout.addWidget(label, idx, 0)
            angle_layout.addWidget(self.sliders[idx], idx, 1)
            angle_layout.addWidget(self.value_labels[idx], idx, 2)

        main_layout.addWidget(angle_group)

        # Reset button
        reset_btn = QtWidgets.QPushButton("Reset to Zero")
        reset_btn.clicked.connect(self.reset_value)
        main_layout.addWidget(reset_btn)

        main_layout.addStretch()

    def reset_value(self):
        for slider in self.sliders:
            slider.setValue(0)

    def link_ik_changed_callback(self, callback):
        for slider in self.sliders:
            slider.valueChanged.connect(callback)

    def link_ik_released_callback(self, callback):
        for slider in self.sliders:
            slider.sliderReleased.connect(callback)

    def update_label(self, idx, value):
        if idx < self.N_POSITION_SLIDERS:
            self.value_labels[idx].setText(f"{value} mm")
        else:
            self.value_labels[idx].setText(f"{value}°")

    def get_values(self):
        return [slider.value() for slider in self.sliders]
    
    def set_values(self, x: int, y: int, z: int, roll: int, pitch: int, yaw: int):
        values = [x, y, z, roll, pitch, yaw]
        for idx in range(self.N_ANGLE_SLIDERS + self.N_POSITION_SLIDERS):
            self.update_label(idx, values[idx])
            self.sliders[idx].blockSignals(True)
            self.sliders[idx].setValue(values[idx])
            self.sliders[idx].blockSignals(False)