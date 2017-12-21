import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from mycamera import MyCamera

class MainApplication:
	def __init__(self, master, mycam):
		self.master = master
		self.mycam = mycam

		self.frame = tk.Frame(self.master)

		self.label1 = self.build_label("Controls")
		self.button1 = self.build_button("Test", self.cmd_test)
		self.button2 = self.build_button("Line 1", self.cmd_line)
		self.button3 = self.build_button("Line 2", self.cmd_line)
		self.button4 = self.build_button("Configure", self.cmd_calibrate)
		self.button5 = self.build_button("Capture", self.cmd_capture)

		self.w = tk.Canvas(self.frame, width=640, height=480)
		self.w.grid(column=1, row=0, rowspan=10)
		self.w.create_line(0, 0, 640, 480, fill="red")

		self.frame.pack()

	def build_label(self, text):
		label = ttk.Label(self.frame, text=text)
		label.grid()
		return label

	def build_button(self, text, command):
		button = ttk.Button(self.frame, text=text, width=25, command=command)
		button.grid()
		return button

	def cmd_test(self):
		print("Test")

	def cmd_line(self):
		self.w.create_line(640, 0, 0, 480, fill="red")

	def cmd_calibrate(self):
		self.mycam.calibrate()

	def cmd_capture(self):
		pilimage = self.mycam.capture_image()
		self.image = ImageTk.PhotoImage(pilimage)
		self.w.create_image((0, 0), image=self.image)

	def cmd_set_mode(self):
		print("Set mode")

def capture():
	print("Capture")

def main():
	mycam = MyCamera('auto', 0)
	root = tk.Tk()
	app = MainApplication(root, mycam)
	root.mainloop()

if __name__ == "__main__":
	main()
