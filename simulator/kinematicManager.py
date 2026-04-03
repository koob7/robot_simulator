
from kinematic_helper import *
from Wrapper import Wrapper
from PySide6 import QtCore

import logging
import math

from RobotViewport import MovementType
from pathStruct import pathStruct

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

        self.SINGLE_STEP_DISTANCE = 0.2  # mm (for simple linear interpolation)
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


        self.path = pathStruct()
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
        if self.path.get_length() == 0 or self.current_step_index >= self.path.get_length():
            self.simulation_timer.stop()
            self.robot_viewport.status_changed_callback("Simulation completed")
            if hasattr(self, 'animation_end_callback') and self.animation_end_callback:
                self.animation_end_callback()
            return
        
        angles = self.path.joints_angles[self.current_step_index]
        interval_ms = self.path.timestamps[self.current_step_index] * 1000
        velocity = self.path.tcp_speed[self.current_step_index]
        self.wrapper.rotateRobot(self.ROBOT_IK, *angles)
        self.simulation_timer.setInterval(int(interval_ms))
        self.robot_viewport.status_changed_callback("velocity: {:.1f} mm/s".format(velocity))

        self.elapsed_time += self.path.timestamps[self.current_step_index]
        self.current_step_index += 1
        self.velocity_tab.update_progress(self.elapsed_time)

    def abort_motion(self):
        self.simulation_timer.stop()
        self.path.clear()
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

        self.path.clear()
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
            self.path.copy_from(self.plan_linear_motion(target_pose, speed, acceleration))

        elif movement == MovementType.PTP:
            current_angles = (
                self.wrapper.actual_angle_0[self.ROBOT_IK],
                self.wrapper.actual_angle_1[self.ROBOT_IK],
                self.wrapper.actual_angle_2[self.ROBOT_IK],
                self.wrapper.actual_angle_3[self.ROBOT_IK],
                self.wrapper.actual_angle_4[self.ROBOT_IK],
                self.wrapper.actual_angle_5[self.ROBOT_IK],
            )

            self.path.copy_from(self.plan_ptp_motion(current_angles, target_pose, speed, acceleration, [0.0]*6, [0.0]*6, True))
        
        if self.path.get_length() == 0:
            logger.debug("Motion planning failed, skipping movement")
            return

        self.animation_end_callback = callback

        self.simulation_duration = sum(self.path.timestamps) #path.timestamps contains timestamps for each step

        max_tcp_acceleration = max(self.path.tcp_acceleration)
        min_tcp_acceleration = min(self.path.tcp_acceleration)

        tcp_divider = max(abs(max_tcp_acceleration), abs(min_tcp_acceleration))

        max_tcp_speed = max(self.path.tcp_speed)

        for i in range(self.path.get_length()):
            self.path.tcp_acceleration[i] = self.path.tcp_acceleration[i] + tcp_divider

        for i in range(len(self.path.joints_acceleration)):
            for j in range(self.path.get_length()):
                self.path.joints_acceleration[i][j] = self.path.joints_acceleration[i][j] + MAX_ANGULAR_ACCELERATION

        self.velocity_tab.update_velocity_profiles( self.path, max_tcp_speed, tcp_divider*2, MAX_ANGULAR_SPEED, MAX_ANGULAR_ACCELERATION*2, self.simulation_duration)

        self.simulation_timer.start()
        self.animate_movement()

    def calculate_time (self,  elapsed_distance, vel, acc, distance, speed_up_distance, speed_down_distance):
        time = 0.0

        const_distance = distance - speed_up_distance - speed_down_distance

        #speed_up
        if elapsed_distance<=speed_up_distance:
            return math.sqrt((2*elapsed_distance)/acc)
        else:
            time += math.sqrt((2*speed_up_distance)/acc)
            elapsed_distance -= speed_up_distance

        #const phase
        if elapsed_distance<const_distance:
            return time +  elapsed_distance / vel
        else:
            time += const_distance / vel
            elapsed_distance -= const_distance
        
        if elapsed_distance<0:
            return time

        #deceleration  (vel + (vel^2 - 2*acc*spatium)^(1/2))/acc
        sqrt_value = vel**2 - 2*acc*elapsed_distance
        sqrt_value = round(sqrt_value, 6)
        if sqrt_value<0:
            tmp = 10
        time += (vel - math.sqrt(sqrt_value))/acc

        return time

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
            logger.debug("very small movement, move as PTP")
            desired_angles = calculate_ik(*target_pose)
            unwrapped_angles = unwrap_angles(desired_angles, current_angles)
            return self.plan_ptp_motion(current_angles, unwrapped_angles, MAX_ANGULAR_SPEED, MAX_ANGULAR_ACCELERATION, [0.0]*6, [0.0]*6, True)
        
        step_number = math.ceil(linear_distance / self.SINGLE_STEP_DISTANCE)
        single_step_distance = linear_distance/step_number

        #przygotowanie struktur wchodzących do ścieżki path
        new_path: pathStruct = pathStruct()

        previous_tcp_speed = 0.0
        previous_joints_speeds = [0 for _ in range(6)]
        previous_joints_angles = current_angles
        previous_pose = tuple(current_pose)
        previous_pose_time = 0.0
        elapsed_distance = 0.0
        slow_down = False

        speed_up_distance = speed**2/(2*acceleration) #distance needed to reach target velocity with defined acceleration

        if (speed_up_distance>linear_distance/2):
            speed_up_distance = linear_distance/2

        speed_down_distance = speed_up_distance

        for step in range(1, step_number+1):

            #czy tutaj jednak nie powinniśmy korzystać z jakiegoś wzoru na prostą i przesuwania sie o dystans
            # re - to chyba właśnie teraz robimy :D
            elapsed_distance += single_step_distance

            interpolated_pose = interpolate_pose(current_pose, target_pose, step/step_number)
            wrappped_interpolated_joint_angles =calculate_ik(*interpolated_pose)
            interpolated_joints_angles = unwrap_angles(wrappped_interpolated_joint_angles, previous_joints_angles)
            interpolated_pose_time = self.calculate_time(elapsed_distance, speed, acceleration, linear_distance, speed_up_distance, speed_down_distance)

            time_diff = abs(interpolated_pose_time - previous_pose_time)

            error_code = valid_pose(*interpolated_pose) 
            if error_code != ValidErrorCode.VALID:
                logger.debug(f"Invalid pose at step {step}, skipping movement")
                self.robot_viewport.status_changed_callback(error_code.text())
                return new_path.clear()

            # def plan_ptp_motion(self, start_pose, target_pose, v_max, acceleration, v_in, v_out, slow_down: bool, desired_time = None, previous_tcp_speed = 0):

            if (step == step_number):
                slow_down = True

            step_path = self.plan_ptp_motion(previous_joints_angles, interpolated_joints_angles, self.ANGLE_SPEED, self.ANGLE_ACCELERATION, previous_joints_speeds, [0.0]*6, slow_down, time_diff, previous_tcp_speed)           

            new_path.sum_paths(step_path)


            previous_tcp_speed = step_path.tcp_speed[-1]
            previous_joints_speeds = [step_path.joints_speed[i][-1] for i in range(6)]
            previous_joints_angles = interpolated_joints_angles
            previous_pose = interpolated_pose
            previous_pose_time = interpolated_pose_time

        return new_path


  

    def calculate_spatium (self,  elapsed_time, v_in, v_const, acc, duration, speed_up_time, speed_down_time):
        spatium = 0.0

        const_time = duration - speed_up_time - speed_down_time

        #speed_up
        if elapsed_time<=speed_up_time:
            return v_in*elapsed_time + acc*elapsed_time**2/2
        else:
            spatium += v_in*speed_up_time + acc*speed_up_time**2/2
            elapsed_time -= speed_up_time

        #const phase
        if elapsed_time<const_time:
            return spatium + v_const*elapsed_time
        else:
            spatium += v_const*const_time
            elapsed_time -= const_time
        
        #deceleration
        spatium += v_const*elapsed_time - acc*elapsed_time**2/2

        return spatium


    def calculate_minimial_joint_time (self, spatium, v_max, acceleration, v_in, v_out, slow_down: bool):
        #zogdnie z diagramem draw.io

        Sa = (v_max**2 - v_in**2) / (2 * acceleration)
        divider = 0
        Sd = 0
        Sc = 0
        Td = 0

        if spatium == 0:
            return 0.0

        if slow_down:
            divider = 2
            Sd = (v_max**2 - v_out**2) / (2 * acceleration)
            #V_out - zostaje bez zmian
        
        else:
            #Sd - już ustawione na 0
            v_out = 0 #redundancja ale zostawmy
            divider = 1
        
        if spatium - Sa - Sd <=0:
            Sc = 0 # redundancja ale zostawmy
        else:
            Sc = spatium - Sa - Sd

        new_v = math.sqrt (((spatium - Sc)*2*acceleration + v_in**2 + v_out**2) / divider)

        if slow_down:
            Td = (new_v - v_out)/acceleration
        else:
            Td = 0 #redundancja ale zostawmy

        Ta = (new_v - v_in)/acceleration
        Tc = Sc/new_v

        time = Ta + Tc + Td

        return time

    def plan_ptp_motion(self, start_pose, target_pose, v_max, acceleration, v_in, v_out, slow_down: bool, desired_time = None, previous_tcp_speed = 0):
        #przygotowanie danych
        if v_max > MAX_ANGULAR_SPEED:
            logger.info(f"Requested speed {v_max} exceeds maximum angular speed, capping to {MAX_ANGULAR_SPEED}")
            v_max = MAX_ANGULAR_SPEED
        
        if acceleration > MAX_ANGULAR_ACCELERATION:
            logger.info(f"Requested acceleration {acceleration} exceeds maximum angular acceleration, capping to {MAX_ANGULAR_ACCELERATION}")
            acceleration = MAX_ANGULAR_ACCELERATION

        directions = [1 if target_pose[i] - start_pose[i] >= 0 else -1 for i in range(6)]

        joints_diff_angles = [abs(target_pose[i] - start_pose[i]) for i in range(6)]

        #wyznaczenie minimalnego czasu symulacji
        joints_required_time = [0.0]*6
        for i in range(6):
            joints_required_time[i] = self.calculate_minimial_joint_time(joints_diff_angles[i], v_max, acceleration, v_in[i], v_out[i], slow_down)

        #desired time is already considered
        simulation_time = max(joints_required_time)
        simulation_time_index = joints_required_time.index(simulation_time)
        if desired_time:
            simulation_time = max(simulation_time, desired_time)

        simulation_steps = math.ceil(joints_diff_angles[simulation_time_index]/self.SINGLE_STEP_ANGLE)
        simulation_step_time = simulation_time/simulation_steps

        # wyznaczenie prędkości docelowej dla każdej z osi - zgodnie ze wzorami matlab

        joints_speed = [v_max] * 6

        for i in range(6):
            if slow_down:
                sqrt_value = (
                    simulation_time**2 * acceleration**2
                    + 2*simulation_time * acceleration * v_in[i]
                    + 2*simulation_time * acceleration * v_out[i]
                    - 4 * joints_diff_angles[i] * acceleration
                    - v_in[i]**2
                    + 2 * v_in[i] * v_out[i]
                    - v_out[i]
                )
                sqrt_value = round(sqrt_value, 9)

                joints_speed[i] = (
                    v_in[i]/2 
                    + v_out[i]/2 
                    + (acceleration * simulation_time)/2 
                    - (math.sqrt(sqrt_value))/2
                )

            else:
                sqrt_value = acceleration*(acceleration * simulation_time**2 + 2 * v_in[i] * simulation_time - 2 * joints_diff_angles[i])
                sqrt_value = round(sqrt_value, 9)

                joints_speed[i] = (v_in[i] - math.sqrt(sqrt_value) + acceleration * simulation_time)


        # commented values not used now - just for debugging purposes
        # speed_up_distance   = [(joints_speed[i]**2 - v_in[i]**2)/(2*acceleration) for i in range(6)]
        # speed_down_distance = [(joints_speed[i]**2 - v_out[i]**2)/(2*acceleration) for i in range(6)]

        speed_up_time  = [(joints_speed[i] - v_in[i])/acceleration for i in range(6)]

        speed_down_time = [0.0] * 6
        if slow_down:
            speed_down_time = [(joints_speed[i] - v_out[i])/acceleration for i in range(6)]
        # const_time  = [(joints_diff_angles[i] - speed_up_distance[i] - speed_down_distance[i])/joints_speed[i] if joints_speed[i]!=0 else 0 for i in range(6)]
    

        #przygotowanie struktur wchodzących do ścieżki path
        new_path: pathStruct = pathStruct()

        #previous_tcp_speed is passed as argument to function
        previous_joints_speeds = v_in
        previous_joints_angles = start_pose
        previous_pose = tuple(calculate_fk(*start_pose))

        elapsed_time = 0.0

        for step in range(simulation_steps):

            elapsed_time += simulation_step_time
        
            interpolated_joint_angles = [start_pose[i] + directions[i] * self.calculate_spatium(elapsed_time, v_in[i], joints_speed[i], acceleration, simulation_time, speed_up_time[i], speed_down_time[i]) for i in range(6)]

            if elapsed_time >= round(simulation_time, 6):
                interpolated_joint_angles = target_pose

            interpolated_pose = calculate_fk(*interpolated_joint_angles)
            interpolated_distance = math.sqrt(sum((interpolated_pose[i] - previous_pose[i]) ** 2 for i in range(3)))

            error_code = valid_pose(*interpolated_pose) 
            if error_code != ValidErrorCode.VALID:
                logger.debug(f"Invalid pose at step {step}, skipping movement")
                self.robot_viewport.status_changed_callback(error_code.text())
                return pathStruct()

            tcp_speed = abs(interpolated_distance)/simulation_step_time
            tcp_acceleration = (tcp_speed - previous_tcp_speed)/simulation_step_time/2 #0 is in the midle of chart so values have to be scaled by 2

            joints_speeds = [abs(interpolated_joint_angles[i] - previous_joints_angles[i]) / simulation_step_time for i in range(6)]
            joints_accelerations = [(joints_speeds[i] - previous_joints_speeds[i]) / simulation_step_time for i in range(6)]

            new_path.append(simulation_step_time, tcp_speed, tcp_acceleration, interpolated_pose, joints_speeds, joints_accelerations, interpolated_joint_angles)

            previous_tcp_speed = tcp_speed
            previous_pose = interpolated_pose

            previous_joints_speeds = joints_speeds
            previous_joints_angles = interpolated_joint_angles
            
        return new_path