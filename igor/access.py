# Access control
import web
import xpath
import base64
import jwt
import random
import time
import urlparse

NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }

NORMAL_OPERATIONS = {'get', 'put', 'post', 'delete'}
AUTH_OPERATIONS = {'delegate'}
ALL_OPERATIONS = NORMAL_OPERATIONS | AUTH_OPERATIONS

CASCADING_RULES = {'self', 'descendant', 'descendant-or-self', 'child'}
CASCADING_RULES_IMPLIED = {
    'self' : {'self'},
    'descendant' : {'descendant', 'child'},
    'descendant-or-self' : {'self', 'descendant', 'descendant-or-self', 'child'},
    'child' : {'child'}
}

DEBUG=False
DEBUG_DELEGATION=True

# For the time being: define this to have the default token checker allow everything
# the dummy token allows
DEFAULT_IS_ALLOW_ALL=True


def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class AccessControlError(ValueError):
    pass

class BaseAccessToken:
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self):
        self.identifier = None

    def __repr__(self):
        return "%s(0x%x)" % (self.__class__.__name__, id(self))
        
    def _getIdentifiers(self):
        """Internal method - Returns a list of all token IDs of this token (and any subtokens it contains)"""
        return [self.identifier]
        
    def _hasExternalRepresentationFor(self, url):
        """Internal method - return True if this token can be represented externally and _getExternalRepresentation can be called"""
        return False
        
    def _getExternalRepresentation(self):
        """Internal method - return the external representation of this token"""

    def _getExternalContent(self):
        """Internal method - return key/value pairs that are important for external representation"""
        return {}
        
    def _allows(self, operation, accessChecker):
        """Internal method - return True if this token allows 'operation' on the element represented by 'accessChecker'"""
        if DEBUG: print 'access: %s %s: no access at all allowed by %s' % (operation, accessChecker.destination, self)
        return False
        
    def _allowsDelegation(self, path, rights):
        """Internal method - return True if the given path/rights are a subset of this token, and if this token can be delegated"""
        return False
        
    def _getTokenWithIdentifier(self, identifier):
        """Internal method - return the individual (sub)token with the given ID or None"""
        return None
        
    def _getTokenDescription(self):
        """Returns a list with descriptions of all tokens in this tokenset"""
        return [dict(cid=self.identifier)]
        
    def _addChild(self, childId):
        """Register a new child token to this one"""
        assert 0

    def _delChild(self, childId):
        """Unregister a child token"""
        
    def _save(self):
        """Saves a token back to stable storage"""
        assert 0
        
    def _revoke(self):
        """Revoke this token"""
        assert 0
        
    def _getOwner(self):
        """Is the current carrier the owner of this token?"""
        return False
        
    def _setOwner(self, newOwner):
        """Set new owner of this token"""
        assert 0

    def _getObject(self):
        """Returns the object to which this token pertains"""
        return None
        
    def _removeToken(self, tokenId):
        """Remove token tokenId from this set"""
        assert 0
        
    def addToHeadersFor(self, headers, url):
        """Add this token to the (http request) headers if it has an external representation for this destination"""
        pass

    def addToHeadersAsOTP(self, headers):
        """Add this token to the (http request) headers in one-time-password form, for internal Igor use only"""
        otp = singleton.produceOTPForToken(self)
        headers['Authorization'] = 'Basic ' + base64.b64encode(otp)
        
class IgorAccessToken(BaseAccessToken):
    """A token without an external representation that allows everything everywhere.
    To be used sparingly by Igor itself."""

    def __init__(self):
        self.identifier = '*SUPER*'
        
    def _allows(self, operation, accessChecker):
        if not operation in NORMAL_OPERATIONS:
            if DEBUG: print 'access: %s %s: not allowed by supertoken' % (operation, accessChecker.destination)
        if DEBUG: print 'access: %s %s: allowed by supertoken' % (operation, accessChecker.destination)
        return True

    def _allowsDelegation(self, path, rights):
        """Internal method - return True, the supertoken is the root of all tokens"""
        return True

_igorSelfToken = IgorAccessToken()
_accessSelfToken = _igorSelfToken

class AccessToken(BaseAccessToken):
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self, content, defaultIdentifier=None, owner=None):
        BaseAccessToken.__init__(self)
        self.owner = owner
        self.content = dict(content)
        toDelete = []
        for k in self.content:
            if not self.content[k]:
                toDelete.append(k)
        for k in toDelete:
            del self.content[k]
        #
        # Determine identifier
        #
        if defaultIdentifier == None:
            defaultIdentifier = 'no-id-%x' % id(self)
        self.identifier = content.get('cid', defaultIdentifier)
        singleton._registerTokenWithIdentifier(self.identifier, self)
        #
        # Check whether this capability is meant for this igor (no aud or aud matches our URL)
        #
        if 'aud' in content:
            audience = content['aud']
            ourUrl = singleton._getSelfAudience()
            self.validForSelf = (audience == ourUrl)
            if DEBUG: print 'access: <aud> matches: %s' % self.validForSelf
        else:
            self.validForSelf = True
        if DEBUG:  print 'access: Created:', repr(self)
        
    def __repr__(self):
        return "%s(0x%x, %s)" % (self.__class__.__name__, id(self), repr(self.content))
        
    def _hasExternalRepresentationFor(self, url):
        return 'iss' in self.content and 'aud' in self.content and url.startswith(self.content['aud'])

    def _getExternalContent(self):
        rv = {}
        if 'iss' in self.content: rv['iss'] = self.content['iss']
        if 'aud' in self.content: rv['aud'] = self.content['aud']
        if 'subj' in self.content: rv['subj'] = self.content['subj']
        return rv
        
    def _getExternalRepresentation(self):
        iss = self.content.get('iss')
        aud = self.content.get('aud')
        # xxxjack Could check for multiple aud values based on URL to contact...
        if not iss or not aud:
            print 'access: _getExternalRepresentation: no iss and aud, so no external representation'
            raise myWebError('404 Cannot lookup shared key for iss=%s aud=%s' % (iss, aud))
        externalKey = singleton._getSharedKey(iss, aud)
        externalRepresentation = jwt.encode(self.content, externalKey, algorithm='HS256')
        if DEBUG: print 'access: %s: externalRepresentation %s' % (self, externalRepresentation)
        return externalRepresentation
        
    def _allows(self, operation, accessChecker):
        # First check this this capability is for us.
        if not self.validForSelf:
            if DEBUG: print 'access: Not for this Igor: AccessToken %s' % self
            return False
        cascadingRule = self.content.get(operation)
        if not cascadingRule:
            if DEBUG: print 'access: %s %s: no %s access allowed by AccessToken %s' % (operation, accessChecker.destination, operation, self)
            return False
        path = self.content.get('obj')
        if not path:
            if DEBUG: print 'access: %s %s: no path-based access allowed by AccessToken %s' % (operation, accessChecker.destination, self)
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

    def _allowsDelegation(self, newPath, newRights):
        """Internal method - return True if the given path/rights are a subset of this token, and if this token can be delegated"""
        # Check whether this token can be delegated
        if not self.content.get('delegate'):
            if DEBUG_DELEGATION: print 'access: delegate %s: no delegation right on AccessToken %s' % (newPath, self)
            return False
        # Check whether the path is contained in our path
        path = self.content.get('obj')
        if not path:
            if DEBUG_DELEGATION: print 'access: delegate %s: no path-based access allowed by AccessToken %s' % (newPath, self)
            return False
        subPath = newPath[len(path):]
        if not newPath.startswith(path) or not subPath[:1] in ('', '/'):
            if DEBUG_DELEGATION: print 'access: delegate %s: path not contained within path for AccessToken %s' % (newPath, self)
            return False
        newIsSelf = subPath == ''
        newIsChild = subPath.count('/') == 1
        # Check that the requested rights match
        for operation, newCascadingRule in newRights.items():
            if not newCascadingRule:
                # If we don't want this operation it is always okay.
                continue
            oldCascadingRule = self.content.get(operation)
            if not oldCascadingRule:
                # If the operation isn't allowed at all it's definitely not okay.
                if DEBUG_DELEGATION: print 'access: delegate %s: no %s access allowed by AccessToken %s' % (newPath, operation, self)
                return False
            if newIsSelf:
                if not newCascadingRule in CASCADING_RULES_IMPLIED.get(oldCascadingRule, {}):
                    if DEBUG_DELEGATION: print 'access: delegate %s: %s=%s not allowd by %s=%s for AccessToken %s' % (newPath, operation, newCascadingRule, operation, oldCascadingRule, self)
                    return False
            elif newIsChild:
                # xxxjack for now only allow if original rule includes all descendants
                if not oldCascadingRule in ('descendant', 'descendant-or-self'):
                    if DEBUG_DELEGATION: print 'access: delegate %s: %s=%s not allowd by %s=%s for AccessToken %s (xxxjack temp)' % (newPath, operation, newCascadingRule, operation, oldCascadingRule, self)
                    return False
            else:
                # xxxjack for now only allow if original rule includes all descendants
                if not oldCascadingRule in ('descendant', 'descendant-or-self'):
                    if DEBUG_DELEGATION: print 'access: delegate %s: %s=%s not allowd by %s=%s for AccessToken %s (xxxjack temp)' % (newPath, operation, newCascadingRule, operation, oldCascadingRule, self)
                    return False
        # Everything seems to be fine.
        return True       
        
    def _getTokenWithIdentifier(self, identifier):
        if identifier == self.identifier:
            return self
        #
        # We also return the data for child tokens, if needed.
        # xxxjack I don't like this...
        #
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        if not identifier in children:
            return None
        return singleton._loadTokenWithIdentifier(identifier)
        
    def _getTokenDescription(self):
        """Returns a list with descriptions of all tokens in this tokenset"""
        rv = dict(self.content)
        rv['cid'] = self.identifier
        rv['owner'] = self.owner
        return [rv]
        
    def addToHeadersFor(self, headers, url):
        # xxxjack assume checking has been done
        externalRepresentation = self._getExternalRepresentation()
        if not externalRepresentation:
            return
        headers['Authorization'] = 'Bearer ' + externalRepresentation

    def _addChild(self, childId):
        """Register a new child token to this one"""
        if DEBUG_DELEGATION: print 'access: adding child %s to %s' % (childId, self.identifier)
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        children.append(childId)
        self.content['child'] = children
        self._save()
        
    def _delChild(self, childId):
        """Unregister a child token"""
        if DEBUG_DELEGATION: print 'access: adding child %s to %s' % (childId, self.identifier)
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        children.remove(childId)
        self.content['child'] = children
        self._save()
        
    def _save(self):
        """Saves a token back to stable storage"""
        if DEBUG_DELEGATION: print 'access: saving capability %s' % self.identifier
        capNodeList = singleton.database.getElements("//au:capability[cid='%s']" % self.identifier, 'put', _accessSelfToken, namespaces=NAMESPACES)
        if len(capNodeList) == 0:
            print 'access: Warning: Cannot save token %s because it is not in the database' % self.identifier
            return
        elif len(capNodeList) > 1:
            print 'access: Error: Cannot save token %s because it occurs %d times in the database' % (self.identifier, len(capNodeList))
            raise myWebError("500 Access: multiple capabilities with cid=%s" % self.identifier)
        oldCapElement = capNodeList[0]
        newCapElement = singleton.database.elementFromTagAndData("capability", self.content, namespace=NAMESPACES)
        parentElement = oldCapElement.parentNode
        parentElement.replaceChild(newCapElement, oldCapElement)
              
    def _getOwner(self):
        return self.owner
        
    def _setOwner(self, newOwner):
        """Set new owner of this token"""
        if DEBUG_DELEGATION: print 'access: set owner %s on capability %s' % (newOwner, self.identifier)
        capNodeList = singleton.database.getElements("//au:capability[cid='%s']" % self.identifier, 'delete', _accessSelfToken, namespaces=NAMESPACES)
        if len(capNodeList) == 0:
            print 'access: Warning: Cannot setOwner token %s because it is not in the database' % self.identifier
            return False
        elif len(capNodeList) > 1:
            print 'access: Error: Cannot setOwner token %s because it occurs %d times in the database' % (self.identifier, len(capNodeList))
            raise myWebError("500 Access: multiple capabilities with cid=%s" % self.identifier)
        oldCapElement = capNodeList[0]
        parentElement = oldCapElement.parentNode
        newParentElementList = singleton.database.getElements(newOwner, "post", _accessSelfToken)
        if len(newParentElementList) == 0:
            print 'access: cannot setOwner %s because it is not in the database'
            raise myWebError("401 Unknown new token owner %s" % newOwner)
        if len(newParentElementList) > 1:
            print 'access: cannot setOwner %s because it occurs multiple times in the database'
            raise myWebError("401 Multiple new token owner %s" % newOwner)
        newParentElement = newParentElementList[0]
        newCapElement = singleton.database.elementFromTagAndData("capability", self.content, namespace=NAMESPACES)
        newParentElement.appendChild(oldCapElement) # This also removes it from where it is now...
        self.owner = newOwner
        return True

    def _getObject(self):
        """Returns the object to which this token pertains"""
        return self.content.get('obj')

    def _revoke(self):
        """Revoke this token"""
        if DEBUG_DELEGATION: print 'access: revoking capability %s' % self.identifier
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        for ch in children:
            print 'access: WARNING: Recursive delete of capability not yet implemented: %s' % ch
        singleton.database.delValues("//au:capability[cid='%s']" % self.identifier, _accessSelfToken, namespaces=NAMESPACES)
          
class ExternalAccessTokenImplementation(AccessToken):
    def __init__(self, content):
        AccessToken.__init__(self, content)
        
def ExternalAccessToken(content):
    sharedKey = singleton._getSharedKey()
    try:
        content = jwt.decode(content, sharedKey, issuer=singleton._getSelfIssuer(), audience=singleton._getSelfAudience(), algorithm='RS256')
    except jwt.DecodeError:
        print 'access: ERROR: incorrect signature on bearer token %s' % content
        raise myWebError('400 Incorrect signature on key')
    except jwt.InvalidIssuerError:
        print 'access: ERROR: incorrect issuer on bearer token %s' % content
        raise myWebError('400 Incorrect issuer on key')
    except jwt.InvalidAudienceError:
        print 'access: ERROR: incorrect audience on bearer token %s' % content
        raise myWebError('400 Incorrect audience on key')
    cid = content.get('cid')
    if not cid:
        print 'access: ERROR: no cid on bearer token %s' % content
        raise myWebError('400 Missing cid on key')
    if singleton._isTokenOnRevokeList():
        print 'access: ERROR: token has been revoked: %s' % content
        raise myWebError('400 Revoked token')
    return ExternalAccessTokenImplementation(content)

class MultiAccessToken(BaseAccessToken):

    def __init__(self, contentList=[], tokenList=[], owner=None):
        self.tokens = []
        for c in contentList:
            self.tokens.append(AccessToken(c, owner=owner))
        for t in tokenList:
            self.tokens.append(t)
        self.externalTokenCache = {}

    def _getIdentifiers(self):
        rv = []
        for t in self.tokens:
            rv += t._getIdentifiers()
        return rv
                    
    def _hasExternalRepresentationFor(self, url):
        if url in self.externalTokenCache:
            return not not self.externalTokenCache[url]
        for t in self.tokens:
            if t._hasExternalRepresentationFor(url):
                self.externalTokenCache[url] = t
                return True
        self.externalTokenCache[url] = False
        return False
        
    def _allows(self, operation, accessChecker):
        if DEBUG: print 'access: %s %s: MultiAccessToken(%d)' % (operation, accessChecker.destination, len(self.tokens))
        for t in self.tokens:
            if t._allows(operation, accessChecker):
                return True
        return False      

    def _getTokenWithIdentifier(self, identifier):
        for t in self.tokens:
            rv = t._getTokenWithIdentifier(identifier)
            if rv: 
                return rv
        return None
        
    def _getTokenDescription(self):
        """Returns a list with descriptions of all tokens in this tokenset"""
        rv = []
        for t in self.tokens:
            rv += t._getTokenDescription()
        return rv
        
    def addToHeadersFor(self, headers, url):
        if self._hasExternalRepresentationFor(url):
            t = self.externalTokenCache[url]
            # xxxjack should cache
            t.addToHeadersFor(headers, url)

    def _removeToken(self, tokenId):
        """Remove token tokenId from this set"""
        toRemove = None
        for t in self.tokens:
            if t.identifier == tokenId:
                toRemove = t
                break
        assert toRemove
        self.tokens.remove(t)
        self.externalTokenCache = {}
        
    def _appendToken(self, token):
        """Add a token object to the end of the list of tokens"""
        self.tokens.append(token)
        self.externalTokenCache = {}

def _combineTokens(token1, token2):
    """Return union of two tokens (which may be AccessToken, MultiAccessToken or None)"""
    if token1 is None:
        return token2
    if token2 is None:
        return token1
    if hasattr(token1, '_appendToken'):
        token1._appendToken(token2)
        return token1
    return MultiAccessToken(tokenList=[token1, token2])

class AccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, destination):
        self.destination = destination
        
    def allowed(self, operation, token):
        """Test whether the token (or set of tokens) allows this operation on the element represented by this AccessChecker"""
        if not token:
            if DEBUG: print 'access: %s %s: no access allowed for token=None' % (operation, self.destination)
            return False
        if not operation in ALL_OPERATIONS:
            raise myWebError("500 Access: unknown operation '%s'" % operation)
        ok = token._allows(operation, self)
        if not ok:
            identifiers = token._getIdentifiers()
            print '\taccess: %s %s: no access allowed by %d tokens:' % (operation, self.destination, len(identifiers))
            for i in identifiers:
                print '\t\t%s' % i
        return ok
    
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
        self.COMMAND = None
        self._otp2token = {}
        self._defaultTokenInstance = None
        self._self_audience = None
        self._tokenCache = {}
        self._revokeList = []
        
    def _registerTokenWithIdentifier(self, identifier, token):
        self._tokenCache[identifier] = token
        
    def _loadTokenWithIdentifier(self, identifier):
        if identifier in self._tokenCache:
            return self._tokenCache[identifier]
        capNodeList = singleton.database.getElements("//au:capability[cid='%s']" % identifier, 'get', _accessSelfToken, namespaces=NAMESPACES)
        if len(capNodeList) == 0:
            print 'access: Warning: Cannot get token %s (child of %s) because it is not in the database' % (identifier, self.identifier)
            raise myWebError("500 Access: no capability with cid=%s (child of %s)" % (identifier, self.identifier))
        elif len(capNodeList) > 1:
            print 'access: Error: Cannot save token %s because it occurs %d times in the database' % (self.identifier, len(capNodeList))
            raise myWebError("500 Access: multiple capabilities with cid=%s (child of %s)" % (identifier, self.identifier))
        capData = singleton.database.tagAndDictFromElement(capNodeList[0])[1]
        return AccessToken(capData)
        
    def _save(self):
        """Save database or capability store, if possible"""
        if self.COMMAND:
            self.COMMAND.queue('save', _accessSelfToken)

    def produceOTPForToken(self, token):
        """Produce a one-time-password form of this token, for use internally or for passing to a plugin script (to be used once)"""
        # The key format is carefully selected so it can be used as user:pass combination
        k = '-otp-%d:%d' % (random.getrandbits(64), random.getrandbits(64))
        self._otp2token[k] = token
        return k
        
    def _consumeOTPForToken(self, otp):
        """Internal method - turns an OTP back into the token it refers to and invalidates the OTP"""
        # xxxjack should use a mutex here
        token = self._otp2token.get(otp)
        if token:
            del self._otp2token[otp]
            return token
        else:
            print 'access: Invalid OTP presented: ', otp
            raise myWebError("498 Invalid OTP presented")
            
    def invalidateOTPForToken(self, otp):
        """Invalidate an OTP, if it still exists. Used when a plugin script exits, in case it has not used its OTP"""
        if otp in self._otp2token:
            del self._otp2token[otp]
            
    def setDatabase(self, database):
        """Temporary helper method - Informs the access checker where it can find the database object"""
        self.database = database
        
    def setSession(self, session):
        """Temporary helper method - Informs the access checker where sessions are stored"""
        self.session = session
        
    def setCommand(self, command):
        """Temporary helper method - Set command processor so access can save the database"""
        self.COMMAND = command

    def _defaultToken(self):
        """Internal method - returns token(s) for operations/users/plugins/etc that have no explicit tokens"""
        if self._defaultTokenInstance == None and self.database:
            defaultContainer = self.database.getElements('au:access/au:defaultCapabilities', 'get', _accessSelfToken, namespaces=NAMESPACES)
            if len(defaultContainer) != 1:
                raise myWebError("501 Database should contain single au:access/au:defaultCapabilities")
            self._defaultTokenInstance = self._tokenForElement(defaultContainer[0])
        if self._defaultTokenInstance == None:
            print 'access: _defaultToken() called but no database (or no default token in database)'
        return self._defaultTokenInstance
        
    def checkerForElement(self, element):
        """Returns an AccessChecker for an XML element"""
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
        """Returns an AccessChecker for an external entrypoint that is not a tree element"""
        if not entrypoint or entrypoint[0] != '/' or entrypoint.startswith('/data'):
            print 'access: ERROR: attempt to get checkerForEntrypoint(%s)' % entrypoint
            return DefaultAccessChecker()
        return AccessChecker(entrypoint)
        
    def _tokenForElement(self, element, owner=None):
        """Internal method - returns token(s) that are stored in a given element (identity/action/plugindata/etc)"""
        nodelist = xpath.find("au:capability", element, namespaces=NAMESPACES)
        if not nodelist:
            return None
        tokenDataList = map(lambda e: self.database.tagAndDictFromElement(e)[1], nodelist)
        if len(tokenDataList) > 1:
            return MultiAccessToken(tokenDataList, owner=owner)
        rv = AccessToken(tokenDataList[0], owner=owner)
        return rv
        
    def tokenForAction(self, element):
        """Return token(s) for an <action> element"""
        token =  self._tokenForElement(element)
        tokenForAllActions = self._tokenForElement(element.parentNode)
        token = _combineTokens(token, tokenForAllActions)
        return _combineTokens(token, self._defaultToken())
        
    def _tokenForUser(self, username):
        """Internal method - Return token(s) for a user with the given name"""
        if not username or '/' in username:
            raise myWebError('401 Illegal username')
        elements = self.database.getElements('identities/%s' % username, 'get', _accessSelfToken)
        if len(elements) != 1:
            raise myWebError('501 Database error: %d users named %s' % (len(elements), username))
        element = elements[0]
        token = self._tokenForElement(element, owner='identities/%s' % username)
        tokenForAllUsers = self._tokenForElement(element.parentNode)
        token = _combineTokens(token, tokenForAllUsers)
        return _combineTokens(token, self._defaultToken())
        
    def tokenForPlugin(self, pluginname):
        """Return token(s) for a plugin with the given pluginname"""
        # xxxjack not yet implemented
        return self.tokenForIgor()

    def tokenForIgor(self):
        """Return token for igor itself (use sparingly)"""
        return _igorSelfToken
        
    def tokenForRequest(self, headers):
        """Return token for the given incoming http(s) request"""
        if 'HTTP_AUTHORIZATION' in headers:
            authHeader = headers['HTTP_AUTHORIZATION']
            authFields = authHeader.split()
            if authFields[0].lower() == 'bearer':
                decoded = authFields[1] # base64.b64decode(authFields[1])
                if DEBUG: print 'access: tokenForRequest: returning token found in Authorization: Bearer header'
                return self._externalAccessToken(decoded)
            if authFields[0].lower() == 'basic':
                decoded = base64.b64decode(authFields[1])
                if decoded.startswith('-otp-'):
                    # This is a one time pad, not a username/password combination
                    if DEBUG: print 'access: tokenForRequest: found OTP in Authorization: Basic header'
                    return self._consumeOTPForToken(decoded)
                username, password = decoded.split(':')
                if DEBUG: print 'access: tokenForRequest: searching for token for Authorization: Basic %s:xxxxxx header' % username
                if self.userAndPasswordCorrect(username, password):
                    return self._tokenForUser(username)
                else:
                    web.header('WWW_Authenticate', 'Basic realm="igor"')
                    raise web.HTTPError('401 Unauthorized')
            # Add more here for other methods
        if self.session and 'user' in self.session and self.session.user:
            if DEBUG: print 'access: tokenForRequest: returning token for session.user %s' % self.session.user
            return self._tokenForUser(self.session.user)
        # xxxjack should we allow carrying tokens in cookies?
        if DEBUG: print 'access: no token found for request %s' % headers.get('PATH_INFO', '???')
        return self._defaultToken()
        
    def _externalAccessToken(self, data):
        """Internal method - Create a token from the given "Authorization: bearer" data"""
        # xxxjack not yet implemented
        return ExternalAccessToken(data)
    
    def getTokenDescription(self, token, tokenId=None):
        """Returns a list of dictionaries which describe the tokens"""
        if tokenId:
            token = token._getTokenWithIdentifier(tokenId)
            if not token:
                if DEBUG_DELEGATION: print 'access: getTokenDescription: no such token ID: %s' % tokenId
                raise myWebError('404 No such token: %s' % tokenId)
        return token._getTokenDescription()
        
    def newToken(self, token, tokenId, newOwner, newPath=None, **kwargs):
        """Create a new token based on an existing token. Returns ID of new token."""
        #
        # Split remaining args into rights and other content
        #
        newRights = {}
        content = {}
        for k, v in kwargs.items():
            # Note delegate right is checked implicitly, below.
            if k in NORMAL_OPERATIONS:
                newRights[k] = v
            else:
                content[k] = v
        #
        # Check that original token exists, and allows this delegation
        #
        token = token._getTokenWithIdentifier(tokenId)
        if newPath == None:
                newPath = token._getObject()
        if not token:
            if DEBUG_DELEGATION: print 'access: newToken: no such token ID: %s' % tokenId
            raise myWebError('404 No such token: %s' % tokenId)
        if not token._allowsDelegation(newPath, newRights):
            raise myWebError('401 Delegation not allowed')
        #
        # Check the new parent exists
        #
        parentElement = self.database.getElements(newOwner, 'post', _accessSelfToken, namespaces=NAMESPACES)
        if len(parentElement) != 1:
            if DEBUG_DELEGATION: print 'access: newToken: no unique destination %s' % newOwner
            raise web.notfound()
        parentElement = parentElement[0]
        #
        # Construct the data for the new token.
        #
        newId = 'token-%d' % random.getrandbits(64)
        token._addChild(newId)
        tokenData = dict(cid=newId, obj=newPath, parent=tokenId)
        moreData = token._getExternalContent()
        tokenData.update(moreData)
        tokenData.update(newRights)
        tokenData.update(content)

        element = self.database.elementFromTagAndData("capability", tokenData, namespace=NAMESPACES)
        #
        # Insert into the tree
        #
        parentElement.appendChild(element)
        #
        # Save
        #
        self._save()
        #
        # Return the ID
        #
        return newId
        
    def passToken(self, token, tokenId, newOwner):
        """Pass token ownership to a new owner. Token must be in the set of tokens that can be passed."""
        tokenToPass = token._getTokenWithIdentifier(tokenId)
        if not tokenToPass:
            raise myWebError("401 No such token: %s" % tokenId)
        oldOwner = tokenToPass._getOwner()
        if not oldOwner:
            raise myWebError("401 Not owner of token %s" % tokenId)
        if oldOwner == newOwner:
            return ''
        if not tokenToPass._setOwner(newOwner):
            raise myWebError("401 Cannot move token %s to new owner %s" % (tokenId, newOwner))
        token._removeToken(tokenId)
        #
        # Save
        #
        self._save()
        
    def revokeToken(self, token, parentId, tokenId):
        """Revoke a token"""
        parentToken = token._getTokenWithIdentifier(parentId)
        if not parentToken:
            raise myWebError("404 No such parent token: %s" % parentId)
        childToken = token._getTokenWithIdentifier(tokenId)
        if not childToken:
            raise myWebError("404 No such token: %s" % tokenId)
        self._addToRevokeList(tokenId)
        childToken._revoke()
        parentToken._delChild(tokenId)
        #
        # Save
        #
        self._save()
        
    def exportToken(self, token, tokenId, subject=None, lifetime=None, **kwargs):
        """Create an external representation of this token, destined for the given subject"""
        #
        # Add keys needed for external token
        #
        if subject:
            kwargs['sub'] = subject
        if not lifetime:
            lifetime = 60*60*24*365 # One year
        lifetime = int(lifetime)
        kwargs['nvb'] = str(int(time.time())-1)
        kwargs['nva'] = str(int(time.time()) + lifetime)
        if not 'aud' in kwargs:
            kwargs['aud'] = self._getSelfAudience()
        kwargs['iss'] = self._getSelfIssuer()
        #
        # Create the new token
        #
        newTokenId = self.newToken(token, tokenId, self._getExternalTokenOwner(), **kwargs)
        tokenToExport = token._getTokenWithIdentifier(newTokenId)
        
        #
        # Create the external representation
        #
        assert tokenToExport._hasExternalRepresentationFor(self._getSelfAudience())
        externalRepresentation = tokenToExport._getExternalRepresentation()
        #
        # Save
        #
        self._save()
        return externalRepresentation
        
    def externalRepresentation(self, token, tokenId):
        tokenToExport = token._getTokenWithIdentifier(tokenId)
        if not tokenToExport:
            raise myWebError("401 No such token: %s" % tokenId)
        assert tokenToExport._hasExternalRepresentationFor(self._getSelfAudience())
        externalRepresentation = tokenToExport._getExternalRepresentation()
        return externalRepresentation
        
        
    def _getSelfAudience(self):
        """Return an audience identifier that refers to us"""
        if not self._self_audience:
            self._self_audience = singleton.database.getValue('services/igor/url', _accessSelfToken)
        return self._self_audience


    def _getSelfIssuer(self):
        """Return ourselves as an issuer"""
        return urlparse.urljoin(self._getSelfAudience(),  '/issuer')

    def _getExternalTokenOwner(self):
        """Return the location where we store external tokens"""
        return '/data/au:access/au:exportedCapabilities'

    def _getSharedKey(self, iss=None, aud=None):
        if iss is None:
            iss = self._getSelfIssuer()
        if aud is None:
            aud = self._getSelfAudience()
        keyPath = "au:access/au:sharedKeys/au:sharedKey[iss='%s'][aud='%s']/externalKey" % (iss, aud)
        externalKey = self.database.getValue(keyPath, _accessSelfToken, namespaces=NAMESPACES)
        if not externalKey:
            print 'access: _getExternalRepresentation: no key found at %s' % keyPath
            raise myWebError('404 No shared key found for iss=%s, aud=%s' % (iss, aud))
        return externalKey

    def _addToRevokeList(self, tokenId):
        """Add given token to the revocation list"""
        if self._revokeList is None:
            self._loadRevokeList()
        if not tokenId in self._revokeList:
            self._revokeList.append(tokenId)
            element = self.database.elementFromTagAndData("revokedCapability", dict(cid=tokenId), namespace=NAMESPACES)
            parents = self.database.getElements('au:access/au:revokedCapabilities', 'post', _accessSelfToken, namespaces=NAMESPACES)
            assert len(parents) == 1
            parents[0].appendChild(element)
        
    def _isTokenOnRevokeList(self, tokenId):
        """Check whether a given token is on the revoke list"""
        if self._revokeList is None:
            self._loadRevokeList()
        return tokenId in self._revokeList
        
    def _loadRevokeList(self):
        self._revokeList = self.database.getValues('au:access/au:revokedCapabilities/au:revokedCapability/cid', _accessSelfToken, namespaces=NAMESPACES)
        
    def getSubjectList(self):
        """Return list of subjects that trust this issuer"""
        # xxxjack this is wrong: it also returns keys shared with other issuers
        subjectValues = self.database.getValues('au:access/au:sharedKeys/au:sharedKey/sub', _accessSelfToken, namespaces=NAMESPACES)
        subjectValues = map(lambda x : x[1], subjectValues)
        subjectValues = list(subjectValues)
        subjectValues.sort()
        return subjectValues

    def getAudienceList(self):
        """Return list of audiences that trust this issuer"""
        audienceValues = self.database.getValues('au:access/au:sharedKeys/au:sharedKey/sub', _accessSelfToken, namespaces=NAMESPACES)
        audienceValues = set(audienceValues)
        audienceValues = list(audienceValues)
        audienceValues.sort()
        return audienceValues

    def userAndPasswordCorrect(self, username, password):
        """Return True if username/password combination is valid"""
        # xxxjack this method should not be in the Access element
        if self.database == None or not username or not password:
            if DEBUG: print 'access: basic authentication: database, username or password missing'
            return False
        if '/' in username:
            raise myWebError('401 Illegal username')
        encryptedPassword = self.database.getValue('identities/%s/encryptedPassword' % username, _accessSelfToken)
        if not encryptedPassword:
            if DEBUG: print 'access: basic authentication: no encryptedPassword for user', username
            return False
        import passlib.hash
        import passlib.utils.binary
        salt = encryptedPassword.split('$')[3]
        salt = passlib.utils.binary.ab64_decode(salt)
        passwordHash = passlib.hash.pbkdf2_sha256.using(salt=salt).hash(password)
        if encryptedPassword != passwordHash:
            if DEBUG: print 'access: basic authentication: password mismatch for user', username
            return False
        if DEBUG: print 'access: basic authentication: login for user', username
        return True
#
# Create a singleton Access object
#   
singleton = Access()
