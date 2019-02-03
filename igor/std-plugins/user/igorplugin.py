from __future__ import print_function
from __future__ import unicode_literals
from builtins import object
import os
import sys
import re

NAME_RE = re.compile(r'[a-zA-Z_][-a-zA-Z0-9_.]+')

DEBUG=False

class UserPlugin(object):
    def __init__(self, igor):
        self.igor = igor
    
    def index(self, token=None, callerToken=None):
        raise self.igor.app.raiseNotfound()
    
    def add(self, token=None, callerToken=None, username=None, password=None, returnTo=None):
        if not NAME_RE.match(username):
            self.igor.app.raiseHTTPError('400 Illegal name for user')
        if self.igor.databaseAccessor.get_key('identities/%s' % username, 'application/x-python-object', 'multi', callerToken):
            self.igor.app.raiseHTTPError('400 user already exists')
        # Create identities item
        self.igor.databaseAccessor.put_key('identities/%s' % username, 'text/plain', 'ref', '', 'text/plain', callerToken, replace=True)
        # Create people item
        self.igor.databaseAccessor.put_key('people/%s' % username, 'text/plain', 'ref', '', 'text/plain', callerToken, replace=True)
        # Create password
        self.igor.internal.accessControl('setUserPassword', token=callerToken, username=username, password=password)
        # Create capabilities
        if self.igor.internal.accessControl('hasCapabilitySupport'):
            self.igor.internal.accessControl('newToken', 
                token=callerToken, 
                tokenId='admin-data',
                newOwner='identities/%s' % username, 
                newPath='/data/identities/%s' % username,
                get='descendant-or-self', 
                put='descendant', 
                post='descendant', 
                delete='descendant',
                delegate=True)
            self.igor.internal.accessControl('newToken', 
                token=callerToken, 
                tokenId='admin-data',
                newOwner='identities/%s' % username, 
                newPath='/data/people/%s' % username, 
                put='descendant', 
                post='descendant', 
                delete='descendant',
                delegate=True)
        self.igor.internal.save(token)
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)
        return ''
        
    def delete(self, token=None, callerToken=None, username=None, returnTo=None):
        if not NAME_RE.match(username):
            self.igor.app.raiseHTTPError('400 Illegal name for user')
        if not self.igor.databaseAccessor.get_key('identities/%s' % username, 'application/x-python-object', 'multi', callerToken):
            self.igor.app.raiseHTTPError('404 user %s does not exist' % username)
        self.igor.databaseAccessor.delete_key('people/%s' % username, callerToken)
        # delete or save all capabilities
        # xxxjack to be implemented...
        self.igor.databaseAccessor.delete_key('identities/%s' % username, callerToken)
        self.igor.internal.save(token)
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)
        return ''
        
    def password(self, token=None, callerToken=None, username=None, password=None, returnTo=None):
        if not NAME_RE.match(username):
            self.igor.app.raiseHTTPError('400 Illegal name for user')
        if not self.igor.databaseAccessor.get_key('identities/%s' % username, 'application/x-python-object', 'multi', callerToken):
            self.igor.app.raiseHTTPError('404 user %s does not exist' % username)
        self.igor.internal.accessControl('setUserPassword', token=callerToken, username=username, password=password)
        self.igor.internal.save(token)
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)
        return ''
    

def igorPlugin(igor, pluginName, pluginData):
    return UserPlugin(igor)
    
