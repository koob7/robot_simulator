import cv2
import numpy as np
from PySide6 import QtCore, QtWidgets
import os
import robot_vision.config as config
import robot_vision.vision_helper as vision_helper
import robot_control
from Wrapper import Wrapper
from kinematicManager import *
from scipy.spatial.transform import Rotation as Rot

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
                # markers, frames = self.determine_pose_interface.get_mean(10, default_corrections=False)
                markers, frames = self.determine_pose_interface.find_markers(default_corrections=True)
                if markers is not None:
                    self.result_ready.emit(markers)
                self.frame_ready.emit((self.determine_pose_interface, frames))
        except Exception as exception:
            self.error.emit(str(exception))
        finally:
            self.finished.emit()

    def stop(self):
        self.running = False

class ROBOT_VISION_TAB(QtWidgets.QWidget):
    def __init__(self, robot_control: robot_control, parent=None):
        super().__init__()
        self.wrapper = Wrapper()
        self.robot_control = robot_control
        self.tip_pose = None
        self.base_pose = None

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

        default_camera_list = (
            f"{result_path}/single/mx_brio_for_business_1920_1080px"
        )
        if default_camera_list in camera_lists:
            camera_lists.remove(default_camera_list)
            camera_lists.insert(0, default_camera_list)

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

        self.pose_table_headers = [
            "Axis",
            "Target",
            "Camera",
            "Difference",
        ]
        self.target_source = "unknown"
        self.pose_table_names = ["X", "Y", "Z", "Roll", "Pitch", "Yaw"]
        self.pose_table_units = ["mm", "mm", "mm", "deg", "deg", "deg"]
        self.camera_tip_angles = [None] * 6
        self.camera_direct_angles = [None] * 6

        self.pose_table = QtWidgets.QTableWidget(6, len(self.pose_table_headers))
        self.pose_table.setHorizontalHeaderLabels(self.pose_table_headers)
        self.pose_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pose_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.pose_table.verticalHeader().setVisible(False)
        self.pose_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.pose_table.setAlternatingRowColors(True)
        self.pose_table.setMinimumWidth(500)

        for idx, (name, unit) in enumerate(zip(self.pose_table_names, self.pose_table_units)):
            axis_item = QtWidgets.QTableWidgetItem(f"{name} [{unit}]")
            axis_item.setFlags(axis_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.pose_table.setItem(idx, 0, axis_item)
            for column in range(1, len(self.pose_table_headers)):
                value_item = QtWidgets.QTableWidgetItem("-")
                value_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.pose_table.setItem(idx, column, value_item)

        pose_group = QtWidgets.QGroupBox("Pose comparison")
        pose_layout = QtWidgets.QVBoxLayout(pose_group)
        pose_layout.addWidget(self.pose_table)
        self.main_layout.addWidget(pose_group)

        self.angle_table_headers = [
            "Axis",
            "Target",
            "Camera tip",
            "Camera direct",
            "Diff tip",
            "Diff direct",
        ]
        self.angle_table = QtWidgets.QTableWidget(6, len(self.angle_table_headers))
        self.angle_table.setHorizontalHeaderLabels(self.angle_table_headers)
        self.angle_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.angle_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.angle_table.verticalHeader().setVisible(False)
        self.angle_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.angle_table.setAlternatingRowColors(True)
        self.angle_table.setMinimumWidth(720)

        for idx in range(6):
            axis_item = QtWidgets.QTableWidgetItem(f"Axis {idx + 1}")
            axis_item.setFlags(axis_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.angle_table.setItem(idx, 0, axis_item)
            for column in range(1, len(self.angle_table_headers)):
                value_item = QtWidgets.QTableWidgetItem("-")
                value_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.angle_table.setItem(idx, column, value_item)

        angle_group = QtWidgets.QGroupBox("Axis angles [deg]")
        angle_layout = QtWidgets.QVBoxLayout(angle_group)
        angle_layout.addWidget(self.angle_table)
        self.main_layout.addWidget(angle_group)

        self.robot_control.status_updated.connect(self.update_axis_values)

        self.determine_pose_interface = None
        self.reached_value = 6*[None]
        self.vision_thread = None
        self.vision_worker = None
        self.camera_window_names = set()
        self.kinematic_manager = None

    def connect_to_kinematic_manager(self, kinematic_manager):
        self.kinematic_manager = kinematic_manager

    def update_axis_values(self):
        target_angles = self.robot_control.get_current_angles()
        if target_angles is not None and all(angle is not None for angle in target_angles):
            self.target_source = "device"
        elif self.kinematic_manager is not None:
            target_angles = (
                self.kinematic_manager.wrapper.actual_angle_0[self.kinematic_manager.ROBOT_IK],
                self.kinematic_manager.wrapper.actual_angle_1[self.kinematic_manager.ROBOT_IK],
                self.kinematic_manager.wrapper.actual_angle_2[self.kinematic_manager.ROBOT_IK],
                self.kinematic_manager.wrapper.actual_angle_3[self.kinematic_manager.ROBOT_IK],
                self.kinematic_manager.wrapper.actual_angle_4[self.kinematic_manager.ROBOT_IK],
                self.kinematic_manager.wrapper.actual_angle_5[self.kinematic_manager.ROBOT_IK],
            )
            self.target_source = "theoretical"
        else:
            target_pose = [None] * 6
            target_angles = [None] * 6
            self.target_source = "unknown"

        if target_angles is None or any(angle is None for angle in target_angles):
            target_pose = [None] * 6
        else:
            target_pose = calculate_fk(*target_angles)

        pose_target_header = f"Target ({self.target_source})"
        angle_target_header = f"Target ({self.target_source})"
        self.pose_table.setHorizontalHeaderLabels([
            "Axis",
            pose_target_header,
            "Camera",
            "Difference",
        ])
        self.angle_table.setHorizontalHeaderLabels([
            "Axis",
            angle_target_header,
            "Camera tip",
            "Camera direct",
            "Diff tip",
            "Diff direct",
        ])

        for idx in range(6):
            pose_reached = self.reached_value[idx]
            pose_target = target_pose[idx]

            camera_text = "-" if pose_reached is None else f"{pose_reached:.3f}"
            target_text = "-" if pose_target is None else f"{pose_target:.3f}"

            if pose_reached is None or pose_target is None:
                difference_text = "-"
            else:
                difference = pose_target - pose_reached
                difference_text = f"{difference:+.3f}"

            self.pose_table.item(idx, 1).setText(target_text)
            self.pose_table.item(idx, 2).setText(camera_text)
            self.pose_table.item(idx, 3).setText(difference_text)

            angle_target = target_angles[idx]
            tip_angle = self.camera_tip_angles[idx]
            direct_angle = self.camera_direct_angles[idx]

            target_text = "-" if angle_target is None else f"{angle_target:.3f}"
            tip_text = "-" if tip_angle is None else f"{tip_angle:.3f}"
            direct_text = "" if direct_angle is None else f"{direct_angle:.3f}"
            tip_difference = "-" if angle_target is None or tip_angle is None else f"{angle_target - tip_angle:+.3f}"
            direct_difference = "" if direct_angle is None else f"{angle_target - direct_angle:+.3f}"

            self.angle_table.item(idx, 1).setText(target_text)
            self.angle_table.item(idx, 2).setText(tip_text)
            self.angle_table.item(idx, 3).setText(direct_text)
            self.angle_table.item(idx, 4).setText(tip_difference)
            self.angle_table.item(idx, 5).setText(direct_difference)

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
        self.kinematic_manager.show_camera_robot()
        return
    
    def disconnect_from_camera(self):
        if self.vision_worker is not None:
            self.vision_worker.frame_ready.disconnect(self.update_frames)
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
        self.camera_tip_angles = [None] * 6
        self.camera_direct_angles = [None] * 6
        self.update_axis_values()
        
        self.toggle_connect_button(False)
        self.kinematic_manager.hide_camera_robot()
        return

    @QtCore.Slot(object)
    def update_reached_value(self, markers):
        if markers is None:
            return

        if 54 in markers:
            base_pose = markers[54]["qr_tvec"].reshape(3)
            base_R = markers[54]["qr_R"]
            base_pose -= 51/1000 * base_R[:, 2]
            base_pose -= 25/1000 * base_R[:, 1]
            base_pose -= 25/1000 * base_R[:, 0]

            self.base_pose = base_pose
            markers[54]["qr_tvec"] = base_pose

        if 54 in markers and 61 in markers:
            axis_1_2_mutual_pose = vision_helper.get_marker_mutal_pose_YZ(markers, pairs=[(54, 61)])
            

        marker_pose = vision_helper.get_best_marker(markers, (59, 62, 60, 58, 63))
        if marker_pose is None or 54 not in markers:
            return

        #Z - 2 - niebieska
        #Y - 1 - zielona
        #X - 0 - czerwona
        marker_id = marker_pose["qr_id"]
        tvec = marker_pose["qr_tvec"].reshape(3)
        marker_R = marker_pose["qr_R"]
        if marker_id == 59:
            offsets = ((-25, 2), (0, 1), (-25, 0))
        elif marker_id == 62:
            offsets = ((-50, 2), (25, 1), (-25, 0))
        elif marker_id == 60:
            offsets = ((-25, 2), (25, 1), ( 0, 0))
        elif marker_id == 58:
            offsets = ((-25, 2), (25, 1), ( -50, 0))
        elif marker_id == 63:
            offsets = ((-25, 2), (50, 1), ( -25, 0))
        else:
            return


        for distance_mm, axis in offsets:
            tvec += distance_mm / 1000 * marker_R[:, axis]

        rotation = Rot.from_matrix(marker_R).as_euler('xyz')
        self.tip_pose = (*tvec, *rotation)
        marker_pose["qr_tvec"] = tvec

        pose = vision_helper.get_marker_mutal_pose_XYZ(
            markers, pairs=[(54, marker_id)]
        )
        reached_value = pose.get((54, marker_id))

        if reached_value is None:
            return

        reached_value = list(reached_value)
        self.reached_value = reached_value
        x = self.reached_value[0] *1000
        z = self.reached_value[1] *1000
        y = self.reached_value[2] *1000
        roll = self.reached_value[3]
        pich = self.reached_value[4]
        yaw  = self.reached_value[5]

        # tutaj trzeba sprawdzić który marker docelowy wybraliśmy a następnie przesunąć jego środek do końcówki robota
        # rotacja powinna zdostosowana w zależności od tego w którym miejscu marker został zamontowany na kostce robota
        # przypadek markerów 54, 62 jest najprostszy bo zakłada że magnes jest naklejony na czubku robota (zgodnie z osią obrotu osi 6)

        self.reached_value[0] = y
        self.reached_value[1] = x
        self.reached_value[2] = z
        self.reached_value[3] = yaw
        self.reached_value[4] = roll
        self.reached_value[5] = pich

        try:
            degrees = calculate_ik(*self.reached_value)
            self.camera_tip_angles = list(degrees)
        except Exception:
            degrees = None
            self.camera_tip_angles = [None] * 6

        self.update_axis_values()

        if degrees is not None:
            self.kinematic_manager.rotate_camera_robot(*degrees)

    @QtCore.Slot(object)
    def update_frames(self, pose_and_frames):
        determine_pose_interface, frames = pose_and_frames
        if determine_pose_interface is not self.determine_pose_interface:
            return
        if frames is None:
            return

        if not isinstance(frames, (tuple, list)):
            frames = (frames,)
        frames = list(frames)

        camera_names = [determine_pose_interface.camera.get_name()]
        if hasattr(determine_pose_interface, "camera_right"):
            camera_names.append(determine_pose_interface.camera_right.get_name())


        if (self.tip_pose is not None):
            frames[0] = self.draw_point(#rysowanie kropki ma sens tylko dla kamery pierwszej - bo ona nadaje układ współrzędnych
                frames[0],
                self.tip_pose[0],
                self.tip_pose[1],
                self.tip_pose[2],
                determine_pose_interface.camera.get_camera_matrix(),
                determine_pose_interface.camera.get_dist_coeffs(),
                determine_pose_interface.camera.get_scale_factor()
            )

        if (self.base_pose is not None):
            frames[0] = self.draw_point(#rysowanie kropki ma sens tylko dla kamery pierwszej - bo ona nadaje układ współrzędnych
                frames[0],
                self.base_pose[0],
                self.base_pose[1],
                self.base_pose[2],
                determine_pose_interface.camera.get_camera_matrix(),
                determine_pose_interface.camera.get_dist_coeffs(),
                determine_pose_interface.camera.get_scale_factor()
            )

        self.camera_window_names.clear()
        for window_name, frame in zip(camera_names, frames):
            if frame is None:
                continue
            cv2.imshow(window_name, frame)
            self.camera_window_names.add(window_name)

        cv2.waitKey(1)

    @QtCore.Slot(str)
    def report_vision_error(self, message):
        print(message)
    
    def toggle_connect_button(self, connected: bool):
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)

    def draw_point(self, frame, x, y, z, camera_matrix, dist_coeffs, scale_factor):
        if z <= 0:
            return frame

        point_3d = np.array([[x, y, z]], dtype=np.float32)
        points_2d, _ = cv2.projectPoints(
            point_3d,
            np.zeros((3, 1), dtype=np.float32),
            np.zeros((3, 1), dtype=np.float32),
            camera_matrix,
            dist_coeffs
        )

        px, py = np.asarray(points_2d, dtype=np.float64).reshape(-1, 2)[0]
        px *= float(scale_factor)
        py *= float(scale_factor)
        if not np.isfinite(px) or not np.isfinite(py):
            return frame

        frame_height, frame_width = frame.shape[:2]
        center = (
            int(np.clip(round(px), 0, frame_width - 1)),
            int(np.clip(round(py), 0, frame_height - 1)),
        )
        cv2.circle(
            frame,
            center,
            5,
            (0, 0, 255),
            -1
        )
        return frame
