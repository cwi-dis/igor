from __future__ import print_function
from __future__ import unicode_literals
# BLE iBeaconScanner based on https://github.com/adamf/BLE/blob/master/ble-scanner.py
from future import standard_library
standard_library.install_aliases()
from builtins import object
DEBUG = False
# BLE scanner based on https://github.com/adamf/BLE/blob/master/ble-scanner.py
# BLE scanner, based on https://code.google.com/p/pybluez/source/browse/trunk/examples/advanced/inquiry-with-rssi.py

# https://github.com/pauloborges/bluez/blob/master/tools/hcitool.c for lescan
# https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/5.6/lib/hci.h for opcodes
# https://github.com/pauloborges/bluez/blob/master/lib/hci.c#L2782 for functions used by lescan

# performs a simple device inquiry, and returns a list of ble advertizements 
# discovered device

# NOTE: Python's struct.pack() will add padding bytes unless you make the endianness explicit. Little endian
# should be used for BLE. Always start a struct.pack() format string with "<"

import os
import sys
import struct
import bluetooth._bluetooth as bluez
import bleAdvertisementParser
import pprint
import json
import binascii

LE_META_EVENT = 0x3e
LE_PUBLIC_ADDRESS=0x00
LE_RANDOM_ADDRESS=0x01
LE_SET_SCAN_PARAMETERS_CP_SIZE=7
OGF_LE_CTL=0x08
OCF_LE_SET_SCAN_PARAMETERS=0x000B
OCF_LE_SET_SCAN_ENABLE=0x000C
OCF_LE_CREATE_CONN=0x000D

LE_ROLE_MASTER = 0x00
LE_ROLE_SLAVE = 0x01

# these are actually subevents of LE_META_EVENT
EVT_LE_CONN_COMPLETE=0x01
EVT_LE_ADVERTISING_REPORT=0x02
EVT_LE_CONN_UPDATE_COMPLETE=0x03
EVT_LE_READ_REMOTE_USED_FEATURES_COMPLETE=0x04

# Advertisment event types
ADV_IND=0x00
ADV_DIRECT_IND=0x01
ADV_SCAN_IND=0x02
ADV_NONCONN_IND=0x03
ADV_SCAN_RSP=0x04

def noparser(data):
	return data
	
TYPE_TO_NAME = {
	0x01 : ("ad_flags", noparser),
	0x02 : ("ad_partial_16bit_uuids", noparser),
	0x03 : ("ad_16bit_uuids", noparser),
	0x04 : ("ad_partial_32bit_uuids", noparser),
	0x05 : ("ad_32bit_uuids", noparser),
	0x06 : ("ad_partial_128bit_uuids", noparser),
	0x07 : ("ad_128bit_uuids", noparser),
	0x08 : ("ad_short_name", noparser),
	0x09 : ("ad_full_name",	 noparser),
	0x0a : ("ad_txpower", noparser),
	0x0d : ("ad_device_class", noparser),
	0x0e : ("ad_pairing_hash", noparser),
	0x0f : ("ad_pairing_randomizer", noparser),
	0x10 : ("ad_device_id", noparser),
}
class BleScanner(object):
	def __init__(self):
		self.sock = None
		self.old_filter = None

	def open(self, dev_id):
		self.sock = bluez.hci_open_dev(dev_id)

#	def returnnumberpacket(self, pkt):
#		myInteger = 0
#		multiple = 256
#		for c in pkt:
#			myInteger +=  struct.unpack("B",c)[0] * multiple
#			multiple = 1
#		return myInteger 
# 
#	def returnstringpacket(self, pkt):
#		myString = "";
#		for c in pkt:
#			myString +=	 "%02x" %struct.unpack("B",c)[0]
#		return myString 

	def printpacket(self, pkt):
		for c in pkt:
			sys.stdout.write("%02x " % struct.unpack("B",c)[0])
		sys.stdout.write(repr(pkt)+ ' ')

	def get_packed_bdaddr(self, bdaddr_string):
		packable_addr = []
		addr = bdaddr_string.split(':')
		addr.reverse()
		for b in addr: 
			packable_addr.append(int(b, 16))
		return struct.pack("<BBBBBB", *packable_addr)

	def packed_bdaddr_to_string(self, bdaddr_packed):
		return ':'.join('%02x'%i for i in struct.unpack("<BBBBBB", bdaddr_packed[::-1]))

	def hci_enable_le_scan(self):
		self.hci_toggle_le_scan(0x01)

	def hci_disable_le_scan(self):
		self.hci_toggle_le_scan( 0x00)

	def hci_toggle_le_scan(self, enable):
		cmd_pkt = struct.pack("<BB", enable, 0x00)
		bluez.hci_send_cmd(self.sock, OGF_LE_CTL, OCF_LE_SET_SCAN_ENABLE, cmd_pkt)

	def hci_le_set_scan_parameters(self):
		old_filter = self.sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

	def enable_filter(self):
		assert not self.old_filter
		self.old_filter = self.sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

		# perform a device inquiry on bluetooth device #0
		# The inquiry should last 8 * 1.28 = 10.24 seconds
		# before the inquiry is performed, bluez should flush its cache of
		# previously discovered devices
		flt = bluez.hci_filter_new()
		bluez.hci_filter_all_events(flt)
		bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
		self.sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )
	
	def disable_filter(self):
		assert self.old_filter
		self.sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, self.old_filter )
		self.old_filter = None
	
	def parse_advertisement(self):
		while True:
			pkt = self.sock.recv(255)
			ptype, event, plen = struct.unpack("BBB", pkt[:3])
			assert ptype == bluez.HCI_EVENT_PKT # We are filtering for those only, so complain if we get anything else.
			if DEBUG: print("-------------- received", ptype, event, plen) 
			if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
					if DEBUG: print("was event EVT_INQUIRY_RESULT_WITH_RSSI")
			elif event == bluez.EVT_NUM_COMP_PKTS:
					if DEBUG: print("was event EVT_NUM_COMP_PKTS")
			elif event == bluez.EVT_DISCONN_COMPLETE:
					if DEBUG: print("was event EVT_DISCONN_COMPLETE")
					return None
			elif event == LE_META_EVENT:
				subevent, = struct.unpack("<B", pkt[3:4])
				if DEBUG: print("-------------- subevent", subevent)
				pkt = pkt[4:]
				if subevent == EVT_LE_CONN_COMPLETE:
					pass # self.le_handle_connection_complete(pkt)
				elif subevent == EVT_LE_ADVERTISING_REPORT:
					num_reports, = struct.unpack("<B", pkt[0:1])
					pkt = pkt[1:]
					if DEBUG: print("-------------- numreports", num_reports)
					assert num_reports == 1
					while num_reports > 0:
						num_reports -= 1
						# See structure le_advertising_info in /usr/include/bluetooth/hci.h
						adv_evt_type, adv_bdaddr_type, adv_length = struct.unpack("<BBxxxxxxB", pkt[:9])
						adv_bdaddr = pkt[2:8]
						adv_data = pkt[9:9+adv_length]
						# Remove the data from pkt
						pkt = pkt[9+adv_length:]
						# Store in item
						item = dict(
							raw_evt_type=adv_evt_type, 
							raw_bdaddr_type=adv_bdaddr_type, 
							bdaddr=self.packed_bdaddr_to_string(adv_bdaddr)
							)
						item['raw_advertisements'] = binascii.hexlify(adv_data).decode('ascii')
						# If we have one byte left we think it is the rssi, but this is guessed from existing code.
						if len(pkt) == 1:
							rssi, = struct.unpack("<b", pkt)
							item['rssi'] = rssi
						# We don't understand raw_event_type, it seems to be a bluez-ism. only keep if non-zero.
						if adv_evt_type == 0:
						    del item['raw_evt_type']
						# Now try to parse things, and replace the raw data if successful
						if adv_bdaddr_type in (LE_PUBLIC_ADDRESS, LE_RANDOM_ADDRESS):
							del item['raw_bdaddr_type']
							item['bdaddr_type'] = 'public' if adv_bdaddr_type == LE_PUBLIC_ADDRESS else 'random'
						# And parse the advertisement data
						advertisements, allCorrect = bleAdvertisementParser.parse_payload(adv_data)
						if advertisements:
						    item['advertisements'] = advertisements
						    sergioSeesTheLight = False
						    if allCorrect and sergioSeesTheLight:
						        del item['raw_advertisements']
						return item
				else:
					if DEBUG: print("was subevent", subevent)
			else:
				if DEBUG: print("was event", event)

def main():
	scanner = BleScanner()
	scanner.open(0)
	scanner.hci_le_set_scan_parameters()
	scanner.hci_enable_le_scan()
	scanner.enable_filter()
	try:
		while True:
			evt = scanner.parse_advertisement()
			print(evt)
			#print json.dumps(evt)
	finally:
		scanner.disable_filter()
		scanner.hci_disable_le_scan()

if __name__ == '__main__':
	main()
	
