
from kinematic_helper import *
from Wrapper import Wrapper
from PySide6 import QtCore

import logging
import math

from RobotViewport import MovementType

logger = logging.getLogger(__name__)


class kinematicManager:
    def __init__(self, ik_tab, fk_tab, velocity_tab, robot_viewport, robot_control):
        self.ik_tab = ik_tab
        self.fk_tab = fk_tab
        self.velocity_tab = velocity_tab
        self.robot_viewport = robot_viewport
        self.robot_control = robot_control 

        ik_tab.link_ik_changed_callback(self.ik_changed_callback)
        ik_tab.link_ik_released_callback(self.ik_released_callback)

        fk_tab.link_fk_changed_callback(self.fk_changed_callback)
        fk_tab.link_fk_released_callback(self.fk_released_callback)


        #we handle 3 robots with idx
        self.ROBOT_FK = 0 #solid color for forward kinematics simulation
        self.ROBOT_IK = 1 #solid color for inverse kinematics simulation
        self.ROBOT_EDGES = 2 #only edges for movement simulation

        # Stepper motor parameters
        self.LINEAR_VELOCITY = 60.0     # mm/s (target constant linear velocity)
        self.LINERAR_SPEED_UP_VELOCITY = 25.0     # mm/s^2 (velocity during acceleration phase)

        self.ANGLE_SPEED = MAX_ANGULAR_SPEED
        self.ANGLE_ACCELERATION = MAX_ANGULAR_ACCELERATION

        self.SINGLE_STEP_DISTANCE = 0.1  # mm (for simple linear interpolation)
        self.SINGLE_STEP_ANGLE = 0.2 # degrees (for simple linear interpolation in joint space)

        
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
        self.plan_motion(target_pose, movement=MovementType.LINEAR, speed=self.LINEAR_VELOCITY, acceleration=self.LINERAR_SPEED_UP_VELOCITY)

    def animate_movement(self):
        if not self.path:
            self.simulation_timer.stop()
            self.robot_viewport.status_changed_callback("Simulation completed")
            if hasattr(self, 'animation_end_callback') and self.animation_end_callback:
                self.animation_end_callback()
            return
        
        step_time, angles, velocity = self.path.pop(0)
        self.wrapper.rotateRobot(self.ROBOT_IK, *angles)
        self.simulation_timer.setInterval(int(step_time * 1000))
        self.robot_viewport.status_changed_callback("velocity: {:.1f} mm/s".format(velocity))

        self.velocity_tab.update_progress_marker(self.current_step_index)
        self.current_step_index += 1

    def abort_motion(self):
        self.simulation_timer.stop()
        self.path = []
        self.robot_viewport.status_changed_callback("Motion aborted")

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

        self.plan_motion(target_angles, speed=self.ANGLE_SPEED, acceleration=self.ANGLE_ACCELERATION, movement=MovementType.PTP)

    def plan_motion(self, target_pose, movement: MovementType = None, speed = None, acceleration = None,  set_EDGE_ROBOT = False, callback=None):
        if valid_pose(*target_pose) not in self.acceptable_simulated_errors:
                logger.debug("Invalid target pose, skipping IK calculation")
                return

        if set_EDGE_ROBOT:

            if movement == MovementType.LINEAR:
                ik_result = calculate_ik(*target_pose)
            
            elif movement == MovementType.PTP:
                ik_result = target_pose

            self.wrapper.rotateRobot(self.ROBOT_EDGES, *ik_result)
            self.ik_tab.set_values(int(target_pose[0]), int(target_pose[1]), int(target_pose[2]), int(target_pose[3]), int(target_pose[4]), int(target_pose[5]))

            #check calculated ik result with fk
            fk_result = calculate_fk(*ik_result)
            eval_ik_result = calculate_ik(*fk_result)

            self.wrapper.rotateRobot(self.ROBOT_FK, *eval_ik_result)
            self.fk_tab.set_values(int(eval_ik_result[0]), int(eval_ik_result[1]), int(eval_ik_result[2]), int(eval_ik_result[3]), int(eval_ik_result[4]), int(eval_ik_result[5]))




        if movement is None:
            movement = self.robot_viewport.get_current_movement_type()

        if speed is None or acceleration is None:
            if movement == MovementType.LINEAR:
                speed = self.LINEAR_VELOCITY
                acceleration = self.LINERAR_SPEED_UP_VELOCITY
            elif movement == MovementType.PTP:
                speed = self.ANGLE_SPEED
                acceleration = self.ANGLE_ACCELERATION
        if movement == MovementType.LINEAR:
            self.plan_linear_motion(target_pose, speed, acceleration)
        elif movement == MovementType.PTP:
            self.plan_ptp_motion(target_pose, speed, acceleration)

        self.animation_end_callback = callback


    def plan_linear_motion (self, target_pose, speed , acceleration):
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
            self.simulation_timer.start()
            self.animate_movement() 
            return
        
        step_number = math.ceil(linear_distance / self.SINGLE_STEP_DISTANCE)

        forward_path = []
        velocity_profile = []
        previous_angles = current_angles
        previous_pose = current_pose
        previous_joints_speed = [0.0] * 6

        speed_up_distance = speed**2/(2*acceleration) #distance needed to reach target velocity with defined acceleration
        speed_up_steps = math.ceil(speed_up_distance/self.SINGLE_STEP_DISTANCE) #number of steps needed to reach target velocity with defined acceleration

        if (speed_up_steps>step_number/2):
            speed_up_steps = math.ceil(step_number/2)

        for step in range(1, step_number+1):

            interpolated_pose = interpolate_pose(current_pose, target_pose, step/step_number)
            interpolated_distance = math.sqrt(sum((interpolated_pose[i] - previous_pose[i]) ** 2 for i in range(3)))

            if step<= speed_up_steps:
                logger.debug("acceleration phase")
                time = math.sqrt((2*step*self.SINGLE_STEP_DISTANCE)/acceleration) - math.sqrt((2*(step-1)*self.SINGLE_STEP_DISTANCE)/acceleration)

            elif step>= step_number - speed_up_steps:
                logger.debug("deceleration phase")
                remaining_steps = step_number - step + 1
                time = math.sqrt((2*remaining_steps*self.SINGLE_STEP_DISTANCE)/acceleration) - math.sqrt((2*(remaining_steps-1)*self.SINGLE_STEP_DISTANCE)/acceleration)

            elif step>speed_up_steps and step<(step_number - speed_up_steps):
                logger.debug("constant phase")
                time  = interpolated_distance/speed
            
    
            error_code = valid_pose(*interpolated_pose) 
            if error_code != ValidErrorCode.VALID:
                logger.debug(f"Invalid pose at step {step}, skipping movement")
                self.robot_viewport.status_changed_callback(error_code.text())
                self.simulation_timer.stop()
                self.path = []
                return

            tmp =  calculate_ik(*interpolated_pose)
            tmp = unwrap_angles(tmp, previous_angles)    

            angular_speed_limit = valid_max_angular_speed(previous_angles, tmp, time)
            time*= angular_speed_limit

            angular_speeds = [
                abs(tmp[i] - previous_angles[i]) / time
                for i in range(6)
            ]

            previous_joints_speed = angular_speeds      

            angular_acceleration_limit = valid_max_angular_accelaration(previous_joints_speed, angular_speeds, time)
            time *= angular_acceleration_limit

            angular_speeds = [
                abs(tmp[i] - previous_angles[i]) / time
                for i in range(6)
            ]

            tcp_speed = interpolated_distance/time

            forward_path.append((time, tmp, tcp_speed))
            velocity_profile.append(tuple( [tcp_speed] + angular_speeds))
            previous_angles = tmp
            previous_pose = interpolated_pose       
            previous_joints_speed = angular_speeds         

        self.path  = forward_path
        self.path_steps = step_number
        self.current_step_index = 0

        self.velocity_tab.draw_velocity_profiles(velocity_profile)
        self.velocity_tab.update_progress_marker(0)

        self.simulation_timer.start()
        self.animate_movement()

    def plan_ptp_motion(self, target_pose, speed, acceleration):
       
        #for here we get target pose as anglesz

        current_angles = (
            self.wrapper.actual_angle_0[self.ROBOT_IK],
            self.wrapper.actual_angle_1[self.ROBOT_IK],
            self.wrapper.actual_angle_2[self.ROBOT_IK],
            self.wrapper.actual_angle_3[self.ROBOT_IK],
            self.wrapper.actual_angle_4[self.ROBOT_IK],
            self.wrapper.actual_angle_5[self.ROBOT_IK],
        )

        target_pose = unwrap_angles(target_pose, current_angles)

        diff_angles = [target_pose[i] - current_angles[i] for i in range(6)]

        max_angle_diff = max(abs(diff) for diff in diff_angles)

        step_number = math.ceil(max_angle_diff / self.SINGLE_STEP_ANGLE)


        speed_up_angle = speed**2/(2*acceleration) #angle difference needed to reach target velocity with defined acceleration
        speed_up_steps = math.ceil(speed_up_angle/self.SINGLE_STEP_ANGLE) #number of steps needed to reach target velocity with defined acceleration


        forward_path = []
        velocity_profile = []
        previous_angles = current_angles
        previous_pose = calculate_fk(*current_angles)

        if (speed_up_steps>step_number/2):
            speed_up_steps = math.ceil(step_number/2)

        for step in range(1, step_number+1):

            interpolated_angle = interpolate_pose(current_angles, target_pose, step/step_number)
            interpolated_pose = calculate_fk(*interpolated_angle)
            interpolated_distance = math.sqrt(sum((interpolated_pose[i] - previous_pose[i]) ** 2 for i in range(3)))

            error_code = valid_pose(*interpolated_pose)
            if error_code != ValidErrorCode.VALID:
                logger.info(f"Invalid pose at step {step}, skipping movement")
                self.simulation_timer.stop()
                self.path = []
                return

            if step<= speed_up_steps:
                logger.debug("acceleration phase")
                time = math.sqrt((2*step*self.SINGLE_STEP_ANGLE)/acceleration) - math.sqrt((2*(step-1)*self.SINGLE_STEP_ANGLE)/acceleration)

            elif step>= step_number - speed_up_steps:
                logger.debug("deceleration phase")
                remaining_steps = step_number - step + 1
                time = math.sqrt((2*remaining_steps*self.SINGLE_STEP_ANGLE)/acceleration) - math.sqrt((2*(remaining_steps-1)*self.SINGLE_STEP_ANGLE)/acceleration)

            elif step>speed_up_steps and step<(step_number - speed_up_steps):
                logger.debug("constant phase")
                time  = self.SINGLE_STEP_ANGLE/speed

            tcp_speed = interpolated_distance/time
            angular_speeds = [
                abs(interpolated_angle[i] - previous_angles[i]) / time
                for i in range(6)
            ]

            forward_path.append((time, interpolated_angle, tcp_speed))
            velocity_profile.append(tuple( [tcp_speed] + angular_speeds))

            previous_pose = interpolated_pose
            previous_angles = interpolated_angle

        self.path  = forward_path
        self.path_steps = step_number
        self.current_step_index = 0

        self.velocity_tab.draw_velocity_profiles(velocity_profile)
        self.velocity_tab.update_progress_marker(0)

        self.simulation_timer.start()
        self.animate_movement()

