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
    
    def add(self, token=None, username=None, password=None, returnTo=None):
        if not NAME_RE.match(username):
            raise myWebError('400 Illegal name for user')
        if DATABASE_ACCESS.get_key('identities/%s' % username, 'application/x-python-object', 'multi', token):
            raise myWebError('400 user already exists')
        # Create identities item
        DATABASE_ACCESS.put_key('identities/%s' % username, 'text/plain', 'ref', '', 'text/plain', token, replace=True)
        # Create people item
        DATABASE_ACCESS.put_key('people/%s' % username, 'text/plain', 'ref', '', 'text/plain', token, replace=True)
        # Create password
        COMMANDS.accessControl('setUserPassword', token=token, username=username, password=password)
        # Create capabilities
        COMMANDS.accessControl('newToken', 
            token=token, 
            tokenId='admin-data',
            newOwner='identities/%s' % username, 
            newPath='/data/identities/%s' % username,
            get='descendant-or-self', 
            put='descendant', 
            post='descendant', 
            delete='descendant')
        COMMANDS.accessControl('newToken', 
            token=token, 
            tokenId='admin-data',
            newOwner='identities/%s' % username, 
            newPath='/data/people/%s' % username, 
            put='descendant', 
            post='descendant', 
            delete='descendant')
        COMMANDS.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
        
    def delete(self, token=None, username=None, returnTo=None):
        if not NAME_RE.match(username):
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
        
    def password(self, token=None, username=None, password=None, returnTo=None):
        if not NAME_RE.match(username):
            raise myWebError('400 Illegal name for user')
        if not DATABASE_ACCESS.get_key('identities/%s' % username, 'application/x-python-object', 'multi', token):
            raise myWebError('404 user %s does not exist' % username)
        COMMANDS.accessControl('setUserPassword', token=token, username=username, password=password)
        COMMANDS.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
    

def igorPlugin(pluginName, pluginData):
    return UserPlugin()
    
