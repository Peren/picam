import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from mycamera import MyCamera, Config
import datetime
import threading
import time
import queue
import enum

def timing(f):
	def wrap(*args):
		t1 = time.time()
		ret = f(*args)
		t2 = time.time()
		print("{:<32} : {:>6.0f}".format(f.__qualname__, (t2 - t1)*1000))
		return ret
	return wrap

class LiveUpdate(enum.Enum):
	PAUSE = 0
	RUN   = 1
	ONCE  = 2
	EXIT  = 3

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
			self.state = LiveUpdate.PAUSE

		def set_state(self, state):
			print("Set capture: {}".format(state))
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

			return LiveUpdater.WorkItem()

		@timing
		def work(self, item):
			try:
				item.image = self.mycam.capture_image()
			except:
				item.image = None
			return item

	class ScaleWorker(Worker):
		def __init__(self, in_q, out_q):
			LiveUpdater.Worker.__init__(self, in_q, out_q)

		@timing
		def work(self, item):
			if (item.image is not None):
				size = (960, 540)
				item.image.thumbnail(size)
			return item

	class DisplayWorker(Worker):
		def __init__(self, mycanvas, in_q, out_q = None):
			LiveUpdater.Worker.__init__(self, in_q, out_q)
			self.mycanvas = mycanvas

		def get_timestamp(self):
			now = datetime.datetime.now()
			timestamp = now.strftime("%Y%m%d_%H%M%S")
			return timestamp

		@timing
		def work(self, item):
			if (item.image is not None):
				self.mycanvas.set_image(item.image)

				item.timestamp = self.get_timestamp()
				self.mycanvas.set_time(item.timestamp)

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

		self.aw = self.CaptureWorker(mycam, self.aq)
		self.bw = self.ScaleWorker(self.aq, self.bq)
		self.cw = self.DisplayWorker(mycanvas, self.bq, self.cq)
		self.dw = self.AutosaveWorker(mycanvas, self.cq)

	def start(self):
		self.aw.start()
		self.bw.start()
		self.cw.start()
		self.dw.start()

	def join(self):
		self.aw.set_state(LiveUpdate.EXIT)

		self.aq.join()
		self.bq.join()
		self.cq.join()

		self.aw.join()
		self.bw.join()
		self.cw.join()
		self.dw.join()

	def once(self):
		self.aw.set_state(LiveUpdate.ONCE)

	def live(self, status):
		if (status):
			self.aw.set_state(LiveUpdate.RUN)
		else:
			self.aw.set_state(LiveUpdate.PAUSE)

	def autosave(self, status):
		self.dw.set_state(status)

class MyCamMenu(tk.Frame):
	def __init__(self, master, app):
		tk.Frame.__init__(self, master)

		self.widget0 = self.build_label("Controls", grid={"columnspan":1})
		self.widget1 = self.build_labelframe("Resolution", grid={"sticky":"EW"})
		self.widget1.x = self.build_combo(["2592x1944", "1920x1080", "1296x972", "800x600", "640x480"], app.cmd_resolution)
		self.widget2 = self.build_button("Calibrate", app.cmd_calibrate, grid={"columnspan":1})
		self.widget3 = self.build_labelframe("Capture", grid={"sticky":"EW"})
		self.widget3.x = self.build_checkbox("Live", root = self.widget3, command = app.cmd_live)
		self.widget3.y = self.build_button("Now", app.cmd_capture, root = self.widget3, grid={"column":1, "row":0, "sticky":"E"})
		self.widget4 = self.build_labelframe("Save", grid={"sticky":"EW"})
		self.widget4.x = self.build_checkbox("Auto", root = self.widget4, command = app.cmd_autosave)
		self.widget4.y = self.build_button("Now", app.cmd_save, root = self.widget4, grid={"column":1, "row":0, "sticky":"E"})
		self.widget5 = self.build_label("Settings", grid={"columnspan":1})
		self.widget6 = self.build_labelframe2("Mode")
		self.widget7 = self.build_labelframe2("Exposure")
		self.widget8 = self.build_labelframe2("ISO")
		self.widget9 = self.build_labelframe2("Delay")
		self.widget10 = self.build_button("Exit", app.cmd_exit, grid={"columnspan":2})

	def do_grid(self, widget, grid):
		widget.grid(**grid)
		return widget

	def build_labelframe2(self, text, root = None, grid = {}):
		if (root is None): root = self
		frame = ttk.LabelFrame(root, text=text)
		frame.checkbox = self.build_checkbox("Default", root = frame)
		frame.entry = self.build_entry(root = frame, grid={"column":1, "row":0})
		return self.do_grid(frame, grid)

	def build_labelframe(self, text, root = None, grid = {}):
		if (root is None): root = self
		frame = ttk.LabelFrame(root, text=text)
		return self.do_grid(frame, grid)

	def build_label(self, text, root = None, grid = {}):
		if (root is None): root = self
		label = ttk.Label(root, text=text)
		return self.do_grid(label, grid)

	def build_button(self, text, command, root = None, grid = {}):
		if (root is None): root = self
		button = ttk.Button(root, text=text, command=command)
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

	def cmd_resolution(self, size):
		config = Config()
		if (size == "640x480"):
			config.resolution=(640, 480)
		if (size == "800x600"):
			config.resolution=(800, 600)
		if (size == "1280x720"):
			config.resolution=(1280, 720)
		if (size == "1920x1080"):
			config.resolution=(1920, 1080)
		if (size == "2592x1944"):
			config.resolution=(2592, 1944)
		self.mycam.set_config(config)

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
