from .vars import *
import web

class AccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, access, destination):
        self.access = access
        self.destination = destination
        
    def allowed(self, operation, token):
        """Test whether the token (or set of tokens) allows this operation on the element represented by this AccessChecker"""
        if not token:
            return self._failed(operation, token)
        if not operation in ALL_OPERATIONS:
            raise myWebError("500 Access: unknown operation '%s'" % operation)
        ok = token._allows(operation, self)
        if not ok:
            ok = self._failed(operation, token)
        return ok
        
    def _failed(self, operation, token):
            others = {}
            try:
                others['requestPath'] = web.ctx.path
            except AttributeError:
                pass
            try:
                others['action'] = web.ctx.env.get('original_action')
            except AttributeError:
                pass
            try:
                others['representing'] = web.ctx.env.get('representing')
            except AttributeError:
                pass
            ok = self.access._checkerDisallowed(
                operation=operation,
                path=self.destination,
                capabilities=token._getIdentifiers(),
                **others)
    
class DefaultAccessChecker(AccessChecker):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, access):
        # This string will not occur anywhere (we hope:-)
        self.access = access
        self.destination = "(using default-accesschecker)"

    def allowed(self, operation, token):
        print 'access: no access allowed by DefaultAccessChecker'
        others = {}
        try:
            others['requestPath'] = web.ctx.path
        except AttributeError:
            pass
        try:
            others['action'] = web.ctx.env.get('original_action')
        except AttributeError:
            pass
        try:
            others['representing'] = web.ctx.env.get('representing')
        except AttributeError:
            pass
        ok = self.access._checkerDisallowed(
            operation=operation,
            defaultChecker=True,
            capabilities=token._getIdentifiers(),
            **others)
        return ok
