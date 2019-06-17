import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from mycamera import MyCamera, Config
import datetime
import threading
import time
import queue
import enum
import sys
import numpy as np

def trace(*args):
	now = datetime.datetime.now()
	timestamp = now.strftime("%Y%m%d_%H%M%S")
	print("{} {}".format(timestamp, *args))

def timing(f):
	def wrap(*args):
#		print("{:<32} +".format(f.__qualname__))
		t1 = time.time()
		ret = f(*args)
		t2 = time.time()
		print("{:<32} - {:>6.0f}".format(f.__qualname__, (t2 - t1)*1000))
		return ret
	return wrap

class LiveUpdate(enum.Enum):
	PAUSE = 0
	RUN   = 1
	ONCE  = 2
	EXIT  = 3

class Display(enum.Enum):
	NOW  = 0
	AVG  = 1
	DIFF = 2

class LiveUpdater:
	class WorkItem:
		pass

	class Worker(threading.Thread):
		def __init__(self, in_q = None, out_q = None):
			threading.Thread.__init__(self)
			self.in_q = in_q
			self.out_q = out_q

		def get(self):
			if (self.in_q is not None):
				return self.in_q.get()
			return None

		def work(self, item):
			return item

		def run(self):
			while True:
				item = self.get()

				if (item is not None):
					item = self.work(item)

				if (self.in_q is not None):
					self.in_q.task_done()

				if (self.out_q is not None):
					self.out_q.put(item)

				if (item is None):
					print("Exit Worker")
					break

	class CaptureWorker(Worker):
		def __init__(self, mycam, out_q):
			LiveUpdater.Worker.__init__(self, None, out_q)
			self.mycam = mycam
			self.num = 0
			self.cv = threading.Condition()
			self.config = None
			self.state = LiveUpdate.PAUSE

		def set_config(self, config):
			print("Set config: {}".format(config))
			with self.cv:
				self.config = config
				self.cv.notify()

		def set_state(self, state):
			print("Set state: {}".format(state))
			with self.cv:
				self.state = state
				self.cv.notify()

		def get(self):
			with self.cv:
				while self.state is LiveUpdate.PAUSE:
					self.cv.wait()
				if (self.state is LiveUpdate.EXIT):
					return None
				if (self.state is LiveUpdate.ONCE):
					self.set_state(LiveUpdate.PAUSE)

			item = LiveUpdater.WorkItem()
			item.config = self.config
			self.config = None
#			if (self.config is not None):
#				item.config = self.config
#				self.config = None
#			else:
#				item.config = None

			return item

		@timing
		def work(self, item):
			if (item.config is not None):
				self.mycam.set_config(item.config)

#			print("Capture A")
			try:
#				self.mycam.capture("temp.jpg")
				item.image = self.mycam.capture_image()
			except:
#				print("Capture X:", sys.exc_info()[0])
				item.image = None
#			print("Capture B")
			return item

	class WaitingCaptureWorker(CaptureWorker):
		def __init__(self, mycam, out_q, delay):
			LiveUpdater.CaptureWorker.__init__(self, mycam, out_q)
			self.delay = delay
			self.time_now = time.time()

		def get(self):
			last_time = self.time_now
			self.time_now = time.time()
			time_wait = last_time + self.delay - self.time_now
			if time_wait > 0:
				print("Waiting {}s".format(time_wait))
				with self.cv:
					self.cv.wait(timeout=time_wait)
			return LiveUpdater.CaptureWorker.get(self)

	class ScaleWorker(Worker):
		def __init__(self, in_q, out_q):
			LiveUpdater.Worker.__init__(self, in_q, out_q)

		@timing
		def work(self, item):
			if (item.image is not None):
				size = (960, 540)
				item.thumbnail = item.image.copy()
				item.thumbnail.thumbnail(size)
			return item

	class AverageWorker(Worker):
		def __init__(self, in_q, out_q = None):
			LiveUpdater.Worker.__init__(self, in_q, out_q)
			self.avg = None

		def calc_average(self, item):
			if (self.avg is None):
				print("No previous average")
				self.avg = item.thumbnail
			self.avg = Image.blend(self.avg, item.thumbnail, 0.3)

		@timing
		def work(self, item):
			if (item.thumbnail is not None):
				self.calc_average(item)
			item.avg = self.avg

			return item

	class DiffWorker(Worker):
		def __init__(self, in_q, out_q = None):
			LiveUpdater.Worker.__init__(self, in_q, out_q)

		def calc_diff(self, item):
			now = (np.array(item.thumbnail.convert('L'))).astype(np.int)
			avg = (np.array(item.avg.convert('L'))).astype(np.int)
			diff = (now - avg)*10
			mean = diff.mean()
			print("Mean: {}".format(mean))
			item.diff = Image.fromarray(np.absolute(diff-mean)+127)

		@timing
		def work(self, item):
			if (item.thumbnail is not None) and (item.avg is not None):
				self.calc_diff(item)

			return item

	class DisplayWorker(Worker):
		def __init__(self, mycanvas, in_q, out_q = None):
			LiveUpdater.Worker.__init__(self, in_q, out_q)
			self.mycanvas = mycanvas
			self.display = Display.NOW

		def get_timestamp(self):
			now = datetime.datetime.now()
			timestamp = now.strftime("%Y%m%d_%H%M%S")
			return timestamp

		def set_display(self, display):
			self.display = display

		@timing
		def work(self, item):
			image = None
			if (self.display is Display.NOW):
				image = item.thumbnail
			if (self.display is Display.AVG):
				image = item.avg
			if (self.display is Display.DIFF):
				image = item.diff

			if (image is not None):
				self.mycanvas.set_image(image)

				item.timestamp = self.get_timestamp()
				self.mycanvas.set_time(item.timestamp)
			else:
				print("No display")

			return item

	class AutosaveWorker(Worker):
		def __init__(self, mycanvas, in_q, out_q = None):
			LiveUpdater.Worker.__init__(self, in_q, out_q)
			self.mycanvas = mycanvas
			self.state = False

		def set_state(self, state):
			print("Set autosave: {}".format(state))
			self.state = state

		@timing
		def work(self, item):
			if (self.state is True and
				item.image is not None):
				print("Saving...")
				item.filename = "{}.png".format(item.timestamp)
				item.image.save(item.filename)
				print("Save '{}'".format(item.filename))
			return item

	def __init__(self, mycam, mycanvas):
		self.aq = queue.Queue(1)
		self.bq = queue.Queue(1)
		self.cq = queue.Queue(1)
		self.dq = queue.Queue(1)
		self.eq = queue.Queue(1)

#		self.aw = self.WaitingCaptureWorker(mycam, self.aq, 60)
		self.aw = self.CaptureWorker(mycam, self.aq)
		self.bw = self.ScaleWorker(self.aq, self.bq)
		self.cw = self.AverageWorker(self.bq, self.cq)
		self.dw = self.DiffWorker(self.cq, self.dq)
		self.ew = self.DisplayWorker(mycanvas, self.dq, self.eq)
		self.fw = self.AutosaveWorker(mycanvas, self.eq)

	def start(self):
		self.aw.start()
		self.bw.start()
		self.cw.start()
		self.dw.start()
		self.ew.start()
		self.fw.start()

	def join(self):
		self.aw.set_state(LiveUpdate.EXIT)

		self.aq.join()
		self.bq.join()
		self.cq.join()
		self.dq.join()
		self.eq.join()

		self.aw.join()
		self.bw.join()
		self.cw.join()
		self.dw.join()
		self.ew.join()
		self.fw.join()

	def set_display(self, display):
		self.ew.set_display(display)

	def set_config(self, config):
		self.aw.set_config(config)

	def once(self):
		self.aw.set_state(LiveUpdate.ONCE)

	def live(self, status):
		if (status):
			self.aw.set_state(LiveUpdate.RUN)
		else:
			self.aw.set_state(LiveUpdate.PAUSE)

	def autosave(self, status):
		self.fw.set_state(status)

class MyCamMenu(tk.Frame):
	def __init__(self, master, app):
		tk.Frame.__init__(self, master)

		self.widget0 = self.build_label("Controls", grid = {"columnspan":1})
		self.widget1a = self.build_labelframe("Display", grid = {"sticky":"EW"})
		self.widget1a.x = self.build_combo(["Now", "Avg", "Diff"], root = self.widget1a, command = app.cmd_display)
		self.widget1 = self.build_labelframe("Resolution", grid = {"sticky":"EW"})
		self.widget1.x = self.build_combo(["2592x1944", "1920x1440", "1920x1200", "1920x1080", "1296x972", "800x600", "960x540", "640x480"], root = self.widget1, command = app.cmd_resolution)
#		self.widget1b = self.build_labelframe("Scale", grid = {"sticky":"EW"})
#		self.widget1b.x = self.build_combo(["2592x1944", "1920x1440", "1920x1200", "1920x1080", "1296x972", "800x600", "960x540", "640x480"], root = self.widget1, command = app.cmd_resolution)
		self.widget2 = self.build_button("Calibrate", app.cmd_calibrate, grid = {"columnspan":1})
		self.widget3 = self.build_labelframe("Capture", grid = {"sticky":"EW"})
		self.widget3.x = self.build_checkbox("Live", root = self.widget3, command = app.cmd_live)
		self.widget3.y = self.build_button("Now", app.cmd_capture, root = self.widget3, grid = {"column":1, "row":0, "sticky":"E"})
		self.widget4 = self.build_labelframe("Save", grid = {"sticky":"EW"})
		self.widget4.x = self.build_checkbox("Auto", root = self.widget4, command = app.cmd_autosave)
		self.widget4.y = self.build_button("Now", app.cmd_save, root = self.widget4, grid = {"column":1, "row":0, "sticky":"E"})
		self.widget5 = self.build_label("Settings", grid = {"columnspan":1})
#		self.widget6 = self.build_labelframe("Mode")
#		self.widget6.x = self.build_checkbox("Default", root = self.widget6, command = app.cmd_mode_default)
#		self.widget6.y = self.build_scale(root = self.widget6, command = app.cmd_mode_value, grid = {"column":1, "row":0, "sticky":"E"})
		self.widget6 = self.build_labelframeY("Mode", app.cmd_mode_default, app.cmd_mode_value)
		self.widget7 = self.build_labelframeY("Exposure", app.cmd_exp_default, app.cmd_exp_value)
		self.widgetA = self.build_labelframe("Rotation", grid = {"sticky":"EW"})
		self.widgetA.x = self.build_combo(["0", "90", "180", "270"], root = self.widgetA, command = app.cmd_rotation)
		self.widget8 = self.build_labelframe("ISO")
		self.widget8.x = self.build_checkbox("Default", root = self.widget8, command = app.cmd_iso_default)
		self.widget8.y = self.build_scale(root = self.widget8, command = app.cmd_iso_value, min = 100, max = 1600, steps = 100, grid = {"column":1, "row":0, "sticky":"E"})
#		self.widget8.y = self.build_combo(["100", "200", "320", "400", "500", "640", "800"], root = self.widget8, command = app.cmd_iso_value, grid = {"column":1, "row":0, "sticky":"E"})
#		self.widget8 = self.build_labelframeY("ISO", app.cmd_iso_default, app.cmd_iso_value)
		self.widget9 = self.build_labelframeY("Delay", app.cmd_delay_default, app.cmd_delay_value)
		self.widget10 = self.build_button("Exit", app.cmd_exit, grid = {"columnspan":2})

	def do_grid(self, widget, grid):
		widget.grid(**grid)
		return widget

	def build_labelframe(self, text, root = None, grid = {}):
		if (root is None): root = self
		frame = ttk.LabelFrame(root, text=text)
		return self.do_grid(frame, grid)

	def build_labelframeX(self, text, command, root = None, grid = {}):
		frame = self.build_labelframe(text, root, grid)
		frame.x = self.build_checkbox("Default", root = frame, command = command)
		frame.y = self.build_entry(root = frame, grid = {"column":1, "row":0})
		return frame

	def build_labelframeY(self, text, cmd_check, cmd_value, root = None, grid = {}):
		frame = self.build_labelframe(text, root, grid)
		frame.x = self.build_checkbox("Default", root = frame, command = cmd_check)
		frame.y = self.build_scale(root = frame, command = cmd_value, grid = {"column":1, "row":0})
		return frame

	def build_label(self, text, root = None, grid = {}):
		if (root is None): root = self
		label = ttk.Label(root, text=text)
		return self.do_grid(label, grid)

	def build_button(self, text, command, root = None, grid = {}):
		if (root is None): root = self
		button = ttk.Button(root, text=text, command = command)
		return self.do_grid(button, grid)

	def build_combo(self, values, command = None, root = None, var = None, grid = {}):
		if (root is None): root = self
		if (var is None): var = tk.StringVar()
		combo = ttk.Combobox(root, textvariable=var)
		combo['values'] = values
		combo.current(0)
		if (command is not None):
			combo.bind("<<ComboboxSelected>>", lambda event: command(combo.get()))
		combo.var = var
		return self.do_grid(combo, grid)

	def build_entry(self, root = None, grid = {}):
		if (root is None): root = self
		entry = ttk.Entry(root)
		return self.do_grid(entry, grid)

	def build_checkbox(self, text, root = None, command = None, var = None, grid = {}):
		if (root is None): root = self
		if (var is None): var = tk.IntVar()
		checkbox = tk.Checkbutton(root, text=text, variable=var)
		if (command is not None):
			checkbox.config(command=command)
		checkbox.var = var
		return self.do_grid(checkbox, grid)

	def build_scale(self, root = None, command = None, min = 0, max = 100, steps = 1, grid = {}):
		if (root is None): root = self
		scale = tk.Scale(root, orient=tk.HORIZONTAL, from_ = min, to = max, resolution = steps)
		if (command is not None):
			scale.config(command = command)
		return self.do_grid(scale, grid)

class MyCamCanvas(tk.Canvas):
	def __init__(self, master, *args, **kwargs):
		tk.Canvas.__init__(self, master, *args, **kwargs)

		self.bind("<Button-1>", self.on_click)
		self.bind("<MouseWheel>", self.on_wheel)
		self.bind("<Button-4>", self.on_wheel)
		self.bind("<Button-5>", self.on_wheel)

		self.can_image = self.create_image((0, 0), anchor=tk.NW)
		self.pil_image = None

		self.can_zoom = self.create_image((0, 0))
		self.zoom_pos = (0, 0)
		self.zoom_level = 0

		self.can_time = self.create_text((20, 20), anchor=tk.NW, fill="white")
		self.timestamp = "now"

	def set_zoom(self):
		if self.pil_image is not None:
			def pw2pp(pos, size):
				return (pos[0]-size[0]/2, pos[1]-size[1]/2,
						pos[0]+size[0]/2, pos[1]+size[1]/2)

			def pp2pw(x1, y1, x2, y2):
				center = ((x1+x2)/2, (y1+y2)/2)
				size = (x2-x1, y2-y1)
				return (center, size)

			coords = self.coords(self.can_zoom)
			self.move(self.can_zoom, self.zoom_pos[0]-coords[0], self.zoom_pos[1]-coords[1])
			size = (200, 200)
			zoom_factor = pow(2, self.zoom_level/2)
			zoom = (size[0]/zoom_factor, size[1]/zoom_factor)
			img = self.pil_image.crop(pw2pp(self.zoom_pos, zoom))
			img = img.resize(size)
			self.zoom = ImageTk.PhotoImage(img)
			self.itemconfig(self.can_zoom, image=self.zoom)

	def on_click(self, event):
		self.zoom_pos = (event.x, event.y)
		self.set_zoom()

	def on_wheel(self, event):
		def delta(event):
			if (event.num == 5 or event.delta < 0):
				return -1
			if (event.num == 4 or event.delta > 0):
				return 1
			return 0

		self.zoom_level = sorted([0, self.zoom_level + delta(event), 8])[1]
		self.set_zoom()

	def set_image(self, pil_image):
		self.pil_image = pil_image
		self.image = ImageTk.PhotoImage(pil_image)
		self.itemconfig(self.can_image, image=self.image)

		self.set_zoom()

	def set_time(self, timestamp):
		self.timestamp = timestamp
		self.itemconfig(self.can_time, text=self.timestamp)

	def save(self):
		if self.pil_image is not None:
			filename = "{}.png".format(self.timestamp)
			self.pil_image.save(filename)
			print("Save '{}'".format(filename))
		else:
			print("No image")

class MainApplication(tk.Frame):
	def __init__(self, master, mycam):
		tk.Frame.__init__(self, master)
		self.mycam = mycam

		self.menu = MyCamMenu(self, self)
		self.menu.grid()
		self.canvas = MyCamCanvas(self, width=960, height=540)
		self.canvas.grid(column=1, row=0, sticky=tk.N+tk.S+tk.E+tk.W)

		tk.Grid.columnconfigure(self, 1, weight=1)
		tk.Grid.rowconfigure(self, 0, weight=1)

		self.updater = LiveUpdater(self.mycam, self.canvas)
		self.updater.start()

	def cmd_test(self):
		print("Test")

	def cmd_display(self, display):
		print("Display {}".format(display))
		if (display == "Now"):
			self.updater.set_display(Display.NOW)
		elif (display == "Avg"):
			self.updater.set_display(Display.AVG)
		elif (display == "Diff"):
			self.updater.set_display(Display.DIFF)
		else:
			print("Unknown")

	def cmd_resolution(self, size):
		config = Config()
		if (size == "640x480"):
			config.resolution=(640, 480)
		if (size == "960x540"):
			config.resolution=(960, 540)
		if (size == "800x600"):
			config.resolution=(800, 600)
		if (size == "1280x720"):
			config.resolution=(1280, 720)
		if (size == "1920x1080"):
			config.resolution=(1920, 1080)
		if (size == "1920x1200"):
			config.resolution=(1920, 1200)
		if (size == "1920x1440"):
			config.resolution=(1920, 1440)
		if (size == "2592x1944"):
			config.resolution=(2592, 1944)
#		self.mycam.set_config(config)
		self.updater.set_config(config)

	def cmd_calibrate(self):
		self.mycam.calibrate()

	def cmd_capture(self):
		self.updater.once()

	def cmd_set_mode(self):
		print("Set mode")

	def cmd_live(self):
		live = self.menu.widget3.x.var.get()
		if (live > 0):
			self.updater.live(True)
		else:
			self.updater.live(False)

	def cmd_save(self):
		self.canvas.save()

	def cmd_autosave(self):
		auto = self.menu.widget4.x.var.get()
		if (auto > 0):
			self.updater.autosave(True)
		else:
			self.updater.autosave(False)

	def cmd_mode_default(self):
		mode = self.menu.widget6.x.var.get()
		print("X {}".format(mode))

	def cmd_mode_value(self, value):
		print(value)

	def cmd_rotation(self, rotation):
		print(rotation)
		rot = 0
		if (rotation == "90"):
			rot = 90
		if (rotation == "180"):
			rot = 180
		if (rotation == "270"):
			rot = 270

		config = Config(rotation = rot)
		self.mycam.set_config(config)

	def cmd_exp_default(self):
		exp = self.menu.widget7.x.var.get()
		print("Exp {}".format(exp))

	def cmd_exp_value(self, value):
		print("Exp val: {}".format(value))

	def cmd_iso_default(self):
		iso = self.menu.widget8.x.var.get()
		print("ISO {}".format(iso))
		if (iso != 0):
			config = Config(iso = 0)
			self.mycam.set_config(config)

	def cmd_iso_value(self, value):
		self.menu.widget8.x.deselect()

		config = Config(iso = int(value))
		self.mycam.set_config(config)
		print("ISO {}".format(value))

	def cmd_delay_default(self):
		print("Delay default")

	def cmd_delay_value(self, value):
		print("Delay value: {}".format(value))

	def cmd_exit(self):
		print("Exit")
		self.master.destroy()

	def join_updater(self):
		print("Join LiveUpdater")
		self.updater.join()

def main():
	mycam = MyCamera('auto', 0)
	root = tk.Tk()
	app = MainApplication(root, mycam)
	app.pack()
	root.mainloop()
	app.join_updater()

if __name__ == "__main__":
	main()
