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

        for i in range(self.N_ARM_SLIDERS):
            self.sliders[i] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[i].setMinimum(-180)
            self.sliders[i].setMaximum(180)
            self.sliders[i].setSingleStep(1)
            self.sliders[i].setPageStep(10)
            self.sliders[i].setValue(0)
            self.sliders[i].valueChanged.connect(self.on_value_changed)

            label = QtWidgets.QLabel(f"Joint {i + 1}:")
            label.setStyleSheet("font-weight: bold;")
            self.value_labels[i] = QtWidgets.QLabel("0°")
            font = self.value_labels[i].font()
            font.setBold(True)
            self.value_labels[i].setFont(font)
            self.value_labels[i].setMinimumWidth(60)

            joint_layout.addWidget(label, i, 0)
            joint_layout.addWidget(self.sliders[i], i, 1)
            joint_layout.addWidget(self.value_labels[i], i, 2)

        main_layout.addWidget(joint_group)

        # Reset button
        reset_btn = QtWidgets.QPushButton("Reset to Zero")
        reset_btn.clicked.connect(self.reset_value)
        main_layout.addWidget(reset_btn)

        main_layout.addStretch()

    def on_value_changed(self, value: int):
        slider = self.sender()
        index = self.sliders.index(slider)

        self.value_labels[index].setText(f"{value}°")
        print(f"FK Joint {index + 1}: {value}")

    def reset_value(self):
        for slider in self.sliders:
            slider.setValue(0)