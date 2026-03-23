
from PySide6 import QtCore, QtWidgets, QtGui


class VelocityChartWidget(QtWidgets.QWidget):
	def __init__(self, title, color, parent=None):
		super().__init__(parent)
		self.title = title
		self.series_color = QtGui.QColor(color)
		self.values = []
		self.progress_index = -1
		self._static_cache = None
		self._cache_size = QtCore.QSize()
		self.setMinimumHeight(60)

	def set_series(self, values):
		self.values = list(values)
		self.progress_index = -1
		self._invalidate_cache()
		self.update()

	def set_progress(self, index):
		self.progress_index = index
		self.update()

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._invalidate_cache()

	def _invalidate_cache(self):
		self._static_cache = None
		self._cache_size = QtCore.QSize()

	def _build_static_cache(self):
		rect = self.rect()
		if rect.width() <= 0 or rect.height() <= 0:
			self._static_cache = None
			self._cache_size = QtCore.QSize()
			return

		pixmap = QtGui.QPixmap(rect.size())
		pixmap.fill(QtCore.Qt.GlobalColor.transparent)

		painter = QtGui.QPainter(pixmap)
		painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

		painter.fillRect(rect, QtGui.QColor(32, 34, 40))

		chart_rect = rect.adjusted(8, 22, -8, -8)
		if chart_rect.width() <= 0 or chart_rect.height() <= 0:
			painter.end()
			self._static_cache = pixmap
			self._cache_size = rect.size()
			return

		painter.setPen(QtGui.QPen(QtGui.QColor(80, 84, 92), 1))
		mid_y = chart_rect.center().y()
		painter.drawLine(chart_rect.left(), mid_y, chart_rect.right(), mid_y)

		title_pen = QtGui.QPen(QtGui.QColor(220, 220, 220))
		painter.setPen(title_pen)
		painter.drawText(rect.adjusted(8, 4, -8, -4), QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop, self.title)

		if len(self.values) < 2:
			painter.setPen(QtGui.QPen(QtGui.QColor(160, 160, 160), 1))
			painter.drawText(chart_rect, QtCore.Qt.AlignmentFlag.AlignCenter, "No data")
			painter.end()
			self._static_cache = pixmap
			self._cache_size = rect.size()
			return

		min_v = min(self.values)
		max_v = max(self.values)
		if abs(max_v - min_v) < 1e-9:
			span = max(1.0, abs(max_v))
			min_v -= span * 0.5
			max_v += span * 0.5

		x_step = chart_rect.width() / (len(self.values) - 1)
		points = []
		inv_span = 1.0 / (max_v - min_v)
		for i, value in enumerate(self.values):
			x = chart_rect.left() + i * x_step
			y_norm = (value - min_v) * inv_span
			y = chart_rect.bottom() - y_norm * chart_rect.height()
			points.append(QtCore.QPointF(x, y))

		painter.setPen(QtGui.QPen(self.series_color, 1.6))
		painter.drawPolyline(points)

		current_label = f"{self.values[-1]:.1f}"
		painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 1))
		painter.drawText(chart_rect.adjusted(0, 0, -2, -2), QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop, current_label)

		painter.end()
		self._static_cache = pixmap
		self._cache_size = rect.size()

	def paintEvent(self, event):
		_ = event
		if self._static_cache is None or self._cache_size != self.size():
			self._build_static_cache()

		painter = QtGui.QPainter(self)
		if self._static_cache is None:
			return

		painter.drawPixmap(0, 0, self._static_cache)

		chart_rect = self.rect().adjusted(8, 22, -8, -8)
		if chart_rect.width() <= 0 or chart_rect.height() <= 0:
			return

		if len(self.values) < 2:
			return

		if 0 <= self.progress_index < len(self.values):
			x_step = chart_rect.width() / (len(self.values) - 1)
			progress_x = chart_rect.left() + self.progress_index * x_step
			painter.setPen(QtGui.QPen(QtGui.QColor(255, 230, 80), 1))
			painter.drawLine(int(progress_x), chart_rect.top(), int(progress_x), chart_rect.bottom())


class VELOCITY_TAB(QtWidgets.QWidget):
	def __init__(self):
		super().__init__()
		self._series_length = 0

		layout = QtWidgets.QGridLayout(self)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setHorizontalSpacing(8)
		layout.setVerticalSpacing(8)

		labels = [
			("TCP [mm/s]", "#00d3b8"),
			("J1 [deg/s]", "#ff6b6b"),
			("J2 [deg/s]", "#4dabf7"),
			("J3 [deg/s]", "#51cf66"),
			("J4 [deg/s]", "#ffd43b"),
			("J5 [deg/s]", "#ffa94d"),
			("J6 [deg/s]", "#da77f2"),
		]

		self.charts = []
		for idx, (title, color) in enumerate(labels):
			chart = VelocityChartWidget(title, color, self)
			self.charts.append(chart)
			layout.addWidget(chart, idx, 0)

		layout.setRowStretch(len(labels), 1)

	def draw_velocity_profiles(self, speed_rows):
		self._series_length = len(speed_rows)
		if not speed_rows:
			for chart in self.charts:
				chart.set_series([])
			return

		channels = list(zip(*speed_rows))
		for i, chart in enumerate(self.charts):
			chart.set_series(channels[i] if i < len(channels) else [])

	def update_progress_marker(self, step_index):
		if self._series_length <= 0:
			return
		clamped = max(0, min(step_index, self._series_length - 1))
		for chart in self.charts:
			chart.set_progress(clamped)
