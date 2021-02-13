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

    def _put_basic(self, callerToken, endpoint, data, method='PUT'):
        """low-level method to PUT data to any endpoint (in python form)"""
        jsondata = json.dumps(data)
        r = self._sendrequest(method, endpoint, {'Content-type': 'application/json'}, None, callerToken, data=jsondata)
        return r.text

    def _get_basic(self, callerToken, endpoint):
        """low-level method to GET data from any endpoint (in python form)"""
        r = self._sendrequest('GET', endpoint, {}, None, callerToken)
        rv = json.loads(r.text)
        return rv

    def _get_registered_appliances(self, callerToken):
        """Return list of registered appliances, for index.html"""
        db = self.igor.databaseAccessor.get_key(f'devices/{self.pluginName}', 'application/x-python-object', 'content', callerToken)
        rv = []
        for brand, branddb in db.items():
            for group, groupdb in branddb.items():
                for appliance, state in groupdb.items():
                    rv.append((brand, group, appliance, state))
                else:
                    rv.append((brand, group, '', ''))
            else:
                rv.append((brand, '', '', ''))
        return rv

    def _do_register(self, callerToken, brand, group, appliance):
        # First create database entry
        if appliance:
            appdata = dict(appliance='')
        else:
            appdata = ''
        data = dict(brand=dict(group=appdata))
        self.igor.databaseAccessor.put_key(f'devices/{self.pluginName}', 'text/plain', 'ref', data, 'application/x-python-object', callerToken, replace=True)
        # Now submit callback to iotsa433. First get our URL.
        url = self.igor.databaseAccessor.get_key('services/igor/url', 'text/plain', 'content', callerToken)
        url = urllib.parse.urljoin(url, f'/plugin/{self.pluginName}/changed')
        callbackData = dict(brand=brand, group=group, url=url, parameters=True)
        try:
            ok = self._put_basic(callerToken, '/api/433receive', callbackData, method='POST')
        except self.igor.app.getHTTPError() as e:
            return str(e)
        if ok.lower().strip() == 'ok':
            return None
        return ok.strip()

    def _do_send(self, callerToken, brand, group, appliance, state):
        data = dict(brand=brand, group=group, appliance=appliance, state=state)
        try:
            ok = self._put_basic(callerToken, '/api/433send', data)
        except self.igor.app.getHTTPError() as e:
            return str(e)
        if ok.lower().strip() == 'ok':
            return None
        return ok.strip()
    
    def changed(self, brand=None, group=None, appliance=None, state=None, token=None, callerToken=None, **kwargs):
        """Callback URL for iotsa433 device. If all of brand, group, appliance and state are set: enter into the database"""
        if brand and group and appliance and state:
            ref = f'devices/{self.pluginName}/{brand}/{group}/{appliance}'
            current = self.igor.databaseAccessor.get_key(ref, 'text/plain', 'content', token)
            if current == state:
                print(f'{self.pluginName}: changed: ignore duplicate brand={brand} group={group} appliance={appliance} state={state}')
            else:
                # self.igor.databaseAccessor.put_key(f'plugindata/{name}/protocol', 'text/plain', 'ref', description['protocol'], 'text/plain', callerToken, replace=True)

                self.igor.databaseAccessor.put_key(ref, 'text/plain', 'ref', state, 'text/plain', callerToken, replace=True)
                if 0:
                    tocall = dict(
                        method='PUT', 
                        url=ref, 
                        mimetype='text/plain', 
                        data=state, 
                        representing='devices/%s' % self.pluginName, 
                        token=token)
                    self.igor.urlCaller.callURL(tocall)
            return 'ok\n'
        else:
            print(f'{self.pluginName}: changed: ignore unknown brand={brand} group={group} appliance={appliance} state={state} rest={kwargs}')
            return 'ignored\n'

    def push(self, *args, **kwargs):
        print(f'{self.pluginName}: push: args={args} kwargs={kwargs}')
        return 'ok\n'

    def oldpull(self, token=None, callerToken=None):
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

    def _oldpush(self, token=None, callerToken=None):
        target = self.igor.databaseAccessor.get_key('devices/%s/target' % self.pluginName, 'application/json', 'content', token)
        method = self.pluginData.get('pushMethod', 'PUT')
        r = relf._sendrequest(method, {'Content-Type': 'application/json'}, None, token, callerToken, data=target)
        return 'ok\n'
    
def igorPlugin(igor, pluginName, pluginData):
    return Iotsa433Plugin(igor, pluginName, pluginData)
