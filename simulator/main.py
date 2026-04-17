import sys
from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper
from RobotViewport import RobotViewport
from IK_TAB import IK_TAB
from FK_TAB import FK_TAB
from VELOCITY_TAB import VELOCITY_TAB
from kinematicManager import kinematicManager
from USART_TAB import USART_TAB
from programSimulation import ProgramSimulation
from usart_control import USARTControl
from robot_control import robot_control, ROBOT_STATUS_TAB

from PySide6.QtCore import QTimer, Signal

import math
from ctypes import c_float, POINTER

import time

import logging

logging.basicConfig(
    level=logging.INFO,  # DEBUG / INFO / WARNING / ERROR / CRITICAL
    format="%(levelname)s: %(message)s"
)

class ButtonTabWidget(QtWidgets.QWidget):
    tab_minimized = Signal(object,bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.widgets = {}
        self.active_widgets = {}

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.minimumHeight = 200
        self.main_layout.addWidget(self.splitter)

    def add_tab(self, widget: QtWidgets.QWidget, name: str, default_active=False):
        self.widgets[name] = widget

        if hasattr(widget, "on_tab_minimized"):
            self.tab_minimized.connect(widget.on_tab_minimized)

        btn = QtWidgets.QPushButton(name)
        btn.clicked.connect(lambda checked=False, n=name: self.toggle_tab(n))
        self.button_layout.addWidget(btn)
        if default_active:
            self.toggle_tab(name)

    def toggle_tab(self, name: str):
        widget = self.widgets[name]
        state = widget in self.active_widgets
        self.tab_minimized.emit(widget, state)
        if widget in self.active_widgets:
            self.active_widgets.pop(widget)
            widget.setParent(None)
        else:
            self.active_widgets[widget] = True
            self.splitter.addWidget(widget)
        
        count = self.splitter.count()
        if count > 0:
            self.splitter.setSizes([self.splitter.width() // count] * count)
        

class MainWindow(QtWidgets.QSplitter):
    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Vertical)
        self.setWindowTitle("Robot simulator")
        self.resize(1000, 700)

        self.robot_viewport = RobotViewport()
        self.addWidget(self.robot_viewport)

        self.usart_control = USARTControl()

        self.ik_tab = IK_TAB()
        self.fk_tab = FK_TAB()
        self.velocity_tab = VELOCITY_TAB()
        self.usart_tab = USART_TAB(usart_interface=self.usart_control)
        self.program_simulation_tab = ProgramSimulation(self.ik_tab, self.robot_viewport)
        self.robot_control = robot_control(self.usart_control)
        self.robot_status_tab = ROBOT_STATUS_TAB(self.robot_control)

        self.tabs = ButtonTabWidget()
        self.tabs.add_tab(self.ik_tab, "IK control")
        self.tabs.add_tab(self.fk_tab, "FK control", default_active=True)
        self.tabs.add_tab(self.velocity_tab, "Velocity chart")
        self.tabs.add_tab(self.usart_tab, "USART monitor", default_active=True)
        self.tabs.add_tab(self.robot_status_tab, "Robot control", default_active=True)
        self.tabs.add_tab(self.program_simulation_tab, "Program Simulation")
        self.addWidget(self.tabs)


        self.setStretchFactor(0, 2)  # robot_viewport
        self.setStretchFactor(1, 1)  # tabs

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Apply modern stylesheet
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    kinematic_manager = kinematicManager(window.ik_tab, window.fk_tab, window.velocity_tab, window.robot_viewport, window.robot_control)

    window.program_simulation_tab.connect_to_kinematic_manager(kinematic_manager)

    sys.exit(app.exec())