"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os
import dhcpleases
import time

from builtins import object
class DHCPPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
    
    def pull(self, token=None, callerToken=None):
        leaseFile = self.pluginData.get('leaseFile', '/var/lib/dhcp/dhcpd.leases')
        useArp = self.pluginData.get('useArp', True)
        usePing = self.pluginData.get('usePing', True)
        fields = self.pluginData.get('fields', 'client-hostname,hardware,ip-address,alive,arp,ping').split(',')
        
        with open(leaseFile) as fp:
            leases = dhcpleases.parse_leases_file(fp)
        activeLeases = dhcpleases.select_active_leases(leases, dhcpleases.timestamp_now())
        if usePing:
            activeLeases = dhcpleases.test_pingable(activeLeases)
        if useArp:
            activeLeases = dhcpleases.test_arp(activeLeases)
        if fields:
            activeLeases = dhcpleases.filter_keys(activeLeases, fields)

        data = dict(lease=activeLeases, lastActivity=time.time())
        path = 'sensors/%s' % self.pluginName
        rv = self.igor.databaseAccessor.put_key(path, 'application/x-python-object', None, data, 'application/x-python-object', token, replace=True)
        return 'ok\n'

def igorPlugin(igor, pluginName, pluginData):
    return DHCPPlugin(igor, pluginName, pluginData)
