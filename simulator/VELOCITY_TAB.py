from PySide6 import QtCore, QtWidgets, QtGui

from Wrapper import Wrapper
from pathStruct import pathStruct

class RenderWorker(QtCore.QObject):
	finished = QtCore.Signal()
    
	def __init__(self, wrapper):
		super().__init__()
		self.wrapper = wrapper
		self.next_timestamp = -1
		self.running = True
		self.minimized = False

	@QtCore.Slot()
	def run(self):
		while self.running:
			if not self.minimized:
				self.wrapper.render_charts(self.next_timestamp)
			QtCore.QThread.msleep(16)  # ~60 FPS

	def stop(self):
		self.running = False

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
		self.duration = 0.0

		for i in range (self.CHART_COUNT):
			self.chart_windows[i] = QtWidgets.QWidget(self)
			self.set_geometry(i)
			self.wrapper.connect_chart(i, self.chart_windows[i].winId())

		self.render_thread = QtCore.QThread()
		self.render_worker = RenderWorker(self.wrapper)
		self.render_worker.moveToThread(self.render_thread)
		self.render_thread.started.connect(self.render_worker.run)
		self.render_worker.minimized = False

		self.render_thread.start()

	def closeEvent(self, event):
		self.render_worker.stop()
		self.render_thread.quit()
		self.render_thread.wait()
		event.accept()


	def set_geometry(self, index):
		height = self.height()
		chart_height = self.minimum_chart_height
		if height > self.minimum_chart_height * self.CHART_COUNT + self.chart_space*self.CHART_COUNT+self.chart_space:
			chart_height = (height - self.chart_space*self.CHART_COUNT - self.chart_space)//self.CHART_COUNT

		self.chart_windows[index].setGeometry(10, self.chart_space + (chart_height + self.chart_space)*index, self.width()-20, chart_height)

	def resizeEvent(self, event):
		width = self.width()
		for i in range(self.CHART_COUNT):
			self.set_geometry(i)

		event.accept()

	def on_tab_minimized(self, widget: QtWidgets.QWidget, minimized: bool):
		if widget != self:
			return

		self.render_worker.minimized = minimized

	def update_progress(self, time_elapsed):
		if time_elapsed >= self.duration:
			self.render_worker.next_timestamp = -1
		else:
			self.render_worker.next_timestamp = time_elapsed

	def update_velocity_profiles(self, path: pathStruct,  max_tcp_speed, max_tcp_acceleration, max_joint_speed, max_joint_acceleration, duration):
		self.steps_len = path.get_length()
		self.duration = duration
		
		self.wrapper.update_chart_data(int(0), path.tcp_speed, path.tcp_acceleration, int(self.steps_len), int(max_tcp_speed), int(max_tcp_acceleration))

		for i in range(6):
			self.wrapper.update_chart_data(int(i+1), path.joints_speed[i], path.joints_acceleration[i], int(self.steps_len), int(max_joint_speed), int(max_joint_acceleration))

		self.wrapper.update_timestamps(path.timestamps, self.duration, int(self.steps_len))

	def update_chart_data(self, index, data_speed, data_acceleration, data_len, max_speed_value, max_acceleration_value):
		self.wrapper.update_chart_data(index, data_speed, data_acceleration, data_len, max_speed_value, max_acceleration_value)