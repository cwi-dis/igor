from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
from .vars import *
import base64
import urllib.parse

class BaseAccessToken(object):
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self):
        self.identifier = None

    def __repr__(self):
        return "%s(0x%x, cids:%s)" % (self.__class__.__name__, id(self), '/'.join(self.getIdentifiers()))
        
    def getIdentifiers(self):
        """Returns a list of all token IDs of this token (and any subtokens it contains)"""
        return [self.identifier]
        
    def _hasExternalRepresentationFor(self, url):
        """Internal method - return token ID if this token can be represented externally and _getExternalRepresentation can be called"""
        return None
        
    def _getExternalRepresentation(self):
        """Internal method - return the external representation of this token"""

    def _getExternalContent(self):
        """Internal method - return key/value pairs that are important for external representation"""
        return {}
        
    def _allows(self, operation, accessChecker):
        """Internal method - return True if this token allows 'operation' on the element represented by 'accessChecker'"""
        if DEBUG: print('access: %s %s: no access at all allowed by %s' % (operation, accessChecker.destination, self))
        return False
        
    def _allowsDelegation(self, path, rights, aud=None):
        """Internal method - return True if the given path/rights are a subset of this token, and if this token can be delegated"""
        return False
        
    def _getTokenWithIdentifier(self, identifier, recursive=False):
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
        headers['Authorization'] = 'Basic ' + base64.b64encode(otp.encode('utf-8')).decode('ascii')
        
class IgorAccessToken(BaseAccessToken):
    """A token without an external representation that allows everything everywhere.
    To be used sparingly by Igor itself."""

    def __init__(self):
        self.identifier = '*SUPER*'
        
    def _allows(self, operation, accessChecker):
        if not operation in NORMAL_OPERATIONS:
            if DEBUG: print('access: %s %s: not allowed by supertoken' % (operation, accessChecker.destination))
        if DEBUG: print('access: %s %s: allowed by supertoken' % (operation, accessChecker.destination))
        return True

    def _allowsDelegation(self, path, rights, aud=None):
        """Internal method - return True, the supertoken is the root of all tokens"""
        return False

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
            ourUrl = singleton.getSelfAudience()
            self.validForSelf = (audience == ourUrl)
            if DEBUG: print('access: <aud> matches: %s' % self.validForSelf)
        else:
            self.validForSelf = True
        if DEBUG:  print('access: Created:', repr(self))
        
    def __repr__(self):
        return "%s(0x%x, %s)" % (self.__class__.__name__, id(self), repr(self.content))
        
    def __eq__(self, other):
        if not isinstance(other, AccessToken):
            return False
        return self.content == other.content
        
    def _hasExternalRepresentationFor(self, url):
        if not 'aud' in self.content:
            return None
        if url.startswith(self.content['aud']):
            if DEBUG: print('access: capability %s matches url %s' % (self, url))
            return self.identifier
        p = urllib.parse.urlparse(url)
        if p.netloc == self.content['aud']:
            if DEBUG: print('access: capability %s matches hostname in %s' % (self, url))
            return self.identifier
        return None

    def _getExternalContent(self):
        rv = dict(cid=self.identifier)
        for key in ['obj', 'iss', 'aud', 'sub', 'nvb', 'nva', 'get', 'put', 'post', 'delete']:
            if key in self.content:
                rv[key] = self.content[key]
        if not 'iss' in rv:
            rv['iss'] = singleton.getSelfIssuer()
        return rv
        
    def _getExternalRepresentation(self):
        tokenContent = self._getExternalContent()
        externalRepresentation = singleton._encodeOutgoingData(tokenContent)
        return externalRepresentation
        
    def _allows(self, operation, accessChecker):
        # First check this this capability is for us.
        if not self.validForSelf:
            if DEBUG: print('access: Not for this Igor: AccessToken %s' % self)
            return False
        cascadingRule = self.content.get(operation)
        if not cascadingRule:
            if DEBUG: print('access: %s %s: no %s access allowed by AccessToken %s' % (operation, accessChecker.destination, operation, self))
            return False
        path = self.content.get('obj')
        if not path:
            if DEBUG: print('access: %s %s: no path-based access allowed by AccessToken %s' % (operation, accessChecker.destination, self))
            return False
        dest = accessChecker.destination
        destHead = dest[:len(path)]
        destTail = dest[len(path):]
        if cascadingRule == 'self':
            if dest != path:
                if DEBUG: print('access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path))
                return False
        elif cascadingRule == 'descendant-or-self':
            if destHead != path or destTail[:1] not in ('', '/'):
                if DEBUG: print('access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path))
                return False
        elif cascadingRule == 'descendant':
            if destHead != path or destTail[:1] != '/':
                if DEBUG: print('access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path))
                return False
        elif cascadingRule == 'child':
            if destHead != path or destTail[:1] != '/' or destTail.count('/') != 1:
                if DEBUG: print('access: %s %s: does not match cascade=%s for path=%s' % (operation, dest, cascadingRule, path))
                return False
        else:
            raise AccessControlError('Capability has unknown cascading rule %s for operation %s' % (cascadingRule, operation))
        if DEBUG: print('access: %s %s: allowed by AccessToken %s' % (operation, accessChecker.destination, self))
        return True

    def _allowsDelegation(self, newPath, newRights, aud=None):
        """Internal method - return True if the given path/rights are a subset of this token, and if this token can be delegated"""
        # Check whether this token can be delegated
        canDelegate = self.content.get('delegate')
        if not canDelegate:
            if DEBUG_DELEGATION: print('access: delegate %s: no delegation right on AccessToken %s' % (newPath, self))
            return False
        # Check whether this is the external-supertoken and whether we want to create a new external token
        if canDelegate == 'external':
            if aud:
                # Was: if aud and aud != singleton.getSelfAudience():
                # xxxjack no further checks for external tokens. This may need refining.
                return True
            else:
                if DEBUG_DELEGATION: print('access: delegate %s: only allowed for external audience' % newPath)
                return False
        elif 'aud' in self.content:
            if aud != self.content.get('aud'):
                if DEBUG_DELEGATION: print('access: delegate %s: audience %s, capability is for %s' % (newPath, aud, self.content.get('aud')))
                return False
        else:
            if aud and aud != singleton.getSelfAudience():
                if DEBUG_DELEGATION: print('access: delegate %s: cannot delegate to external %s' % (newPath, aud))
                return False
        # Check whether the path is contained in our path
        path = self.content.get('obj')
        if not path:
            if DEBUG_DELEGATION: print('access: delegate %s: no path-based access allowed by AccessToken %s' % (newPath, self))
            return False
        subPath = newPath[len(path):]
        if not newPath.startswith(path) or not subPath[:1] in ('', '/'):
            if DEBUG_DELEGATION: print('access: delegate %s: path not contained within path for AccessToken %s' % (newPath, self))
            return False
        newIsSelf = subPath == ''
        newIsChild = subPath.count('/') == 1
        # Check that the requested rights match
        for operation, newCascadingRule in list(newRights.items()):
            if not newCascadingRule:
                # If we don't want this operation it is always okay.
                continue
            oldCascadingRule = self.content.get(operation)
            if not oldCascadingRule:
                # If the operation isn't allowed at all it's definitely not okay.
                if DEBUG_DELEGATION: print('access: delegate %s: no %s access allowed by AccessToken %s' % (newPath, operation, self))
                return False
            if newIsSelf:
                if not newCascadingRule in CASCADING_RULES_IMPLIED.get(oldCascadingRule, {}):
                    if DEBUG_DELEGATION: print('access: delegate %s: %s=%s not allowed by %s=%s for AccessToken %s' % (newPath, operation, newCascadingRule, operation, oldCascadingRule, self))
                    return False
            elif newIsChild:
                # xxxjack for now only allow if original rule includes all descendants
                if not oldCascadingRule in ('descendant', 'descendant-or-self'):
                    if DEBUG_DELEGATION: print('access: delegate %s: %s=%s not allowed by %s=%s for AccessToken %s' % (newPath, operation, newCascadingRule, operation, oldCascadingRule, self))
                    return False
            else:
                # xxxjack for now only allow if original rule includes all descendants
                if not oldCascadingRule in ('descendant', 'descendant-or-self'):
                    if DEBUG_DELEGATION: print('access: delegate %s: %s=%s not allowed by %s=%s for AccessToken %s' % (newPath, operation, newCascadingRule, operation, oldCascadingRule, self))
                    return False
        # Everything seems to be fine.
        return True       
        
    def _getTokenWithIdentifier(self, identifier, recursive=False):
        if identifier == self.identifier:
            return self
        #
        # We also return the data for child tokens, if needed.
        # xxxjack I don't like this...
        #
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        if identifier in children:
            return singleton._loadTokenWithIdentifier(identifier)
        # If we search recursively we also look in our children (and so forth)
        if recursive:
            for childId in children:
                childToken = singleton._loadTokenWithIdentifier(childId)
                candidate = childToken._getTokenWithIdentifier(identifier, recursive=True)
                if candidate:
                    return candidate
        return None
        
    def _getTokenDescription(self):
        """Returns a list with descriptions of all tokens in this tokenset"""
        rv = dict(self.content)
        rv['cid'] = self.identifier
        rv['owner'] = self.owner
        return [rv]
        
    def addToHeadersFor(self, headers, url):
        # xxxjack assume checking has been done
        if DEBUG: print('access: add token %s to headers for request to %s' % (self, url))
        externalRepresentation = self._getExternalRepresentation()
        if not externalRepresentation:
            return
        headers['Authorization'] = 'Bearer ' + externalRepresentation
        return self.identifier

    def _getChildIdList(self):
        """Return list of token IDs of direct children"""
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        return children
        
    def _addChild(self, childId):
        """Register a new child token to this one"""
        if DEBUG_DELEGATION: print('access: adding child %s to %s' % (childId, self.identifier))
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        children.append(childId)
        self.content['child'] = children
        self._save()
        
    def _delChild(self, childId):
        """Unregister a child token"""
        if DEBUG_DELEGATION: print('access: adding child %s to %s' % (childId, self.identifier))
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        children.remove(childId)
        self.content['child'] = children
        self._save()
        
    def _save(self):
        """Saves a token back to stable storage"""
        if DEBUG_DELEGATION: print('access: saving capability %s' % self.identifier)
        capNodeList = singleton.igor.database.getElements("//au:capability[cid='%s']" % self.identifier, 'put', _accessSelfToken, namespaces=NAMESPACES)
        if len(capNodeList) == 0:
            print('access: Warning: Cannot save token %s because it is not in the database' % self.identifier)
            return
        elif len(capNodeList) > 1:
            print('access: Error: Cannot save token %s because it occurs %d times in the database' % (self.identifier, len(capNodeList)))
            raise AccessControlError("Database Error: multiple capabilities with cid=%s" % self.identifier)
        oldCapElement = capNodeList[0]
        newCapElement = singleton.igor.database.elementFromTagAndData("capability", self.content, namespace=AU_NAMESPACE)
        parentElement = oldCapElement.parentNode
        parentElement.replaceChild(newCapElement, oldCapElement)
        singleton._save()
              
    def _getOwner(self):
        return self.owner
        
    def _setOwner(self, newOwner):
        """Set new owner of this token"""
        if DEBUG_DELEGATION: print('access: set owner %s on capability %s' % (newOwner, self.identifier))
        capNodeList = singleton.igor.database.getElements("//au:capability[cid='%s']" % self.identifier, 'delete', _accessSelfToken, namespaces=NAMESPACES)
        if len(capNodeList) == 0:
            print('access: Warning: Cannot setOwner token %s because it is not in the database' % self.identifier)
            return False
        elif len(capNodeList) > 1:
            print('access: Error: Cannot setOwner token %s because it occurs %d times in the database' % (self.identifier, len(capNodeList)))
            raise AccessControlError("Database Error: multiple capabilities with cid=%s" % self.identifier)
        oldCapElement = capNodeList[0]
        parentElement = oldCapElement.parentNode
        newParentElementList = singleton.igor.database.getElements(newOwner, "post", _accessSelfToken)
        if len(newParentElementList) == 0:
            print('access: cannot setOwner %s because it is not in the database')
            raise AccessControlError("Internal Error: Unknown new token owner %s" % newOwner)
        if len(newParentElementList) > 1:
            print('access: cannot setOwner %s because it occurs multiple times in the database')
            raise AccessControlError("Database Error: Multiple new token owner %s" % newOwner)
        newParentElement = newParentElementList[0]
        newCapElement = singleton.igor.database.elementFromTagAndData("capability", self.content, namespace=AU_NAMESPACE)
        newParentElement.appendChild(oldCapElement) # This also removes it from where it is now...
        self.owner = newOwner
        return True

    def _getObject(self):
        """Returns the object to which this token pertains"""
        return self.content.get('obj')

    def _revoke(self):
        """Revoke this token"""
        if DEBUG_DELEGATION: print('access: revoking capability %s' % self.identifier)
        children = self.content.get('child', [])
        if type(children) != type([]):
            children = [children]
        for ch in children:
            print('access: WARNING: Recursive delete of capability not yet implemented: %s' % ch)
        singleton.igor.database.delValues("//au:capability[cid='%s']" % self.identifier, _accessSelfToken, namespaces=NAMESPACES)
          
class ExternalAccessTokenImplementation(AccessToken):
    def __init__(self, content):
        AccessToken.__init__(self, content)

class MultiAccessToken(BaseAccessToken):

    def __init__(self, contentList=[], tokenList=[], owner=None):
        self.tokens = []
        for c in contentList:
            self.tokens.append(AccessToken(c, owner=owner))
        for t in tokenList:
            self._appendToken(t)
        self.externalTokenCache = {}

    def getIdentifiers(self):
        rv = []
        for t in self.tokens:
            rv += t.getIdentifiers()
        return rv
                    
    def _hasExternalRepresentationFor(self, url):
        if url in self.externalTokenCache:
            return not not self.externalTokenCache[url]
        for t in self.tokens:
            tid = t._hasExternalRepresentationFor(url)
            if tid:
                if DEBUG: print('access: capability %s has child matching url %s' % (self, url))
                self.externalTokenCache[url] = t
                return tid
        if DEBUG: print('access: capability %s has no children matching url %s' % (self, url))
        self.externalTokenCache[url] = False
        return None
        
    def _allows(self, operation, accessChecker):
        if DEBUG: print('access: %s %s: MultiAccessToken(%d)' % (operation, accessChecker.destination, len(self.tokens)))
        for t in self.tokens:
            if t == self:
                raise AccessControlError("Database Error: Recursive capability")
            if t._allows(operation, accessChecker):
                return True
        return False      

    def _getTokenWithIdentifier(self, identifier, recursive=False):
        for t in self.tokens:
            rv = t._getTokenWithIdentifier(identifier, recursive)
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
            return t.addToHeadersFor(headers, url)
        else:
            if DEBUG: print('access: %s has no token for %s' % (self, url))

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
        """Add a token object to the end of the list of tokens, if it isn't there already'"""
        assert token != self
        if token in self.tokens:
            # If the token is in here already we don't need to add it again
            return
        if isinstance(token, MultiAccessToken):
            # If the token is itself a multiaccess token we append its children recursively
            for t in token.tokens:
                self._appendToken(t)
            return
        # Otherwise it is a normal token that isn't in here yet. Append it (and clear the cache).
        self.tokens.append(token)
        self.externalTokenCache = {}
