
from kinematic_helper import *
from Wrapper import Wrapper
from PySide6 import QtCore

import logging
import math

logger = logging.getLogger(__name__)


class kinematicManager:
    def __init__(self, ik_tab, fk_tab):
        self.ik_tab = ik_tab
        self.fk_tab = fk_tab
        
        #we handle 3 robots with idx
        self.ROBOT_FK = 0 #solid color for forward kinematics simulation
        self.ROBOT_IK = 1 #solid color for inverse kinematics simulation
        self.ROBOT_EDGES = 2 #only edges for movement simulation


        self.wrapper = Wrapper()

        self.wrapper.moveRobot(self.ROBOT_FK, 300, 0, 0)
        self.wrapper.moveRobot(self.ROBOT_IK, 0, 0, 0)
        self.wrapper.moveRobot(self.ROBOT_EDGES, 0, 0, 0)

        self._edges_path = []
        self._edges_path_idx = 0
        self._edges_anim_timer = QtCore.QTimer()
        self._edges_anim_timer.setInterval(16)
        self._edges_anim_timer.timeout.connect(self._animate_edges_step)

    def ik_changed_callback(self, _value=None):
        user_position = self.ik_tab.get_values()
        logger.debug(f"User input IK: {user_position}")

        ik_result = calculate_ik(user_position[0], user_position[1], user_position[2], user_position[3], user_position[4], user_position[5])
        self.wrapper.rotateRobot(self.ROBOT_EDGES, ik_result[0], ik_result[1], ik_result[2], ik_result[3], ik_result[4], ik_result[5])

        #check calculated ik result with fk
        fk_result = calculate_fk(ik_result[0], ik_result[1], ik_result[2], ik_result[3], ik_result[4], ik_result[5])
        eval_ik_result = calculate_ik( fk_result[0], fk_result[1], fk_result[2], fk_result[3], fk_result[4], fk_result[5])

        self.wrapper.rotateRobot(self.ROBOT_FK, eval_ik_result[0], eval_ik_result[1], eval_ik_result[2], eval_ik_result[3], eval_ik_result[4], eval_ik_result[5])
        self.fk_tab.set_values(int(eval_ik_result[0]), int(eval_ik_result[1]), int(eval_ik_result[2]), int(eval_ik_result[3]), int(eval_ik_result[4]), int(eval_ik_result[5]))

    def fk_changed_callback(self, _value=None):
        user_angles = self.fk_tab.get_values()
        logger.debug(f"User input FK: {user_angles}")

        self.wrapper.rotateRobot(self.ROBOT_FK, user_angles[0], user_angles[1], user_angles[2], user_angles[3], user_angles[4], user_angles[5])

        #check calculated fk result with ik
        fk_result = calculate_fk(user_angles[0], user_angles[1], user_angles[2], user_angles[3], user_angles[4], user_angles[5])
        ik_result =  calculate_ik(fk_result[0], fk_result[1], fk_result[2], fk_result[3], fk_result[4], fk_result[5])

        self.wrapper.rotateRobot(self.ROBOT_EDGES, ik_result[0], ik_result[1], ik_result[2], ik_result[3], ik_result[4], ik_result[5])
        self.ik_tab.set_values(int(fk_result[0]), int(fk_result[1]), int(fk_result[2]), int(fk_result[3]), int(fk_result[4]), int(fk_result[5]))

    def ik_released_callback(self, _value=None):
        target_pose = self.ik_tab.get_values()
        logger.debug(f"IK released target pose: {target_pose}")

        self._plan_linear_pose_motion(target_pose)

    def _animate_edges_step(self):
        if self._edges_path_idx >= len(self._edges_path):
            self._edges_anim_timer.stop()
            return

        ik_step = self._edges_path[self._edges_path_idx]
        self.wrapper.rotateRobot(self.ROBOT_IK, *ik_step)
        self._edges_path_idx += 1

    def fk_released_callback(self, _value=None):
        target_angles = self.fk_tab.get_values()
        target_pose = calculate_fk(
            target_angles[0],
            target_angles[1],
            target_angles[2],
            target_angles[3],
            target_angles[4],
            target_angles[5],
        )
        logger.debug(f"FK released target pose (from FK): {target_pose}")

        self._plan_linear_pose_motion(target_pose)


    def _plan_linear_pose_motion(self, target_pose):
        current_angles = (
            self.wrapper.actual_angle_0[self.ROBOT_IK],
            self.wrapper.actual_angle_1[self.ROBOT_IK],
            self.wrapper.actual_angle_2[self.ROBOT_IK],
            self.wrapper.actual_angle_3[self.ROBOT_IK],
            self.wrapper.actual_angle_4[self.ROBOT_IK],
            self.wrapper.actual_angle_5[self.ROBOT_IK],
        )
        current_pose = calculate_fk(*current_angles)

        linear_distance = math.sqrt(
            (target_pose[0] - current_pose[0]) ** 2
            + (target_pose[1] - current_pose[1]) ** 2
            + (target_pose[2] - current_pose[2]) ** 2
        )
        angular_distance = math.sqrt(
            (target_pose[3] - current_pose[3]) ** 2
            + (target_pose[4] - current_pose[4]) ** 2
            + (target_pose[5] - current_pose[5]) ** 2
        )

        steps_by_position = int(linear_distance / 2.0)
        steps_by_orientation = int(angular_distance / 1.0)
        steps = max(10, min(1200, max(steps_by_position, steps_by_orientation)))

        previous_angles = current_angles
        path = []
        for step in range(1, steps + 1):
            t = step / steps
            interpolated_pose = [
                current_pose[i] + (target_pose[i] - current_pose[i]) * t
                for i in range(6)
            ]

            ik_step = list(calculate_ik(*interpolated_pose))

            # Keep each axis close to the previous one to avoid 360-degree jumps.
            for i in range(6):
                while ik_step[i] - previous_angles[i] > 180.0:
                    ik_step[i] -= 360.0
                while ik_step[i] - previous_angles[i] < -180.0:
                    ik_step[i] += 360.0

            max_delta = max(abs(ik_step[i] - previous_angles[i]) for i in range(6))
            substeps = max(1, int(math.ceil(max_delta / 1.0)))

            for substep in range(1, substeps + 1):
                ratio = substep / substeps
                limited_step = tuple(
                    previous_angles[i] + (ik_step[i] - previous_angles[i]) * ratio
                    for i in range(6)
                )
                path.append(limited_step)

            previous_angles = tuple(ik_step)

        self._edges_path = path
        self._edges_path_idx = 0
        if self._edges_path:
            if self._edges_anim_timer.isActive():
                self._edges_anim_timer.stop()
            self._edges_anim_timer.start()