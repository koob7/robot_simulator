import tkinter as tk
from tkinter import ttk
from Wrapper import Wrapper


class App:
	def __init__(self, root):
		self.root = root
		self.root.title("Canvas + 9 Sliderów")

		main_frame = ttk.Frame(root)
		main_frame.pack(fill="both", expand=True)

		self.canvas = tk.Canvas(main_frame, bg="white", width=500, height=500)
		self.canvas.pack(side="left", fill="both", expand=True)

		# bind resize handler
		self.canvas.bind("<Configure>", self.on_canvas_resize)

		sliders_frame = ttk.Frame(main_frame, padding=10)
		sliders_frame.pack(side="right", fill="y")

		self.sliders = []

		for axis in ["camX", "camY", "camZ"]:
			label = ttk.Label(sliders_frame, text=f"Pozycja {axis}")
			label.pack()

			slider = tk.Scale(sliders_frame, from_=-300.0, to=300.0, resolution=0.01, orient="horizontal", length=300)
			slider.pack()
			self.sliders.append(slider)
		label = ttk.Label(sliders_frame, text=f"camAngleX")
		label.pack()
		slider = tk.Scale(sliders_frame, from_=-180.0, to=180.0, resolution=0.01, orient="horizontal", length=300)
		slider.pack()
		self.sliders.append(slider)
		label = ttk.Label(sliders_frame, text=f"camAngleY")
		label.pack()
		slider = tk.Scale(sliders_frame, from_=-180.0, to=180.0, resolution=0.01, orient="horizontal", length=300)
		slider.pack()
		self.sliders.append(slider)

		for axis in ["X", "Y", "Z"]:
			label = ttk.Label(sliders_frame, text=f"Pozycja {axis}")
			label.pack()

			slider = tk.Scale(sliders_frame, from_=-30.0, to=30.0, resolution=0.01, orient="horizontal", length=300)
			slider.pack()
			self.sliders.append(slider)
		for i in range(7):
			label = ttk.Label(sliders_frame, text=f"Kąt {i + 1}")
			label.pack()

			slider = tk.Scale(sliders_frame, from_=-180.0, to=180.0, resolution=0.01, orient="horizontal", length=300)
			slider.pack()
			self.sliders.append(slider)

		self.wrapper = Wrapper()
		self.wrapper.Initialize(self.canvas.winfo_id())
		self.wrapper.InitializeScene()
		self.wrapper.SetCamera(5.0, 0, 0, 0, 0)

		self.update_canvas()

	def update_canvas(self):
		values = [slider.get() for slider in self.sliders]
		camX, camY, camZ = values[0], values[1], values[2]
		camAngleX, camAngleY = values[3], values[4]
		x, y, z = values[5], values[6], values[7]
		angles = values[8:]

		self.wrapper.SetCamera(camX, camY, camZ, -camAngleX * 0.017453292519943295, camAngleY * 0.017453292519943295)
		self.wrapper.RobotMove(0, x, y, z, angles[0] * 0.017453292519943295, angles[1] * 0.017453292519943295, angles[2] * 0.017453292519943295, angles[3] * 0.017453292519943295, angles[4] * 0.017453292519943295, angles[5] * 0.017453292519943295, angles[6] * 0.017453292519943295)

		self.wrapper.Render()
		self.root.after(1, self.update_canvas)

	def on_canvas_resize(self, event):
		self.wrapper.CalcProjectionMatrix(event.width, event.height)


if __name__ == "__main__":
	root = tk.Tk()
	app = App(root)
	root.mainloop()
