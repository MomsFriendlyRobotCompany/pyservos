

##############################################
# The MIT License (MIT)
# Copyright (c) 2016 Kevin Walchko
# see LICENSE for full details
##############################################
# Serial interfaces (real and test) for communications with XL-320 servos.

from __future__ import division
from __future__ import print_function
import serial as PySerial
import time
# import os
# import pty


class ServoSerial(object):
	"""
	A wrapper around pyserial to work with Dynamixel servos' half duplex
	interface. This requires extra hardware added to your normal full duplex
	serial port. Also, this uses the  RTS pin to toggle between Tx and Rx.

	All data that goes into this class via write() or returns from it via read()
	is a simple array of bytes (e.g., [1,34,234,1,0,24,67]). Internally, the class
	transforms those into a binary stream.

	This class also uses Packet to find and verify what is returned form read()
	is a valid packet.

	RPi3 sucks ... they screwed up the serial port, the RTS pin doesn't work so I
	just toggle pin 17 and treat it as an output pin.
	"""
	# my board
	DD_WRITE = False      # data direction set to write .. RTS is backwards
	DD_READ = True        # data direction set to read .. RTS is backwards
	# old way, did I screw soemthing up?
	# DD_WRITE = True      # data direction set to write
	# DD_READ = False        # data direction set to read

	# SLEEP_TIME = 0.0    # sleep time between read/write
	# SLEEP_TIME = 0.005    # sleep time between read/write
	# SLEEP_TIME = 0.0005    # sleep time between read/write
	SLEEP_TIME = 0.00005    # sleep time between read/write
	# fake = False
	loop_addr = 'loop://'
	pi_pin = None

	def __init__(self, port, baud_rate=1000000, pi_pin=None):
		"""
		Constructor: sets up the serial port

		If you want to use a USB serial port, then set rts_hw to 0 (False). If you
		want to use the RPi seiral port, then you need to use a pin to toggle TX/Rx.
		Set rst_hw to any valid BCM pin greater than 0.
		"""
		# redo port if it is fake
		# not sure this works on Windows
		# os.read(master,1000)
		if port in ['dummy', 'fake', 'test', '/dev/null']:
			# import pty
			# master, slave = pty.openpty()
			# port = os.ttyname(slave)
			# self.serial = PySerial.Serial(port)
			# self.fake = True
			self.serial = PySerial.serial_for_url(self.loop_addr, timeout=0.1)
		else:
			self.serial = PySerial.Serial()
			self.serial.baudrate = baud_rate
			self.serial.port = port
		# the default time delay on the servo is 0.5 msec before it returns a status pkt
		# self.serial.timeout = 0.0001  # time out waiting for blocking read()
		self.serial.timeout = 0.005
		if pi_pin:
			self.pi_pin = pi_pin
			# import GPIO

	def __del__(self):
		"""
		Destructor: closes the serial port
		"""
		self.close()

	def setRTS(self, level):
		# if self.fake:
		# 	return

		time.sleep(self.SLEEP_TIME)
		# only need one of thse, but the lazy option to if statements to determin
		# if using DTR or RTS as the direction pin
		if self.pi_pin:
			pass
		else:
			self.serial.dtr = level
			self.serial.rts = level

	def open(self):
		if self.serial.is_open:
			# raise Exception('SeroSerial::open() ... Oops, port is already open')
			return

		self.serial.open()

		self.setRTS(self.DD_WRITE)
		if self.serial.isOpen():
			print('Opened {} @ {}'.format(self.serial.name, self.serial.baudrate))
			# print(self.serial.get_settings())
		else:
			raise Exception('Could not open {}'.format(self.serial.port))

	@staticmethod
	def decode(buff):
		"""
		Transforms the raw buffer data read in into a list of bytes

		does serial.to_bypes() do the same thing?
		"""
		# print('>>>', buff)
		# pp = list(map(ord, buff))
		pp = list(bytearray(buff))
		if 0 == len(pp) == 1:
			pp = []
		return pp

	def read(self, how_much=128):  # FIXME: 128 might be too much ... what is largest?
		"""
		This toggles the RTS pin and reads in data. It also converts the buffer
		back into a list of bytes and searches through the list to find valid
		packets of info. If there is more than one packet, this returns an
		array of valid packets.
		"""
		self.setRTS(self.DD_READ)

		data = self.serial.read(how_much)
		# print('read() data', data, 'len(data)', len(data))
		if data:
			# print('>>', data)
			data = self.decode(data)
			# print('decode', data)
			# ret = Packet.findPkt(data)
			# print('ret', ret)
		else:
			# data = []
			data = None
		return data

	def write(self, pkt):
		"""
		This is a simple serial write command. It toggles the RTS pin and formats
		all of the data into bytes before it writes.

		in:
			pkt - array of bytes to send: [2,3,4]
		return:
			number of bytes written to serial port
		"""
		self.setRTS(self.DD_WRITE)
		self.serial.flushInput()
		# prep data array for transmition
		pkt = bytearray(pkt)
		pkt = bytes(pkt)

		num = self.serial.write(pkt)
		# self.serial.flush()
		# print('wrote {} of len(pkt) = {}'.format(num, len(pkt)))
		return num

	def sendPkt(self, pkt, retry=5, sleep_time=0.01):
		"""
		Sends a packet and waits for a return. If no return is given, then it
		resends the packet. If an error occurs, it also resends the packet.

		in:
			pkt - command packet to send to servo
			retry - how many retries should this do? default = 5
		return:
			None or response packet
		"""
		# for cnt in range(retry):
		# 	# self.serial.flushInput()
		# 	self.write(pkt)  # send packet to servo
		# 	ans = self.read()  # get return status packet
		#
		# 	if ans:
		# 		# check for error and resend
		# 		return ans
		#
		# 	else:
		# 		# print('>> retry {} <<'.format(cnt))
		# 		time.sleep(sleep_time)
		#
		# return None
		ans = None
		while retry:
			# print('wrote', retry)
			self.write(pkt)  # send packet to servo
			time.sleep(0.001)  # need to wait some time between read/write
			ans = self.read()  # get return status packet

			if ans:
				break

			time.sleep(sleep_time)
			retry -= 1

		return ans

	def close(self):
		"""
		If the serial port is open, it closes it.
		"""
		if self.serial.is_open:
			self.serial.close()

	# def flushInput(self):
	# 	"""
	# 	Flush the input.
	# 	"""
	# 	self.serial.flushInput()
