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
        for i in range(self.N_POSITION_SLIDERS):
            self.sliders[i] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[i].setMinimum(-300)
            self.sliders[i].setMaximum(300)
            self.sliders[i].setSingleStep(1)
            self.sliders[i].setPageStep(10)
            self.sliders[i].setValue(0)

            label = QtWidgets.QLabel(f"{labels_pos[i]} Position:")
            label.setStyleSheet("font-weight: bold;")
            self.value_labels[i] = QtWidgets.QLabel("0 mm")
            font = self.value_labels[i].font()
            font.setBold(True)
            self.value_labels[i].setFont(font)
            self.value_labels[i].setMinimumWidth(60)

            pos_layout.addWidget(label, i, 0)
            pos_layout.addWidget(self.sliders[i], i, 1)
            pos_layout.addWidget(self.value_labels[i], i, 2)

        main_layout.addWidget(pos_group)

        # Angle Control Group
        angle_group = QtWidgets.QGroupBox("Angle Control (degrees)")
        angle_layout = QtWidgets.QGridLayout(angle_group)
        angle_layout.setSpacing(6)

        labels_angle = ["Roll", "Pitch", "Yaw"]
        for i in range(self.N_ANGLE_SLIDERS):
            idx = self.N_POSITION_SLIDERS + i
            self.sliders[idx] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[idx].setMinimum(-180)
            self.sliders[idx].setMaximum(180)
            self.sliders[idx].setSingleStep(1)
            self.sliders[idx].setPageStep(10)
            self.sliders[idx].setValue(0)

            label = QtWidgets.QLabel(f"{labels_angle[i]}:")
            label.setStyleSheet("font-weight: bold;")
            self.value_labels[idx] = QtWidgets.QLabel("0°")
            font = self.value_labels[idx].font()
            font.setBold(True)
            self.value_labels[idx].setFont(font)
            self.value_labels[idx].setMinimumWidth(60)

            angle_layout.addWidget(label, i, 0)
            angle_layout.addWidget(self.sliders[idx], i, 1)
            angle_layout.addWidget(self.value_labels[idx], i, 2)

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

    def get_values(self):
        return [slider.value() for slider in self.sliders]