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
        
    def _findNetworks(self, token=None):
        rv = {}
        try:
            rv['networks'] = self.wifi.findNetworks()
        except iotsaControl.api.UserIntervention as e:
            rv['message'] = e
        return rv
    
    def _findDevices(self, token=None):
        rv = {}
        try:
            rv['devices'] = self.wifi.findDevices()
        except iotsaControl.api.UserIntervention as e:
            rv['message'] = e
        return rv
        
    def _getorset(self, device, protocol=None, credentials=None, port=None, module="config", noverify=False, token=None, returnTo=None, reboot=None, _name=None, _value=None, **kwargs):
        #
        # Get a handle on the device
        #
        handler = self._getHandler(device, protocol, credentials, port, noverify, token)
        #
        # Get a handle on the module
        #
        accessor = iotsaControl.api.IotsaConfig(handler, module)
        accessor.load()
        rv = {module : accessor.status}
        if _name:
            kwargs[_name] = _value
        if kwargs or reboot:
            for k, v in kwargs.items():
                accessor.set(k, v)
            if reboot:
                accessor.set('reboot', True)
            try:
                returned = accessor.save()
                if isinstance(returned, dict):
                    for k, v in returned.items():
                        rv[k] = v
            except iotsaControl.api.UserIntervention as e:
                rv['message'] = str(e)
        rv['device'] = device
        rv['module'] = module
        return rv
        
    def getorset(self, *args, returnTo=None, **kwargs):
        rv = self._getorset(*args, **kwargs)
        return self._returnOrSeeother(rv, returnTo)
        
    def pull(self, device, protocol=None, credentials=None, port=None, module="config", noverify=False, token=None, returnTo=None):
        handler = self._getHandler(device, protocol, credentials, port, noverify, token)
        modules = module.split('/')
        key = 'devices/%s/%s' % (self.pluginName, device)
        # Create the entry if it doesn't exist yet
        try:
            _ = self.igor.databaseAccessor.get_key(key, 'application/x-python-object', None, token)
        except self.igor.app.getHTTPError():
            self.igor.databaseAccessor.put_key(key, 'text/plain', None, '', 'text/plain', token)
        # Fill it will all module info requested.
        for mod in modules:
            #
            # Get a handle on the module
            #
            accessor = iotsaControl.api.IotsaConfig(handler, mod)
            accessor.load()
            data = accessor.status
            modKey = key + '/' + mod
            self.igor.databaseAccessor.put_key(modKey, 'text/plain', None, data, 'application/x-python-object', token)
        rv = {}
        return self._returnOrSeeother(rv, returnTo)
            
    def push(self, device, protocol=None, credentials=None, port=None, module="config", noverify=False, token=None, returnTo=None):
        handler = self._getHandler(device, protocol, credentials, port, noverify, token)
        key = 'devices/%s/%s/%s' % (self.pluginName, device, module)
        #
        # Get a handle on the module
        #
        accessor = iotsaControl.api.IotsaConfig(handler, module)
        accessor.load()
        newdata = self.igor.databaseAccessor.get_key(key, 'application/x-python-object', None, token)
        if not isinstance(newdata, dict):
            self.igor.app.raiseHTTPError("500 data for %s is not in correct form" % key)
        for k, v in newdata.items():
            accessor.status[k] = v
            try:
                accessor.save()
            except iotsaControl.api.UserIntervention as e:
                rv['message'] = str(e)
        return self._returnOrSeeother(rv, returnTo)
                    
    def _getHandler(self, device, protocol, credentials, port, noverify, token=None):
        """Return a handler for this device"""
        #
        # Persist settings for protocol, credentials, port, noverify for one device
        #
        sessionItem = self.igor.app.getSessionItem('iotsaDiscovery', {})
        if sessionItem.get('device', None) != device:
            sessionItem = {}
        sessionItem['device'] = device
        if protocol:
            sessionItem['protocol'] = protocol
        else:
            protocol = sessionItem.get('protocol')
        if credentials:
            sessionItem['credentials'] = credentials
        else:
            credentials = sessionItem.get('credentials')
        if port:
            sessionItem['port'] = port
        else:
            port = sessionItem.get('port')
        if noverify:
            sessionItem['noverify'] = noverify
        else:
            noverify = sessionItem.get('noverify')
        self.igor.app.setSessionItem('iotsaDiscovery', sessionItem)
        handler = iotsaControl.api.IotsaDevice(
            device, 
            protocol=(protocol if protocol else 'https'), 
            port=(int(port) if port else None), 
            noverify=(not not noverify)
            )
        # xxxjack need to call setBearerToken() with token for this device, if needed.
        if credentials:
            username, password = credentials.split(':')
            handler.setLogin(username, password)
        return handler
        
    def _returnOrSeeother(self, rv, returnTo):
        """Either return a JSON object or pass it to seeother as a query"""
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
