import sys
import time
import math
from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper


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


class RobotViewport(QtWidgets.QWidget):


    def __init__(self):
        super().__init__()
        self.setMinimumHeight(300)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.wrapper = Wrapper()
        self._initialized = False

        self.render_timer = QtCore.QTimer(self)
        self.render_timer.setInterval(16)
        self.render_timer.timeout.connect(self.render_frame)

        self.actual_x = 5.0
        self.actual_y = 0.0
        self.actual_z = 0.0

        self.yaw = 0.0
        self.pitch = 0.0

        self.speed = 50.0
        self.previous_time = time.monotonic()
        self.mouse_sensitivity = 0.003
        self.max_pitch = 1.45

        self.is_rotating = False
        self.last_mouse_pos = None

        self.keys_pressed = set()

        self.homeButton = QtWidgets.QPushButton("🏠", self)
        self.homeButton.setFont(QtGui.QFont("Segoe UI Emoji", 14))
        self.homeButton.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
        self.homeButton.setFixedSize(32, 32)
        self.homeButton.move(10, 10)
        self.homeButton.raise_()
        self.homeButton.clicked.connect(self.resetView)


        self.resetView()


    def resetView(self):
        self.actual_x = 0
        self.actual_y = 20
        self.actual_z = -80
        self.yaw = 0.00
        self.pitch = 0.08
        self.updateCamera()


    def keyPressEvent(self, event):
        self.keys_pressed.add(event.key())
        self.setFocus()

    def keyReleaseEvent(self, event):
        self.keys_pressed.discard(event.key())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.is_rotating = True
            self.last_mouse_pos = event.position()
            self.setFocus()
            self.setCursor(QtCore.Qt.CursorShape.BlankCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.is_rotating = False
            self.last_mouse_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_rotating and self.last_mouse_pos is not None:
            current_pos = event.position()
            delta = current_pos - self.last_mouse_pos
            self.last_mouse_pos = current_pos

            self.yaw += delta.x() * self.mouse_sensitivity
            self.pitch -= delta.y() * self.mouse_sensitivity
            self.pitch = max(-self.max_pitch, min(self.max_pitch, self.pitch))
            self.updateCamera()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if self._initialized:
            return

        self.wrapper.Initialize(int(self.winId()))
        self.wrapper.InitializeScene()
        self.wrapper.SetCamera(self.actual_x, self.actual_y, self.actual_z, self.yaw, self.pitch)
        self.wrapper.CalcProjectionMatrix(max(1, self.width()), max(1, self.height()))

        self._initialized = True
        self.setFocus()
        self.render_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.homeButton.move(10, 10)
        self.homeButton.raise_()
        if self._initialized:
            self.wrapper.CalcProjectionMatrix(max(1, event.size().width()), max(1, event.size().height()))

    def updateCamera(self):
        if self._initialized:
            self.wrapper.SetCamera(-self.actual_x, self.actual_y, self.actual_z, -self.yaw, -self.pitch)

    def render_frame(self):
        if self._initialized:
            now = time.monotonic()
            dt = now - self.previous_time
            self.previous_time = now
            dt = min(dt, 0.05)

            move = self.speed * dt
            forward_x = math.sin(self.yaw)
            forward_z = math.cos(self.yaw)
            right_x = math.cos(self.yaw)
            right_z = -math.sin(self.yaw)

            if QtCore.Qt.Key.Key_W in self.keys_pressed:
                self.actual_x += forward_x * move
                self.actual_z += forward_z * move

            if QtCore.Qt.Key.Key_S in self.keys_pressed:
                self.actual_x -= forward_x * move
                self.actual_z -= forward_z * move

            if QtCore.Qt.Key.Key_D in self.keys_pressed:
                self.actual_x += right_x * move
                self.actual_z += right_z * move

            if QtCore.Qt.Key.Key_A in self.keys_pressed:
                self.actual_x -= right_x * move
                self.actual_z -= right_z * move

            if QtCore.Qt.Key.Key_Q in self.keys_pressed:
                self.actual_y += move

            if QtCore.Qt.Key.Key_E in self.keys_pressed:
                self.actual_y -= move

            self.updateCamera()

            self.wrapper.Render()


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