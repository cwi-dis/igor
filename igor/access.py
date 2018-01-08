# Access control
import web
import xpath
import base64

NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }

NORMAL_OPERATIONS = {'get', 'put', 'post', 'run'}
AUTH_OPERATIONS = {'auth'}
ALL_OPERATIONS = NORMAL_OPERATIONS | AUTH_OPERATIONS

# For the time being: define this to have the default token checker allow everything
# the dummy token allows
DEFAULT_IS_ALLOW_ALL=True

class AccessControlError(ValueError):
    pass

class DummyAccessToken:
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self, allowOperations=[], matchAll=False):
        self.allowOperations = allowOperations
        self.matchAll = matchAll

    def addToHeaders(self, headers):
        pass
        
    def getContent(self):
        return None
        
class IgorAccessToken(DummyAccessToken):
    """A token without an external representation that allows everything everywhere.
    To be used sparingly by Igor itself."""
    def addToHeaders(self, headers):
        pass
        
_igorSelfToken = IgorAccessToken(matchAll=True, allowOperations=ALL_OPERATIONS)
_accessSelfToken = _igorSelfToken

class AccessToken(DummyAccessToken):
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self, content, allowOperations=NORMAL_OPERATIONS, matchAll=False):
        DummyAccessToken.__init__(self, allowOperations=allowOperations, matchAll=matchAll)
        self.content = content
        
    def addToHeaders(self, headers):
        headers['Authorization'] = 'Bearer ' + self.content
        
    def getContent(self):
        return self.content
        
class DummyAccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self):
        pass
        
    def allowed(self, operation, token):
        if not operation in ALL_OPERATIONS:
            raise web.InternalError("Access: unknown operation '%s'" % operation)
        if DEFAULT_IS_ALLOW_ALL:
            return True
        match = token.matchAll
        if not match:
            return False
        if operation in token.allowOperations:
            return True
        return False
           
class AccessChecker(DummyAccessChecker):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, content):
        self.content = content
        
    def allowed(self, operation, token):
        if not operation in ALL_OPERATIONS:
            raise web.InternalError("Access: unknown operation '%s'" % operation)
        match = token.matchAll or (token.getContent() == self.content)
        if not match:
            return False
        if operation in token.allowOperations:
            return True
        return False

class Access:
    def __init__(self):
        self.database = None
        self.session = None
        
    def setDatabase(self, database):
        self.database = database
        
    def setSession(self, session):
        self.session = session
        
    def checkerForElement(self, element):
        nodelist = xpath.find("au:requires", element, namespaces=NAMESPACES)
        if not nodelist:
            return DummyAccessChecker()
        if len(nodelist) > 1:
            raise AccessControlError("Action has multiple au:requires")
        requiresValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        return AccessChecker(requiresValue)
            
        
    def tokenForAction(self, element):
        nodelist = xpath.find("au:carries", element, namespaces=NAMESPACES)
        if not nodelist:
            return DummyAccessToken()
        if len(nodelist) > 1:
            raise AccessControlError("Action has multiple au:carries")
        carriesValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        return AccessToken(carriesValue)
        
    def tokenForUser(self, username):
        if not username or '/' in username:
            raise web.HTTPError('401 Illegal username')
        elements = self.database.getElements('identities/%s' % username, 'get', _accessSelfToken)
        if len(elements) != 1:
            raise web.HTTPError('501 Database error: %d users named %s' % (len(elements), username))
        return self.tokenForAction(elements[0])
        
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
            if authFields[0].lower() == 'basic':
                print 'xxxjack authfields[1]', authFields[1]
                decoded = base64.b64decode(authFields[1])
                print 'xxxjack decoded', decoded
                username, password = decoded.split(':')
                if self.userAndPasswordCorrect(username, password):
                    return self.tokenForUser(username)
                else:
                    web.header('WWW_Authenticate', 'Basic realm="igor"')
                    raise web.HTTPError('401 Unauthorized')
            # Add more here for other methods
        if self.session and 'user' in self.session and self.session.user:
            return self.tokenForUser(self.session.user)
        return DummyAccessToken()

    def userAndPasswordCorrect(self, username, password):
        if self.database == None or not username or not password:
            return False
        if '/' in username:
            raise web.HTTPError('401 Illegal username')
        encryptedPassword = self.database.getValue('identities/%s/encryptedPassword' % username, _accessSelfToken)
        if not encryptedPassword:
            print 'xxxjack no password for user', username
            return False
        import passlib.hash
        import passlib.utils.binary
        salt = encryptedPassword.split('$')[3]
        salt = passlib.utils.binary.ab64_decode(salt)
        passwordHash = passlib.hash.pbkdf2_sha256.using(salt=salt).hash(password)
        if encryptedPassword != passwordHash:
            print 'xxxjack mismatched password', encryptedPassword, passwordHash
            return False
        return True
        
singleton = Access()
