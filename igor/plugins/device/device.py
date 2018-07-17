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
        if type(description) != type({}):
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
            # xxxx create ssl stuff
            deviceKey = self._genSecretKey(aud=hostname)
            rv['sharedKey'] = deviceKey
            deviceTokenId = COMMANDS.accessControl('newToken',
                token=token,
                tokenId='root',
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

    def _genSecretKey(self, aud=None, sub=None):
        assert 0
                
    def addAction(self, token=None, subject=None, verb='get', obj='/', returnTo=None):
        rv = self._addAction(token, verb, obj)
        if returnTo:
            queryString = urllib.urlencode(rv)
            if '?' in returnTo:
                returnTo = returnTo + '&' + queryString
            else:
                returnTo = returnTo + '?' + queryString
            raise web.seeother(returnTo)
        return json.dumps(rv)

    def _addAction(self, token=None, subject=None, verb='get', obj='/'):
        newTokenId = actionTokenId = COMMANDS.accessControl('newToken',
            token=token,
            tokenId='root',
            newOwner='identities/admin',
            **{verb : 'self'}
            )
        newTokenRepresentation = COMMANDS.accessControl('exportToken',
            token=token,
            tokenId=newTokenId,
            subject=subject
            )
        return dict(verb=verb, obj=obj, token=newTokenRepresentation)
        
    def delete(self, token=None, name, hostname, returnTo=None):
        self._delSecretKey(aud=hostname)
        self._delSecretKey(sub=hostname)
        if not NAME_RE.match(name):
            raise myWebError('400 Illegal name for user')
        if not DATABASE_ACCESS.get_key('identities/%s' % username, 'application/x-python-object', 'multi', token):
            raise myWebError('404 user %s does not exist' % username)
        DATABASE_ACCESS.delete_key('people/%s' % username, token)
        # delete or save all capabilities
        # xxxjack to be implemented...
        DATABASE_ACCESS.delete_key('identities/%s' % username, token)
        COMMANDS.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
        
def igorPlugin(pluginName, pluginData):
    return DevicePlugin()
    
