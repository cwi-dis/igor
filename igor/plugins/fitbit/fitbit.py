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
NAME="fitbit"

KEYS_PER_APP=['client_id', 'client_secret']
KEYS_PER_USER = ['access_token', 'refresh_token']
DEFAULT_METHODS=['get_bodyweight']

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

def _refresh(tokenData):
    DATABASE_ADDESS.put_key('identities/%s/plugindata/%s/token' % (PLUGINDATA['user'], NAME), 'application/x-python-object', None, tokenData, 'application/x-python-object', replace=True)
    
def fitbit(methods='get_bodyweight', **kwargs):
    if kwargs: print 'xxxjack fitbit extra kwargs', kwargs
    if not 'token' in PLUGINDATA:
        raise myWebError("401 Fitbit requires 'token' plugindata for user '%s'" % PLUGINDATA.get('user'))
    oauthSettings = PLUGINDATA['token']
    for k in KEYS_PER_USER:
        if not k in oauthSettings:
            raise myWebError("401 Fitbit 'token' plugindata for user '%s' misses '%s'" % (PLUGINDATA.get('user'), k))
    for k in KEYS_PER_APP:
        if not k in PLUGINDATA:
            raise myWebError("401 Fitbit requires global plugindata '%s'" % k)
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
    
def auth1(**kwargs):
    if kwargs: print 'xxxjack fitbit/auth1 extra kwargs', kwargs
    oauthSettings = {}
    for k in KEYS_PER_APP:
        if not k in PLUGINDATA:
            raise myWebError("401 fitbit/auth1 requires global plugindata '%s'" % k)
        oauthSettings[k] = PLUGINDATA[k]
    
    if not 'user' in PLUGINDATA:
        raise myWebError("401 fitbit/auth1 requires 'user' argument" % k)
        
    fb = fitbit.Fitbit(refresh_cb=_refresh, **oauthSettings)
    
    step2url = DATABASE_ACCESS.get_key('service/igor/url', 'text/plain')
    step2url = urlparse.urljoin(step2url, '/plugin/%s/auth2' % NAME)
    step2url += '?' + urllib.urlencode(dict(user=PLUGINDATA['user']))
    redirectUrl = fb.client.authorize_token_url(redirect_uri=step2url)
    raise web.seeother(redirectUrl)
    
def auth2(code=None, **kwargs):
    if kwargs: print 'xxxjack fitbit/auth2 extra kwargs', kwargs
    oauthSettings = {}
    for k in KEYS_PER_APP:
        if not k in PLUGINDATA:
            raise myWebError("401 fitbit/auth2 requires global plugindata '%s'" % k)
        oauthSettings[k] = PLUGINDATA[k]

    if not 'user' in PLUGINDATA:
        raise myWebError("401 fitbit/auth2 requires 'user' argument" % k)

    fb = fitbit.Fitbit(refresh_cb=_refresh, **oauthSettings)

    token = fb.client.fetch_access_token(code, None)
    _refresh(token)
    return 'ok\n'
