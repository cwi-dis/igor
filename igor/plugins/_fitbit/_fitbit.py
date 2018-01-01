"""Copy values or subtrees, either locally or remotely.

Currently a quick hack using either direct database access or httplib2, synchronously.
Should use callUrl, so local/remote becomes similar, and some form
of callback mechanism so it can run asynchronously.
"""
print 'xxxjack fitbit plugin'
import requests
import web
import json
import urlparse
import urllib
from fitbit import Fitbit
from requests.packages import urllib3
urllib3.disable_warnings()
import os
import sys

print 'xxxjack fitbit own name, file', __name__, __file__
print 'xxxjack fitbit fitbit name, file', Fitbit.__module__, Fitbit.__module__
#print 'xxxjack cwd', os.getcwd()
#print 'xxxjack path', sys.path

DATABASE_ACCESS=None
PLUGINDATA=None
COMMANDS=None

KEYS_PER_APP=['client_id', 'client_secret']
KEYS_PER_USER = ['access_token', 'refresh_token']
DEFAULT_METHODS=['get_bodyweight']

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class FitbitPlugin:
    def __init__(self, pluginName, pluginData):
        self.pluginName = pluginName
        self.pluginData = pluginData
        self.user = None
        
    def _refresh(self, tokenData):
        print 'xxxjack fitbit._refresh for user %s: tokenData=%s' % (self.user, repr(tokenData))
        DATABASE_ACCESS.put_key('identities/%s/plugindata/%s/token' % (self.user, self.pluginName), 'application/x-python-object', None, tokenData, 'application/x-python-object', replace=True)
        COMMANDS.queue('save')
        print 'xxxjack queued save call'
    
    def index(self, user=None, userData={}, methods=None, **kwargs):
        if not user:
            raise myWebError("401 Fitbitplugin requires user argument")
        self.user = user
        if not 'token' in userData:
            raise myWebError("401 Fitbitplugin requires 'token' plugindata for user '%s'" % user)
        oauthSettings = userData['token']
        for k in KEYS_PER_USER:
            if not k in oauthSettings:
                raise myWebError("401 Fitbitplugin 'token' plugindata for user '%s' misses '%s'" % (user, k))
        for k in KEYS_PER_APP:
            if not k in self.pluginData:
                raise myWebError("401 Fitbitplugin requires global plugindata '%s'" % k)
            oauthSettings[k] = self.pluginData[k]
        
        fb = Fitbit(refresh_cb=self._refresh, **oauthSettings)
    
        # Populate kwargs from userData, unless already specified in the parameters
        for k, v in userData.items():
            if k != 'token' and k != 'methods' and not k in kwargs:
                kwargs[k] = v
        # Convert to strings (fitbit library doesn't like unicode)
        for k, v in kwargs.items():
            kwargs[k] = v
            
        results = {}
        if methods == None:
            methods = userData.get('methods', 'get_bodyweight')
        methods = methods.split(',')
        for method in methods:
            m = getattr(fb, method)
            item = m(**kwargs)
            print "xxxjack method", method, "returned", m
            results.update(item)
        
        DATABASE_ACCESS.put_key('sensors/_fitbit/%s' % user, 'application/x-python-object', None, results, 'application/x-python-object', replace=True)
        return str(results)
    
    def auth1(self, user=None, userData={}, **kwargs):
        if not user:
            raise myWebError("401 fitbitplugin/auth1 requires 'user' argument")
        oauthSettings = {}
        for k in KEYS_PER_APP:
            if not k in self.pluginData:
                raise myWebError("401 fitbitplugin/auth1 requires global plugindata '%s'" % k)
            oauthSettings[k] = self.pluginData[k]
    
        
        fb = Fitbit(**oauthSettings)
    
        step2url = DATABASE_ACCESS.get_key('services/igor/url', 'text/plain', 'content')
        step2url = urlparse.urljoin(step2url, '/plugin/%s/auth2' % self.pluginName)
        #step2url += '?' + urllib.urlencode(dict(user=user))
        redirectUrl, _ = fb.client.authorize_token_url(redirect_uri=step2url, state=user)
        raise web.seeother(redirectUrl)
    
    def auth2(self, code=None, state=None, **kwargs):
        oauthSettings = {}
        self.user = state
        for k in KEYS_PER_APP:
            if not k in self.pluginData:
                raise myWebError("401 fitbitplugin/auth2 requires global plugindata '%s'" % k)
            oauthSettings[k] = self.pluginData[k]

        if not state:
            raise myWebError("401 fitbitplugin/auth2 requires 'state' argument")
        if not code:
            raise myWebError("401 fitbitplugin/auth2 requires 'code' argument")

        step2url = DATABASE_ACCESS.get_key('services/igor/url', 'text/plain', 'content')
        step2url = urlparse.urljoin(step2url, '/plugin/%s/auth2' % self.pluginName)

        fb = Fitbit(state=state, redirect_uri=step2url, **oauthSettings)

        token = fb.client.fetch_access_token(code)
        self._refresh(token)
        return 'ok\n'

def igorPlugin(pluginName, pluginData):
    return FitbitPlugin(pluginName, pluginData)
    
