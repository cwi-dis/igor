import web
import os
import sys
import re

NAME_RE = re.compile(r'[a-zA-Z_][-a-zA-Z0-9_.]+')

DEBUG=False

DATABASE_ACCESS=None
PLUGINDATA=None
COMMANDS=None

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class UserPlugin:
    def __init__(self):
        pass
    
    def index(self, token=None):
        raise web.notfound()
    
    def add(self, token=None, name=None, password=None, returnTo=None):
        if not NAME_RE.match(name):
            raise myWebError('400 Illegal name for user')
        if DATABASE_ACCESS.get_key('identities/%s' % name, 'application/x-python-object', 'multi', token):
            raise myWebError('400 user already exists')
        # Create identities item
        DATABASE_ACCESS.put_key('identities/%s' % name, 'text/plain', 'ref', '', 'text/plain', token, replace=True)
        # Create people item
        DATABASE_ACCESS.put_key('people/%s' % name, 'text/plain', 'ref', '', 'text/plain', token, replace=True)
        # Create password
        COMMANDS.accessControl('setUserPassword', token=token, username=name, password=password)
        # Create capabilities
        # xxxjack
        COMMANDS.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
        
    def delete(self, token=None, name=None, returnTo=None):
        if not NAME_RE.match(name):
            raise myWebError('400 Illegal name for user')
        if not DATABASE_ACCESS.get_key('identities/%s' % name, 'application/x-python-object', 'multi', token):
            raise myWebError('404 user %s does not exist' % name)
        DATABASE_ACCESS.delete_key('people/%s' % name, token)
        # xxxjack delete or save all capabilities
        DATABASE_ACCESS.delete_key('identities/%s' % name, token)
        COMMANDS.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
        
    def password(self, token=None, name=None, password=None, returnTo=None):
        if not NAME_RE.match(name):
            raise myWebError('400 Illegal name for user')
        if not DATABASE_ACCESS.get_key('identities/%s' % name, 'application/x-python-object', 'multi', token):
            raise myWebError('404 user %s does not exist' % name)
        COMMANDS.accessControl('setUserPassword', token=token, username=name, password=password)
        COMMANDS.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
    

def igorPlugin(pluginName, pluginData):
    return UserPlugin()
    
