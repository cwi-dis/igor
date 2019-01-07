"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os

from builtins import object
class SmartmeterIotsaPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
    
    def pull(self, token=None, callerToken=None):
        protocol = self.pluginData.get('protocol', 'http')
        host = self.pluginData.get('host', '%s.local' % self.pluginName)
        url = "%s://%s/p1?format=json" % (protocol, host)
        method = 'GET'
        
        headers = {}
        addedTokenId = token.addToHeadersFor(headers, url)
        
        kwargs = {}
        if os.environ.get('IGOR_TEST_NO_SSL_VERIFY'):
            kwargs['verify'] = False
        
        try:
            r = requests.request(method, url, headers=headers, **kwargs)
        except requests.exceptions.ConnectionError as e:
            return self.igor.app.raiseHTTPError("502 Error accessing %s: cannot connect" % (url))
        except requests.exceptions.Timeout as e:
            return self.igor.app.raiseHTTPError("502 Error accessing %s: timeout during connect" % (url))
        except requests.exceptions.RequestException as e:
            return self.igor.app.raiseHTTPError("502 Error accessing %s: %s" % (url, repr(e)))
        if r.status_code == 401:
            # If we get a 401 Unauthorized error we also report it through the access control errors
            print('401 error from external call, was carrying capability %s' % addedTokenId)
            failureDescription = dict(operation=method.lower(), path=url, external=True, capID=token.getIdentifiers(), plugin=self.pluginName)
            self.igor.internal._accessFailure(failureDescription)
        r.raise_for_status()
        
        # Note we do not decode the JSON here. Keep as-is and let database-put do that
        jsonData = r.text
        tocall = dict(
            method='PUT', 
            url='/data/sensors/%s' % self.pluginName, 
            mimetype='application/json', 
            data=jsonData, 
            representing='sensors/%s' % self.pluginName, 
            token=token)
        self.igor.urlCaller.callURL(tocall)
        return 'ok\n'
    
def igorPlugin(igor, pluginName, pluginData):
    return SmartmeterIotsaPlugin(igor, pluginName, pluginData)
