from .vars import *

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
