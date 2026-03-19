from ctypes import CDLL, c_uint64, c_uint32, c_float, c_int32
import os


class Wrapper:
	def __init__(self):
		self.dll = CDLL('example/opengl_drawer.dll')
		self.dll.Initialize.argtypes = [c_uint64]
		self.dll.CalcProjectionMatrix.argtypes = [c_int32, c_int32]
		self.dll.SetCamera.argtypes = [c_float, c_float, c_float, c_float, c_float]
		self.dll.RobotMove.argtypes = [c_uint32, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float]

	def Initialize(self, hwnd):
		self.dll.Initialize(hwnd)

	def CalcProjectionMatrix(self, res_x, res_y):
		self.dll.CalcProjectionMatrix(res_x, res_y)

	def SetCamera(self, x, y, z, angle_x, angle_y):
		self.dll.SetCamera(x, y, z, angle_x, angle_y)

	def InitializeScene(self):
		self.dll.InitializeScene()

	def RobotMove(self, idx, x, y, z, angle_0, angle_1, angle_2, angle_3, angle_4, angle_5, angle_6):
		self.dll.RobotMove(idx, x, y, z, angle_0, angle_1, angle_2, angle_3, angle_4, angle_5, angle_6)

	def Render(self):
		self.dll.Render()
