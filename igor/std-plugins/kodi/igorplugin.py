"""Sample plugin module for Igor"""
import requests
import os
import kodijson

class KodiPlugin:
    def __init__(self, igor, pluginName, pluginData):
        self.verbose = True
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        self.kodi = None
        self.reinit()
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
    
    def reinit(self, token=None, callerToken=None):
        kodiUrl = self.pluginData["url"]
        # xxxjack should optionally retrieve username and password
        if self.verbose: print(f"{self.pluginName}: Kodi({kodiUrl})")
        self.kodi = kodijson.Kodi(kodiUrl)

    def pull(self, token=None, callerToken=None):
        # Get list of strings that indicates which properties we want for currently playing media items
        propertyList = self.pluginData['playbackInfo']['item']
        # Get currently active players (within Kodi). We use type as the name for our outer element, and is id to find what it is playing.
        activePlayerData = self.kodi.Player.GetActivePlayers()
        if self.verbose: print(f"{self.pluginName}: GetActivePlayers() returned {activePlayerData}")
        if 'error' in activePlayerData:
            error = activePlayerData["error"]
            print(f"{self.pluginName}.pull: GetActivePlayers: Kodi error {error}")
            return self.igor.app.raiseHTTPError(f"502 Kodi error {error.get('message', '')} code={error.get('code', 'unknown')}")
            
        result = {}
        activePlayers = activePlayerData['result']
        for playerData in activePlayers:
            playerId = playerData['playerid']
            playerType = playerData['type']
            playingItemData = self.kodi.Player.GetItem(playerid=playerId, properties=propertyList)
            if self.verbose: print(f"{self.pluginName}: GetItem(playerid={playerId}, properties={propertyList}) returned {playingItemData}")
            if 'error' in playingItemData:
                error = playingItemData["error"]
                print(f"{self.pluginName}.pull: GetItem: Kodi error {error}")
                return self.igor.app.raiseHTTPError(f"502 Kodi error {error.get('message', '')} code={error.get('code', 'unknown')}")
            # Store resulting item under name of the type (presumably video or audio)
            result[playerType] = playingItemData['result']['item']
        rv = self.igor.databaseAccessor.put_key(f'/data/devices/{self.pluginName}/current', 'application/x-python-object', None, result, 'application/x-python-object', token, replace=True)
        if self.verbose: print(f"{self.pluginName}: put_key('/data/devices/{self.pluginName}/current', {result} returned {rv})")
        
        return rv
            

    def push(self, token=None, callerToken=None):
        return self.igor.app.raiseHTTPError("500 Not yet implemented")
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
    return KodiPlugin(igor, pluginName, pluginData)
