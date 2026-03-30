from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QComboBox
import time
import math

from Wrapper import Wrapper

import enum


class MovementType(enum.Enum):
    LINEAR = 0
    PTP = 1


class RobotViewport(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.wrapper = Wrapper()
        self._initialized = False

        self.render_timer = QtCore.QTimer(self)
        self.render_timer.setInterval(16)
        self.render_timer.timeout.connect(self.render_frame)

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


        self.movement_type_combo = QComboBox(self)
        self.movement_type_combo.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
        self.movement_type_combo.addItem("Linear", MovementType.LINEAR)
        self.movement_type_combo.addItem("PTP", MovementType.PTP)
        self.position_movement_type_combo()
        self.movement_type_combo.raise_()

        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
        self.status_label.setStyleSheet(
            "QLabel {"
            "color: white;"
            "background-color: rgba(0, 0, 0, 140);"
            "padding: 4px 8px;"
            "border-radius: 4px;"
            "}"
        )

        self.status_changed_callback("Welcome")
        self.status_label.raise_()


        self.resetView()

    def get_current_movement_type(self):
        return self.movement_type_combo.currentData()

    def resetView(self):
        self.actual_x = 44
        self.actual_y = 33
        self.actual_z = 75
        self.yaw = - 144 * math.pi / 180
        self.pitch = -8 * math.pi / 180
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
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.keys_pressed.add(QtCore.Qt.MouseButton.MiddleButton)
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
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.keys_pressed.discard(QtCore.Qt.MouseButton.MiddleButton)
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

            if QtCore.Qt.MouseButton.MiddleButton in self.keys_pressed:
                move_speed = self.mouse_sensitivity * 15

                right_x = math.cos(self.yaw)
                right_z = -math.sin(self.yaw)

                self.actual_x -= right_x * delta.x() * move_speed
                self.actual_z -= right_z * delta.x() * move_speed
                self.actual_y += delta.y() * move_speed
            else:
                self.yaw += delta.x() * self.mouse_sensitivity
                self.pitch -= delta.y() * self.mouse_sensitivity
                self.pitch = max(-self.max_pitch, min(self.max_pitch, self.pitch))
            self.updateCamera()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom_speed = self.mouse_sensitivity * 20
        forward_x = math.sin(self.yaw)
        forward_z = math.cos(self.yaw)
        forward_y = math.sin(self.pitch)

        self.actual_x += forward_x * delta * zoom_speed
        self.actual_z += forward_z * delta * zoom_speed
        self.actual_y += forward_y * delta * zoom_speed
        self.updateCamera()
        event.accept()

        

    def showEvent(self, event):
        super().showEvent(event)
        if self._initialized:
            return

        self.wrapper.Initialize(int(self.winId()))
        self.wrapper.InitializeScene()
        self.wrapper.SetCamera(self.actual_x, self.actual_y, self.actual_z, self.yaw, self.pitch)


        self._initialized = True
        self.setFocus()
        self.render_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.homeButton.move(10, 10)
        self.homeButton.raise_()
        self.position_status_label()
        self.status_label.raise_()
        self.position_movement_type_combo()
        self.movement_type_combo.raise_()


    def position_status_label(self):
        self.status_label.adjustSize()
        x = max(10, self.width() - self.status_label.width() - 10)
        self.status_label.move(x, 10)

    def position_movement_type_combo(self):
        self.movement_type_combo.adjustSize()
        x = max(10, self.width() - self.movement_type_combo.width() - 10)
        self.movement_type_combo.move(x, 50)

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

    def status_changed_callback(self, value):
        self.status_label.setText(value)
        self.position_status_label()