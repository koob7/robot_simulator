
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
        self.LINEAR_VELOCITY = 60.0     # mm/s (target constant linear velocity)
        self.LINERAR_SPEED_UP_VELOCITY = 25.0     # mm/s^2 (velocity during acceleration phase)
        self.FRAME_TIME = 0.016         # 16ms per frame (~60 FPS)
        self.SINGLE_STEP_DISTANCE = 0.1  # mm (for simple linear interpolation)

        self.max_motors_angle_speed = [self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED]

        self.wrapper = Wrapper()

        self.wrapper.moveRobot(self.ROBOT_FK, 300, 0, 0)
        self.wrapper.moveRobot(self.ROBOT_IK, 0, 0, 0)
        self.wrapper.moveRobot(self.ROBOT_EDGES, 0, 0, 0)


        self.path = []
        self.path_steps = 0
        self.simulation_timer = QtCore.QTimer()
        self.simulation_timer.timeout.connect(self.animate_movement)

    def ik_changed_callback(self, _value=None):
        user_position = self.ik_tab.get_values()
        logger.debug(f"User input IK: {user_position}")

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

        self.wrapper.rotateRobot(self.ROBOT_FK, *user_angles)

        #check calculated fk result with ik
        fk_result = calculate_fk(*user_angles)
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
            self.velocity_changed_callback(0)
            return

        if self.path_steps == 0:
            self.simulation_timer.stop()
            self.velocity_changed_callback(0)
            return
        
        step_time, angles, velocity = self.path.pop(0)
        self.wrapper.rotateRobot(self.ROBOT_IK, *angles)
        self.simulation_timer.setInterval(int(step_time * 1000))
        self.velocity_changed_callback(velocity)
        self.path_steps -= 1


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

    def connect_velocity_changed_callback(self, callback):
        self.velocity_changed_callback = callback
        callback(0)


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
        previous_angles = current_angles

        speed_up_distance = self.LINEAR_VELOCITY**2/(2*self.LINERAR_SPEED_UP_VELOCITY) #distance needed to reach target velocity with defined acceleration
        speed_up_steps = math.ceil(speed_up_distance/self.SINGLE_STEP_DISTANCE) #number of steps needed to reach target velocity with defined acceleration

        if (speed_up_steps>step_number):
            speed_up_steps = math.ceil(step_number/2)

        for step in range(1, step_number+1):

            if step<= speed_up_steps:
                logger.debug("Przyspieszanie")
                time = math.sqrt((2*step*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY) - math.sqrt((2*(step-1)*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY)

            elif step>= step_number - speed_up_steps:
                logger.debug("Hamowanie")
                remaining_steps = step_number - step + 1
                time = math.sqrt((2*remaining_steps*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY) - math.sqrt((2*(remaining_steps-1)*self.SINGLE_STEP_DISTANCE)/self.LINERAR_SPEED_UP_VELOCITY)

            elif step>speed_up_steps and step<(step_number - speed_up_steps):
                logger.debug("Stała prędkość")
                time  = self.SINGLE_STEP_DISTANCE/self.LINEAR_VELOCITY
               
            tmp =  calculate_ik(*self.interpolate_pose(current_pose, target_pose, step/step_number))
            tmp = self.unwrap_angles(tmp, previous_angles)    

            time*= self.valid_max_angular_speed(previous_angles, tmp, time)

            forward_path.append((time, tmp, self.SINGLE_STEP_DISTANCE/time))
            previous_angles = tmp
                

        self.path  = forward_path
        self.path_steps = step_number

        self.simulation_timer.start()
        self.animate_movement()


