from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import serial
import sys
import argparse
import time
import urllib.request, urllib.parse, urllib.error
import socket

DEBUG=False

DEFAULT_SERIAL='/dev/tty.usbserial-A700ekiO'
DEFAULT_BAUD=57600
DEFAULT_TIMEOUT=0.5

class RFIDReader(object):
    def __init__(self, port, baudrate, timeout):
        if DEBUG: print('opening', port)
        self.port = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        if DEBUG: print('open')
        time.sleep(2)
        
    def scanForCard(self):
        packetStart = '\xaa'
        stationID = '\x00'
        payload = '\x03\x25\x26\x01'
        crc = '\x01' # XOR of stationID and payload
        packetEnd = '\xbb'
        packet = packetStart + stationID + payload + crc + packetEnd
        if DEBUG: print('>>>', repr(packet))
        self.port.write(packet)
        self.port.flush()
        
        card = None
        dataReceived = ''
        while True:
            newData = self.port.readline()
            if DEBUG: print('<<<', repr(newData))
            if not newData:
                break
            dataReceived += newData
        if dataReceived:
            card = self.decodeData(dataReceived)
        return card
        
    def decodeData(self, dataReceived):
        lines = dataReceived.split()
        packet = []
        for line in lines:
            line = line.strip()
            try:
                value = int(line, 16)
            except ValueError:
                return None
            packet.append(value)
        if DEBUG: print('...', repr(packet))
        if not packet:
            return None
        if packet[0] != 0xaa:   # Packet start
            return None
        if packet[-1] != 0xbb:  # Packet end
            return None
        if len(packet) < 10:
            return 0
        # Should test checksum, etc
        if packet[2] != 6:  # Don't know, some kind of flag that there is a card
            return None
        cardID = packet[5:9]
        return ':'.join(['%02.2x' % x for x in cardID])
        
def main():
    global DEBUG
    parser = argparse.ArgumentParser(description="RFID Reader")
    parser.add_argument("-l", "--line", metavar="PORT", help="Serial port", default=DEFAULT_SERIAL)
    parser.add_argument("-b", "--baud", type=int, metavar="BAUD", help="Baud rate", default=DEFAULT_BAUD)
    parser.add_argument("-t", "--timeout", type=float, metavar="TIMEOUT", help="Timeout in seconds", default=0.5)
    parser.add_argument("-s", "--server", action="store_true", help="Run indefinitely")
    parser.add_argument("-q", "--quiet", action="store_true", help="Do not print cards on stdout")
    parser.add_argument("-u", "--url", metavar="URL", help="Send request to URL when new card detected (use %%s for card ID)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print debug output")
    args = parser.parse_args()

    DEBUG=args.verbose
        
    rr = RFIDReader(args.line, args.baud, args.timeout)
    foundCard = False
    lastCard = None
    while True:
        if DEBUG: sys.stdout.flush()
        card = rr.scanForCard()
        if card:
            foundCard = True
            if not args.quiet:
                print(card)
            if card != lastCard:
                lastCard = card
                url = args.url
                if '%' in url:
                    url = url % card
                try:
                    r = urllib.request.urlopen(url)
                    r.read()
                except IOError as arg:
                    print('%s: %s' % (url, arg))
                r = None
        else:
            lastCard = None
        if not args.server:
            break
    if foundCard:
        sys.exit(0)
    else:
        sys.exit(1)
    
if __name__ == '__main__':
    main()
    
