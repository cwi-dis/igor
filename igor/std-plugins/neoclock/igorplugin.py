"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os

from builtins import object
class NeoclockPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
    
    # xxxjack should add methods to get/set timezone, etc.
    # xxxjack should add general iotsa methods
    
    def push(self, token=None, callerToken=None):
        protocol = self.pluginData.get('protocol', 'http')
        host = self.pluginData.get('host', '%s.local' % self.pluginName)
        url = "%s://%s/alert" % (protocol, host)
        method = 'GET'
    
        headers = {}
        addedTokenId = token.addToHeadersFor(headers, url)
    
        kwargs = {}
        if os.environ.get('IGOR_TEST_NO_SSL_VERIFY'):
            kwargs['verify'] = False

        status = self.igor.databaseAccessor.get_key('devices/%s' % self.pluginName, 'application/x-python-object', 'content', token)
        statusArgs = dict(
            timeout=status.get('timeout', 600), 
            temporalStatus=status.get('outerStatus', '0x0'),
            status="%s/%s" % (status.get('innerStatus', '0x0'), status.get('timeoutStatus', '0x0'))
            )

        try:
            r = requests.request(method, url, headers=headers, params=statusArgs, **kwargs)
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

        return 'ok\n'
    
def igorPlugin(igor, pluginName, pluginData):
    return NeoclockPlugin(igor, pluginName, pluginData)
