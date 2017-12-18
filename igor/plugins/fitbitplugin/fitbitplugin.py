"""Copy values or subtrees, either locally or remotely.

Currently a quick hack using either direct database access or httplib2, synchronously.
Should use callUrl, so local/remote becomes similar, and some form
of callback mechanism so it can run asynchronously.
"""
import requests
import web
import json
import urlparse
import urllib
import fitbit
from requests.packages import urllib3
urllib3.disable_warnings()

DATABASE_ACCESS=None
PLUGINDATA=None
NAME="fitbitplugin"

KEYS_PER_APP=['client_id', 'client_secret']
KEYS_PER_USER = ['access_token', 'refresh_token']
DEFAULT_METHODS=['get_bodyweight']

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

def _refresh(tokenData, user=None):
    if user == None:
        user = PLUGINDATA['user']
    print 'xxxjack fitbitplugin._refresh token', tokenData
    DATABASE_ADDESS.put_key('identities/%s/plugindata/%s/token' % (user, NAME), 'application/x-python-object', None, tokenData, 'application/x-python-object', replace=True)
    
def fitbitplugin(methods='get_bodyweight', **kwargs):
    if kwargs: print 'xxxjack fitbit extra kwargs', kwargs
    if not 'token' in PLUGINDATA:
        raise myWebError("401 Fitbitplugin requires 'token' plugindata for user '%s'" % PLUGINDATA.get('user'))
    oauthSettings = PLUGINDATA['token']
    for k in KEYS_PER_USER:
        if not k in oauthSettings:
            raise myWebError("401 Fitbitplugin 'token' plugindata for user '%s' misses '%s'" % (PLUGINDATA.get('user'), k))
    for k in KEYS_PER_APP:
        if not k in PLUGINDATA:
            raise myWebError("401 Fitbitplugin requires global plugindata '%s'" % k)
        oauthSettings[k] = PLUGINDATA[k]
        
    fb = fitbit.Fitbit(refresh_cb=_refresh, **oauthSettings)
    
    results = {}
    methods = methods.split(',')
    for method in methods:
        m = getattr(fb, method)
        item = m()
        results.update(item)
        
    DATABASE_ACCESS.put_key('sensors/fitbit/%s' % PLUGINDATA['user'], 'application/x-python-object', None, results, 'application/x-python-object', replace=True)
    return 'ok\n'
    
def fitbitplugin_auth1(user=None, **kwargs):
    print 'xxxjack fitbitplugin/auth1 extra kwargs', kwargs, 'PLUGINDATA', PLUGINDATA
    oauthSettings = {}
    for k in KEYS_PER_APP:
        if not k in PLUGINDATA:
            raise myWebError("401 fitbitplugin/auth1 requires global plugindata '%s'" % k)
        oauthSettings[k] = PLUGINDATA[k]
    
    if not user:
        raise myWebError("401 fitbitplugin/auth1 requires 'user' argument")
        
    fb = fitbit.Fitbit(**oauthSettings)
    
    step2url = DATABASE_ACCESS.get_key('services/igor/url', 'text/plain', 'content')
    step2url = urlparse.urljoin(step2url, '/plugin/%s/auth2' % NAME)
    #step2url += '?' + urllib.urlencode(dict(user=user))
    redirectUrl, _ = fb.client.authorize_token_url(redirect_uri=step2url, state=user)
    raise web.seeother(redirectUrl)
    
def fitbitplugin_auth2(code=None, state=None, **kwargs):
    print 'xxxjack fitbitplugin/auth2 extra kwargs', kwargs, 'PLUGINDATA', PLUGINDATA
    oauthSettings = {}
    for k in KEYS_PER_APP:
        if not k in PLUGINDATA:
            raise myWebError("401 fitbitplugin/auth2 requires global plugindata '%s'" % k)
        oauthSettings[k] = PLUGINDATA[k]

    if not state:
        raise myWebError("401 fitbitplugin/auth2 requires 'state' argument")
    if not code:
        raise myWebError("401 fitbitplugin/auth2 requires 'code' argument")

    print 'xxxjack fitbitplugin_auth2 oauthSettings', oauthSettings
    fb = fitbit.Fitbit(**oauthSettings)

    token = fb.client.fetch_access_token(code)
    _refresh(token, user=state)
    return 'ok\n'
