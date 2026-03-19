
from kinematic_helper import *
from Wrapper import Wrapper

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
        pass

    def fk_released_callback(self, _value=None):
        pass