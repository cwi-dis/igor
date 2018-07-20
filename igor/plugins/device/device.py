import web
import os
import sys
import re
import json

NAME_RE = re.compile(r'[a-zA-Z_][-a-zA-Z0-9_.]+')

DEBUG=False

DATABASE_ACCESS=None
PLUGINDATA=None
COMMANDS=None

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class DevicePlugin:
    def __init__(self):
        pass
    
    def index(self, token=None):
        raise web.notfound()
    
    def add(self, token=None, name=None, description=None, returnTo=None):
        if True:
                identifiers = token._getIdentifiers()
                print '\tdevice: add: Tokens:'
                for i in identifiers:
                    print '\t\t%s' % i

        if not NAME_RE.match(name):
            raise myWebError('400 Illegal name for device')
        if not description:
            description = {}
        elif type(description) != type({}):
            description = json.loads(description)
        if type(description) != type({}):
            raise myWebError('400 description must be dictionary or json object')
        isDevice = description.get('isDevice', False)
        isSensor = description.get('isSensor', False)
        hostname = description.get('hostname', name + '.local')

        if not hostname:
            raise myWebError('400 hostname must be set')
        if isDevice:
            databaseEntry = 'devices/%s' % name
        elif isSensor:
            databaseEntry = 'sensors/%s' % name
        else:
            raise myWebError('400 either isDevice or isSensor must be set')
            
        if DATABASE_ACCESS.get_key(databaseEntry, 'application/x-python-object', 'multi', token):
            raise myWebError('400 %s already exists' % name)
            
        # Create item
        DATABASE_ACCESS.put_key(databaseEntry, 'text/plain', 'ref', '', 'text/plain', token, replace=True)

        rv = {}
        
        if isDevice:
            deviceKey = self._genSecretKey(aud=hostname, token=token)
            rv['sharedKey'] = deviceKey
            deviceTokenId = COMMANDS.accessControl('newToken',
                token=token,
                tokenId='external',
                newOwner='identities/admin',
                newPath=description.get('obj', '/'),
                get='descendant-or-self',
                put='descendant-or-self',
                post='descendant',
                delete='descendant',
                aud=hostname
                )
            rv['deviceTokenId'] = deviceTokenId
        if isSensor:
            actions = description.get('actions', {})
            if actions:
                actionResults = {}
                for actionName in actions.keys():
                    actionData = self._addAction(token, subject=hostname, **actions[actionName])
                    actionResults[actionName] = actionData
                rv['actions'] = actionResults
        if returnTo:
            queryString = urllib.urlencode(rv)
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            raise web.seeother(returnTo)
        return json.dumps(rv)

    def _genSecretKey(self, token=None, aud=None, sub=None):
        return COMMANDS.accessControl('createSharedKey', token=token, aud=aud, sub=sub)
                
    def addAction(self, token=None, subject=None, verb='get', obj=None, returnTo=None):
        rv = self._addAction(token, subject, verb, obj)
        if returnTo:
            queryString = urllib.urlencode(rv)
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            raise web.seeother(returnTo)
        return json.dumps(rv)

    def _addAction(self, token=None, subject=None, verb='get', obj=None):
        if not obj:
            raise myWebError('400 missing obj for action')
        if obj.startswith('/action/'):
            parentTokenId = 'admin-action'
        else:
            raise myWebError('400 bad action %s' % obj)
        print 'xxxjack obj', obj
        newTokenId = actionTokenId = COMMANDS.accessControl('newToken',
            token=token,
            tokenId=parentTokenId,
            newOwner='identities/admin',
            newPath=obj,
            delegate=True,
            **{verb : 'self'}
            )
        newTokenRepresentation = COMMANDS.accessControl('exportToken',
            token=token,
            tokenId=newTokenId,
            subject=subject
            )
        return dict(verb=verb, obj=obj, token=newTokenRepresentation)
        
    def delete(self, name, hostname=None, token=None, returnTo=None):
        if not NAME_RE.match(name):
            raise myWebError('400 Illegal name for user')
        if not hostname:
            hostname = name + '.local'
        self._delSecretKey(aud=hostname, token=token)
        self._delSecretKey(sub=hostname, token=token)
        isDevice = not not DATABASE_ACCESS.get_key('devices/%s' % name, 'application/x-python-object', 'multi', token)
        isSensor = not not DATABASE_ACCESS.get_key('sensors/%s' % name, 'application/x-python-object', 'multi', token)
        if not isDevice and not isSensor:
            raise myWebError('404 %s does not exist' % name)
        DATABASE_ACCESS.delete_key('devices/%s' % name, token)
        DATABASE_ACCESS.delete_key('sensors/%s' % name, token)
        DATABASE_ACCESS.delete_key('status/devices/%s' % name, token)
        DATABASE_ACCESS.delete_key('status/sensors/%s' % name, token)
        COMMANDS.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
        
    def _delSecretKey(self, token=None, aud=None, sub=None):
        COMMANDS.accessControl('deleteSharedKey', token=token, aud=aud, sub=sub)
        
    def list(self, token=None):
        allNames = self._getNames('devices/*', token) + self._getNames('sensors/*', token) + self._getNames('status/sensors/*', token) + self._getNames('status/devices/*', token)
        allNames = list(set(allNames))
        allNames.sort()
        print 'xxxjack allnames', allNames
        rv = []
        for name in allNames:
            descr = dict(name=name)
            hostname = None
            representing = None
            if DATABASE.getElements('devices/' + name, 'get', token):
                descr['isDevice'] = True
                hostname = DATABASE.getValue('devices/%s/hostname' % name, token)
                representing = 'devices/' + name
            if DATABASE.getElements('sensors/' + name, 'get', token):
                descr['isSensor'] = True
                hostname = None
                representing = 'sensors/' + name
            if hostname:
                descr['hostname'] = hostname
                
            if DATABASE.getElements('status/devices/' + name, 'get', token):
                descr['status'] = '/data/status/devices/' + name
            elif DATABASE.getElements('status/sensors/' + name, 'get', token):
                descr['status'] = '/data/status/sensors/' + name
            
            if representing:
                actionElements = DATABASE.getElements('actions/action[representing="%s"]' % representing, 'get', token)
                actionPaths = []
                for e in actionElements:
                    actionPaths.append(DATABASE.getXPathForElement(e))
                if actionPaths:
                    descr['actions'] = actionPaths
            rv.append(descr)
        return json.dumps(rv)
            
    def _getNames(self, path, token):
        allElements = DATABASE.getElements(path, 'get', token)
        rv = []
        for e in allElements:
            name = e.tagName
            if ':' in name: continue
            rv.append(name)
        return rv
        
def igorPlugin(pluginName, pluginData):
    return DevicePlugin()
    
