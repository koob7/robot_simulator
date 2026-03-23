
from kinematic_helper import *
from Wrapper import Wrapper
from PySide6 import QtCore

import logging
import math

logger = logging.getLogger(__name__)


class kinematicManager:
    def __init__(self, ik_tab, fk_tab, velocity_tab):
        self.ik_tab = ik_tab
        self.fk_tab = fk_tab
        self.velocity_tab = velocity_tab
        
        #we handle 3 robots with idx
        self.ROBOT_FK = 0 #solid color for forward kinematics simulation
        self.ROBOT_IK = 1 #solid color for inverse kinematics simulation
        self.ROBOT_EDGES = 2 #only edges for movement simulation

        # Stepper motor parameters
        self.MAX_ANGULAR_SPEED = 60.0  # degrees per second (max speed for any joint)
        self.LINEAR_VELOCITY = 60.0     # mm/s (target constant linear velocity)
        self.LINERAR_SPEED_UP_VELOCITY = 25.0     # mm/s^2 (velocity during acceleration phase)
        self.FRAME_TIME = 0.016         # 16ms per frame (~60 FPS)
        self.SINGLE_STEP_DISTANCE = 0.1  # mm (for simple linear interpolation)

        self.max_motors_angle_speed = [self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED]

        self.wrapper = Wrapper()

        self.wrapper.moveRobot(self.ROBOT_FK, 300, 0, 0)
        self.wrapper.moveRobot(self.ROBOT_IK, 0, 0, 0)
        self.wrapper.moveRobot(self.ROBOT_EDGES, 0, 0, 0)

        default_pose = (D4+D6, 0, D1+A2, 0, 0, 0)
        default_angles = calculate_ik(*default_pose)
        
        self.ik_tab.set_values(int(default_pose[0]), int(default_pose[1]), int(default_pose[2]), int(default_pose[3]), int(default_pose[4]), int(default_pose[5]))
        self.fk_tab.set_values(int(default_angles[0]), int(default_angles[1]), int(default_angles[2]), int(default_angles[3]), int(default_angles[4]), int(default_angles[5]))

        self.wrapper.rotateRobot(self.ROBOT_FK, *default_angles)
        self.wrapper.rotateRobot(self.ROBOT_IK, *default_angles)
        self.wrapper.rotateRobot(self.ROBOT_EDGES, *default_angles)

        self.acceptable_simulated_errors = [ValidErrorCode.VALID, ValidErrorCode.WRONG_ANGLES, ValidErrorCode.TARGET_POSE_TOO_CLOSE, ValidErrorCode.WRIST_POSE_TOO_CLOSE]


        self.path = []
        self.path_steps = 0
        self.current_step_index = 0
        self.simulation_timer = QtCore.QTimer()
        self.simulation_timer.timeout.connect(self.animate_movement)

    def ik_changed_callback(self, _value=None):
        user_position = self.ik_tab.get_values()
        logger.debug(f"User input IK: {user_position}")

        if valid_pose(*user_position) not in self.acceptable_simulated_errors:
            logger.debug("Invalid target pose, skipping IK calculation")
            return

        ik_result = calculate_ik(*user_position)
        self.wrapper.rotateRobot(self.ROBOT_EDGES, *ik_result)

        #check calculated ik result with fk
        fk_result = calculate_fk(*ik_result)
        eval_ik_result = calculate_ik(*fk_result)

        self.wrapper.rotateRobot(self.ROBOT_FK, *eval_ik_result)
        self.fk_tab.set_values(int(eval_ik_result[0]), int(eval_ik_result[1]), int(eval_ik_result[2]), int(eval_ik_result[3]), int(eval_ik_result[4]), int(eval_ik_result[5]))

    def fk_changed_callback(self, _value=None):
        user_angles = self.fk_tab.get_values()
        logger.debug(f"User input FK: {user_angles}")

        fk_result = calculate_fk(*user_angles)
        if valid_pose(*fk_result) not in self.acceptable_simulated_errors:
            logger.debug("Invalid target pose from FK, skipping movement")
            return

        self.wrapper.rotateRobot(self.ROBOT_FK, *user_angles)

        #check calculated fk result with ik
        ik_result =  calculate_ik(*fk_result)

        self.wrapper.rotateRobot(self.ROBOT_EDGES, *ik_result)
        self.ik_tab.set_values(int(fk_result[0]), int(fk_result[1]), int(fk_result[2]), int(fk_result[3]), int(fk_result[4]), int(fk_result[5]))

    def ik_released_callback(self, _value=None):
        target_pose = self.ik_tab.get_values()
        logger.debug(f"IK released target pose: {target_pose}")

        #self._plan_linear_pose_motion(target_pose)
        self.motion_planner(target_pose)

    def animate_movement(self):
        if not self.path:
            self.simulation_timer.stop()
            self.status_changed_callback("Simulation completed")
            return
        
        step_time, angles, velocity = self.path.pop(0)
        self.wrapper.rotateRobot(self.ROBOT_IK, *angles)
        self.simulation_timer.setInterval(int(step_time * 1000))
        self.status_changed_callback("velocity: {:.1f} mm/s".format(velocity))

        self.velocity_tab.update_progress_marker(self.current_step_index)
        self.current_step_index += 1


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

        self.motion_planner(target_pose)

    def connect_status_changed_callback(self, callback):
        self.status_changed_callback = callback
        callback("Connected to simulator")

    def interpolate_pose(self, pose1, pose2, t):
        return tuple(
            pose1[i] + (pose2[i] - pose1[i]) * t
            for i in range(6)
        )
    
    def unwrap_angles(self, angles, reference):
        unwrapped = []
        for i in range(6):
            angle = angles[i]
            while angle - reference[i] > 180.0:
                angle -= 360.0
            while angle - reference[i] < -180.0:
                angle += 360.0
            unwrapped.append(angle)
        return tuple(unwrapped)
    
    def valid_max_angular_speed(self, angles1, angles2, time):
        max_overspeed = 1.0
        for i in range(6):
            angular_speed = abs(angles2[i] - angles1[i]) / time
            if angular_speed > self.max_motors_angle_speed[i]:
                if angular_speed > max_overspeed:
                    max_overspeed = angular_speed/self.max_motors_angle_speed[i]
        return max_overspeed


    def motion_planner (self, target_pose):
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
            logger.debug("very small movement, temporary skip")
            return
        
        step_number = math.ceil(linear_distance / self.SINGLE_STEP_DISTANCE)

        forward_path = []
        velocity_profile = []
        previous_angles = current_angles
        previous_pose = current_pose

        speed_up_distance = self.LINEAR_VELOCITY**2/(2*self.LINERAR_SPEED_UP_VELOCITY) #distance needed to reach target velocity with defined acceleration
        speed_up_steps = math.ceil(speed_up_distance/self.SINGLE_STEP_DISTANCE) #number of steps needed to reach target velocity with defined acceleration

        if (speed_up_steps>step_number):
            speed_up_steps = math.ceil(step_number/2)

        for step in range(1, step_number+1):

            interpolated_pose = self.interpolate_pose(current_pose, target_pose, step/step_number)
            interpolated_distance = math.sqrt(sum((interpolated_pose[i] - previous_pose[i]) ** 2 for i in range(3)))

            if step<= speed_up_steps:
                logger.debug("acceleration phase")
                time = math.sqrt((2*step*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY) - math.sqrt((2*(step-1)*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY)

            elif step>= step_number - speed_up_steps:
                logger.debug("deceleration phase")
                remaining_steps = step_number - step + 1
                time = math.sqrt((2*remaining_steps*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY) - math.sqrt((2*(remaining_steps-1)*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY)

            elif step>speed_up_steps and step<(step_number - speed_up_steps):
                logger.debug("constant phase")
                time  = interpolated_distance/self.LINEAR_VELOCITY
            
    
            error_code = valid_pose(*interpolated_pose) 
            if error_code != ValidErrorCode.VALID:
                logger.debug(f"Invalid pose at step {step}, skipping movement")
                self.status_changed_callback(error_code.text())
                self.simulation_timer.stop()
                self.path = []
                return

            tmp =  calculate_ik(*interpolated_pose)
            tmp = self.unwrap_angles(tmp, previous_angles)    

            time*= self.valid_max_angular_speed(previous_angles, tmp, time)

            angular_speeds = [
                abs(tmp[i] - previous_angles[i]) / time
                for i in range(6)
            ]
            tcp_speed = interpolated_distance/time

            forward_path.append((time, tmp, tcp_speed))
            velocity_profile.append(tuple( [tcp_speed] + angular_speeds))
            previous_angles = tmp
            previous_pose = interpolated_pose                

        self.path  = forward_path
        self.path_steps = step_number
        self.current_step_index = 0

        self.velocity_tab.draw_velocity_profiles(velocity_profile)
        self.velocity_tab.update_progress_marker(0)

        self.simulation_timer.start()
        self.animate_movement()


