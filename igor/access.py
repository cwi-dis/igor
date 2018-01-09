# Access control
import web
import xpath
import base64

NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }

NORMAL_OPERATIONS = {'get', 'put', 'post', 'run'}
AUTH_OPERATIONS = {'auth'}
ALL_OPERATIONS = NORMAL_OPERATIONS | AUTH_OPERATIONS

DEBUG=True

# For the time being: define this to have the default token checker allow everything
# the dummy token allows
DEFAULT_IS_ALLOW_ALL=True

class AccessControlError(ValueError):
    pass

class BaseAccessToken:
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self):
        pass

    def __repr__(self):
        return "%s(0x%x)" % (self.__class__.__name__, id(self))
        
    def hasExternalRepresentation(self):
        return False
        
    def addToHeaders(self, headers):
        pass
        
    def addToEnv(self, env):
        pass
        
    def allows(self, operation, accessChecker):
        if DEBUG: print 'access: %s %s: no access at all allowed by %s' % (operation, accessChecker.destination, self)
        return False
        
        
class IgorAccessToken(BaseAccessToken):
    """A token without an external representation that allows everything everywhere.
    To be used sparingly by Igor itself."""
        
    def allows(self, operation, accessChecker):
        if DEBUG: print 'access: %s %s: allowed by %s' % (operation, accessChecker.destination, self)
        return True
        
    def addToEnv(self, env):
        env['IGOR_SELF_TOKEN'] = repr(self)
        
_igorSelfToken = IgorAccessToken()
_accessSelfToken = _igorSelfToken

class AccessToken(BaseAccessToken):
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self, content):
        BaseAccessToken.__init__(self)
        self.content = content
        self.allowOperations = NORMAL_OPERATIONS
        
    def hasExternalRepresentation(self):
        return True
        
    def addToHeaders(self, headers):
        headers['Authorization'] = 'Bearer ' + self.content
        
    def allows(self, operation, accessChecker):
        if not operation in self.allowOperations:
            if DEBUG: print 'access: %s %s: no %s access allowed by AccessToken %s' % (operation, accessChecker.destination, operation, self)
            return False
        if self.content != accessChecker.content:
            if DEBUG: print 'access: %s %s: signature mismatch for AccessToken %s' % (operation, accessChecker.destination, self)
            return False
        if DEBUG: print 'access: %s %s: allowed by AccessToken %s' % (operation, accessChecker.destination, self)
        return True

class DefaultAccessToken(AccessToken):
    def __init__(self):
        AccessToken.__init__(self, "DEFAULT-CAPABILITY")      
         
_defaultToken = DefaultAccessToken()

class MultiAccessToken(BaseAccessToken):

    def __init__(self, contentList):
        self.tokens = []
        for c in contentList:
            self.tokens.append(AccessToken(c))
            
    def hasExternalRepresentation(self):
        for t in self.tokens:
            if t.hasExternalRepresentation():
                return True
        return False
        
    def addToHeaders(self, headers):
        for t in self.tokens:
            if t.hasExternalRepresentation():
                t.addToHeaders(headers)
                return
        raise AccessControlError("Token has no external representation")
        
    def allows(self, operation, accessChecker):
        if DEBUG: print 'access: %s %s: MultiAccessToken(%d)' % (operation, accessChecker.destination, len(self.tokens))
        for t in self.tokens:
            if t.allows(operation, accessChecker):
                return True
        return False      
           
class AccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, content, destination=None):
        self.content = content
        if destination == None:
            destination = "some-element"
        self.destination = destination
        
    def allowed(self, operation, token):
        if not token:
            if DEBUG: print 'access: %s %s: no access allowed for token=None' % (operation, self.destination)
            return False
        if not operation in ALL_OPERATIONS:
            raise web.InternalError("Access: unknown operation '%s'" % operation)
        return token.allows(operation, self)
    
class DefaultAccessChecker(AccessChecker):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self):
        # This string will not occur anywhere (we hope:-)
        self.content = repr(self)
        self.destination = "(using default-accesschecker)"

class Access:
    def __init__(self):
        self.database = None
        self.session = None
        self.internalTokens = {}
        
    def internalTokenForToken(self, token):
        k = str(random.random())
        self.internalTokens[k] = token
        return k
        
    def setDatabase(self, database):
        self.database = database
        
    def setSession(self, session):
        self.session = session
        
    def checkerForElement(self, element, representingElement=None):
        if not element:
            return DefaultAccessChecker()
        nodelist = xpath.find("au:requires", element, namespaces=NAMESPACES)
        if not nodelist:
            return self.checkerForElement(element.parentNode, representingElement if representingElement else element)
        if len(nodelist) > 1:
            raise AccessControlError("Action has multiple au:requires")
        requiresValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        destination = None
        if DEBUG and self.database:
            destination = self.database.getXPathForElement(element)
            if representingElement:
                destination += " (representing %s)" % self.database.getXPathForElement(representingElement)
        return AccessChecker(requiresValue, destination)
            
        
    def _tokenForElement(self, element):
        nodelist = xpath.find("au:carries", element, namespaces=NAMESPACES)
        if not nodelist:
            return None
        tokenValueList = []
        for n in nodelist:
            carriesValue = "".join(t.nodeValue for t in n.childNodes if t.nodeType == t.TEXT_NODE)
            tokenValueList.append(carriesValue)
        if len(tokenValueList) > 1:
            return MultiAccessToken(tokenValueList)
        rv = AccessToken(tokenValueList[0])
        return rv
        
    def tokenForAction(self, element):
        token =  self._tokenForElement(element)
        if token == None:
            # Check whether there is a default token for all actions
            if element.parentNode:
                token = self._tokenForElement(element.parentNode)
        if token == None:
            if DEBUG: print 'access: no token found for action %s' % self.database.getXPathForElement(element)
            token = _defaultToken
        return token
        
    def tokenForUser(self, username):
        if not username or '/' in username:
            raise web.HTTPError('401 Illegal username')
        elements = self.database.getElements('identities/%s' % username, 'get', _accessSelfToken)
        if len(elements) != 1:
            raise web.HTTPError('501 Database error: %d users named %s' % (len(elements), username))
        token = self._tokenForElement(elements[0])
        if token == None:
            token = _defaultToken
            if DEBUG: print 'access: no token found for user %s' % self.database.getXPathForElement(username)
        return token
        
    def tokenForPlugin(self, pluginname):
        return self.tokenForIgor()

    def tokenForIgor(self):
        return _igorSelfToken
        
    def tokenForRequest(self, headers):
        if 'IGOR_SELF_TOKEN' in headers:
            if headers['IGOR_SELF_TOKEN'] == repr(_igorSelfToken):
                return _igorSelfToken
            raise web.HTTPError('500 Incorrect IGOR_SELF_TOKEN')
        if 'HTTP_AUTHORIZATION' in headers:
            authHeader = headers['HTTP_AUTHORIZATION']
            authFields = authHeader.split()
            if authFields[0].lower() == 'bearer':
                return AccessToken(authFields[1])
            if authFields[0].lower() == 'basic':
                decoded = base64.b64decode(authFields[1])
                username, password = decoded.split(':')
                if self.userAndPasswordCorrect(username, password):
                    return self.tokenForUser(username)
                else:
                    web.header('WWW_Authenticate', 'Basic realm="igor"')
                    raise web.HTTPError('401 Unauthorized')
            # Add more here for other methods
        if self.session and 'user' in self.session and self.session.user:
            return self.tokenForUser(self.session.user)
        if DEBUG: print 'access: no token found for request %s' % headers.get('PATH_INFO', '???')
        return _defaultToken

    def userAndPasswordCorrect(self, username, password):
        if self.database == None or not username or not password:
            return False
        if '/' in username:
            raise web.HTTPError('401 Illegal username')
        encryptedPassword = self.database.getValue('identities/%s/encryptedPassword' % username, _accessSelfToken)
        if not encryptedPassword:
            return False
        import passlib.hash
        import passlib.utils.binary
        salt = encryptedPassword.split('$')[3]
        salt = passlib.utils.binary.ab64_decode(salt)
        passwordHash = passlib.hash.pbkdf2_sha256.using(salt=salt).hash(password)
        if encryptedPassword != passwordHash:
            return False
        return True
        
singleton = Access()
