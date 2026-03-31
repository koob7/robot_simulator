
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

        self.current_step_index = 0
        self.elapsed_time = 0.0
        
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
        if not self.path or self.current_step_index >= len(self.path[0]):
            self.simulation_timer.stop()
            self.robot_viewport.status_changed_callback("Simulation completed")
            if hasattr(self, 'animation_end_callback') and self.animation_end_callback:
                self.animation_end_callback()
            return
        
        angles = self.path[4][self.current_step_index]
        interval_ms = self.path[0][self.current_step_index] * 1000
        velocity = self.path[1][0][self.current_step_index]
        self.wrapper.rotateRobot(self.ROBOT_IK, *angles)
        self.simulation_timer.setInterval(int(interval_ms))
        self.robot_viewport.status_changed_callback("velocity: {:.1f} mm/s".format(velocity))

        self.elapsed_time += self.path[0][self.current_step_index]
        self.current_step_index += 1
        self.velocity_tab.update_progress(self.elapsed_time)

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

        self.path = []
        self.current_step_index = 0
        self.elapsed_time = 0.0

        if speed is None or acceleration is None:
            if movement == MovementType.LINEAR:
                speed = self.LINEAR_VELOCITY
                acceleration = self.LINERAR_SPEED_UP_VELOCITY
            elif movement == MovementType.PTP:
                speed = self.ANGLE_SPEED
                acceleration = self.ANGLE_ACCELERATION
        if movement == MovementType.LINEAR:
            self.path = self.plan_linear_motion(target_pose, speed, acceleration)
        elif movement == MovementType.PTP:
            self.path = self.plan_ptp_motion(target_pose, speed, acceleration)
        
        if self.path is None:
            logger.debug("Motion planning failed, skipping movement")
            return

        self.animation_end_callback = callback

        self.simulation_duration = sum(self.path[0]) #path[0] contains timestamps for each step

        max_tcp_acceleration = max(self.path[1][1])
        min_tcp_acceleration = min(self.path[1][1])

        tcp_divider = max(abs(max_tcp_acceleration), abs(min_tcp_acceleration))

        max_tcp_speed = max(self.path[1][0])

        for i in range(len(self.path[1][1])):
            self.path[1][1][i] = self.path[1][1][i] + tcp_divider

        for i in range(len(self.path[3])):
            for j in range(len(self.path[3][i])):
                self.path[3][i][j] = self.path[3][i][j] + MAX_ANGULAR_ACCELERATION

        velocity_profile = [self.path[0], self.path[1], self.path[2], self.path[3]]
        self.velocity_tab.update_velocity_profiles(velocity_profile, len(self.path[0]), max_tcp_speed, tcp_divider*2, MAX_ANGULAR_SPEED, MAX_ANGULAR_ACCELERATION*2, self.simulation_duration)

        self.simulation_timer.start()
        self.animate_movement()



    def plan_linear_motion (self, target_pose, speed , acceleration):
        return None
        # current_angles = (
        #     self.wrapper.actual_angle_0[self.ROBOT_IK],
        #     self.wrapper.actual_angle_1[self.ROBOT_IK],
        #     self.wrapper.actual_angle_2[self.ROBOT_IK],
        #     self.wrapper.actual_angle_3[self.ROBOT_IK],
        #     self.wrapper.actual_angle_4[self.ROBOT_IK],
        #     self.wrapper.actual_angle_5[self.ROBOT_IK],
        # )

        # current_pose = calculate_fk(*current_angles)

        # # Distance in Cartesian space
        # linear_distance = math.sqrt(
        #     sum((target_pose[i] - current_pose[i]) ** 2 for i in range(3))
        # )


        # if linear_distance < 0.1:
        #     logger.debug("very small movement, temporary skip")
        #     self.simulation_timer.start()
        #     self.animate_movement() 
        #     return
        
        # step_number = math.ceil(linear_distance / self.SINGLE_STEP_DISTANCE)

        # forward_path = []
        # velocity_profile = [[], [], [], [], [], [], [], [] ,[], [], [], [], [], []]

        # previous_angles = current_angles
        # previous_pose = current_pose
        # previous_joints_speed = [0.0] * 6
        # previous_tcp_speed = 0.0

        # speed_up_distance = speed**2/(2*acceleration) #distance needed to reach target velocity with defined acceleration
        # speed_up_steps = math.ceil(speed_up_distance/self.SINGLE_STEP_DISTANCE) #number of steps needed to reach target velocity with defined acceleration

        # if (speed_up_steps>step_number/2):
        #     speed_up_steps = math.ceil(step_number/2)

        # for step in range(1, step_number+1):

        #     interpolated_pose = interpolate_pose(current_pose, target_pose, step/step_number)
        #     interpolated_distance = math.sqrt(sum((interpolated_pose[i] - previous_pose[i]) ** 2 for i in range(3)))

        #     if step<= speed_up_steps:
        #         logger.debug("acceleration phase")
        #         time = math.sqrt((2*step*self.SINGLE_STEP_DISTANCE)/acceleration) - math.sqrt((2*(step-1)*self.SINGLE_STEP_DISTANCE)/acceleration)

        #     elif step>= step_number - speed_up_steps:
        #         logger.debug("deceleration phase")
        #         remaining_steps = step_number - step + 1
        #         time = math.sqrt((2*remaining_steps*self.SINGLE_STEP_DISTANCE)/acceleration) - math.sqrt((2*(remaining_steps-1)*self.SINGLE_STEP_DISTANCE)/acceleration)

        #     elif step>speed_up_steps and step<(step_number - speed_up_steps):
        #         logger.debug("constant phase")
        #         time  = interpolated_distance/speed
            
    
        #     error_code = valid_pose(*interpolated_pose) 
        #     if error_code != ValidErrorCode.VALID:
        #         logger.debug(f"Invalid pose at step {step}, skipping movement")
        #         self.robot_viewport.status_changed_callback(error_code.text())
        #         self.simulation_timer.stop()
        #         self.path = []
        #         return

        #     tmp =  calculate_ik(*interpolated_pose)
        #     tmp = unwrap_angles(tmp, previous_angles)    



        #     angular_speeds = [
        #         abs(tmp[i] - previous_angles[i]) / time
        #         for i in range(6)
        #     ]

        #     angular_speed_limit = valid_max_angular_speed(previous_angles, tmp, time)
        #     time*= angular_speed_limit

        #     angular_speeds = [
        #         abs(tmp[i] - previous_angles[i]) / time
        #         for i in range(6)
        #     ]

            
        #     angular_acceleration_limit = valid_max_angular_accelaration(previous_joints_speed, angular_speeds, time)
        #     time *= angular_acceleration_limit
            
        #     angular_speeds = [
        #         abs(tmp[i] - previous_angles[i]) / time
        #         for i in range(6)
        #     ]

        #     for i in range (6):
        #         velocity_profile[i*2 + 3].append((angular_speeds[i] - previous_joints_speed[i]) / time / 2 + MAX_ANGULAR_ACCELERATION/2)

        #     for i in range(6):
        #         velocity_profile[i*2 + 2].append(angular_speeds[i])

        #     tcp_speed = interpolated_distance/time

        #     velocity_profile[0].append(tcp_speed)
        #     velocity_profile[1].append((tcp_speed - previous_tcp_speed)/time/2 + acceleration/2)

        #     forward_path.append((time, tmp, tcp_speed))

        #     previous_angles = tmp
        #     previous_pose = interpolated_pose       
        #     previous_joints_speed = angular_speeds
        #     previous_tcp_speed = tcp_speed         

        # self.path  = forward_path
        # self.path_steps = step_number
        # self.current_step_index = 0

        # self.velocity_tab.update_velocity_profiles(velocity_profile, step_number, speed, acceleration, MAX_ANGULAR_SPEED, MAX_ANGULAR_ACCELERATION)
        # self.velocity_tab.update_progress(0)

        # self.simulation_timer.start()
        # self.animate_movement()

    def calculate_spatium (self,  elapsed_time, v_in, v_const, v_out, acc, duration, speed_up_time, speed_down_time):
        spatium = 0.0

        #distance during acceleration phase
        time = min(speed_up_time, elapsed_time)
        spatium += v_in*time + acc*time**2/2
        if elapsed_time <speed_up_time:
            return spatium

        time = 0.0
        const_time = duration - speed_up_time - speed_down_time

        if elapsed_time > const_time + speed_up_time:
            time = const_time
        else:
            time = elapsed_time - speed_up_time
        spatium += v_const*time

        if elapsed_time > const_time + speed_up_time:
            time = elapsed_time - const_time - speed_up_time
            spatium += v_const*time - acc*time**2/2

        return spatium


    def plan_ptp_motion(self, target_pose, speed, acceleration, initial_speed = None, final_speed = None, slow_down = True):
       
        #for here we get target pose as anglesz

        current_angles = (
            self.wrapper.actual_angle_0[self.ROBOT_IK],
            self.wrapper.actual_angle_1[self.ROBOT_IK],
            self.wrapper.actual_angle_2[self.ROBOT_IK],
            self.wrapper.actual_angle_3[self.ROBOT_IK],
            self.wrapper.actual_angle_4[self.ROBOT_IK],
            self.wrapper.actual_angle_5[self.ROBOT_IK],
        )

        if initial_speed is None:
            initial_speed = [0.0] * 6

        if final_speed is None:
            final_speed = [0.0] * 6

        angle_speed = [speed] * 6
        target_pose = unwrap_angles(target_pose, current_angles)

        directions = [1 if target_pose[i] - current_angles[i] >= 0 else -1 for i in range(6)]

        diff_angles = [abs(target_pose[i] - current_angles[i]) for i in range(6)]

        s_acc = [(speed**2 - initial_speed[i]**2)/(2*acceleration) for i in range(6)]
        s_dec = [0.0] * 6
        if slow_down:
            s_dec = [(speed**2 - final_speed[i]**2  )/(2*acceleration) for i in range(6)]
        

        const_angle  = [diff_angles[i] - s_acc[i] - s_dec[i] for i in range(6)]

        for i in range(6):
            if const_angle[i]<0:
                const_angle[i] = 0
                angle_speed[i] = math.sqrt((diff_angles[i]*acceleration + (initial_speed[i]**2 + final_speed[i]**2 *(1 if slow_down else 0))/2))
            #dla else nic nie musimy robić

        minimal_time = [0.0] * 6
        for i in range(6):
            if angle_speed[i] !=0:
                minimal_time[i] = (angle_speed[i] - initial_speed[i])/acceleration + (angle_speed[i] - final_speed[i])/acceleration*(1 if slow_down else 0) + const_angle[i]/angle_speed[i]


        simulation_time = max(minimal_time)
        simulation_time_index = minimal_time.index(simulation_time)
        simulation_steps = int(diff_angles[simulation_time_index]//self.SINGLE_STEP_ANGLE)
        simulation_step_time = simulation_time/simulation_steps

        #----------------------------------------------------------------------------------#
        # pierwsza cześć obliczeń z zeszytu #

        # wzorki z matlab
        if slow_down:
            for i in range(6):
                angle_speed[i] = (
                    initial_speed[i]/2 
                    + final_speed[i]/2 
                    + (acceleration * simulation_time)/2 
                    - (math.sqrt(
                        simulation_time**2 * acceleration**2 
                        + 2*simulation_time * acceleration * initial_speed[i] 
                        + 2*simulation_time * acceleration * final_speed[i] 
                        - 4 * diff_angles[i] * acceleration 
                        - initial_speed[i]**2 
                        + 2 * initial_speed[i] * final_speed[i] 
                        - final_speed[i] 
                        )
                    )/2
                )

        else:
            for i in range(6):
                angle_speed[i] = (
                    initial_speed[i]
                    - math.sqrt( acceleration * ( acceleration * simulation_time**2
                        + 2 * initial_speed[i] * simulation_time
                        - 2 * diff_angles[i]
                        ))
                    + acceleration * simulation_time
                )


        # commented values not used now - just for debugging purposes
        # speed_up_distance   = [(angle_speed[i]**2 - initial_speed[i]**2)/(2*acceleration) for i in range(6)]
        # speed_down_distance = [(angle_speed[i]**2 - final_speed[i]**2)/(2*acceleration) for i in range(6)]

        speed_up_time  = [(angle_speed[i] - initial_speed[i])/acceleration for i in range(6)]

        speed_down_time = [0.0] * 6
        if slow_down:
            speed_down_time = [(angle_speed[i] - final_speed[i])/acceleration for i in range(6)]
        # const_time  = [(diff_angles[i] - speed_up_distance[i] - speed_down_distance[i])/angle_speed[i] if angle_speed[i]!=0 else 0 for i in range(6)]
    


        timestamps = []
        tcp_profile = [[], []]
        joint_speed_profiles = [[] for _ in range(6)]
        joint_acceleration_profiles = [[] for _ in range(6)]
        angles_profile = [tuple(0 for _ in range(6))]

        interpolated_angle_table = [0.0] * 6


        previous_joint_speeds = *initial_speed,
        previous_angles = *current_angles,
        previous_tcp_speed = 0.0

        previous_pose = calculate_fk(*current_angles)

        elapsed_time = 0.0

        for step in range(simulation_steps):

            elapsed_time += simulation_step_time

            for i in range(6):
                interpolated_angle_table[i] = current_angles[i] + directions[i] * self.calculate_spatium(elapsed_time, initial_speed[i], angle_speed[i], final_speed[i], acceleration, simulation_time, speed_up_time[i], speed_down_time[i])

            if elapsed_time >= simulation_time - 0.001:
                interpolated_angle_table = target_pose

            interpolated_pose = calculate_fk(*interpolated_angle_table)
            interpolated_distance = math.sqrt(sum((interpolated_pose[i] - previous_pose[i]) ** 2 for i in range(3)))
            timestamps.append(simulation_step_time)

            tcp_speed = abs(interpolated_distance)/simulation_step_time
            tcp_profile[0].append(tcp_speed)
            tcp_profile[1].append((tcp_speed-previous_tcp_speed)/simulation_step_time/2)
            previous_tcp_speed = tcp_speed

            joint_speeds = [abs(interpolated_angle_table[i] - previous_angles[i]) / simulation_step_time for i in range(6)]
            for i in range(6):
                joint_speed_profiles[i].append(joint_speeds[i])
                joint_acceleration_profiles[i].append((joint_speeds[i] - previous_joint_speeds[i]) / simulation_step_time / 2)

            angles_profile.append(tuple(interpolated_angle_table))

            previous_angles = tuple(interpolated_angle_table)
            previous_joint_speeds = joint_speeds
            previous_pose = interpolated_pose

        return timestamps, tcp_profile, joint_speed_profiles, joint_acceleration_profiles, angles_profile

