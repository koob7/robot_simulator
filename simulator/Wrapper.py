from ctypes import CDLL, c_uint64, c_uint32, c_float, c_int32


class Wrapper:
	def __init__(self):
		self.dll = CDLL('example/opengl_drawer.dll')
		self.dll.Initialize.argtypes = [c_uint64]
		self.dll.CalcProjectionMatrix.argtypes = [c_int32, c_int32]
		self.dll.SetCamera.argtypes = [c_float, c_float, c_float, c_float, c_float]
		self.dll.RobotMove.argtypes = [c_uint32, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float, c_float]

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
		self.actual_angle_6 = []

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
			self.actual_angle_6,
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
		self.dll.InitializeScene()

	def moveRobot(self, idx, x, y, z):
		self._ensure_idx(idx)
		self.actual_x[idx] = x
		self.actual_y[idx] = y
		self.actual_z[idx] = z

		self.RobotMove(
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
			self.actual_angle_6[idx],
		)

	def rotateRobot(self, idx, angle_0, angle_1, angle_2, angle_3, angle_4, angle_5):
		self._ensure_idx(idx)
		self.actual_angle_0[idx] = angle_0
		self.actual_angle_1[idx] = angle_0
		self.actual_angle_2[idx] = angle_1
		self.actual_angle_3[idx] = angle_2
		self.actual_angle_4[idx] = angle_3
		self.actual_angle_5[idx] = angle_4

		self.RobotMove(
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
			self.actual_angle_6[idx],
		)


	def _RobotMove(self, idx, x, y, z, angle_0, angle_1, angle_2, angle_3, angle_4, angle_5, angle_6):
		self.dll.RobotMove(idx, x, y, z, angle_0, angle_1, angle_2, angle_3, angle_4, angle_5, angle_6)

	def Render(self):
		self.dll.Render()
