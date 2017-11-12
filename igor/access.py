# Access control
import web
import xpath

# xxxjack this isn't the right exception...
def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }

class DummyAccessToken:
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self):
        pass

    def addToHeaders(self, headers):
        pass
        
    def getContent(self):
        return None
        
class IgorAccessToken(DummyAccessToken):
    def addToHeaders(self, headers):
        print 'xxxjack insert nothing into headers for IgorAccessToken'
        pass

_igorSelfToken = DummyAccessToken()

class AccessToken(DummyAccessToken):
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self, content):
        print 'xxxjack create AccessToken(%s)' % content
        self.content = content
        
    def addToHeaders(self, headers):
        print 'xxxjack insert AccessToken(%s) into header' % self.content
        headers['Authorization'] = 'Bearer ' + self.content
        
    def getContent(self):
        return self.content
        
class DummyAccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self):
        pass
        
    def allowed(self, operation, token):
        return True
           
class AccessChecker(DummyAccessChecker):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, content):
        self.content = content
        
    def allowed(self, operation, token):
        if token is IGOR_SELF_TOKEN:
            return True
        return token.getContent() == self.content

class Access:
    def __init__(self):
        pass
        
    def checkerForElement(self, element):
        nodelist = xpath.find("au:requires", element, namespaces=NAMESPACES)
        if not nodelist:
            return DummyAccessChecker()
        if len(nodelist) > 1:
            raise myWebError("500 action has multiple au:requires")
        requiresValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        return AccessChecker(requiresValue)
            
        
    def tokenForAction(self, element):
        nodelist = xpath.find("au:carries", element, namespaces=NAMESPACES)
        if not nodelist:
            return DummyAccessToken()
        if len(nodelist) > 1:
            raise myWebError("500 action has multiple au:carries")
        carriesValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        return AccessToken(carriesValue)
        
    def tokenForPlugin(self, pluginname):
        return self.tokenForIgor()

    def tokenForIgor(self):
        return _igorSelfToken
        
    def tokenForRequest(self, headers):
        if 'HTTP_AUTHORIZATION' in headers:
            authHeader = headers['HTTP_AUTHORIZATION']
            authFields = authHeader.split()
            if authFields[0].lower() == 'bearer':
                return AccessToken(authFields[1])
            # Add more here for other methods
        return DummyAccessToken()

singleton = Access()
