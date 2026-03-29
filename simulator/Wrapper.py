from ctypes import CDLL, c_uint64, c_uint32, c_float, c_int32, c_char_p, POINTER
import math
import sys
import os

def resource_path(relative_path):
	if hasattr(sys, '_MEIPASS'):
		return os.path.join(sys._MEIPASS, relative_path)
	return os.path.join(os.path.abspath("."), relative_path)
class Wrapper:
	def __init__(self):
		dll_path = resource_path('opengl_exe/opengl_drawer.dll')
		self.dll = CDLL(dll_path)
		self.dll.InitializeScene.argtypes = [c_char_p, c_char_p]
		self.dll.Initialize.argtypes = [c_uint64]
		self.dll.CalcProjectionMatrix.argtypes = [c_int32, c_int32]
		self.dll.SetCamera.argtypes = [c_float, c_float, c_float, c_float, c_float]
		self.dll.RobotMove.argtypes = [c_uint32, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float]

		self.dll.connect_chart.argtypes = [c_uint32, c_uint64]
		self.dll.close_chart.argtypes = [c_uint32]
		self.dll.update_chart_data.argtypes = [c_uint32, POINTER(c_float), c_uint32, c_uint32]
		self.dll.calc_chart_size.argtypes = [c_uint32]
		self.dll.render_charts.argtypes = [c_float]


		# Dynamiczne tablice stanu robota (rozszerzane na zadany indeks).
		self.actual_x = []
		self.actual_y = []
		self.actual_z = []

		self.actual_angle_0 = []
		self.actual_angle_1 = []
		self.actual_angle_2 = []
		self.actual_angle_3 = []
		self.actual_angle_4 = []
		self.actual_angle_5 = []

	def connect_chart(self, chart_id, hwnd):
		self.dll.connect_chart(chart_id, hwnd)

	def close_chart(self, chart_id):
		self.dll.close_chart(chart_id)

	def update_chart_data(self, chart_id, data_array, data_len, max_value):
		self.dll.update_chart_data(chart_id, data_array, data_len, max_value)

	def calc_chart_size(self, chart_id):
		self.dll.calc_chart_size(chart_id)

	def render_charts(self, progress):
		self.dll.render_charts(progress)

	def _ensure_idx(self, idx):
		if idx < 0:
			raise IndexError("idx must be >= 0")

		new_size = idx + 1
		for arr in [
			self.actual_x,
			self.actual_y,
			self.actual_z,
			self.actual_angle_0,
			self.actual_angle_1,
			self.actual_angle_2,
			self.actual_angle_3,
			self.actual_angle_4,
			self.actual_angle_5,
		]:
			missing = new_size - len(arr)
			if missing > 0:
				arr.extend([0.0] * missing)

	def Initialize(self, hwnd):
		self.dll.Initialize(hwnd)

	def CalcProjectionMatrix(self, res_x, res_y):
		self.dll.CalcProjectionMatrix(res_x, res_y)

	def SetCamera(self, x, y, z, angle_x, angle_y):
		self.dll.SetCamera(x, y, z, angle_x, angle_y)

	def InitializeScene(self):
		shaders_path = resource_path("opengl_source/shaders")
		models_path = resource_path("3d_models")
		self.dll.InitializeScene(shaders_path.encode(), models_path.encode())

	def _RobotMove(self, idx: int, x: float, y: float, z: float, angle_0: float, angle_1: float, angle_2: float, angle_3: float, angle_4: float, angle_5: float):
		self.dll.RobotMove(idx, x/10, y/10, z/10, math.radians(angle_0)-math.pi/2, math.radians(angle_1)-math.pi/2, math.radians(angle_2)-math.pi/2, math.radians(angle_3)-math.pi/2, math.radians(angle_4), math.radians(angle_5))

	def moveRobot(self, idx: int, x: float, y: float, z: float):
		self._ensure_idx(idx)
		self.actual_x[idx] = x
		self.actual_y[idx] = y
		self.actual_z[idx] = z

		self._RobotMove(
			idx,
			self.actual_x[idx],
			self.actual_y[idx],
			self.actual_z[idx],
			self.actual_angle_0[idx],
			self.actual_angle_1[idx],
			self.actual_angle_2[idx],
			self.actual_angle_3[idx],
			self.actual_angle_4[idx],
			self.actual_angle_5[idx],
		)

	def rotateRobot(self, idx: int, angle_0: float, angle_1: float, angle_2: float, angle_3: float, angle_4: float, angle_5: float):
		self._ensure_idx(idx)
		self.actual_angle_0[idx] = angle_0
		self.actual_angle_1[idx] = angle_1
		self.actual_angle_2[idx] = angle_2
		self.actual_angle_3[idx] = angle_3
		self.actual_angle_4[idx] = angle_4
		self.actual_angle_5[idx] = angle_5

		self._RobotMove(
			idx,
			self.actual_x[idx],
			self.actual_y[idx],
			self.actual_z[idx],
			self.actual_angle_0[idx],
			self.actual_angle_1[idx],
			self.actual_angle_2[idx],
			self.actual_angle_3[idx],
			self.actual_angle_4[idx],
			self.actual_angle_5[idx],
		)

	def Render(self):
		self.dll.Render()
