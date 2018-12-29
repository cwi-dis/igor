from __future__ import unicode_literals
# Access control
from builtins import object
from .consistency import StructuralConsistency

NAMESPACES = { 
    "own":"http://jackjansen.nl/igor/owner",
     }


class AccessToken(object):
    def __init__(self):
        pass

    def addToHeaders(self, headers):
        pass

    def addToHeadersFor(self, headers, url):
        pass

    def addToHeadersAsOTP(self, headers):
        pass
        
    def getIdentifiers(self):
        return []
        
_token = AccessToken()

class AccessControlError(ValueError):
    pass
          
class AccessChecker(object):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self):
        pass

    def allowed(self, operation, token, tentative=False):
        return True
        
_checker = AccessChecker()

class OTPHandler(object):

    def produceOTPForToken(self, token):
        """Produce a one-time-password form of this token, for use internally or for passing to a plugin script (to be used once)"""
        return ":"
            
    def invalidateOTPForToken(self, otp):
        """Invalidate an OTP, if it still exists. Used when a plugin script exits, in case it has not used its OTP"""
        pass
            
    
class TokenStorage(object):
    pass
        
class RevokeList(object):
    pass
    
class IssuerInterface(object):

    def getSelfAudience(self, token=None):
        """Return an audience identifier that refers to us"""
        return '/data'

    def getSelfIssuer(self, token=None):
        """Return URL for ourselves as an issuer"""
        return '/issuer'

    def getSubjectList(self, token=None):
        """Return list of subjects that trust this issuer"""
        return []

    def getAudienceList(self, token=None):
        """Return list of audiences that trust this issuer"""
        return []
        
    def getKeyList(self, token=None):
        """Return list of tuples with (iss, sub, aud) for every key"""
        return []
                
    def getSecretKeysForAudience(self, aud, token=None):
        """Return verbatim secret key for this audience"""
        return []
        
    def createSharedKey(self, sub=None, aud=None, token=None):
        """Create a secret key that is shared between issues and audience"""
        self.igor.app.raiseHTTPError("400 This Igor does not have shared key support")
        
    def deleteSharedKey(self, sub=None, aud=None, token=None):
        """Delete a shared key"""
        self.igor.app.raiseHTTPError("400 This Igor does not have shared key support")

class UserPasswords(object):
        
    def userAndPasswordCorrect(self, username, password):
        """Return True if username/password combination is valid"""
        return True
        
    def setUserPassword(self, username, password, token):
        """Change the password for the user"""
        pass
    

class Access(OTPHandler, TokenStorage, RevokeList, IssuerInterface, UserPasswords):
    def __init__(self):
        self.igor = None
        
    def hasCapabilitySupport(self):
        return False
        
    def setIgor(self, igor):
        """Inform Access singleton of main Igor object. Not passed on __init__ because of app initialization sequence."""
        assert self.igor is None
        self.igor = igor

    def checkerForElement(self, element):
        """Returns an AccessChecker for an XML element"""
        return _checker
            
    def checkerForNewElement(self, path):
        """Returns an AccessChecker for an element that does not exist yet (specified by XPath)"""
        return _checker
            
    def checkerForEntrypoint(self, entrypoint):
        """Returns an AccessChecker for an external entrypoint that is not a tree element"""
        return _checker
        
    def tokenForAction(self, element, token=None):
        """Return token(s) for an <action> element"""
        return _token
        
    def tokenForPlugin(self, pluginname, token=None):
        """Return token(s) for a plugin with the given pluginname"""
        return _token

    def tokenForIgor(self):
        """Return token for igor itself (use sparingly)"""
        return _token
        
    def tokenForAdminUser(self):
        """Return token for admin user of Igor itself (use sparingly)"""
        return _token
        
    def tokenForRequest(self, headers):
        """Return token for the given incoming http(s) request"""
        return _token
        
    def externalTokenForHost(self, host, token=None):
        """If an external token for the given host is available (with the current token) return it"""
        return None
        
    def tokensForSubject(self, sub, token):
        """Return list of token descriptions (accessible via token) valid for subject sub"""
        return []
        
    def getTokenDescription(self, token, tokenId=None):
        """Returns a list of dictionaries which describe the tokens"""
        return []

    def newToken(self, token, tokenId, newOwner, newPath=None, **kwargs):
        """Create a new token based on an existing token. Returns ID of new token."""
        self.igor.app.raiseHTTPError("400 This Igor does not have token support")
        
    def createTokensNeededByElement(self, needElementList, token):
        """Create tokens (if they don't exist yet) based on a list of needCapability elements"""
        pass

    def findCompatibleTokens(self, token, newPath, **kwargs):
        return []

    def passToken(self, token, tokenId, newOwner):
        """Pass token ownership to a new owner. Token must be in the set of tokens that can be passed."""
        self.igor.app.raiseHTTPError("400 This Igor does not have token support")
        
    def revokeToken(self, token, parentId, tokenId):
        """Revoke a token"""
        self.igor.app.raiseHTTPError("400 This Igor does not have token support")
        
    def exportToken(self, token, tokenId, subject=None, lifetime=None, **kwargs):
        """Create an external representation of this token, destined for the given subject"""
        self.igor.app.raiseHTTPError("400 This Igor does not have token support")

    def externalRepresentation(self, token, tokenId):
        self.igor.app.raiseHTTPError("400 This Igor does not have token support")

    def consistency(self, token=None, fix=False, restart=False, extended=False):
        assert self.igor
        assert self.igor.database
        assert self.igor.internal
        if fix:
            self.igor.internal.save(token)
        checker = StructuralConsistency(self.igor, fix, NAMESPACES, _token, extended=extended)
        nChanges, nErrors, rv = checker.check()
        if nChanges:
            self.igor.internal.save(token)
            if restart:
                rv += '\nRestarting Igor'
                self.igor.internal.queue('restart', _token)
            else:
                rv += '\nRestart Igor to update capability data structures'
        return rv
#
# Create a singleton Access object
#   
singleton = None

def createSingleton(noCapabilities=False):
    global singleton
    if singleton: return
    singleton = Access()
