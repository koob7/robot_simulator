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
                markers, frames = self.determine_pose_interface.find_markers(default_corrections=False)
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
        self.kinematic_manager = None

    def connect_to_kinematic_manager(self, kinematic_manager):
        self.kinematic_manager = kinematic_manager

    def update_axis_values(self):
        target_angles = self.robot_control.get_current_angles()#target - bo teoretycznie takie są (robot tak twierdzi)
        if target_angles[0] is None:
            target_pose = 6*[None]
        else:
            target_pose = calculate_fk(*target_angles) if target_angles is not None else 6*[None]
        for idx, (label_target, label_reached) in enumerate(
            zip(self.target_value_labels, self.reached_value_labels)
        ):
            pose_target = target_pose[idx]
            pose_reached = self.reached_value[idx]
            if pose_target is None:
                label_target.setText("-")
            else:
                label_target.setText(f"{pose_target:.3f}")
            
            if pose_reached is None:
                label_reached.setText("-")
            else:
                label_reached.setText(f"{pose_reached:.3f}")

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
        self.update_axis_values()
        
        self.toggle_connect_button(False)
        self.kinematic_manager.hide_camera_robot()
        return

    @QtCore.Slot(object)
    def update_reached_value(self, markers):
        if markers is None:
            return

        original_pose = vision_helper.get_marker_mutal_pose_XYZ(markers, pairs=[(54, 56)])
        original_reached_value = original_pose.get((54, 56))

        marker_56_pose = markers.get(56)
        if marker_56_pose is not None:
            tvec_56 = marker_56_pose["qr_tvec"].reshape(3)
            R_56 = marker_56_pose["qr_R"]
            rot_56 = Rot.from_matrix(R_56).as_euler('xyz')

            #przesunięcie w osi Z - niebieskiej
            tvec_56[0] -= 55/1000 * R_56[0, 2]
            tvec_56[1] -= 55/1000 * R_56[1, 2]
            tvec_56[2] -= 55/1000 * R_56[2, 2]

            #przesunięcie w osi Y - zielonej
            tvec_56[0] -= 25/1000 * R_56[0, 1]
            tvec_56[1] -= 25/1000 * R_56[1, 1]
            tvec_56[2] -= 25/1000 * R_56[2, 1]

            # przesunięcie w osi X - czerwonej
            tvec_56[0] -= 25/1000 * R_56[0, 0]
            tvec_56[1] -= 25/1000 * R_56[1, 0]
            tvec_56[2] -= 25/1000 * R_56[2, 0]
            self.tip_pose = (tvec_56[0], tvec_56[1], tvec_56[2], rot_56[0], rot_56[1], rot_56[2])
            markers[56]["qr_tvec"] = tvec_56
        
        pose = vision_helper.get_marker_mutal_pose_XYZ(markers, pairs=[(54, 56)])
        reached_value = pose.get((54, 56))
        if reached_value is None:
            return

        text = f"rehed poose t:original x {original_reached_value[0]:.2f} y {original_reached_value[1]:.2f} z {original_reached_value[2]:.2f} |reached pose t: x {reached_value[0]:.2f} y {reached_value[1]:.2f} z {reached_value[2]:.2f}"
        print(text)

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
        # przypadek markerów 54, 56 jest najprostszy bo zakłada że magnes jest naklejony na czubku robota (zgodnie z osią obrotu osi 6)

    # phi = phi_in*np.pi/180
    # beta = beta_in*np.pi/180
    # psi = psi_in*np.pi/180

    # c_alfa, s_alfa = np.cos(phi), np.sin(phi)
    # c_beta, s_beta = np.cos(beta), np.sin(beta)
    # c_delta, s_delta = np.cos(psi), np.sin(psi)

    # em = np.eye(3)
    # P = np.array([
    #     [0, 0, 1],
    #     [1, 0, 0],
    #     [0, 1, 0],
    # ])


    # #XYZ
    # em[0, 2] = s_beta
    # em[1, 2] = -s_alfa * c_beta

    # em[2, 2] = c_alfa * c_beta

    # # wyrównanie układów współrzędnych względem siebie
    # em = em @ P

    # # Pozycja nadgarstka
    # Wx = x - D6 * em[0, 2]
    # Wy = y - D6 * em[1, 2]
    # Wz = z - D6 * em[2, 2]



        self.reached_value[0] = y
        self.reached_value[1] = x
        self.reached_value[2] = z
        self.reached_value[3] = yaw
        self.reached_value[4] = roll
        self.reached_value[5] = pich

        # self.reached_value[3] = 1.0  # Set the fourth axis value to 0.0
        # self.reached_value[4] = 1.0  # Set the fifth axis
        # self.reached_value[5] = 1.0  # Set the sixth axis value to 0.0
        self.update_axis_values()

        degrees = calculate_ik(*self.reached_value)
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


        frames[0] = self.draw_point(#rysowanie kropki ma sens tylko dla kamery pierwszej - bo ona nadaje układ współrzędnych
            frames[0],
            self.tip_pose[0],
            self.tip_pose[1],
            self.tip_pose[2],
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
