from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
# Access control
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import xpath
import base64
import random
import time
import urllib.parse
import jwt
import sys
import urllib.request, urllib.parse, urllib.error

from .vars import *
from .capability import *
from .checker import *
from .consistency import *
from .issuer import *

_igorSelfToken = IgorAccessToken()
_accessSelfToken = _igorSelfToken

# xxxjack temporary

from . import capability
capability._accessSelfToken = _accessSelfToken
from . import issuer
issuer._accessSelfToken = _accessSelfToken


def _combineTokens(token1, token2):
    """Return union of two tokens (which may be AccessToken, MultiAccessToken or None)"""
    if token1 is None:
        return token2
    if token2 is None:
        return token1
    if token1 == token2:
        return token1
    if hasattr(token1, '_appendToken'):
        token1._appendToken(token2)
        return token1
    return MultiAccessToken(tokenList=[token1, token2])


class OTPHandler(object):
    """Handle implementation of one-time-passwords (for passing tokens to plugins and scripts)"""
    def __init__(self):
        self._otp2token = {}

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
            print('access: Invalid OTP presented: ', otp)
            self.igor.app.raiseHTTPError("498 Invalid OTP presented")
            
    def invalidateOTPForToken(self, otp):
        """Invalidate an OTP, if it still exists. Used when a plugin script exits, in case it has not used its OTP"""
        if otp in self._otp2token:
            del self._otp2token[otp]

class TokenStorage(object):
    """Handle storing and retrieving capabilities"""
    
    def __init__(self):
        self._tokenCache = {}
        self._defaultTokenInstance = None

    def _clearTokenCaches(self):
        self._tokenCache = {}
        self._defaultTokenInstance = None
        
    def _registerTokenWithIdentifier(self, identifier, token):
        self._tokenCache[identifier] = token
        
    def _loadTokenWithIdentifier(self, identifier):
        if identifier in self._tokenCache:
            return self._tokenCache[identifier]
        capNodeList = self.igor.database.getElements("//au:capability[cid='%s']" % identifier, 'get', _accessSelfToken, namespaces=NAMESPACES)
        if len(capNodeList) == 0:
            print('access: Warning: Cannot get token %s because it is not in the database' % identifier)
            self.igor.app.raiseHTTPError("500 Access: no capability with cid=%s" % identifier)
        elif len(capNodeList) > 1:
            print('access: Error: Cannot get token %s because it occurs %d times in the database' % (identifier, len(capNodeList)))
            self.igor.app.raiseHTTPError("500 Access: multiple capabilities with cid=%s" % identifier)
        capData = self.igor.database.tagAndDictFromElement(capNodeList[0])[1]
        return AccessToken(capData)

    def _defaultToken(self):
        """Internal method - returns token(s) for operations/users/plugins/etc that have no explicit tokens"""
        if self._defaultTokenInstance == None and self.igor.database:
            defaultContainer = self.igor.database.getElements('au:access/au:defaultCapabilities', 'get', _accessSelfToken, namespaces=NAMESPACES)
            if len(defaultContainer) != 1:
                self.igor.app.raiseHTTPError("501 Database should contain single au:access/au:defaultCapabilities")
            self._defaultTokenInstance = self._tokenForElement(defaultContainer[0])
        if self._defaultTokenInstance == None:
            print('access: _defaultToken() called but no database (or no default token in database)')
        return self._defaultTokenInstance
        
    def _tokenForUser(self, username):
        """Internal method - Return token(s) for a user with the given name"""
        if not username or '/' in username:
            self.igor.app.raiseHTTPError('401 Illegal username')
        elements = self.igor.database.getElements('identities/%s' % username, 'get', _accessSelfToken)
        if len(elements) != 1:
            self.igor.app.raiseHTTPError('501 Database error: %d users named %s' % (len(elements), username))
        element = elements[0]
        token = self._tokenForElement(element, owner='identities/%s' % username)
        tokenForAllUsers = self._tokenForElement(element.parentNode)
        token = _combineTokens(token, tokenForAllUsers)
        return _combineTokens(token, self._defaultToken())
 
    def _tokenForElement(self, element, owner=None):
        """Internal method - returns token(s) that are stored in a given element (identity/action/plugindata/etc)"""
        nodelist = xpath.find("au:capability", element, namespaces=NAMESPACES)
        if not nodelist:
            return None
        tokenDataList = [self.igor.database.tagAndDictFromElement(e)[1] for e in nodelist]
        if len(tokenDataList) > 1:
            return MultiAccessToken(tokenDataList, owner=owner)
        rv = AccessToken(tokenDataList[0], owner=owner)
        return rv
        
    def tokensNeededByElement(self, element, optional=False):
        """Return a list of elements describing the tokens this element needs"""
        nodelist = xpath.find(".//au:needCapability", element, namespaces=NAMESPACES)
        if optional:
            nodelist += xpath.find(".//au:mayNeedCapability", element, namespaces=NAMESPACES)
        return nodelist
        
class RevokeList(object):
    """Handles revocation list"""
    def __init__(self):
        self._revokeList = []

    def _addToRevokeList(self, tokenId, nva=None):
        """Add given token to the revocation list"""
        if self._revokeList is None:
            self._loadRevokeList()
        if not tokenId in self._revokeList:
            self._revokeList.append(tokenId)
            revokeData = dict(cid=tokenId)
            if nva:
                revokeData['nva'] = nva
            element = self.igor.database.elementFromTagAndData("revokedCapability", revokeData, namespace=AU_NAMESPACE)
            parents = self.igor.database.getElements('au:access/au:revokedCapabilities', 'post', _accessSelfToken, namespaces=NAMESPACES)
            assert len(parents) == 1
            parents[0].appendChild(element)
            self.igor.database.setChanged()
        
    def _isTokenOnRevokeList(self, tokenId):
        """Check whether a given token is on the revoke list"""
        if self._revokeList is None:
            self._loadRevokeList()
        return tokenId in self._revokeList
        
    def _loadRevokeList(self):
        self._revokeList = self.igor.database.getValues('au:access/au:revokedCapabilities/au:revokedCapability/cid', _accessSelfToken, namespaces=NAMESPACES)
        
class UserPasswords(object):
    """Implements checking of passwords for users"""
    
    def __init__(self):
        pass

    def userAndPasswordCorrect(self, username, password):
        """Return True if username/password combination is valid"""
        assert self.igor
        assert self.igor.database
        # xxxjack this method should not be in the Access element
        if not username:
            if DEBUG: print('access: basic authentication: username missing')
            return False
        if '/' in username:
            self.igor.app.raiseHTTPError('401 Illegal username')
        encryptedPassword = self.igor.database.getValue('identities/%s/encryptedPassword' % username, _accessSelfToken)
        if not encryptedPassword:
            if DEBUG: print('access: basic authentication: no encryptedPassword for user', username)
            return True
        import passlib.hash
        import passlib.utils.binary
        salt = encryptedPassword.split('$')[3]
        salt = passlib.utils.binary.ab64_decode(salt)
        passwordHash = passlib.hash.pbkdf2_sha256.using(salt=salt).hash(password)
        if encryptedPassword != passwordHash:
            if DEBUG: print('access: basic authentication: password mismatch for user', username)
            return False
        if DEBUG: print('access: basic authentication: login for user', username)
        return True

    def setUserPassword(self, username, password, token):
        """Change the password for the user"""
        assert self.igor
        assert self.igor.database
        import passlib.hash
        passwordHash = passlib.hash.pbkdf2_sha256.hash(password)
        element = self.igor.database.elementFromTagAndData('encryptedPassword', passwordHash)
        self.igor.database.delValues('identities/%s/encryptedPassword' % username, token)
        parentElements = self.igor.database.getElements('identities/%s' % username, 'post', token, postChild='encryptedPassword')
        if len(parentElements) == 0:
            self.igor.app.raiseHTTPError('404 User %s not found' % username)
        if len(parentElements) > 1:
            self.igor.app.raiseHTTPError('404 Multiple entries for user %s' % username)
        parentElement = parentElements[0]
        parentElement.appendChild(element)
        self.igor.database.setChanged()

class Access(OTPHandler, TokenStorage, RevokeList, IssuerInterface, UserPasswords):
    def __init__(self, warnOnly=False):
        OTPHandler.__init__(self)
        TokenStorage.__init__(self)
        RevokeList.__init__(self)
        IssuerInterface.__init__(self)
        UserPasswords.__init__(self)
        self.igor = None
        self.warnOnly = warnOnly
        
    def _save(self):
        """Save database or capability store, if possible"""
        if self.igor.internal:
            self.igor.internal.save(_accessSelfToken)

    def hasCapabilitySupport(self):
        return True
        
    def setIgor(self, igor):
        """Inform Access singleton of main Igor object. Not passed on __init__ because of app initialization sequence."""
        assert self.igor is None
        self.igor = igor
        self._initIssuer()

    def checkerForElement(self, element):
        """Returns an AccessChecker for an XML element"""
        assert self.igor
        assert self.igor.database
        if not element:
            print('access: ERROR: attempt to get checkerForElement(None)')
            return DefaultAccessChecker(self)
        path = self.igor.database.getXPathForElement(element)
        if not path:
            print('access: ERROR: attempt to get checkerForElement(%s) that has no XPath' % repr(element))
            return DefaultAccessChecker(self)
        if not path.startswith('/data'):
            print('access: ERROR: attempt to get checkerForElement(%s) with unexpected XPath: %s' % (repr(element), path))
            return DefaultAccessChecker(self)
        return AccessChecker(self, path)
        
    def checkerForNewElement(self, path):
        """Returns an AccessChecker for an element that does not exist yet (specified by XPath)"""
        if not path.startswith('/data'):
            print('access: ERROR: attempt to get checkerForNewElement() with unexpected XPath: %s' %  path)
            return DefaultAccessChecker(self)
        return AccessChecker(self, path)
            
    def checkerForEntrypoint(self, entrypoint):
        """Returns an AccessChecker for an external entrypoint that is not a tree element"""
        if not entrypoint or entrypoint[0] != '/' or entrypoint.startswith('/data'):
            print('access: ERROR: attempt to get checkerForEntrypoint(%s)' % entrypoint)
            return DefaultAccessChecker(self)
        return AccessChecker(self, entrypoint)
        
    def _checkerDisallowed(self, **kwargs):
        if not kwargs.get('tentative'):
            # We don't report errors for tentative checking of access
            if kwargs.get('defaultChecker'):
                print('\taccess: %s ???: no access allowed by default checker' % operation)
            else:
                identifiers = kwargs.get('capID', [])
                print('\taccess: %s %s: no access allowed by %d tokens:' % (kwargs.get('operation', '???'), kwargs.get('path', '???'), len(identifiers)))
                for i in identifiers:
                    print('\t\t%s' % i)
            if 'requestPath' in kwargs:
                print('\taccess: On behalf of request to %s' % kwargs['requestPath'])
            if 'action' in kwargs:
                print('\taccess: On behalf of action %s' % kwargs['action'])
            if 'representing' in kwargs:
                print('\taccess: Representing  %s' % kwargs['representing'])
            self.igor.internal._accessFailure(kwargs)
            if self.warnOnly:
                print('\taccess: allowed anyway because of --warncapabilities mode')
        # If Igor is running in warning-only mode we allow the operation anyway
        return self.warnOnly
        
    def tokenForAction(self, element, token=None):
        """Return token(s) for an <action> element"""
        
        tokenForAction = self._tokenForElement(element)
        if token is None:
            token = tokenForAction
        else:
            token = _combineTokens(token, tokenForAction)
        tokenForAllActions = self._tokenForElement(element.parentNode)
        token = _combineTokens(token, tokenForAllActions)
        return _combineTokens(token, self._defaultToken())
        
    def tokenForPlugin(self, pluginname, token=None):
        """Return token(s) for a plugin with the given pluginname"""
        assert self.igor
        assert self.igor.database
        tokenForPlugin = None
        elements = self.igor.database.getElements("plugindata/%s" % pluginname, 'get', _accessSelfToken)
        if elements:
            tokenForPlugin = self._tokenForElement(elements[0])
        token = _combineTokens(token, tokenForPlugin)
        token = _combineTokens(token, self._defaultToken())
        return token

    def tokenForIgor(self):
        """Return token for igor itself (use sparingly)"""
        return _igorSelfToken

    def tokenForAdminUser(self):
        """Return token for admin user of Igor itself (use sparingly)"""
        return self._tokenForUser('admin')
                
    def tokenForRequest(self, headers):
        """Return token for the given incoming http(s) request"""
        token = None
        if 'HTTP_AUTHORIZATION' in headers:
            authHeader = headers['HTTP_AUTHORIZATION']
            authFields = authHeader.split()
            if authFields[0].lower() == 'bearer':
                decoded = authFields[1] # base64.b64decode(authFields[1])
                if DEBUG: print('access: tokenForRequest: returning token found in Authorization: Bearer header')
                token = self._externalAccessToken(decoded)
            elif authFields[0].lower() == 'basic':
                decoded = base64.b64decode(authFields[1]).decode('utf8')
                if decoded.startswith('-otp-'):
                    # This is a one time pad, not a username/password combination
                    if DEBUG: print('access: tokenForRequest: found OTP in Authorization: Basic header')
                    # OTP-token should already include the default set, so just return
                    return self._consumeOTPForToken(decoded)
                else:
                    username, password = decoded.split(':')
                    if DEBUG: print('access: tokenForRequest: searching for token for Authorization: Basic %s:xxxxxx header' % username)
                    if self.userAndPasswordCorrect(username, password):
                        # _tokenForUser already includes the default set, so just return.
                        return self._tokenForUser(username)
                    else:
                        self.igor.app.raiseHTTPError('401 Unauthorized', headers={'WWW_Authenticate' : 'Basic realm="igor"'})
            # Add more here for other methods
            return _combineTokens(token, self._defaultToken())
        user = self.igor.app.getSessionItem('user')
        if user:
            if DEBUG: print('access: tokenForRequest: returning token for session.user %s' % user)
            return self._tokenForUser(user)
        # xxxjack should we allow carrying tokens in cookies?
        if DEBUG: print('access: no token found for request %s' % headers.get('PATH_INFO', '???'), 'returning', self._defaultToken())
        return self._defaultToken()
        
    def externalTokenForHost(self, host, token=None):
        """If an external token for the given host is available (with the current token) return it"""
        # If the current token gives access to the plugindata for the plugin with this <host> field we also allow access.
        # xxxjack whether we should check for GET access or something else is open to discussion
        pluginElements = self.igor.database.getElements("/data/plugindata/*[host='{}']".format(host), 'get', token)
        for pe in pluginElements:
            pluginName = pe.tagName
            token = self.tokenForPlugin(pluginName, token)
        tid = token._hasExternalRepresentationFor(host)
        if not tid:
            print('access: WARNING: requested external token for request to {} but not available'.format(host))
            return
        extToken = token._getTokenWithIdentifier(tid)
        assert extToken
        rv = extToken._getExternalRepresentation()
        assert rv
        return rv
            
    def tokensForSubject(self, sub, token):
        """Return list of token descriptions (accessible via token) valid for subject sub"""
        # First get the list of all tokens valid for this subject (we filter later for accessible tokens)
        idExpr = "au:access/au:exportedCapabilities/au:capability[sub='{}']/cid".format(sub)
        idList = self.igor.database.getValues(idExpr, _accessSelfToken, namespaces=NAMESPACES)
        # Now attempt to get each of these through the token we carry
        rv = []
        for _, tokId in idList:
            tok = token._getTokenWithIdentifier(tokId)
            if tok:
                rv = rv + tok._getTokenDescription()
        return rv
        
    def _externalAccessToken(self, data):
        """Internal method - Create a token from the given "Authorization: bearer" data"""
        content = self._decodeIncomingData(data)
        cid = content.get('cid')
        if not cid:
            print('access: ERROR: no cid on bearer token %s' % content)
            self.igor.app.raiseHTTPError('400 Missing cid on key')
        if singleton._isTokenOnRevokeList(cid):
            print('access: ERROR: token has been revoked: %s' % content)
            self.igor.app.raiseHTTPError('400 Revoked token')
        return ExternalAccessTokenImplementation(content)
    
    def getTokenDescription(self, token, tokenId=None):
        """Returns a list of dictionaries which describe the tokens"""
        if tokenId:
            originalToken = token
            token = token._getTokenWithIdentifier(tokenId)
            if not token:
                identifiers = originalToken.getIdentifiers()
                print('\taccess: getTokenDescription: no such token ID: %s. Tokens:' % tokenId)
                for i in identifiers:
                    print('\t\t%s' % i)
                self.igor.app.raiseHTTPError('404 No such token: %s' % tokenId)
        return token._getTokenDescription()
        
    def newToken(self, token, tokenId, newOwner, newPath=None, **kwargs):
        """Create a new token based on an existing token. Returns ID of new token."""
        assert self.igor
        assert self.igor.database
        #
        # Split remaining args into rights and other content
        #
        newRights = {}
        content = {}
        for k, v in list(kwargs.items()):
            # Note delegate right is checked implicitly, below.
            if k in NORMAL_OPERATIONS:
                newRights[k] = v
            else:
                content[k] = v
        #
        # Check that original token exists, and allows this delegation
        #
        originalToken = token
        token = token._getTokenWithIdentifier(tokenId)
        if newPath == None:
                newPath = token._getObject()
        if not token:
            identifiers = originalToken.getIdentifiers()
            print('\taccess: newToken: no such token ID: %s. Tokens:' % tokenId)
            for i in identifiers:
                print('\t\t%s' % i)
            self.igor.app.raiseHTTPError('404 No such token: %s' % tokenId)
        if not token._allowsDelegation(newPath, newRights, content.get('aud')):
            self.igor.app.raiseHTTPError('401 Delegation not allowed')
        #
        # Check the new parent exists
        #
        parentElement = self.igor.database.getElements(newOwner, 'post', _accessSelfToken, namespaces=NAMESPACES)
        if len(parentElement) != 1:
            if DEBUG_DELEGATION: print('access: newToken: no unique destination %s' % newOwner)
            self.igor.app.raiseNotfound()
        parentElement = parentElement[0]
        #
        # Construct the data for the new token.
        #
        newId = 'c%d' % random.getrandbits(64)
        token._addChild(newId)
        tokenData = dict(cid=newId, obj=newPath, parent=tokenId)
        moreData = token._getExternalContent()
        for k, v in list(moreData.items()):
            if not k in tokenData:
                tokenData[k] = v
        tokenData.update(newRights)
        tokenData.update(content)
        element = self.igor.database.elementFromTagAndData("capability", tokenData, namespace=AU_NAMESPACE)
        #
        # Insert into the tree
        #
        parentElement.appendChild(element)
        self.igor.database.setChanged()
        #
        # Save
        #
        self._clearTokenCaches()
        self._save()
        #
        # If the new token may affect actions we should update the actions
        #
        if newOwner.startswith('/data/actions') or newOwner.startswith('actions'):
            self.igor.internal.queue('updateActions', _accessSelfToken)
        #
        # Return the ID
        #
        return newId
        
    def createTokensNeededByElement(self, needElementList, token):
        """Create tokens (if they don't exist yet) based on a list of needCapability elements"""
        toCreate = []
        for needElement in needElementList:
            parentElement = needElement.parentNode
            # xxxjack this is a hack. The au:needCapability will be in an <action> or in the plugindata for the element
            if parentElement.tagName == 'action':
                parentToken = self.tokenForAction(parentElement)
                newOwner = self.igor.database.getXPathForElement(parentElement)
            else:
                parentToken = self.tokenForPlugin(parentElement.tagName)
                newOwner = self.igor.database.getXPathForElement(parentElement)
            need = self.igor.database.tagAndDictFromElement(needElement)[1]
            path = need.pop('obj')
            if self.findCompatibleTokens(parentToken, path, **need):
                # The tokens in the parent of the needCapability element already allows it. Nothing to do.
                continue
            # Otherwise we have to create it from the tokens we are carrying
            compatibleTokenIDs = self.findCompatibleTokens(token, path, **need)
            if not compatibleTokenIDs:
                self.igor.app.raiseHTTPError("401 No rights to create capability for %s" % self.igor.database.getXPathForElement(needElement))
            # Remember for later creation
            toCreate.append((compatibleTokenIDs[0], path, need, newOwner))
        # Now create all the needed capabilities
        if not toCreate:
            return
        for tokenId, newPath, need, newOwner in toCreate:
            self.newToken(token, tokenId, newOwner, newPath, **need)
        self._clearTokenCaches()
            
                    
    def findCompatibleTokens(self, token, newPath, **kwargs):
        """Return list of token IDs that allow the given operation."""
        assert self.igor
        assert self.igor.database
        #
        # Get rights from the args
        #
        newRights = {}
        for k, v in list(kwargs.items()):
            # Note delegate right is checked implicitly, below.
            if k in NORMAL_OPERATIONS:
                newRights[k] = v
        rv = []
        for tID in token.getIdentifiers():
            t = token._getTokenWithIdentifier(tID)
            if not t: continue
            if t._allowsDelegation(newPath, newRights, kwargs.get('aud')):
                rv = rv + t.getIdentifiers()
        return rv
                
    def passToken(self, token, tokenId, newOwner):
        """Pass token ownership to a new owner. Token must be in the set of tokens that can be passed."""
        originalToken = token
        tokenToPass = token._getTokenWithIdentifier(tokenId)
        if not tokenToPass:
            identifiers = originalToken.getIdentifiers()
            print('\taccess: passToken: no such token ID: %s. Tokens:' % tokenId)
            for i in identifiers:
                print('\t\t%s' % i)
            self.igor.app.raiseHTTPError("401 No such token: %s" % tokenId)
        oldOwner = tokenToPass._getOwner()
        if not oldOwner:
            self.igor.app.raiseHTTPError("401 Not owner of token %s" % tokenId)
        if oldOwner == newOwner:
            return ''
        if not tokenToPass._setOwner(newOwner):
            self.igor.app.raiseHTTPError("401 Cannot move token %s to new owner %s" % (tokenId, newOwner))
        token._removeToken(tokenId)
        #
        # Save
        #
        self._clearTokenCaches()
        self._save()
        
    def revokeToken(self, token, parentId, tokenId):
        """Revoke a token"""
        parentToken = token._getTokenWithIdentifier(parentId)
        if not parentToken:
            identifiers = token.getIdentifiers()
            print('\taccess: revokeToken: no such token ID: %s. Tokens:' % parentId)
            for i in identifiers:
                print('\t\t%s' % i)
            self.igor.app.raiseHTTPError("404 No such parent token: %s" % parentId)
        self._revokeRecursive(parentToken, tokenId, raiseError=True)
        #
        # Save
        #
        self._clearTokenCaches()
        self._save()
        
    def _revokeRecursive(self, parentToken, childTokenId, raiseError=False):
        """Helper for revoking a token"""
        childToken = parentToken._getTokenWithIdentifier(childTokenId)
        if not childToken:
            print('\taccess: revokeToken: no such token ID: %s. Tokens:' % childTokenId)
            for i in identifiers:
                print('\t\t%s' % i)
            if raiseError:
                self.igor.app.raiseHTTPError("404 No such token: %s" % childTokenId)
            print('Warning: ignored unknown token during recursive revoke')
            return
        # First do the recursion
        grandChildren = childToken._getChildIdList()
        for grandChildId in grandChildren:
            self._revokeRecursive(childToken, grandChildId)
        self._addToRevokeList(childTokenId, childToken.content.get('nva'))
        childToken._revoke()
        parentToken._delChild(childTokenId)
        
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
        if 'aud' in kwargs:
            audience = kwargs['aud']
        else:
            audience = self.getSelfAudience()
            kwargs['aud'] = self.getSelfAudience()
        kwargs['iss'] = self.getSelfIssuer()
        #
        # Create the new token
        #
        # xxxjack we should check whehter the given external token already exists and
        # simply return the external representation if it does...
        #
        newTokenId = self.newToken(token, tokenId, self._getExternalTokenOwner(), **kwargs)
        tokenToExport = token._getTokenWithIdentifier(newTokenId)
        if not tokenToExport:
            # The new token is a grandchild of our token, so we may not be able to get it directly.
            # Try harder.
            parentToken = token._getTokenWithIdentifier(tokenId)
            tokenToExport = parentToken._getTokenWithIdentifier(newTokenId)
        if not tokenToExport:
            self.igor.app.raiseHTTPError('500 created token %s but it does not exist' % newTokenId)
        #
        # Create the external representation
        #
        assert tokenToExport
        assert tokenToExport._hasExternalRepresentationFor(audience)
        externalRepresentation = tokenToExport._getExternalRepresentation()
        #
        # Save
        #
        self._save()
        return externalRepresentation
        
    def externalRepresentation(self, token, tokenId):
        """Return external representation for given token"""
        tokenToExport = token._getTokenWithIdentifier(tokenId, recursive=True)
        if not tokenToExport:
            identifiers = token.getIdentifiers()
            print('\taccess: externalRepresentation: no such token ID: %s. Tokens:' % tokenId)
            for i in identifiers:
                print('\t\t%s' % i)
            self.igor.app.raiseHTTPError("401 No such token: %s" % tokenId)
        assert tokenToExport._hasExternalRepresentationFor(self.getSelfAudience())
        externalRepresentation = tokenToExport._getExternalRepresentation()
        return externalRepresentation
        
    def _getExternalTokenOwner(self):
        """Return the location where we store external tokens"""
        return '/data/au:access/au:exportedCapabilities'
        
    def consistency(self, token=None, fix=False, restart=False, extended=False):
        assert self.igor
        assert self.igor.database
        assert self.igor.internal
        if fix:
            self.igor.internal.save(token)
        checker = CapabilityConsistency(self.igor, fix, AU_NAMESPACE, _accessSelfToken, extended=extended)
        nChanges, nErrors, rv = checker.check()
        if nChanges:
            self.igor.internal.save(token)
            if restart:
                rv += '\nRestarting Igor'
                self.igor.internal.queue('restart', _accessSelfToken)
            else:
                rv += '\nRestart Igor to update capability data structures'
        return rv
#
# Create a singleton Access object
#   
singleton = None

def createSingleton(noCapabilities=False, warnOnly=False):
    global singleton
    if singleton: return
    if warnOnly:
        print('Warning: capability-based access control disabled, with warnings', file=sys.stderr)
        AccessChecker.WARN_ONLY = True
    if noCapabilities:
        print('Warning: capability-based access control disabled', file=sys.stderr)
        from . import dummyAccess
        dummyAccess.createSingleton(noCapabilities)
        singleton = dummyAccess.singleton
    else:
        singleton = Access(warnOnly=warnOnly)
        capability.singleton = singleton
    
