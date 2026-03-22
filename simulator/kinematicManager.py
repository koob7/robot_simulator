
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

        # Stepper motor parameters
        self.MAX_ANGULAR_SPEED = 60.0  # degrees per second (max speed for any joint)
        self.LINEAR_VELOCITY = 50.0     # mm/s (target constant linear velocity)
        self.FRAME_TIME = 0.016         # 16ms per frame (~60 FPS)
        self.RAMP_TIME = 2          # acceleration/deceleration time in seconds

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
        #logger.debug(f"User input IK: {user_position}")

        ik_result = calculate_ik(*user_position)
        self.wrapper.rotateRobot(self.ROBOT_EDGES, *ik_result)

        #check calculated ik result with fk
        fk_result = calculate_fk(*ik_result)
        eval_ik_result = calculate_ik(*fk_result)

        self.wrapper.rotateRobot(self.ROBOT_FK, *eval_ik_result)
        self.fk_tab.set_values(int(eval_ik_result[0]), int(eval_ik_result[1]), int(eval_ik_result[2]), int(eval_ik_result[3]), int(eval_ik_result[4]), int(eval_ik_result[5]))

    def fk_changed_callback(self, _value=None):
        user_angles = self.fk_tab.get_values()
        #logger.debug(f"User input FK: {user_angles}")

        self.wrapper.rotateRobot(self.ROBOT_FK, *user_angles)

        #check calculated fk result with ik
        fk_result = calculate_fk(*user_angles)
        ik_result =  calculate_ik(*fk_result)

        self.wrapper.rotateRobot(self.ROBOT_EDGES, *ik_result)
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

    def _get_velocity_profile(self, num_frames):
        """
        Generate normalized velocity profile with smooth S-curve ramps.
        Returns list of weights (sum = 1.0).
        """

        ramp_frames = int(self.RAMP_TIME / self.FRAME_TIME)
        ramp_frames = max(2, min(ramp_frames, num_frames // 2))

        profile = []

        def smoothstep(x):
            # S-curve: 3x^2 - 2x^3 (lepsze niż kwadrat)
            return x * x * (3 - 2 * x)

        for i in range(num_frames):
            if i < ramp_frames:
                # acceleration
                t = i / (ramp_frames - 1)
                v = smoothstep(t)

            elif i >= num_frames - ramp_frames:
                # deceleration
                t = (i - (num_frames - ramp_frames)) / (ramp_frames - 1)
                v = smoothstep(1 - t)

            else:
                # constant velocity
                v = 1.0

            profile.append(v)

        # 🔑 NORMALIZACJA (kluczowa!)
        total = sum(profile)
        profile = [v / total for v in profile]

        return profile

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
        """
        Linear Cartesian motion with smooth velocity ramping (S-curve)
        and joint speed constraints.
        """

        current_angles = (
            self.wrapper.actual_angle_0[self.ROBOT_IK],
            self.wrapper.actual_angle_1[self.ROBOT_IK],
            self.wrapper.actual_angle_2[self.ROBOT_IK],
            self.wrapper.actual_angle_3[self.ROBOT_IK],
            self.wrapper.actual_angle_4[self.ROBOT_IK],
            self.wrapper.actual_angle_5[self.ROBOT_IK],
        )

        current_pose = calculate_fk(*current_angles)

        # Distance in Cartesian space
        linear_distance = math.sqrt(
            sum((target_pose[i] - current_pose[i]) ** 2 for i in range(3))
        )

        if linear_distance < 0.1:
            logger.debug(f"Very small movement ({linear_distance:.2f}mm)")
            self._edges_path = [calculate_ik(*target_pose)]
            self._edges_path_idx = 0
            if self._edges_anim_timer.isActive():
                self._edges_anim_timer.stop()
            self._edges_anim_timer.start()
            return

        motion_time = linear_distance / self.LINEAR_VELOCITY
        num_frames = max(10, int(motion_time / self.FRAME_TIME))

        # 🔑 velocity profile (normalized)
        velocity_profile = self._get_velocity_profile(num_frames)

        # 🔑 cumulative t (0 → 1)
        t_values = []
        cumulative = 0.0
        for v in velocity_profile:
            cumulative += v
            t_values.append(cumulative)

        path = []
        previous_angles = current_angles

        for frame in range(num_frames):
            t = t_values[frame]

            # Cartesian interpolation
            interpolated_pose = [
                current_pose[i] + (target_pose[i] - current_pose[i]) * t
                for i in range(6)
            ]

            ik_step = list(calculate_ik(*interpolated_pose))

            # unwrap angles
            for i in range(6):
                while ik_step[i] - previous_angles[i] > 180.0:
                    ik_step[i] -= 360.0
                while ik_step[i] - previous_angles[i] < -180.0:
                    ik_step[i] += 360.0

            max_delta = max(abs(ik_step[i] - previous_angles[i]) for i in range(6))

            max_step = self.MAX_ANGULAR_SPEED * self.FRAME_TIME
            substeps = max(1, math.ceil(max_delta / max_step))

            for substep in range(1, substeps + 1):
                ratio = substep / substeps
                step = tuple(
                    previous_angles[i] + (ik_step[i] - previous_angles[i]) * ratio
                    for i in range(6)
                )
                path.append(step)

            previous_angles = tuple(ik_step)

        self._edges_path = path
        self._edges_path_idx = 0

        logger.debug(
            f"Motion planned: {len(path)} steps, "
            f"time={motion_time:.2f}s, ramp={self.RAMP_TIME:.2f}s"
        )

        if self._edges_path:
            if self._edges_anim_timer.isActive():
                self._edges_anim_timer.stop()
            self._edges_anim_timer.start()