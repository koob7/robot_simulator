
from kinematic_helper import *
from Wrapper import Wrapper
from PySide6 import QtCore

import math

import logging

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
        self.wrapper.moveRobot(self.ROBOT_EDGES, -300, 0, 0)#TODO temporary

        self.edge_motion_timer = QtCore.QTimer()
        self.edge_motion_timer.setInterval(16)
        self.edge_motion_timer.timeout.connect(self._edge_motion_step)
        self.edge_motion_path = []
        self.edge_motion_idx = 0

    def ik_changed_callback(self, _value=None):
        user_position = self.ik_tab.get_values()
        logger.debug(f"User input IK: {user_position}")

        ik_result = calculate_ik(user_position[0], user_position[1], user_position[2], user_position[3], user_position[4], user_position[5])
        self.wrapper.rotateRobot(self.ROBOT_IK, ik_result[0], ik_result[1], ik_result[2], ik_result[3], ik_result[4], ik_result[5])

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

        self.wrapper.rotateRobot(self.ROBOT_IK, ik_result[0], ik_result[1], ik_result[2], ik_result[3], ik_result[4], ik_result[5])
        self.ik_tab.set_values(int(fk_result[0]), int(fk_result[1]), int(fk_result[2]), int(fk_result[3]), int(fk_result[4]), int(fk_result[5]))

    def ik_released_callback(self, _value=None):
        target_pose = self.ik_tab.get_values()
        logger.debug(f"IK release target pose: {target_pose}")

        if self.edge_motion_timer.isActive():
            self.edge_motion_timer.stop()

        if len(self.wrapper.actual_angle_0) <= self.ROBOT_EDGES:
            current_angles = [0.0] * 6
        else:
            current_angles = [
                self.wrapper.actual_angle_0[self.ROBOT_EDGES],
                self.wrapper.actual_angle_1[self.ROBOT_EDGES],
                self.wrapper.actual_angle_2[self.ROBOT_EDGES],
                self.wrapper.actual_angle_3[self.ROBOT_EDGES],
                self.wrapper.actual_angle_4[self.ROBOT_EDGES],
                self.wrapper.actual_angle_5[self.ROBOT_EDGES],
            ]

        current_pose = calculate_fk(
            current_angles[0],
            current_angles[1],
            current_angles[2],
            current_angles[3],
            current_angles[4],
            current_angles[5],
        )

        dx = target_pose[0] - current_pose[0]
        dy = target_pose[1] - current_pose[1]
        dz = target_pose[2] - current_pose[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        droll = target_pose[3] - current_pose[3]
        dpitch = target_pose[4] - current_pose[4]
        dyaw = target_pose[5] - current_pose[5]
        orientation_distance = math.sqrt(droll * droll + dpitch * dpitch + dyaw * dyaw)

        steps = max(1, int(max(distance / 5.0, orientation_distance / 3.0)))

        path = []
        for step in range(1, steps + 1):
            t = step / steps
            interp_pose = [
                current_pose[0] + (target_pose[0] - current_pose[0]) * t,
                current_pose[1] + (target_pose[1] - current_pose[1]) * t,
                current_pose[2] + (target_pose[2] - current_pose[2]) * t,
                current_pose[3] + (target_pose[3] - current_pose[3]) * t,
                current_pose[4] + (target_pose[4] - current_pose[4]) * t,
                current_pose[5] + (target_pose[5] - current_pose[5]) * t,
            ]

            ik_step = calculate_ik(
                interp_pose[0],
                interp_pose[1],
                interp_pose[2],
                interp_pose[3],
                interp_pose[4],
                interp_pose[5],
            )
            path.append(ik_step)

        self.edge_motion_path = path
        self.edge_motion_idx = 0

        if self.edge_motion_path:
            self.edge_motion_timer.start()

    def _edge_motion_step(self):
        if self.edge_motion_idx >= len(self.edge_motion_path):
            self.edge_motion_timer.stop()
            return

        ik_step = self.edge_motion_path[self.edge_motion_idx]
        self.wrapper.rotateRobot(
            self.ROBOT_EDGES,
            ik_step[0],
            ik_step[1],
            ik_step[2],
            ik_step[3],
            ik_step[4],
            ik_step[5],
        )
        self.edge_motion_idx += 1

    def fk_released_callback(self, _value=None):
        pass