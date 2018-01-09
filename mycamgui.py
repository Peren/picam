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

class MyCamMenu(tk.Frame):
	def __init__(self, master, app):
		tk.Frame.__init__(self, master)

		self.widget1 = self.build_label("Controls", grid={"columnspan":1})
		self.widget2 = self.build_button("Calibrate", app.cmd_calibrate, grid={"columnspan":2})
		self.widget3 = self.build_labelframe("Capture", grid={"sticky":"EW"})
		self.widget3.x = self.build_checkbox("Live", root = self.widget3)
		self.widget3.y = self.build_button("Now", app.cmd_capture, root = self.widget3, grid={"column":1, "row":0, "sticky":"E"})
		self.widget4 = self.build_button("Save...", app.cmd_save, grid={"columnspan":1})
		self.widget5 = self.build_label("Settings", grid={"columnspan":1})
		self.widget6 = self.build_labelframe("Mode")
		self.widget6.x = self.build_checkbox("Default", root = self.widget6)
		self.widget6.y = self.build_entry(root = self.widget6, grid={"column":1, "row":0})
		self.widget7 = self.build_labelframe2("Exposure")
		self.widget8 = self.build_labelframe2("ISO")
		self.widget9 = self.build_labelframe2("Delay")
		self.widget10 = self.build_button("Exit", app.cmd_exit, grid={"columnspan":2})

	def build_labelframe2(self, text, root = None, grid = {}):
		if (root is None): root = self
		frame = ttk.LabelFrame(root, text=text)
		frame.checkbox = self.build_checkbox("Default", root = frame)
		frame.entry = self.build_entry(root = frame, grid={"column":1, "row":0})
		return do_grid(frame, grid)

	def build_labelframe(self, text, root = None, grid = {}):
		if (root is None): root = self
		frame = ttk.LabelFrame(root, text=text)
		return do_grid(frame, grid)

	def build_label(self, text, root = None, grid = {}):
		if (root is None): root = self
		label = ttk.Label(root, text=text)
		return do_grid(label, grid)

	def build_button(self, text, command, root = None, grid = {}):
		if (root is None): root = self
		button = ttk.Button(root, text=text, command=command)
		return do_grid(button, grid)

	def build_entry(self, root = None, grid = {}):
		if (root is None): root = self
		entry = ttk.Entry(root)
		return do_grid(entry, grid)

	def build_checkbox(self, text, root = None, var = None, grid = {}):
		if (root is None): root = self
		if (var is None): var = tk.IntVar()
		checkbox = tk.Checkbutton(root, text=text, variable=var)
		checkbox.var = var
		return do_grid(checkbox, grid)

class MyCamCanvas(tk.Canvas):
	def __init__(self, master, *args, **kwargs):
		tk.Canvas.__init__(self, master, *args, **kwargs)

		self.canimage = self.create_image((0, 0), anchor=tk.NW)
		self.cantime = self.create_text((20, 20), anchor=tk.NW, fill="white")

	def set_image(self, pil_image):
		self.image = ImageTk.PhotoImage(pil_image)
		self.itemconfig(self.canimage, image=self.image)

	def set_time(self, timestamp):
		self.itemconfig(self.cantime, text=timestamp)

class MainApplication(tk.Frame):
	def __init__(self, master, mycam):
		tk.Frame.__init__(self, master)
		self.mycam = mycam

		self.menu = MyCamMenu(self, self)
		self.menu.grid()
		self.w = MyCamCanvas(self, width=960, height=540)
		self.w.grid(column=10, row=0)

		self.pilimage = None

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

		self.w.set_image(self.pilimage)

		self.timestamp = get_timestamp()
		self.w.set_time(self.timestamp)

	def cmd_set_mode(self):
		print("Set mode")

	def cmd_save(self):
		if self.pilimage is not None:
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
	app.pack()
	root.mainloop()

if __name__ == "__main__":
	main()
