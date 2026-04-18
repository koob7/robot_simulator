from PySide6 import QtCore, QtWidgets



class FK_TAB(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.N_ARM_SLIDERS = 6

        self.sliders = [None] * (self.N_ARM_SLIDERS)
        self.value_labels = [None] * (self.N_ARM_SLIDERS)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Joint Control Group
        joint_group = QtWidgets.QGroupBox("Joint Angles (degrees)")
        joint_layout = QtWidgets.QGridLayout(joint_group)
        joint_layout.setSpacing(6)

        for idx in range(self.N_ARM_SLIDERS):
            self.sliders[idx] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[idx].setMinimum(-180)
            self.sliders[idx].setMaximum(180)
            self.sliders[idx].setSingleStep(1)
            self.sliders[idx].setPageStep(10)
            self.sliders[idx].setValue(0)

            label = QtWidgets.QLabel(f"Joint {idx + 1}:")
            label.setStyleSheet("font-weight: bold;")
            self.value_labels[idx] = QtWidgets.QLabel("0°")
            font = self.value_labels[idx].font()
            font.setBold(True)
            self.value_labels[idx].setFont(font)
            self.value_labels[idx].setMinimumWidth(60)
            self.sliders[idx].valueChanged.connect(
                lambda value, idx=idx: self.update_label(idx, value)
            )

            joint_layout.addWidget(label, idx, 0)
            joint_layout.addWidget(self.sliders[idx], idx, 1)
            joint_layout.addWidget(self.value_labels[idx], idx, 2)

        main_layout.addWidget(joint_group)

        # Reset button
        reset_btn = QtWidgets.QPushButton("Reset to Zero")
        reset_btn.clicked.connect(self.reset_value)
        main_layout.addWidget(reset_btn)

        main_layout.addStretch()

    def reset_value(self):
        for slider in self.sliders:
            slider.setValue(0)
        self.sliders[2].setValue(90)
        self.fk_released_callback()

    def update_label(self, idx, value):
        self.value_labels[idx].setText(f"{value}°")

    def link_fk_changed_callback(self, callback):
        for slider in self.sliders:
            slider.valueChanged.connect(callback)

    def link_fk_released_callback(self, callback):
        for slider in self.sliders:
            slider.sliderReleased.connect(callback)
        self.fk_released_callback = callback
        

    def get_values(self):
        return [slider.value() for slider in self.sliders]
    
    def set_values(self, angle_0: int, angle_1: int, angle_2: int, angle_3: int, angle_4: int, angle_5: int):
        angles = [angle_0, angle_1, angle_2, angle_3, angle_4, angle_5]
        for idx in range(self.N_ARM_SLIDERS):
            self.value_labels[idx].setText(f"{angles[idx]}°")
            self.sliders[idx].blockSignals(True)
            self.sliders[idx].setValue(angles[idx])
            self.sliders[idx].blockSignals(False)