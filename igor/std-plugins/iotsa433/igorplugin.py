"""Sample plugin module for Igor"""
import requests
import os
import json
import urllib

class Iotsa433Plugin:
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
    
    def _prepareRequest(self, token):
        """Prepare headers and kwargs for a GET or PUT request"""
        headers = {}
        kwargs = {}
        addedTokenId = None
        if self.pluginData.get('secured'):
            addedTokenId = token.addToHeadersFor(headers, url)
        elif (credentials := self.pluginData.get('credentials')):
                username, password = credentials.split(':')
                kwargs['auth'] = username, password
        if os.environ.get('IGOR_TEST_NO_SSL_VERIFY'):
            kwargs['verify'] = False
        return headers, kwargs, addedTokenId

    def _sendrequest(self, method, endpoint, extraHeaders, token, callerToken, **kwargs):
        protocol = self.pluginData.get('protocol', 'http')
        host = self.pluginData.get('host', '%s.local' % self.pluginName)
        if not endpoint:
            endpoint = self.pluginData.get('endpoint', 'api')
        url = f"{protocol}://{host}"
        url = urllib.parse.urljoin(url, endpoint)
        method = 'GET'
        
        headers, kwargs, addedTokenId = self._prepareRequest(token)
        for k, v in extraHeaders.items():
            headers[k] = v
        try:
            r = requests.request(method, url, headers=headers, **kwargs)
        except requests.exceptions.ConnectionError as e:
            return self.igor.app.raiseHTTPError("502 Error accessing %s: cannot connect" % (url))
        except requests.exceptions.Timeout as e:
            return self.igor.app.raiseHTTPError("502 Error accessing %s: timeout during connect" % (url))
        except requests.exceptions.RequestException as e:
            return self.igor.app.raiseHTTPError("502 Error accessing %s: %s" % (url, repr(e)))
        if r.status_code == 401 and addedTokenId:
            # If we get a 401 Unauthorized error we also report it through the access control errors
            print(f'401 Unauthorized error from external call, was carrying capability {addedTokenId}')
            failureDescription = dict(operation=method.lower(), path=url, external=True, capID=token.getIdentifiers(), plugin=self.pluginName)
            self.igor.internal._accessFailure(failureDescription)
        r.raise_for_status()
        return r

    def _put_basic(self, callerToken, endpoint, data):
        """low-level method to PUT data to any endpoint (in python form)"""
        jsondata = json.dumps(data)
        r = self._sendrequest('PUT', endpoint, {'Contept-type': 'application/json'}, None, callerToken, data=jsondata)
        return r.text

    def _get_basic(self, callerToken, endpoint):
        """low-level method to GET data from any endpoint (in python form)"""
        r = self._sendrequest('GET', endpoint, {}, None, callerToken)
        rv = json.loads(r.text)
        return rv

    def pull(self, token=None, callerToken=None):
        print(f"xxxjack IotsaPlugin.pull() called. token={token}, callerToken={callerToken}")
        r = self._sendrequest('GET', None, {}, token, callerToken)
        
        # Note we do not decode the JSON here. Keep as-is and let database-put do that
        jsonData = r.text
        tocall = dict(
            method='PUT', 
            url='/data/devices/%s/current' % self.pluginName, 
            mimetype='application/json', 
            data=jsonData, 
            representing='devices/%s' % self.pluginName, 
            token=token)
        self.igor.urlCaller.callURL(tocall)
        return 'ok\n'
        
    def push(self, token=None, callerToken=None):
        target = self.igor.databaseAccessor.get_key('devices/%s/target' % self.pluginName, 'application/json', 'content', token)
        method = self.pluginData.get('pushMethod', 'PUT')
        r = relf._sendrequest(method, {'Content-Type': 'application/json'}, None, token, callerToken, data=target)
        return 'ok\n'
    
def igorPlugin(igor, pluginName, pluginData):
    return Iotsa433Plugin(igor, pluginName, pluginData)
