from __future__ import print_function
from __future__ import unicode_literals
from builtins import object
from .vars import *

class AccessChecker(object):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, access, destination):
        self.access = access
        self.destination = destination
        
    def allowed(self, operation, token, tentative=False):
        """Test whether the token (or set of tokens) allows this operation on the element represented by this AccessChecker"""
        if not token:
            return self._failed(operation, token, tentative)
        if not operation in ALL_OPERATIONS:
            self.access.igor.app.raiseHTTPError("500 Access: unknown operation '%s'" % operation)
        ok = token._allows(operation, self)
        if not ok:
            ok = self._failed(operation, token, tentative)
        return ok
        
    def _failed(self, operation, token, tentative):
        traceInfo = self.access.igor.app.getOperationTraceInfo()
        ok = self.access._checkerDisallowed(
            operation=operation,
            path=self.destination,
            capID=token.getIdentifiers(),
            tentative=tentative,
            **traceInfo)
        return ok
    
class DefaultAccessChecker(AccessChecker):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, access):
        # This string will not occur anywhere (we hope:-)
        self.access = access
        self.destination = "(using default-accesschecker)"

    def allowed(self, operation, token, tentative=False):
        print('access: no access allowed by DefaultAccessChecker')
        traceInfo = self.access.igor.app.getOperationTraceInfo()
        ok = self.access._checkerDisallowed(
            operation=operation,
            defaultChecker=True,
            capabilities=token.getIdentifiers(),
            tentative=tentative,
            **traceinfo)
        return ok
