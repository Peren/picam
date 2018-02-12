from picamera import PiCamera
from time import sleep
from PIL import Image
import argparse
import io
import numpy as np
from fractions import Fraction
import datetime
import os

class Config:
	resolution = (1920, 1080)
	sensor_mode = 3
	exposure = 0
	iso = 0
	exposure_mode = 'auto'

	def __init__(self, resolution = (1920, 1080), sensor_mode = 3, exposure = 0, iso = 0, exposure_mode = 'auto'):
		self.resolution = resolution
		self.sensor_mode = sensor_mode
		self.exposure = exposure
		self.iso = iso
		self.exposure_mode = exposure_mode

class MyCamera:
	camera = PiCamera()

	def __init__(self, mode='auto', exposure=0, iso=0):
		self.configure(mode, exposure, iso)

	def config(self, config):
		self.configure(config.mode, config.exposure, config.iso)

	def set_config(self, config):
		if (config.resolution is not None):
			self.camera.resolution = config.resolution
		if (config.sensor_mode is not None):
			self.camera.sensor_mode = config.sensor_mode
		if (config.exposure is not None):
			framerate = 30
			if (config.exposure > 0):
				framerate = Fraction(1000, config.exposure)
			self.camera.framerate = framerate
			shutter_speed = config.exposure * 1000
			self.camera.shutter_speed = shutter_speed
		if (config.iso is not None):
			self.camera.iso = config.iso
		if (config.exposure_mode is not None):
			self.camera.exposure_mode = config.exposure_mode

	def configure(self, mode, exposure, iso):
		shutter_speed = exposure * 1000
		framerate = 30
		if exposure > 0:
			framerate = Fraction(1000, exposure)

		# Force sensor mode 3 (the long exposure mode), set
		# the framerate to 1/6fps, the shutter speed to 6s,
		# and ISO to 800 (for maximum gain)
		#	resolution=(1280, 720),
		self.camera.resolution = (1920, 1080)
		self.camera.sensor_mode = 3
		self.camera.framerate = framerate
		self.camera.shutter_speed = shutter_speed
		self.camera.iso = iso
		# Give the camera a good long time to set gains and
		# measure AWB (you may wish to use fixed AWB instead)

#		self.camera.exposure_mode = 'off'
		self.camera.exposure_mode = mode
#		self.camera.annotate_text = "Gain: {}, Exposure: {}".format(old_gain, old_speed)

	def calibrate(self):
		old_gain = None
		old_speed = None
		for i in range(30):
			sleep(1)
			new_a_gain = self.camera.analog_gain
			new_d_gain = self.camera.digital_gain
			new_speed = self.camera.exposure_speed
			print("Analog Gain: {}, Digital Gain: {}, Exposure: {} ({})".format(new_a_gain, new_d_gain, new_speed, i))

			if (old_gain == new_a_gain and
				old_speed == new_speed and
				not new_a_gain == 0 and
				not new_speed == 0):
				break
			else:
				old_gain = new_a_gain
				old_speed = new_speed

	def capture(self, file):
		# Finally, capture an image with a 6s exposure. Due
		# to mode switching on the still port, this will take
		# longer than 6 seconds
		a_gain = self.camera.analog_gain
		d_gain = self.camera.digital_gain
		speed = self.camera.exposure_speed
		print("Saving {} ({}, {}, {})".format(file, a_gain, d_gain, speed), end='', flush=True)
		self.camera.annotate_text = "Analog Gain: {}, Digital Gain: {}, Exposure: {}".format(a_gain, d_gain, speed)
		print('.', end='', flush=True)
		self.camera.capture(file)
		print('.', end='', flush=True)

	def capture_image(self):
		stream = io.BytesIO()
		self.camera.capture(stream, format='png')
		stream.seek(0)
		return Image.open(stream)

def parse_args():
	parser = argparse.ArgumentParser(description="MyCamera console")
	parser.add_argument('--file', '-f', help='Image name', default='test.jpg')
	parser.add_argument('--mode', '-m', help='Exposure mode', default='auto')
	parser.add_argument('--exposure', '-e', help='Exposure', type=int, default=0)
	parser.add_argument('--iso', '-i', help='ISO', type=int, default=0)
	parser.add_argument('--number', '-n', help='Number of images', type=int, default=1)
	parser.add_argument('--delay', '-d', help='Delay between images', type=int, default=0)
	return parser.parse_args()

def print_args(args):
	print("File: {}".format(args.file))
	print("Mode: {}".format(args.mode))
	print("Expo: {}".format(args.exposure))
	print("Iso: {}".format(args.iso))
	print("Number: {}".format(args.number))
	print("Delay: {}".format(args.delay))
	print()

def main():
	args = parse_args()
	print_args(args)

	my_camera = MyCamera(args.mode, args.exposure, args.iso)

	now = datetime.datetime.now()
	timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')

	path = '/share/pics/{}'.format(timestamp)
	os.makedirs(path)
	print("Create folder: {}".format(path))

	for i in range(args.number):
		file = args.file.replace(".", "_{}_{}.".format(args.exposure, i), 1)
		my_camera.capture(path +"/"+ file)
		if args.delay > 0:
			sleep(args.delay)
			print('.')

if __name__ == "__main__":
	main()
