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
    
    def index(self, user=None, userData={}, methods=None, token=None, **kwargs):
        if not user:
            self.igor.app.raiseHTTPError("401 Fitbitplugin requires user argument")
        self.user = user
        self.token = token
        if not 'token' in userData:
            self.igor.app.raiseHTTPError("401 Fitbitplugin requires 'token' plugindata for user '%s'" % user)
        oauthSettings = userData['token']
        for k in KEYS_PER_USER:
            if not k in oauthSettings:
                self.igor.app.raiseHTTPError("401 Fitbitplugin 'token' plugindata for user '%s' misses '%s'" % (user, k))
        for k in KEYS_PER_APP:
            if not k in self.pluginData:
                self.igor.app.raiseHTTPError("401 Fitbitplugin requires global plugindata '%s'" % k)
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
            except Exception as ex:
                print('Exception in fitbit.%s with args %s' % (method, repr(kwargs)))
                traceback.print_exc(file=sys.stdout)
                self.igor.app.raiseHTTPError("501 fitbit error %s" % repr(ex))
            if DEBUG: print("xxxjack method", method, "returned", m)
            results.update(item)
        
        self.igor.databaseAccessor.put_key('sensors/_fitbit/%s' % user, 'application/x-python-object', None, results, 'application/x-python-object', token, replace=True)
        return str(results)
    
    def auth1(self, user=None, userData={}, token=None, **kwargs):
        if not user:
            self.igor.app.raiseHTTPError("401 fitbitplugin/auth1 requires 'user' argument")
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
    
    def auth2(self, code=None, state=None, token=None, **kwargs):
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

def igorPlugin(igor, pluginName, pluginData):
    return FitbitPlugin(igor, pluginName, pluginData)
    
