import sys
from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper
from RobotViewport import RobotViewport
from IK_TAB import IK_TAB
from FK_TAB import FK_TAB
from kinematicManager import kinematicManager

import logging

logging.basicConfig(
    level=logging.WARNING,  # INFO / DEBUG / WARNING / ERROR
    format="%(levelname)s: %(message)s"
)

class MainWindow(QtWidgets.QSplitter):
    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Vertical)
        self.setWindowTitle("Robot simulator")
        self.resize(700, 500)

        self.robot_viewport = RobotViewport()
        self.addWidget(self.robot_viewport)

        self.ik_tab = IK_TAB()
        self.fk_tab = FK_TAB()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.ik_tab, "IK control")
        self.tabs.addTab(self.fk_tab, "FK control")
        self.addWidget(self.tabs)

        self.setSizes([340, 160])


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Apply modern stylesheet
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    kinematic_manager = kinematicManager(window.ik_tab, window.fk_tab)
    window.ik_tab.link_ik_changed_callback(kinematic_manager.ik_changed_callback)
    window.ik_tab.link_ik_released_callback(kinematic_manager.ik_released_callback)

    window.fk_tab.link_fk_changed_callback(kinematic_manager.fk_changed_callback)
    window.fk_tab.link_fk_released_callback(kinematic_manager.fk_released_callback)

    sys.exit(app.exec())