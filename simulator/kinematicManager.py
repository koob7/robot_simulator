
from kinematic_helper import *
from Wrapper import Wrapper


class kinematicManager:
    def __init__(self, ik_tab, fk_tab):
        self.ik_tab = ik_tab
        self.fk_tab = fk_tab
        
        #we handle 3 robots with idx
        #   - 0 - solid color for forward kinematics simulation
        #   - 1 - solid color for inverse kinematics simulation
        #   - 2 - only edges for movement simulation
        self.wrapper = Wrapper()

        self.wrapper.moveRobot(0, 200, 0, 0)
        self.wrapper.moveRobot(1, 0, 0, 0)
        self.wrapper.moveRobot(2, -200, 0, 0)#TODO temporary

    def ik_changed_callback(self, _value=None):
        ik_values = self.ik_tab.get_values()
        print("IK changed:", ik_values)

    def fk_changed_callback(self, _value=None):
        fk_values = self.fk_tab.get_values()
        print("FK changed:", fk_values)
        self.wrapper.rotateRobot(0, fk_values[0], fk_values[1], fk_values[2], fk_values[3], fk_values[4], fk_values[5])