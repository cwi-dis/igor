"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os
import iotsaControl
import json
import urllib
import socket

from builtins import object
class IotsaDiscoveryPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        self.wifi = iotsaControl.api.IotsaWifi()
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
        
    def _findNetworks(self, token=None, callerToken=None):
        rv = {}
        try:
            rv['networks'] = self.wifi.findNetworks()
        except iotsaControl.api.UserIntervention as e:
            rv['message'] = e
        return rv
    
    def _findDevices(self, token=None, callerToken=None):
        rv = {}
        try:
            rv['devices'] = self.wifi.findDevices()
        except iotsaControl.api.UserIntervention as e:
            rv['message'] = e
        return rv
        
    def _getorset(self, device, protocol=None, credentials=None, port=None, module="config", noverify=False, token=None, callerToken=None, returnTo=None, reboot=None, _name=None, _value=None, includeConfig=False, **kwargs):
        #
        # Get a handle on the device
        #
        handler = self._getHandler(device, protocol, credentials, port, noverify, token)
        #
        # Get a handle on the module
        #
        rv = dict(device=device, module=module)
        accessor = iotsaControl.api.IotsaConfig(handler, module)
        try:
            self._load(accessor)
        except self.igor.app.getHTTPError() as e:
            rv['message'] = self.igor.app.stringFromHTTPError(e)
            return rv
        rv[module] = accessor.status
        #
        # Also load global device config, if wanted
        #
        if includeConfig and module != "config":
            acConfig = iotsaControl.api.IotsaConfig(handler, "config")
            try:
                self._load(acConfig)
            except self.igor.app.getHTTPError() as e:
                return {'message' : self.igor.app.stringFromHTTPError(e)}
            rv['config'] = acConfig.status
        #
        # Set variables, if wanted
        #
        if _name:
            kwargs[_name] = _value
        if kwargs or reboot:
            for k, v in kwargs.items():
                accessor.set(k, v)
            if reboot:
                accessor.set('reboot', True)
            try:
                returned = self._save(accessor)
                if isinstance(returned, dict):
                    for k, v in returned.items():
                        rv[k] = v
            except iotsaControl.api.UserIntervention as e:
                rv['message'] = str(e)
        return rv
        
    def getorset(self, *args, returnTo=None, **kwargs):
        rv = self._getorset(*args, **kwargs)
        return self._returnOrSeeother(rv, returnTo)
        
    def pull(self, device, protocol=None, credentials=None, port=None, module="config", noverify=False, token=None, callerToken=None, returnTo=None):
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
            try:
                self._load(accessor)
                data = accessor.status
            except self.igor.app.getHTTPError() as e:
                data = {'message' : self.igor.app.stringFromHTTPError(e)}
            modKey = key + '/' + mod
            self.igor.databaseAccessor.put_key(modKey, 'text/plain', None, data, 'application/x-python-object', token)
        rv = {}
        return self._returnOrSeeother(rv, returnTo)
            
    def push(self, device, protocol=None, credentials=None, port=None, module="config", noverify=False, token=None, callerToken=None, returnTo=None):
        handler = self._getHandler(device, protocol, credentials, port, noverify, token)
        key = 'devices/%s/%s/%s' % (self.pluginName, device, module)
        #
        # Get a handle on the module
        #
        accessor = iotsaControl.api.IotsaConfig(handler, module)
        self._load(accessor)
        newdata = self.igor.databaseAccessor.get_key(key, 'application/x-python-object', None, token)
        if not isinstance(newdata, dict):
            self.igor.app.raiseHTTPError("500 data for %s is not in correct form" % key)
        for k, v in newdata.items():
            accessor.status[k] = v
        rv = {}
        try:
            returned = self._save(accessor)
            if isinstance(returned, dict):
                for k, v in returned.items():
                    rv[k] = v
        except iotsaControl.api.UserIntervention as e:
            rv['message'] = str(e)
        return self._returnOrSeeother(rv, returnTo)
                    
    def _getHandler(self, device, protocol, credentials, port, noverify, token=None, callerToken=None):
        """Return a handler for this device"""
        #
        # Persist settings for protocol, credentials, port, noverify for one device
        #
        if not device:
            return self.igor.app.raiseHTTPError("400 No device specified")
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
        # Now we try to set either the token or the credentials
        if credentials:
            username, password = credentials.split(':')
            handler.setLogin(username, password)
        else:
            extToken = self.igor.access.externalTokenForHost(device, token)
            if extToken:
                handler.setBearerToken(extToken)
        return handler
        
    def _getpersist(self, device, clearNoverify=False):
        """Get persistent settings for this device"""
        sessionItem = self.igor.app.getSessionItem('iotsaDiscovery', {})
        if sessionItem.get('device', None) != device:
            return None, None, None, None
        if clearNoverify:
            sessionItem['noverify'] = False
            self.igor.app.setSessionItem('iotsaDiscovery', sessionItem)
        rv = sessionItem.get('protocol'), sessionItem.get('credentials'), sessionItem.get('port'), sessionItem.get('noverify')
        return rv
            
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
        
    def _load(self, accessor):
        """Wrapper to return better errors"""
        try:
            return accessor.load()
        except requests.exceptions.SSLError as e:
            return self.igor.app.raiseHTTPError("502 Incorrect certificate or other SSL failure while accessing %s: %s" % (e.request.url, e))
        except requests.exceptions.ConnectionError as e:
            return self.igor.app.raiseHTTPError("502 Cannot connect to %s" % e.request.url)
        except requests.exceptions.Timeout as e:
            return self.igor.app.raiseHTTPError("502 Timeout while connecting to %s" % e.request.url)
        except requests.exceptions.RequestException as e:
            value = str(e)
            if value[:3] == '401':
                # Special case: we forward 401 (access denied) errors as-is
                return self.igor.app.raiseHTTPError(value)
            return self.igor.app.raiseHTTPError("502 Error while accessing %s: %s" % (e.request.url, value))

    def _save(self, accessor):
        """Wrapper to return better errors"""
        try:
            return accessor.save()
        except requests.exceptions.SSLError as e:
            return self.igor.app.raiseHTTPError("502 Incorrect certificate or other SSL failure while accessing %s: %s" % (e.request.url, e))
        except requests.exceptions.ConnectionError as e:
            return self.igor.app.raiseHTTPError("502 Cannot connect to %s" % e.request.url)
        except requests.exceptions.Timeout as e:
            return self.igor.app.raiseHTTPError("502 Timeout while connecting to %s" % e.request.url)
        except requests.exceptions.RequestException as e:
            value = str(e)
            if value[:3] == '401':
                # Special case: we forward 401 (access denied) errors as-is
                return self.igor.app.raiseHTTPError(value)
            return self.igor.app.raiseHTTPError("502 Error while accessing %s: %s" % (e.request.url, value))
            
    def _setIndexed(self, device, module, index, newSettings, protocol=None, credentials=None, port=None, noverify=False, token=None, callerToken=None):
        """Helper for templates: change settings for a single entry for a module that has multiple entries"""
        handler = self._getHandler(device, protocol, credentials, port, noverify, token)
        apiName = "%s/%d" % (module, int(index))
        accessor = iotsaControl.api.IotsaConfig(handler, apiName)
        for k, v in newSettings.items():
            accessor.set(k, v)
        rv = ""
        try:
            _ = self._save(accessor)
        except iotsaControl.api.UserIntervention as e:
            rv = str(e)
        except self.igor.app.getHTTPError() as e:
            rv = self.igor.app.stringFromHTTPError(e)
        return rv
                
    def _getIgorUrl(self, token=None, callerToken=None):
        """Helper for templates: get base URL for this igor, in a iotsa-compatible form.
        This method is a workaround for iotsa currently not being able to handle .local hostnames
        so we convert such a hostname into IP address.
        """
        igorInfo = self.igor.databaseAccessor.get_key('services/igor', 'application/x-python-object', None, token)
        host = igorInfo['host']
        if host.endswith('.local'):
            host = socket.gethostbyname(host)
        return "%s://%s:%s" % (igorInfo['protocol'], host, igorInfo['port'])
        
    def _getIgorFingerprint(self, token=None, callerToken=None):
        """Helper for templates: return the SSL certificate fingerprint for this igor."""
        return self.igor.database.getValue('services/igor/fingerprint', token=token)
        
    def _getActionsForDevice(self, device=None, token=None, callerToken=None):
        """Helper for templates: returns list of action names this device might trigger"""
        list = self.igor.database.getValues('actions/action/name', token=token)
        return [x[1] for x in list]
        
    def _getTokensForDevice(self, device=None, token=None, callerToken=None):
        """Helper for templates: return list of all capabilities valid for this device as subject"""
        descriptions = self.igor.access.tokensForSubject(device, token)
        rv = []
        for desc in descriptions:
            items = []
            for k in ['obj', 'get', 'put', 'post', 'delete']:
                if k in desc:
                    items.append('{}={}'.format(k, desc[k]))
            rv.append((' '.join(items), desc['cid']))
        return rv
        
def igorPlugin(igor, pluginName, pluginData):
    return IotsaDiscoveryPlugin(igor, pluginName, pluginData)
