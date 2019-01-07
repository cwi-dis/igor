"""Copy values or subtrees, either locally or remotely.

Currently a quick hack using either direct database access or httplib2, synchronously.
Should use callUrl, so local/remote becomes similar, and some form
of callback mechanism so it can run asynchronously.
"""
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import requests
import json
import urllib.parse
import urllib.request, urllib.parse, urllib.error
from fitbit import Fitbit
import oauthlib.oauth2.rfc6749.errors
from requests.packages import urllib3
urllib3.disable_warnings()
import os
import sys
import traceback

DEBUG=False

KEYS_PER_APP=['client_id', 'client_secret']
KEYS_PER_USER = ['access_token', 'refresh_token']
DEFAULT_METHODS=['get_bodyweight']

class FitbitPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        self.user = None
        self.token = None
        
    def _refresh(self, tokenData):
        if DEBUG: print('xxxjack fitbit._refresh for user %s: tokenData=%s' % (self.user, repr(tokenData)))
        self.igor.databaseAccessor.put_key('identities/%s/plugindata/%s/token' % (self.user, self.pluginName), 'application/x-python-object', None, tokenData, 'application/x-python-object', self.token, replace=True)
        self.igor.internal.queue('save', self.token)
        if DEBUG: print('xxxjack queued save call')
    
    def index(self, user=None, userData={}, methods=None, token=None, callerToken=None, **kwargs):
        """Main entry point - get Fitbit data for a single user"""
        if not user:
            self.igor.app.raiseHTTPError("400 Fitbitplugin requires user argument")
        self.user = user
        self.token = token
        if not 'token' in userData:
            self.igor.app.raiseHTTPError("403 Fitbitplugin requires 'token' plugindata for user '%s'" % user)
        oauthSettings = userData['token']
        for k in KEYS_PER_USER:
            if not k in oauthSettings:
                self.igor.app.raiseHTTPError("403 Fitbitplugin 'token' plugindata for user '%s' misses '%s'" % (user, k))
        for k in KEYS_PER_APP:
            if not k in self.pluginData:
                self.igor.app.raiseHTTPError("403 Fitbitplugin requires global plugindata '%s'" % k)
            oauthSettings[k] = self.pluginData[k]
        
        fb = Fitbit(refresh_cb=self._refresh, **oauthSettings)
    
        # Populate kwargs from userData, unless already specified in the parameters
        for k, v in list(userData.items()):
            if k != 'token' and k != 'methods' and not k in kwargs:
                kwargs[k] = v
        # Convert to strings (fitbit library doesn't like unicode)
        for k, v in list(kwargs.items()):
            kwargs[k] = v
            
        results = {}
        if methods == None:
            methods = userData.get('methods', 'get_bodyweight')
        methods = methods.split(',')
        for method in methods:
            if DEBUG: print('xxxjack calling method', method, 'with', kwargs)
            m = getattr(fb, method)
            try:
                item = m(**kwargs)
            except oauthlib.oauth2.rfc6749.errors.OAuth2Error as ex:
                descr = ex.description
                if not descr:
                    descr = str(ex)
                self.igor.app.raiseHTTPError("502 Fitbit OAuth2 error: %s" % descr)
            except Exception as ex:
                print('Exception in fitbit.%s with args %s' % (method, repr(kwargs)))
                traceback.print_exc(file=sys.stdout)
                self.igor.app.raiseHTTPError("502 fitbit error %s" % repr(ex))
            if DEBUG: print("xxxjack method", method, "returned", m)
            results.update(item)
        
        self.igor.databaseAccessor.put_key('sensors/%s/%s' % (self.pluginName, user), 'application/x-python-object', None, results, 'application/x-python-object', token, replace=True)
        return str(results)
    
    def auth1(self, user=None, userData=None, token=None, callerToken=None, **kwargs):
        """OAuth2 entry point 1 - start with authentication sequence, redirect user's browser to Fitbit site"""
        if not user:
            self.igor.app.raiseHTTPError("401 fitbitplugin/auth1 requires 'user' argument")
        if not isinstance(userData, dict):
            self.igor.app.raiseHTTPError('401 Element /data/identities/%s/plugindata/%s/token is missing' % (self.user, self.pluginName))
        oauthSettings = {}
        for k in KEYS_PER_APP:
            if not k in self.pluginData:
                self.igor.app.raiseHTTPError("401 fitbitplugin/auth1 requires global plugindata '%s'" % k)
            oauthSettings[k] = self.pluginData[k]
    
        
        fb = Fitbit(**oauthSettings)
    
        step2url = self.igor.databaseAccessor.get_key('services/igor/url', 'text/plain', 'content', token)
        step2url = urllib.parse.urljoin(step2url, '/plugin/%s/auth2' % self.pluginName)
        #step2url += '?' + urllib.urlencode(dict(user=user))
        redirectUrl, _ = fb.client.authorize_token_url(redirect_uri=step2url, state=user)
        return self.igor.app.raiseSeeother(redirectUrl)
    
    def auth2(self, code=None, state=None, token=None, callerToken=None, **kwargs):
        """Oatth2 entry point 2 - return data from Fitbit site via the user's browser"""
        oauthSettings = {}
        self.user = state
        self.token = token
        for k in KEYS_PER_APP:
            if not k in self.pluginData:
                self.igor.app.raiseHTTPError("401 fitbitplugin/auth2 requires global plugindata '%s'" % k)
            oauthSettings[k] = self.pluginData[k]

        if not state:
            self.igor.app.raiseHTTPError("401 fitbitplugin/auth2 requires 'state' argument")
        if not code:
            self.igor.app.raiseHTTPError("401 fitbitplugin/auth2 requires 'code' argument")

        step2url = self.igor.databaseAccessor.get_key('services/igor/url', 'text/plain', 'content', token)
        step2url = urllib.parse.urljoin(step2url, '/plugin/%s/auth2' % self.pluginName)

        fb = Fitbit(state=state, redirect_uri=step2url, **oauthSettings)

        fbToken = fb.client.fetch_access_token(code)
        self._refresh(fbToken)
        return 'ok\n'

    def settings(self, client_id='', client_secret='', system='', token=None, callerToken=None, returnTo=None, **kwArgs):
        """Set global settings for fitbit plugin"""
        rv = 'ok\n'
        if client_id:
            rv = self.igor.databaseAccessor.put_key('plugindata/%s/client_id' % self.pluginName, 'text/plain', None, client_id, 'text/plain', token, replace=True)
        if client_secret:
            rv = self.igor.databaseAccessor.put_key('plugindata/%s/client_secret' % self.pluginName, 'text/plain', None, client_secret, 'text/plain', token, replace=True)
        if system:
            rv = self.igor.databaseAccessor.put_key('plugindata/%s/system' % self.pluginName, 'text/plain', None, system, 'text/plain', token, replace=True)
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)
        return rv
        
    def userSettings(self, user=None, delete=False, userData=None, token=None, callerToken=None, returnTo=None, _newName=None, _newValue=None, **kwArgs):
        """Create or delete Fitbit user, or change per-user settings"""
        rv = ''
        if delete:
            rv = self.igor.databaseAccessor.delete_key('identities/%s/plugindata/%s' % (user, self.pluginName))
        else:
            if userData == None:
                # User does not have fitbit data yet. Create.
                userData = {}
                for k, v in kwArgs:
                    userData[k] = v
                if _newName:
                    userData[_newName] = _newValue
                rv = self.igor.databaseAccessor.put_key('identities/%s/plugindata/%s' % (user, self.pluginName), 'text/plain', None, userData, 'application/x-python-object', token)
            elif kwArgs or _newName:
                for k, v in kwArgs.items():
                    rv = self.igor.databaseAccessor.put_key('identities/%s/plugindata/%s/%s' % (user, self.pluginName, k), 'text/plain', None, v, 'text/plain', token, replace=True)
                if _newName:
                    rv = self.igor.databaseAccessor.put_key('identities/%s/plugindata/%s/%s' % (user, self.pluginName, _newName), 'text/plain', None, _newValue, 'text/plain', token, replace=True)
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)
        return rv
            
        
def igorPlugin(igor, pluginName, pluginData):
    return FitbitPlugin(igor, pluginName, pluginData)
    
