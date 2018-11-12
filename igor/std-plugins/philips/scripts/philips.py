#!/usr/bin/python
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import socket
import struct
import select
import json
import urllib.request, urllib.parse, urllib.error
import sys

DEBUG=False

ORDER = [
    ('192', '168', '1'),
    ('10', '0', '1'),
    ('10', '0', '2')
    ]

JOINTSPACE_PORT=1925
VOODOO_PORT=2323
VOODOO_VERSION=0x03010401
VPMT_DISCOVER=1

VOODOO_DISCOVER = struct.pack('<l28xll16s96s96s96s', VOODOO_VERSION, VPMT_DISCOVER, 0, '1234567890123456', 'Python Control', 'Jack', 'Philips.py')

class JointSpaceRemote(object):
    def __init__(self, ipaddr=None):
        self.tv = None
        
    def connect(self):
        while not self.tv:
            self.tv = self.findTV()
            if self.tv:
                break
            if DEBUG: print("TV not found, is it turned on?'")
            return False
        return True
        
    def findTV(self, ipaddr=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
        sock.bind(('', VOODOO_PORT))
        if ipaddr:
            sock.sendto(VOODOO_DISCOVER, (ipaddr, VOODOO_PORT))
        else:
            sock.sendto(VOODOO_DISCOVER, ('<broadcast>', VOODOO_PORT))
        while True:
            result = select.select([sock], [], [], 5)
            if sock in result[0]:
                msg, sender = sock.recvfrom(2000)
                if DEBUG: print('Got message from', sender[0])
                myHostName = socket.gethostname()
                if not '.' in myHostName:
                    myHostName = myHostName + '.local'
                if not sender[0] in socket.gethostbyname_ex(myHostName)[2]:
                    # It is not our own message. It must be the Philips TV.
                    return sender[0]
            else:
                break
        return None
    
    def getData(self, path):
        assert self.tv
        url = 'http://%s:1925/1/%s' % (self.tv, path)
        if DEBUG: print('GET', url)
        data = urllib.request.urlopen(url).read()
        ##print 'RAW', data
        data = json.loads(data)
        ##print 'DECODED', data
        return data
    
    def putData(self, path, data):
        assert self.tv
        url = 'http://%s:1925/1/%s' % (self.tv, path)
        data = json.dumps(data)
        if DEBUG: print('POST %s DATA %s' % (url, data))
        data = urllib.request.urlopen(url, data).read()
        if data:
            if DEBUG: print('PUTDATA RETURNED', data)
        
    def curWatching(self):
        assert self.tv
        data = self.getData('sources/current')
        source = data['id']
        if source == 'tv':
            chanID = self.getData('channels/current')['id']
            chanInfo = self.getData('channels/%s' % chanID)
            name = chanInfo['name']
        else:
            names = self.getData('sources')
            name = names[source]['name']
        return source, name
        
    def cmd_sources(self):
        """List available input sources"""
        assert self.tv
        data = self.getData('sources')
        for source, descr in list(data.items()):
            print('%s\t%s' % (source, descr['name']))

    def cmd_channels(self):
        """List available TV channels"""
        assert self.tv
        data = self.getData('channels')
        all = []
        for fingerprint, descr in list(data.items()):
            all.append((int(descr['preset']), descr['name']))
        all.sort()
        for preset, name in all:
            print('%s\t%s' % (preset, name))
    
    def cmd_source(self, source=None):
        """Set to the given input source (or print current source)"""
        assert self.tv
        if source:
            self.putData('sources/current', {'id' : source })
        else:
            data = self.getData('sources/current')
            print(data['id'])
        
    def cmd_channel(self, channel=None):
        """Set to the given TV channel, by name, number or ID (or list current channel)"""
        assert self.tv
        if channel:
            data = self.getData('channels')
            for chID, chDescr in list(data.items()):
                if chID == channel or chDescr['preset'] == channel or chDescr['name'] == channel:
                    self.putData('channels/current', { 'id' : chID })
                    self.putData('sources/current', {'id' : 'tv' })
                    return
            print('No such channel: %s' % channel, file=sys.stderr)
        else:
            data = self.getData('channels/current')
            chID = data['id']
            data = self.getData('channels')
            print('%s\t%s' % (data[chID]['preset'], data[chID]['name']))
    
    def cmd_volume(self, volume=None):
        """Change volume on the TV"""
        assert self.tv
        if volume is None:
            data = self.getData('audio/volume')
            muted = ' (muted)' if data['muted'] else ''
            print('%d%s' % (data['current'], muted))
        else:
            volume = int(volume)
            self.putData('audio/volume', { 'muted' : False, 'current' : volume })
            
    def cmd_json(self, data=None):
        """Return all data as a JSON object"""
        if data is None:
            data = {}
            volumeData = self.getData('audio/volume')
            data['volume'] = volumeData['current']
            data['muted'] = volumeData['muted']
            data['source'] = self.getData('sources/current')['id']
            data['power'] = True
            data['ip-address'] = self.tv
            data['url'] = 'http://%s:1925/1/' % (self.tv)
        else:
            jData = json.loads(data)
            assert 0
        print(json.dumps(data))
            

    def cmd_help(self):
        """List available commands"""
        for name in dir(self):
            if name[:4] == 'cmd_':
                method = getattr(self, name)
                doc = method.__doc__
                print('%s\t%s' % (name[4:], doc))
                
def main():
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        global DEBUG
        DEBUG=True
        del sys.argv[1]
    tv = JointSpaceRemote()
    if not tv.connect():
        if len(sys.argv) == 2 and sys.argv[1] == 'json':
            print('{"power":false}')
            sys.exit(0)
        print("TV not found, is it turned on?", file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) <= 1:
        print(tv.curWatching())
    else:
        cmdName = 'cmd_' + sys.argv[1]
        if not hasattr(tv, cmdName):
            print('Unknown command: %s. Use help for help' % sys.argv[1], file=sys.stderr)
            sys.exit(2)
        cmd = getattr(tv, cmdName)
        cmd(*sys.argv[2:])

if __name__ == '__main__':
    main()
