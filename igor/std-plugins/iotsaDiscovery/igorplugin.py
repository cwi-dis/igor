"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os
import iotsaControl
import json
import urllib

from builtins import object
class IotsaDiscoveryPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        self.wifi = iotsaControl.api.IotsaWifi()
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
        
    def findNetworks(self, returnTo=None, token=None):
        rv = self.wifi.findNetworks()
        if returnTo:
            queryString = urllib.parse.urlencode(dict(networks='/'.join(rv)))
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            return self.igor.app.raiseSeeother(returnTo)
        return json.dumps(rv)
    
    def findDevices(self, returnTo=None, token=None):
        rv = self.wifi.findDevices()
        if returnTo:
            queryString = urllib.parse.urlencode(dict(devices='/'.join(rv)))
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            return self.igor.app.raiseSeeother(returnTo)
        return json.dumps(rv)
        
    def getorset(self, device, protocol=None, port=None, module="config", noverify=False, token=None, returnTo=None, **kwargs):
        handler = iotsaControl.api.IotsaDevice(
            device, 
            protocol=(protocol if protocol else 'https'), 
            port=(int(port) if port else None), 
            noverify=(not not noverify)
            )
        # xxxjack need to call setBearerToken() with token for this device, if needed.
        accessor = iotsaControl.api.IotsaConfig(handler, module)
        accessor.load()
        rv = accessor.status
        if kwargs:
            for k, v in kwargs.items():
                accessor.set(k, v)
            try:
                accessor.save()
            except iotsaControl.api.UserIntervention as e:
                rv['message'] = str(e)
        rv['device'] = device
        rv['module'] = module
        if protocol:
            rv['protocol'] = protocol
        if returnTo:
            for k in rv.keys():
                if isinstance(rv[k], list) and rv[k] and isinstance(rv[k][0], str):
                    rv[k] = '/'.join(rv[k])
                else:
                    rv[k] = str(rv[k])
            queryString = urllib.parse.urlencode(rv)
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            return self.igor.app.raiseSeeother(returnTo)
        return json.dumps(rv)
        
def igorPlugin(igor, pluginName, pluginData):
    return IotsaDiscoveryPlugin(igor, pluginName, pluginData)
