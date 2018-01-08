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

class BaseAccessToken:
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self):
        pass

    def hasExternalRepresentation(self):
        return False
        
    def addToHeaders(self, headers):
        pass
        
    def allows(self, operation, accessChecker):
        return False
        
        
class IgorAccessToken(BaseAccessToken):
    """A token without an external representation that allows everything everywhere.
    To be used sparingly by Igor itself."""
        
    def allows(self, operation, accessChecker):
        return True
        
_igorSelfToken = IgorAccessToken()
_accessSelfToken = _igorSelfToken
_defaultToken = _igorSelfToken # For now: will become BaseAccessToken() later.

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
            return False
        if self.content != accessChecker.content:
            return False
        return True
        
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
        
    def allows(self, opreation, accessChecker):
        for t in self.tokens:
            if t.allows(operation, accessChecker):
                return True
        return False      
           
class AccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, content):
        self.content = content
        
    def allowed(self, operation, token):
        if not token:
            return False
        if not operation in ALL_OPERATIONS:
            raise web.InternalError("Access: unknown operation '%s'" % operation)
        return token.allows(operation, self)
        match = token.matchAll or (token.getContent() == self.content)
        if not match:
            return False
        if operation in token.allowOperations:
            return True
        return False
    
class DefaultAccessChecker(AccessChecker):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self):
        # This string will not occur anywhere (we hope:-)
        self.content = repr(self)

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
            return DefaultAccessChecker()
        if len(nodelist) > 1:
            raise AccessControlError("Action has multiple au:requires")
        requiresValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        return AccessChecker(requiresValue)
            
        
    def _tokenForElement(self, element):
        nodelist = xpath.find("au:carries", element, namespaces=NAMESPACES)
        if not nodelist:
            return _defaultToken
        tokenValueList = []
        for n in nodelist:
            carriesValue = "".join(t.nodeValue for t in n.childNodes if t.nodeType == t.TEXT_NODE)
            tokenValueList.append(carriesValue)
        if len(tokenValueList) > 1:
            return MultiAccessToken(tokenValueList)
        return AccessToken(tokenValueList)
        
    def tokenForAction(self, element):
        return self._tokenForElement(element)
        
    def tokenForUser(self, username):
        if not username or '/' in username:
            raise web.HTTPError('401 Illegal username')
        elements = self.database.getElements('identities/%s' % username, 'get', _accessSelfToken)
        if len(elements) != 1:
            raise web.HTTPError('501 Database error: %d users named %s' % (len(elements), username))
        return self._tokenForElement(elements[0])
        
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
