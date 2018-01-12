# Access control
import web
import xpath
import base64
import jwt

NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }

NORMAL_OPERATIONS = {'get', 'put', 'post', 'delete'}
AUTH_OPERATIONS = {'auth'}
ALL_OPERATIONS = NORMAL_OPERATIONS | AUTH_OPERATIONS

DEBUG=False

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
        env['IGOR_SELF_TOKEN'] = singleton.internalTokenForToken(self)
        
    def allows(self, operation, accessChecker):
        if DEBUG: print 'access: %s %s: no access at all allowed by %s' % (operation, accessChecker.destination, self)
        return False
        
        
class IgorAccessToken(BaseAccessToken):
    """A token without an external representation that allows everything everywhere.
    To be used sparingly by Igor itself."""
        
    def allows(self, operation, accessChecker):
        if DEBUG: print 'access: %s %s: allowed by %s' % (operation, accessChecker.destination, self)
        return True
        
_igorSelfToken = IgorAccessToken()
_accessSelfToken = _igorSelfToken

class AccessToken(BaseAccessToken):
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self, content):
        BaseAccessToken.__init__(self)
        self.content = content
        if DEBUG:  print 'access: Created:', repr(self)
        
    def __repr__(self):
        return "%s(0x%x, %s)" % (self.__class__.__name__, id(self), repr(self.content))
        
    def hasExternalRepresentation(self):
        return 'externalKey' in self.content
        
    def addToHeaders(self, headers):
        externalKey = self.content.get('externalKey')
        if not externalKey:
            return
        externalRepresentation = jwt.encode(self.content, externalKey, algorithm='HS256')
        if DEBUG: print 'access: %s: externalRepresentation %s' % (self, externalRepresentation)
        headers['Authorization'] = 'Bearer ' + externalRepresentation
        
    def allows(self, operation, accessChecker):
        cascadingRule = self.content.get(operation)
        if not cascadingRule:
            if DEBUG: print 'access: %s %s: no %s access allowed by AccessToken %s' % (operation, accessChecker.destination, operation, self)
            return False
        path = self.content.get('xpath')
        if not path:
            if DEBUG: print 'access: %s %s: no path-based access allowed by AccessToken %s' % (operation, accessChecker.destination, operation, self)
            return False
        dest = accessChecker.destination
        destHead = dest[:len(path)]
        destTail = dest[len(path):]
        if cascadingRule == 'self':
            if dest != path:
                if DEBUG: print 'access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path)
                return False
        elif cascadingRule == 'descendant-or-self':
            if destHead != path or destTail[:1] not in ('', '/'):
                if DEBUG: print 'access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path)
                return False
        elif cascadingRule == 'descendant':
            if destHead != path or destTail[:1] != '/':
                if DEBUG: print 'access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path)
                return False
        elif cascadingRule == 'child':
            if destHead != path or destTail[:1] != '/' or destTail.count('/') != 1:
                if DEBUG: print 'access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path)
                return False
        else:
            raise AccessControlError('Capability has unknown cascading rule %s for operation %s' % (cascadingRule, operation))
        if DEBUG: print 'access: %s %s: allowed by AccessToken %s' % (operation, accessChecker.destination, self)
        return True

class ExternalAccessToken(BaseAccessToken):
    def __init__(self, content):
        assert 0
        
class MultiAccessToken(BaseAccessToken):

    def __init__(self, contentList):
        self.tokens = []
        for c in contentList:
            self.tokens.append(AccessToken(c))
            
    def hasExternalRepresentation(self):
        for t in self.tokens[:1]:
            if t.hasExternalRepresentation():
                return True
        return False
        
    def addToHeaders(self, headers):
        for t in self.tokens[:1]:
            if t.hasExternalRepresentation():
                t.addToHeaders(headers)
                return
        
    def allows(self, operation, accessChecker):
        if DEBUG: print 'access: %s %s: MultiAccessToken(%d)' % (operation, accessChecker.destination, len(self.tokens))
        for t in self.tokens:
            if t.allows(operation, accessChecker):
                return True
        return False      
           
class AccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, destination):
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
        self.destination = "(using default-accesschecker)"

    def allowed(self, operation, token):
        if DEBUG: print 'access: no access allowed by DefaultAccessChecker'
        return False
        
class Access:
    def __init__(self):
        self.database = None
        self.session = None
        self.internalTokens = {}
        self._defaultTokenInstance = None
        
    def internalTokenForToken(self, token):
        k = id(token)
        self.internalTokens[k] = token
        return k
        
    def setDatabase(self, database):
        self.database = database
        
    def setSession(self, session):
        self.session = session
        
    def _defaultToken(self):
        if self._defaultTokenInstance == None and self.database:
            defaultContainer = self.database.getElements('au:access/au:defaultCapabilities', 'get', _accessSelfToken, namespaces=NAMESPACES)
            if len(defaultContainer) != 1:
                raise web.HTTPError("501 Database should contain single au:access/au:defaultCapabilities")
            self._defaultTokenInstance = self._tokenForElement(defaultContainer[0])
        if self._defaultTokenInstance == None:
            print 'access: _defaultToken() called but no database (or no default token in database)'
        return self._defaultTokenInstance
        
    def checkerForElement(self, element):
        if not element:
            print 'access: ERROR: attempt to get checkerForElement(None)'
            return DefaultAccessChecker()
        path = self.database.getXPathForElement(element)
        if not path:
            print 'access: ERROR: attempt to get checkerForElement(%s) that has no XPath' % repr(element)
            return DefaultAccessChecker()
        if not path.startswith('/data'):
            print 'access: ERROR: attempt to get checkerForElement(%s) with unexpected XPath: %s' % (repr(element), path)
            return DefaultAccessChecker()
        return AccessChecker(path)
            
    def checkerForEntrypoint(self, entrypoint):
        if not entrypoint or entrypoint[0] != '/' or entrypoint.startswith('/data'):
            print 'access: ERROR: attempt to get checkerForEntrypoint(%s)' % entrypoint
            return DefaultAccessChecker()
        return AccessChecker(entrypoint)
        
    def _tokenForElement(self, element):
        nodelist = xpath.find("au:capability", element, namespaces=NAMESPACES)
        if not nodelist:
            return None
        tokenDataList = map(lambda e: self.database.tagAndDictFromElement(e)[1], nodelist)
        if len(tokenDataList) > 1:
            return MultiAccessToken(tokenDataList)
        rv = AccessToken(tokenDataList[0])
        return rv
        
    def tokenForAction(self, element):
        token =  self._tokenForElement(element)
        if token == None:
            # Check whether there is a default token for all actions
            if element.parentNode:
                token = self._tokenForElement(element.parentNode)
        if token == None:
            if DEBUG: print 'access: no token found for action %s' % self.database.getXPathForElement(element)
            token = self._defaultToken()
        return token
        
    def tokenForUser(self, username):
        if not username or '/' in username:
            raise web.HTTPError('401 Illegal username')
        elements = self.database.getElements('identities/%s' % username, 'get', _accessSelfToken)
        if len(elements) != 1:
            raise web.HTTPError('501 Database error: %d users named %s' % (len(elements), username))
        token = self._tokenForElement(elements[0])
        if token == None:
            token = self._defaultToken()
            if DEBUG: print 'access: no token found for user %s' % username
        return token
        
    def tokenForPlugin(self, pluginname):
        return self.tokenForIgor()

    def tokenForIgor(self):
        return _igorSelfToken
        
    def tokenForRequest(self, headers):
        if 'IGOR_SELF_TOKEN' in headers:
            if headers['IGOR_SELF_TOKEN'] in self.internalTokens:
                return self.internalTokens[headers['IGOR_SELF_TOKEN']]
            raise web.HTTPError('500 Incorrect IGOR_SELF_TOKEN %s' % headers['IGOR_SELF_TOKEN'])
        if 'HTTP_AUTHORIZATION' in headers:
            authHeader = headers['HTTP_AUTHORIZATION']
            authFields = authHeader.split()
            if authFields[0].lower() == 'bearer':
                decoded = authFields[1] # base64.b64decode(authFields[1])
                return self._externalAccessToken(decoded)
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
        # xxxjack should we allow carrying tokens in cookies?
        if DEBUG: print 'access: no token found for request %s' % headers.get('PATH_INFO', '???')
        return self._defaultToken()

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
        
    def _externalAccessToken(self, data):
        print 'xxxjack attempt to get external access token for', data
        return self._defaultToken()
        
singleton = Access()
