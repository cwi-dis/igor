# Access control
import web

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

class Access:
    def __init__(self):
        pass
        
    def produceOTPForToken(self, token):
        """Produce a one-time-password form of this token, for use internally or for passing to a plugin script (to be used once)"""
        return ":"
            
    def invalidateOTPForToken(self, otp):
        """Invalidate an OTP, if it still exists. Used when a plugin script exits, in case it has not used its OTP"""
        pass
            
    def setDatabase(self, database):
        """Temporary helper method - Informs the access checker where it can find the database object"""
        pass
        
    def setSession(self, session):
        """Temporary helper method - Informs the access checker where sessions are stored"""
        pass
        
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
        
    def getSubjectList(self):
        """Return list of subjects that trust this issuer"""
        return []

    def getAudienceList(self):
        """Return list of audiences that trust this issuer"""
        return []

    def userAndPasswordCorrect(self, username, password):
        """Return True if username/password combination is valid"""
        return True
#
# Create a singleton Access object
#   
singleton = Access()
