import sys
from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper
from RobotViewport import RobotViewport
from IK_TAB import IK_TAB
from FK_TAB import FK_TAB

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

    sys.exit(app.exec())