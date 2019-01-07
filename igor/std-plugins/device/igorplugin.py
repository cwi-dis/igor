from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import os
import sys
import re
import json
import urllib.request, urllib.parse, urllib.error

NAME_RE = re.compile(r'[a-zA-Z_][-a-zA-Z0-9_.]+')

DEBUG=False

class DevicePlugin(object):
    def __init__(self, igor):
        self.igor = igor
        self.hasCapabilities = self.igor.internal.accessControl('hasCapabilitySupport')
    
    def index(self, token=None, callerToken=None):
        raise self.igor.app.raiseNotfound()
    
    def add(self, token=None, callerToken=None, name=None, description=None, returnTo=None, secured=False, **kwargs):
        rv = self._add(callerToken, name, description, **kwargs)
        if returnTo:
            queryString = urllib.parse.urlencode(rv)
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            return self.igor.app.raiseSeeother(returnTo)
        return json.dumps(rv)

    def _add(self, callerToken, name=None, description=None, exportTokens=None, secured=False, **kwargs):
        if not NAME_RE.match(name):
            self.igor.app.raiseHTTPError('400 Illegal name for device')
        if not description:
            description = kwargs
        elif type(description) != type({}):
            description = json.loads(description)
        if type(description) != type({}):
            self.igor.app.raiseHTTPError('400 description must be dictionary or json object')
            
        deviceType = description.get('deviceType', None)
        if not deviceType:
            self.igor.app.raiseHTTPError('400 deviceType missing')
            
        isDevice = deviceType in {'activeDevice', 'activeSensorDevice'}
        isSensor = deviceType in {'activeSensor', 'polledSensor', 'passiveSensor'}
        if not isDevice and not isSensor:
            self.igor.app.raiseHTTPError('400 unknown deviceType %s' % deviceType)
        
        isActive = deviceType in {'activeSensor', 'activeSensorDevice'}
        isPassive = deviceType == 'passiveSensor'
        hasPlugin = not isPassive
        hostname = description.get('hostname', None)
        if not hostname and (isDevice or isActive):
            hostname = name + '.local'

        if isDevice:
            databaseEntry = 'devices/%s' % name
        elif isSensor:
            databaseEntry = 'sensors/%s' % name
        else:
            assert 0
            
        if self.igor.databaseAccessor.get_key(databaseEntry, 'application/x-python-object', 'multi', callerToken):
            self.igor.app.raiseHTTPError('400 %s already exists' % name)
            
        rv = dict(name=name, deviceType=deviceType, isDevice=isDevice, isSensor=isSensor)
        if hostname:
            rv['hostname'] = hostname

        tokenOwner = 'identities/{}'.format(self.igor.app.getSessionItem('user', 'admin'))
        if hasPlugin:
            pluginName = description.get('plugin', '')
            if not pluginName:
                self.igor.app.raiseHTTPError('400 deviceType %s requires plugin' % deviceType)
            msg = self.igor.plugins.installstd(pluginName=name, stdName=pluginName, token=callerToken)
            if msg:
                rv['message'] = msg
            tokenWantedOwner = 'plugindata/{}'.format(pluginName)
        else:
            # Create item
            entryValues = {}
            self.igor.databaseAccessor.put_key(databaseEntry, 'text/plain', 'ref', entryValues, 'application/x-python-object', callerToken, replace=True)
            # Create status item
            self.igor.databaseAccessor.put_key('status/' + databaseEntry, 'text/plain', 'ref', '', 'text/plain', callerToken, replace=True)

        
        if secured and isDevice and self.hasCapabilities:
            deviceKey = self._genSecretKey(callerToken, aud=hostname)
            rv['audSharedKeyId'] = deviceKey
            deviceTokenId = self.igor.internal.accessControl('newToken',
                token=callerToken,
                tokenId='external',
                newOwner=tokenOwner,
                newPath=description.get('obj', '/'),
                get='descendant-or-self',
                put='descendant-or-self',
                post='descendant',
                delete='descendant',
                delegate=True,
                aud=hostname
                )
            rv['deviceTokenId'] = deviceTokenId
            rv['tokenOwner'] = tokenOwner
            if tokenWantedOwner:
                rv['deviceTokenWantedOwner'] = tokenWantedOwner
        if secured and isActive and self.hasCapabilities:
            deviceKey = self._genSecretKey(callerToken, sub=hostname)
            rv['subSharedKeyId'] = deviceKey
            actions = description.get('actions', {})
            if actions:
                actionResults = {}
                for actionName in list(actions.keys()):
                    actionData = self._addActionCap(callerToken, subject=hostname, tokenOwner=tokenOwner, exportTokens=exportTokens, **actions[actionName])
                    actionResults[actionName] = actionData
                rv['actions'] = actionResults
        return rv
        
    def _genSecretKey(self, callerToken, aud=None, sub=None):
        return self.igor.internal.accessControl('createSharedKey', token=callerToken, aud=aud, sub=sub)
                
    def addActionCap(self, callerToken, subject=None, verb='get', obj=None, returnTo=None, tokenOwner=None, exportTokens=False):
        if tokenOwner == None:
            tokenOwner = 'identities/{}'.format(igor.app.getSessionItem('user', 'admin'))
        rv = self._addActionCap(callerToken, subject, verb, obj, tokenOwner, exportTokens)
        rv['tokenOwner'] = tokenOwner
        if returnTo:
            queryString = urllib.parse.urlencode(rv)
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            return self.igor.app.raiseSeeother(returnTo)
        return json.dumps(rv)

    def _addActionCap(self, callerToken, subject=None, verb='get', obj=None, tokenOwner='identities/admin', exportTokens=False):
        if not self.hasCapabilities:
            return{}
        if not obj:
            self.igor.app.raiseHTTPError('400 missing obj for action')
        if obj.startswith('/action/'):
            parentTokenId = 'admin-action'
        else:
            self.igor.app.raiseHTTPError('400 bad action %s' % obj)
        newTokenId = actionTokenId = self.igor.internal.accessControl('newToken',
            token=callerToken,
            tokenId=parentTokenId,
            newOwner=tokenOwner,
            newPath=obj,
            delegate=True,
            **{verb : 'self'}
            )
        rv = dict(verb=verb, obj=obj, actionTokenId=newTokenId)
        if exportTokens:
            newTokenRepresentation = self.igor.internal.accessControl('exportToken',
                token=callerToken,
                tokenId=newTokenId,
                subject=subject
                )
            rv['actionTokenRepresentation'] = newTokenRepresentation
        return rv
                    
    def delete(self, name, hostname=None, token=None, callerToken=None, returnTo=None):
        if not NAME_RE.match(name):
            self.igor.app.raiseHTTPError('400 Illegal name for device')
        if not hostname:
            hostname = name + '.local'
        if self.hasCapabilities:
            self._delSecretKey(callerToken, aud=hostname)
            self._delSecretKey(callerToken, sub=hostname)
        isDevice = not not self.igor.databaseAccessor.get_key('devices/%s' % name, 'application/x-python-object', 'multi', callerToken)
        isSensor = not not self.igor.databaseAccessor.get_key('sensors/%s' % name, 'application/x-python-object', 'multi', callerToken)
        self.igor.databaseAccessor.delete_key('devices/%s' % name, callerToken)
        self.igor.databaseAccessor.delete_key('sensors/%s' % name, callerToken)
        self.igor.databaseAccessor.delete_key('status/devices/%s' % name, callerToken)
        self.igor.databaseAccessor.delete_key('status/sensors/%s' % name, callerToken)
        if self.igor.plugins.exists(name):
            self.igor.plugins.uninstall(name, callerToken)
        self.igor.internal.save(callerToken)
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)
        return ''
        
    def _delSecretKey(self, callerToken, aud=None, sub=None):
        self.igor.internal.accessControl('deleteSharedKey', token=callerToken, aud=aud, sub=sub)
        
    def list(self, token=None, callerToken=None):
        rv = self._list(callerToken)
        return json.dumps(rv)

    def _list(self, callerToken):
        """Return list of dictionaries describing all devices"""
        def _getNames(path):
            """Helper to get all non-namespaced children tag names"""
            allElements = self.igor.database.getElements(path, 'get', callerToken)
            rv = []
            for e in allElements:
                name = e.tagName
                if ':' in name: continue
                rv.append(name)
            return rv
        #
        # Collect all names of devices and sensors tha occur anywhere (sorted)
        #
        allNames = _getNames('devices/*') + _getNames('sensors/*') + _getNames('status/sensors/*') + _getNames('status/devices/*')
        allNames = list(set(allNames))
        allNames.sort()
        #
        # For each of these collect the relevant information
        #
        rv = []
        for name in allNames:
            descr = dict(name=name)
            hostname = None
            representing = None
            entries = []
            statusEntries = []
            if self.igor.database.getElements('devices/' + name, 'get', callerToken):
                descr['isDevice'] = True
                entries.append('devices/' + name)
                representing = 'devices/' + name
            if self.igor.database.getElements('sensors/' + name, 'get', callerToken):
                descr['isSensor'] = True
                entries.append('sensors/' + name)
                representing = 'sensors/' + name
            if self.igor.database.getElements('plugindata/' + name, 'get', callerToken):
                descr['isPlugin'] = True
                entries.append('plugindata/' + name)
                hostname = self.igor.database.getValue('plugindata/%s/host' % name, callerToken)

            if hostname:
                descr['hostname'] = hostname
                
            if self.igor.database.getElements('status/devices/' + name, 'get', callerToken):
                statusEntries.append('status/devices/' + name)
            if self.igor.database.getElements('status/sensors/' + name, 'get', callerToken):
                statusEntries.append('status/sensors/' + name)
            
            descr['entry'] = entries
            descr['status'] = statusEntries
            
            if representing:
                actionElements = self.igor.database.getElements("actions/action[representing='%s']" % representing, 'get', callerToken)
                actionPaths = []
                for e in actionElements:
                    actionPaths.append(self.igor.database.getXPathForElement(e))
                if actionPaths:
                    descr['actions'] = actionPaths
                descr['representing'] = representing

            # See what the type is
            if descr.get('isDevice'):
                if not descr.get('isPlugin'):
                    descr['deviceType'] = 'badDevice (no plugin)'
                else:
                    # We cannot tell difference between activeDevice and activeDeviceSensor.
                    # Could examine actions, but...
                    descr['deviceType'] = 'activeDevice'
            elif descr.get('isSensor'):
                if descr.get('isPlugin'):
                    descr['deviceType'] = 'polledSensor'
                elif descr.get('actionPaths'):
                    descr['deviceType'] = 'activeSensor'
                else:
                    descr['deviceType'] = 'passiveSensor'
            else:
                descr['deviceType'] = 'bad (not Device, not Sensor)'

            rv.append(descr)
        return rv

    def _keyList(self, callerToken):
        """Helper for devices.html"""
        allKeys = self.igor.internal.accessControl(subcommand='getKeyList', token=callerToken)
        allKeysAsTuples = [(k.get('iss', ''), k.get('aud', ''), k.get('sub', '')) for k in allKeys]
        allKeysAsTuples.sort()
        allKeyAudiences = set([k.get('aud') for k in allKeys])
        allKeySubjects = set([k.get('sub') for k in allKeys])
        return dict(allKeysAsTuples=allKeysAsTuples, allKeyAudiences=allKeyAudiences, allKeySubjects=allKeySubjects)
        
            
def igorPlugin(igor, pluginName, pluginData):
    return DevicePlugin(igor)
    
