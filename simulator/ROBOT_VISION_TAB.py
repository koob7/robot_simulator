import cv2
from PySide6 import QtCore, QtWidgets
import os
import robot_vision.config as config
import robot_vision.vision_helper as vision_helper
import robot_control

import robot_vision.single_determine_pose as single_determine_pose
import robot_vision.stereo_determine_pose as stereo_determine_pose


class VisionWorker(QtCore.QObject):
    result_ready = QtCore.Signal(object)
    frame_ready = QtCore.Signal(object)
    error = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, determine_pose_interface):
        super().__init__()
        self.determine_pose_interface = determine_pose_interface
        self.running = True

    @QtCore.Slot()
    def run(self):
        try:
            while self.running and self.determine_pose_interface.is_ready():
                mean, frames = self.determine_pose_interface.get_mean(10)
                reached_value = self.determine_robot_qr_pose(mean)
                self.result_ready.emit(reached_value)
                self.frame_ready.emit((self.determine_pose_interface, frames))
        except Exception as exception:
            self.error.emit(str(exception))
        finally:
            self.finished.emit()

    def stop(self):
        self.running = False

    def determine_robot_qr_pose(self, qr_tab_of_matrix):
        return 6 * [0.0]


class ROBOT_VISION_TAB(QtWidgets.QWidget):
    def __init__(self, robot_control: robot_control, parent=None):
        super().__init__()

        self.robot_control = robot_control

        camera_lists = []
        result_path = f"simulator/robot_vision/{config.calib_results_path}"

        for name in os.listdir(f"{result_path}/single"):
            camera_lists.append(f"{result_path}/single/{name}")

        left_names = os.listdir(f"{result_path}/left")
        right_names = os.listdir(f"{result_path}/right")

        for name in os.listdir(f"{result_path}/stereo"):
            print(f"Processing stereo camera list: {name}")
            left_name, right_name = vision_helper.split_camera_name(name)

            if left_name is None or right_name is None:
                continue

            if left_name in left_names and right_name in right_names:
                camera_lists.append(f"{result_path}/stereo/{name}")


        for camera_list in camera_lists:
            print(f"Found camera list: {camera_list}")

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addStretch(1)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.main_layout.addWidget(QtWidgets.QLabel("Select Camera List:"))

        self.camera_list_combo = QtWidgets.QComboBox()
        self.camera_list_combo.addItems(camera_lists)
        self.camera_list_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.camera_list_combo.setMinimumContentsLength(20)
        self.main_layout.addWidget(self.camera_list_combo)

        self.connect_button = QtWidgets.QPushButton("Connect to Camera")
        self.connect_button.clicked.connect(self.connect_to_camera)
        self.main_layout.addWidget(self.connect_button)

        self.disconnect_button = QtWidgets.QPushButton("Disconnect from Camera")
        self.disconnect_button.clicked.connect(self.disconnect_from_camera)
        self.disconnect_button.setEnabled(False)
        self.main_layout.addWidget(self.disconnect_button)

        self.reached_value_labels = []
        self.target_value_labels = []

        axes_group = QtWidgets.QGroupBox("Axis rotations [deg]")
        axes_layout = QtWidgets.QGridLayout(axes_group)

        axes_layout.addWidget(QtWidgets.QLabel("Axis"), 0, 0)
        axes_layout.addWidget(QtWidgets.QLabel("Reached"), 0, 1)
        axes_layout.addWidget(QtWidgets.QLabel("Target"), 0, 2)

        for idx in range(1, 7):
            axis_name = QtWidgets.QLabel(f"Axis {idx}")
            reached_value = QtWidgets.QLabel("-")
            target_value = QtWidgets.QLabel("-")
            axes_layout.addWidget(axis_name, idx, 0)
            axes_layout.addWidget(reached_value, idx, 1)
            axes_layout.addWidget(target_value, idx, 2)
            self.reached_value_labels.append(reached_value)
            self.target_value_labels.append(target_value)

        self.main_layout.addWidget(axes_group)
        self.robot_control.status_updated.connect(self.update_axis_values)

        self.determine_pose_interface = None
        self.reached_value = 6*[None]
        self.vision_thread = None
        self.vision_worker = None
        self.camera_window_names = set()


    def update_axis_values(self):
        target_angles = self.robot_control.get_current_angles()#target - bo teoretycznie takie są (robot tak twierdzi)
        for idx, label_target, label_reached in enumerate(self.target_value_labels, self.reached_value_labels):
            angle_target = target_angles[idx]
            angle_reached = self.reached_value[idx]
            if angle_target is None:
                label_target.setText("-")
            else:
                label_target.setText(f"{angle_target:.3f}")
            
            if angle_reached is None:
                label_reached.setText("-")
            else:
                label_reached.setText(f"{angle_reached:.3f}")


    def determine_robot_qr_pose(self, qr_tab_of_matrix):

        return 6*[0.0]

    def connect_to_camera(self):

        selected_camera_list = self.camera_list_combo.currentText()

        if "stereo" in selected_camera_list:
            camera_name = os.path.basename(selected_camera_list)
            camera_left_name, camera_right_name = vision_helper.split_camera_name(camera_name)
            width_left, height_left = vision_helper.get_camera_info(camera_left_name)
            width_right, height_right = vision_helper.get_camera_info(camera_right_name)
            name_left = vision_helper.get_camera_name(camera_left_name)
            name_right = vision_helper.get_camera_name(camera_right_name)
            self.determine_pose_interface = stereo_determine_pose.stereo_determine_pose(
                name_left, name_right, width_left, height_left, width_right, height_right
            )

        elif "single" in selected_camera_list:
            camera_name = os.path.basename(selected_camera_list)
            width, height = vision_helper.get_camera_info(camera_name)
            name = vision_helper.get_camera_name(camera_name)
            self.determine_pose_interface = single_determine_pose.single_determine_pose(
                name, width, height
            )

        if not self.determine_pose_interface.is_ready():
            print("Nie można połączyć się z kamerą. Sprawdź połączenie i konfigurację.")
            return

        self.vision_thread = QtCore.QThread(self)
        self.vision_worker = VisionWorker(self.determine_pose_interface)
        self.vision_worker.moveToThread(self.vision_thread)
        self.vision_thread.started.connect(self.vision_worker.run)
        self.vision_worker.result_ready.connect(self.update_reached_value)
        self.vision_worker.frame_ready.connect(self.update_frames)
        self.vision_worker.error.connect(self.report_vision_error)
        self.vision_worker.finished.connect(self.vision_thread.quit)
        self.vision_worker.finished.connect(self.vision_worker.deleteLater)
        self.vision_thread.finished.connect(self.vision_thread.deleteLater)
        self.vision_thread.start()
        
        self.toggle_connect_button(True)
        return
    
    def disconnect_from_camera(self):
        if self.vision_worker is not None:
            self.vision_worker.stop()
        if self.vision_thread is not None:
            self.vision_thread.quit()
            self.vision_thread.wait()

        if self.determine_pose_interface is not None:
            self.determine_pose_interface.__del__()

        self.vision_worker = None
        self.vision_thread = None
        self.determine_pose_interface = None

        for window_name in self.camera_window_names:
            cv2.destroyWindow(window_name)
        self.camera_window_names.clear()

        self.reached_value = 6*[None]
        
        self.toggle_connect_button(False)
        return

    @QtCore.Slot(object)
    def update_reached_value(self, reached_value):
        self.reached_value = reached_value

    @QtCore.Slot(object)
    def update_frames(self, pose_and_frames):
        determine_pose_interface, frames = pose_and_frames
        if frames is None:
            return

        camera_names = [determine_pose_interface.camera.get_name()]
        if hasattr(determine_pose_interface, "camera_right"):
            camera_names.append(determine_pose_interface.camera_right.get_name())

        if not isinstance(frames, tuple):
            frames = (frames,)

        for window_name, frame in zip(camera_names, frames):
            if frame is None:
                continue
            scale = 680 / frame.shape[1]
            display_frame = cv2.resize(frame, None, fx=scale, fy=scale)
            cv2.imshow(window_name, display_frame)
            self.camera_window_names.add(window_name)

        cv2.waitKey(1)

    @QtCore.Slot(str)
    def report_vision_error(self, message):
        print(message)
    
    def toggle_connect_button(self, connected: bool):
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)


    
                
            


