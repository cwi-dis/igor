# Access control
import web
from .consistency import StructuralConsistency

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class AccessToken:
    def __init__(self):
        pass

    def addToHeaders(self, headers):
        pass

    def addToHeadersAsOTP(self, headers):
        pass
        
_token = AccessToken()

class AccessControlError(ValueError):
    pass
          
class AccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self):
        pass

    def allowed(self, operation, token):
        return True
        
_checker = AccessChecker()

class OTPHandler:

    def produceOTPForToken(self, token):
        """Produce a one-time-password form of this token, for use internally or for passing to a plugin script (to be used once)"""
        return ":"
            
    def invalidateOTPForToken(self, otp):
        """Invalidate an OTP, if it still exists. Used when a plugin script exits, in case it has not used its OTP"""
        pass
            
    
class TokenStorage:
    pass
    
class RevokeList:
    pass
    
class IssuerInterface:

    def getSubjectList(self):
        """Return list of subjects that trust this issuer"""
        return []

    def getAudienceList(self):
        """Return list of audiences that trust this issuer"""
        return []
        
    def getKeyList(self):
        """Return list of tuples with (iss, sub, aud) for every key"""
        return []
                
    def createSharedKey(self, sub=None, aud=None):
        """Create a secret key that is shared between issues and audience"""
        raise myWebError("400 This Igor does not have shared key support")
        
    def deleteSharedKey(self, sub=None, aud=None):
        """Delete a shared key"""
        raise myWebError("400 This Igor does not have shared key support")

class UserPasswords:
        
    def userAndPasswordCorrect(self, username, password):
        """Return True if username/password combination is valid"""
        return True
        
    def setUserPassword(self, username, password, token):
        """Change the password for the user"""
        pass
    

class Access(OTPHandler, TokenStorage, RevokeList, IssuerInterface, UserPasswords):
    def __init__(self):
        self.database = None
        self.COMMAND = None
        
    def hasCapabilitySupport(self):
        return False
        
    def setDatabase(self, database):
        """Temporary helper method - Informs the access checker where it can find the database object"""
        self.database = database
        
    def setSession(self, session):
        """Temporary helper method - Informs the access checker where sessions are stored"""
        pass

    def setCommand(self, command):
        """Temporary helper method - Set command processor so access can save the database"""
        self.COMMAND = command
        
    def checkerForElement(self, element):
        """Returns an AccessChecker for an XML element"""
        return _checker
            
    def checkerForEntrypoint(self, entrypoint):
        """Returns an AccessChecker for an external entrypoint that is not a tree element"""
        return _checker
        
    def tokenForAction(self, element):
        """Return token(s) for an <action> element"""
        return _token
        
    def tokenForPlugin(self, pluginname):
        """Return token(s) for a plugin with the given pluginname"""
        # xxxjack not yet implemented
        return _token

    def tokenForIgor(self):
        """Return token for igor itself (use sparingly)"""
        return _token
        
    def tokenForRequest(self, headers):
        """Return token for the given incoming http(s) request"""
        return _token

    def getTokenDescription(self, token, tokenId=None):
        """Returns a list of dictionaries which describe the tokens"""
        return []

    def newToken(self, token, tokenId, newOwner, newPath=None, **kwargs):
        """Create a new token based on an existing token. Returns ID of new token."""
        raise myWebError("400 This Igor does not have token support")
        
    def passToken(self, token, tokenId, newOwner):
        """Pass token ownership to a new owner. Token must be in the set of tokens that can be passed."""
        raise myWebError("400 This Igor does not have token support")
        
    def revokeToken(self, token, parentId, tokenId):
        """Revoke a token"""
        raise myWebError("400 This Igor does not have token support")
        
    def exportToken(self, token, tokenId, subject=None, lifetime=None, **kwargs):
        """Create an external representation of this token, destined for the given subject"""
        raise myWebError("400 This Igor does not have token support")

    def externalRepresentation(self, token, tokenId):
        raise myWebError("400 This Igor does not have token support")

    def consistency(self, token=None, fix=False, restart=False):
        if fix:
            self.COMMAND.save(token)
        checker = StructuralConsistency(self.database, fix, None, _token)
        nChanges, nErrors, rv = checker.check()
        if nChanges:
            self.COMMAND.save(token)
            if restart:
                rv += '\nRestarting Igor'
                self.COMMAND.queue('restart', _token)
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
