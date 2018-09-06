from __future__ import print_function
import web
import os
import sys
import re

NAME_RE = re.compile(r'[a-zA-Z_][-a-zA-Z0-9_.]+')

DEBUG=False

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class UserPlugin:
    def __init__(self, igor):
        self.igor = igor
    
    def index(self, token=None):
        raise web.notfound()
    
    def add(self, token=None, username=None, password=None, returnTo=None):
        if True:
                identifiers = token.getIdentifiers()
                print('\tuser: add: Tokens:')
                for i in identifiers:
                    print('\t\t%s' % i)

        if not NAME_RE.match(username):
            raise myWebError('400 Illegal name for user')
        if self.igor.databaseAccessor.get_key('identities/%s' % username, 'application/x-python-object', 'multi', token):
            raise myWebError('400 user already exists')
        # Create identities item
        self.igor.databaseAccessor.put_key('identities/%s' % username, 'text/plain', 'ref', '', 'text/plain', token, replace=True)
        # Create people item
        self.igor.databaseAccessor.put_key('people/%s' % username, 'text/plain', 'ref', '', 'text/plain', token, replace=True)
        # Create password
        self.igor.internal.accessControl('setUserPassword', token=token, username=username, password=password)
        # Create capabilities
        self.igor.internal.accessControl('newToken', 
            token=token, 
            tokenId='admin-data',
            newOwner='identities/%s' % username, 
            newPath='/data/identities/%s' % username,
            get='descendant-or-self', 
            put='descendant', 
            post='descendant', 
            delete='descendant',
            delegate=True)
        self.igor.internal.accessControl('newToken', 
            token=token, 
            tokenId='admin-data',
            newOwner='identities/%s' % username, 
            newPath='/data/people/%s' % username, 
            put='descendant', 
            post='descendant', 
            delete='descendant',
            delegate=True)
        self.igor.internal.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
        
    def delete(self, token=None, username=None, returnTo=None):
        if True:
                identifiers = token.getIdentifiers()
                print('\tuser: delete: Tokens:')
                for i in identifiers:
                    print('\t\t%s' % i)
        if not NAME_RE.match(username):
            raise myWebError('400 Illegal name for user')
        if not self.igor.databaseAccessor.get_key('identities/%s' % username, 'application/x-python-object', 'multi', token):
            raise myWebError('404 user %s does not exist' % username)
        self.igor.databaseAccessor.delete_key('people/%s' % username, token)
        # delete or save all capabilities
        # xxxjack to be implemented...
        self.igor.databaseAccessor.delete_key('identities/%s' % username, token)
        self.igor.internal.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
        
    def password(self, token=None, username=None, password=None, returnTo=None):
        if not NAME_RE.match(username):
            raise myWebError('400 Illegal name for user')
        if not self.igor.databaseAccessor.get_key('identities/%s' % username, 'application/x-python-object', 'multi', token):
            raise myWebError('404 user %s does not exist' % username)
        self.igor.internal.accessControl('setUserPassword', token=token, username=username, password=password)
        self.igor.internal.save(token)
        if returnTo:
            raise web.seeother(returnTo)
        return ''
    

def igorPlugin(igor, pluginName, pluginData):
    return UserPlugin(igor)
    
