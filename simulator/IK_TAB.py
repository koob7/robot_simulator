from PySide6 import QtCore, QtWidgets




class IK_TAB(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.N_ANGLE_SLIDERS = 3
        self.N_POSITION_SLIDERS = 3

        self.sliders = [None] * (self.N_ANGLE_SLIDERS+self.N_POSITION_SLIDERS)
        self.value_labels = [None] * (self.N_ANGLE_SLIDERS+self.N_POSITION_SLIDERS)

        layout = QtWidgets.QVBoxLayout(self)

        for i in range(self.N_POSITION_SLIDERS):
            self.sliders[i] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[i].setMinimum(-300)
            self.sliders[i].setMaximum(300)
            self.sliders[i].setSingleStep(1)
            self.sliders[i].setPageStep(10)
            self.sliders[i].setValue(0)
            self.sliders[i].valueChanged.connect(self.on_value_changed)

            self.value_labels[i] = QtWidgets.QLabel("Pose: 0")
            layout.addWidget(self.value_labels[i])
            layout.addWidget(self.sliders[i])

        for i in range(self.N_POSITION_SLIDERS,self.N_POSITION_SLIDERS+ self.N_ANGLE_SLIDERS):
            self.sliders[i] = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sliders[i].setMinimum(-180)
            self.sliders[i].setMaximum(180)
            self.sliders[i].setSingleStep(1)
            self.sliders[i].setPageStep(10)
            self.sliders[i].setValue(0)
            self.sliders[i].valueChanged.connect(self.on_value_changed)
            
            self.value_labels[i] = QtWidgets.QLabel("Kat: 0")
            layout.addWidget(self.value_labels[i])
            layout.addWidget(self.sliders[i])


    def on_value_changed(self, value: int):
        slider = self.sender()
        index = self.sliders.index(slider)

        self.value_labels[index].setText(f"Kat: {value}")
        print(f"Slider {index}: {value}")

    def reset_value(self):
        for slider in self.sliders:
            slider.setValue(0)