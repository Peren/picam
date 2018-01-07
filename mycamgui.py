import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from mycamera import MyCamera
import datetime

def get_timestamp():
	now = datetime.datetime.now()
	timestamp = now.strftime("%Y%m%d_%H%M%S")
	return timestamp

def do_grid(widget, grid):
	widget.grid(**grid)
	return widget

class MainApplication:
	def __init__(self, master, mycam):
		self.master = master
		self.mycam = mycam

		self.frame = tk.Frame(self.master)

		self.widget1 = self.build_label("Controls", grid={"columnspan":2})
		self.widget2 = self.build_button("Calibrate", self.cmd_calibrate, grid={"columnspan":2})
		self.widget3x= self.build_checkbox("Continous")
		self.widget3 = self.build_button("Capture", self.cmd_capture, grid={"column":1, "row":2})
		self.widget4 = self.build_button("Save...", self.cmd_save, grid={"columnspan":2})

		self.widget5 = self.build_label("Settings", grid={"columnspan":2})
		self.widget6x = self.build_checkbox("Default")
		self.widget6 = self.build_entry(grid={"column":1, "row":5, "sticky":tk.W})
		self.widget7x = self.build_checkbox("Default")
		self.widget7 = self.build_entry(grid={"column":1, "row":6})
		self.widget8x = self.build_checkbox("Default")
		self.widget8 = self.build_entry(grid={"column":1, "row":7})
		self.widget9x = self.build_checkbox("Default")
		self.widget9 = self.build_entry(grid={"column":1, "row":8})

		self.widget10 = self.build_button("Exit", self.cmd_exit, grid={"columnspan":2})
		self.w = tk.Canvas(self.frame, width=960, height=540)
		self.w.grid(column=10, row=0, rowspan=10)

		self.pilimage = None
		self.canimage = self.w.create_image((0, 0), anchor=tk.NW)
		self.cantime = self.w.create_text((20, 20), anchor=tk.NW, fill="white")

		self.frame.pack()

	def build_label(self, text, grid = {}):
		label = ttk.Label(self.frame, text=text)
		return do_grid(label, grid)

	def build_button(self, text, command, grid = {}):
		button = ttk.Button(self.frame, text=text, command=command)
		return do_grid(button, grid)

	def build_entry(self, grid = {}):
		entry = ttk.Entry(self.frame)
		return do_grid(entry, grid)

	def build_checkbox(self, text, grid = {}):
		var = tk.IntVar()
		checkbox = tk.Checkbutton(self.frame, text=text, variable=var)
		checkbox.var = var
		return do_grid(checkbox, grid)

	def cmd_test(self):
		print("Test")

	def cmd_line(self):
		self.w.create_line(960, 0, 0, 540, fill="red")

	def cmd_calibrate(self):
		self.mycam.calibrate()

	def cmd_capture(self):
		self.pilimage = self.mycam.capture_image()
		size = (960, 540)
		self.pilimage = self.pilimage.resize(size, Image.ANTIALIAS)
		self.image = ImageTk.PhotoImage(self.pilimage)
		self.w.itemconfig(self.canimage, image=self.image)

		self.timestamp = get_timestamp()
		self.w.itemconfig(self.cantime, text=self.timestamp)

	def cmd_set_mode(self):
		print("Set mode")

	def cmd_save(self):
		if self.pilimage is not None:
			#now = datetime.datetime.now()
			#timestamp = now.strftime("%Y%m%d_%H%M%S")
			filename = "{}.png".format(self.timestamp)
			self.pilimage.save(filename)
			print("Save '{}'".format(filename))

		else:
			print("No image")

	def cmd_exit(self):
		print("Exit")
		self.master.destroy()

def capture():
	print("Capture")

def main():
	mycam = MyCamera('auto', 0)
	root = tk.Tk()
	app = MainApplication(root, mycam)
	root.mainloop()

if __name__ == "__main__":
	main()
