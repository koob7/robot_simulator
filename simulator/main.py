import sys
from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper
from RobotViewport import RobotViewport
from IK_TAB import IK_TAB
from FK_TAB import FK_TAB
from VELOCITY_TAB import VELOCITY_TAB
from kinematicManager import kinematicManager
from USART_TAB import USART_TAB

import logging

logging.basicConfig(
    level=logging.INFO,  # DEBUG / INFO / WARNING / ERROR / CRITICAL
    format="%(levelname)s: %(message)s"
)

class ButtonTabWidget(QtWidgets.QWidget):
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

    def add_tab(self, widget: QtWidgets.QWidget, name: str):
        self.widgets[name] = widget
        btn = QtWidgets.QPushButton(name)
        btn.clicked.connect(lambda checked=False, n=name: self.toggle_tab(n))
        self.button_layout.addWidget(btn)

    def toggle_tab(self, name: str):
        widget = self.widgets[name]
        if widget in self.active_widgets:
            self.active_widgets.pop(widget)
            widget.setParent(None)
        else:
            self.active_widgets[widget] = True
            self.splitter.addWidget(widget)
        
        count = self.splitter.count()
        self.splitter.setSizes([self.splitter.width() // count] * count)
            

class MainWindow(QtWidgets.QSplitter):
    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Vertical)
        self.setWindowTitle("Robot simulator")
        self.resize(700, 500)

        self.robot_viewport = RobotViewport()
        self.addWidget(self.robot_viewport)

        self.ik_tab = IK_TAB()
        self.fk_tab = FK_TAB()
        self.velocity_tab = VELOCITY_TAB()
        self.usart_tab = USART_TAB()

        self.tabs = ButtonTabWidget()
        self.tabs.add_tab(self.ik_tab, "IK control")
        self.tabs.add_tab(self.fk_tab, "FK control")
        self.tabs.add_tab(self.velocity_tab, "Velocity chart")
        self.tabs.add_tab(self.usart_tab, "USART monitor")
        self.addWidget(self.tabs)

        self.setSizes([340, 160])


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Apply modern stylesheet
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    kinematic_manager = kinematicManager(window.ik_tab, window.fk_tab, window.velocity_tab)
    window.ik_tab.link_ik_changed_callback(kinematic_manager.ik_changed_callback)
    window.ik_tab.link_ik_released_callback(kinematic_manager.ik_released_callback)

    window.fk_tab.link_fk_changed_callback(kinematic_manager.fk_changed_callback)
    window.fk_tab.link_fk_released_callback(kinematic_manager.fk_released_callback)

    kinematic_manager.connect_status_changed_callback(window.robot_viewport.status_changed_callback)

    sys.exit(app.exec())