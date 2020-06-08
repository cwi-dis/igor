from . import blescan
import igorServlet
import copy
import json
import threading
import sys
import time

AVAILABLE_TIMEOUT=30   # A device is marked unavailable if it hasn't been seen for 30 seconds
DELETE_TIMEOUT=120     # A device is removed if it hasn't been seen for 2 minutes

KEYS=['available', 'lastSeen', 'firstSeen', 'rssi']

urls=(
    '/ble', 'getBLEdata',
    )

class BleScanServer(threading.Thread):

    def __init__(self, **servletArgs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.initScanner()
        self.initServer(servletArgs)
        self.devices = {}
        self.lock = threading.RLock()
        self.significantChange = False
        print('inited', repr(self))
        
    def initScanner(self):
        self.scanner = blescan.BleScanner()
        self.scanner.open(0)
        self.startScanning()
    
    def startScanning(self):
        self.scanner.hci_le_set_scan_parameters()
        self.scanner.hci_enable_le_scan()
        self.scanner.enable_filter()

    def stopScanning(self):
        self.scanner.disable_filter()
        self.scanner.hci_disable_le_scan()
        
    def uninitScanner(self):
        self.stopScanning()
        self.scanner = None

    def initServer(self, servletArgs):
        self.server = igorServlet.IgorServlet(**servletArgs)
        self.server.addEndpoint('/ble', get=self.GET_bleData)
        self.server.addEndpoint('/ibeacon', get=self.GET_ibeaconData)
        self.server.addEndpoint('/nearable', get=self.GET_nearableData)
        self.server.addEndpoint('/cwi_sensortag', get=self.GET_cwi_sensortagData)

    def startServer(self):
        self.server.start()
        
    def stopServer(self):
        self.server.stop()
        
    def uninitServer(self):
        self.server = None
        
    def run(self):
        #print 'run in', repr(self)
        self.startServer()
        try:
            while True:
                evt = self.scanner.parse_advertisement()
                if not evt:
                    #print 'Restarting scan'
                    self.stopScanning()
                    self.startScanning()
                else:
                    #print 'event', evt
                    self.processEvent(**evt)
        finally:
            #print 'run loop exiting'
            self.uninitScanner()
            self.stopServer()
            self.uninitServer()
            #sys.exit(1)
            
    def processEvent(self, bdaddr=None, **args):
        address = bdaddr
        if not address:
            print('event without address')
            return
        with self.lock:
            args['lastSeen'] = time.time()
            args['available'] = True
            if not address in self.devices:
                # New device, store the data
                self.devices[address] = args
                self.significantChange = True
            else:
                # Old device, update the data
                for k, v in list(args.items()):
                    self.devices[address][k] = v
            if not 'firstSeen' in self.devices[address]:
                # Update timestamp for first time we saw the device (in a sequence)
                self.devices[address]['firstSeen'] = time.time()
        #print 'devices is now', self.devices
            
    def updateDevices(self):
        with self.lock:
            now = time.time()
            toDelete = []
            for address, data in list(self.devices.items()):
                available = data['lastSeen'] > now - AVAILABLE_TIMEOUT
                if available != data['available']:
                    self.significantChange = True
                data['available'] = available
                if not available:
                    if 'firstSeen' in data:
                        del data['firstSeen']
                    # Delete devices not seen for some hours
                    if time.time() - data['lastSeen'] > DELETE_TIMEOUT:
                        toDelete.append(address)
            for address in toDelete:
                del self.devices[address]
            #print 'devices is now', self.devices
                        
    def getDevices(self):
        with self.lock:
            #print 'devices=', repr(self), self.devices
            self.updateDevices()
            self.significantChange = False
            return copy.deepcopy(self.devices)


    def GET_bleData(self, all=True):
        devices = self.getDevices()
        devList = []
        for address, values in list(devices.items()):
            item = {'address':address}
            if all:
                item.update(values)
            else:
                for k in KEYS:
                    if k in values:
                        item[k] = values[k]
            devList.append(item)
        rv = {'bleDevice':devList, 'lastActivity' : time.time()}
        return rv
        
    def GET_cwi_sensortagData(self, all=True):
        devices = self.getDevices()
        devDict = {}
        for address, values in list(devices.items()):
            if not 'advertisements' in values or not 'cwi_sensortag' in values['advertisements']:
                continue
            item = values['advertisements']['cwi_sensortag']
            k = address
            if k in devDict:
                if devDict[k].get('lastSeen') > values.get('lastSeen'):
                    # We already recorded a later reading for this sensor
                    continue
            item['address'] = k
            item['lastSeen'] = values['lastSeen']
            devDict[k] = item
        rv = {'cwi_sensortagDevice':list(devDict.values()), 'lastActivity' : time.time()}
        return rv

    def GET_ibeaconData(self, all=True):
        devices = self.getDevices()
        devDict = {}
        for address, values in list(devices.items()):
            if not 'advertisements' in values or not 'ibeacon' in values['advertisements']:
                continue
            item = values['advertisements']['ibeacon']
            k = item.get('uuid', address)
            if k in devDict:
                if devDict[k].get('lastSeen') > values.get('lastSeen'):
                    # We already recorded a later reading for this sensor
                    continue
            item['lastSeen'] = values['lastSeen']
            devDict[k] = item
        rv = {'ibeaconDevice':list(devDict.values()), 'lastActivity' : time.time()}
        return rv

    def GET_nearableData(self, all=True):
        devices = self.getDevices()
        devDict = {}
        for address, values in list(devices.items()):
            if not 'advertisements' in values or not 'nearable' in values['advertisements']:
                continue
            item = values['advertisements']['nearable']
            k = item.get('uuid', address)
            if k in devDict:
                if devDict[k].get('lastSeen') > values.get('lastSeen'):
                    # We already recorded a later reading for this sensor
                    continue
            item['lastSeen'] = values['lastSeen']
            devDict[k] = item
        rv = {'nearableDevice':list(devDict.values()), 'lastActivity' : time.time()}
        return rv

    
