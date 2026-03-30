from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper


class VELOCITY_TAB(QtWidgets.QWidget):
	def __init__(self):
		super().__init__()
		self.setMinimumHeight(600)
		self.setMinimumWidth(200)

		self.wrapper = Wrapper()
		self.minimum_chart_height = 50
		self.chart_space = 10

		self.CHART_COUNT = 7

		self.chart_windows = [None] * self.CHART_COUNT
		self.current_step = 0
		self.steps_len = 0
		self.time_elapsed = 0.0
		self.duration = 0.0
		self.minimized = False


		for i in range (self.CHART_COUNT):
			self.chart_windows[i] = QtWidgets.QWidget(self)
			self.set_geometry(i)
			self.wrapper.connect_chart(i, self.chart_windows[i].winId())

		self.render_charts()

		self.render_timer = QtCore.QTimer(self)
		self.render_timer.setInterval(16)
		self.render_timer.timeout.connect(self.render_charts)
		self.render_timer.start()

	def set_geometry(self, index):
		height = self.height()
		chart_height = self.minimum_chart_height
		if height > self.minimum_chart_height * self.CHART_COUNT + self.chart_space*self.CHART_COUNT+self.chart_space:
			chart_height = (height - self.chart_space*self.CHART_COUNT - self.chart_space)//self.CHART_COUNT

		self.chart_windows[index].setGeometry(10, self.chart_space + (chart_height + self.chart_space)*index, self.width()-20, chart_height)

	def render_charts(self):
		if self.minimized:
			return
		if (self.time_elapsed >= self.duration):
			self.wrapper.render_charts(-1)
			return
		self.wrapper.render_charts(self.time_elapsed)

	def resizeEvent(self, event):
		width = self.width()
		for i in range(self.CHART_COUNT):
			self.set_geometry(i)
			
		self.render_charts()

		event.accept()

	def on_tab_minimized(self, widget: QtWidgets.QWidget, minimized: bool):
		if widget != self:
			return

		self.minimized = minimized

	def update_progress(self, time_elapsed):
		self.time_elapsed = time_elapsed

	def update_velocity_profiles(self, velocity_profile, length, max_tcp_speed, max_tcp_acceleration, max_joint_speed, max_joint_acceleration, duration):
		self.steps_len = length
		self.duration = duration
		
		self.wrapper.update_chart_data(int(0), velocity_profile[1][0], velocity_profile[1][1], int(self.steps_len), int(max_tcp_speed), int(max_tcp_acceleration))

		for i in range(6):
			self.wrapper.update_chart_data(int(i+1), velocity_profile[2][i], velocity_profile[3][i], int(self.steps_len), int(max_joint_speed), int(max_joint_acceleration))

		self.wrapper.update_timestamps(velocity_profile[0], self.duration, int(self.steps_len))

	def update_chart_data(self, index, data_speed, data_acceleration, data_len, max_speed_value, max_acceleration_value):
		self.wrapper.update_chart_data(index, data_speed, data_acceleration, data_len, max_speed_value, max_acceleration_value)