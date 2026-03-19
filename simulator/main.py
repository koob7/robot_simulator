import sys
import time
import math
from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper
from RobotViewport import RobotViewport


class AngleSlider(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMinimum(-180)
        self.slider.setMaximum(180)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setValue(0)

        self.value_label = QtWidgets.QLabel("Kat: 0")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.value_label)
        layout.addWidget(self.slider)

        self.slider.valueChanged.connect(self.on_value_changed)

    def on_value_changed(self, value: int):
        self.value_label.setText(f"Kat: {value}")
        print(value)

    def reset_value(self):
        self.slider.setValue(0)



class MainWindow(QtWidgets.QSplitter):
    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Vertical)
        self.setWindowTitle("Robot simulator")
        self.resize(700, 500)

        self.robot_viewport = RobotViewport()
        self.angle_slider = AngleSlider()

        self.addWidget(self.robot_viewport)
        self.addWidget(self.angle_slider)
        self.setSizes([340, 160])


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())