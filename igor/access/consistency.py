VERBOSE=False

class CannotFix(Exception):
    pass
    
class CapabilityConsistency:
    def __init__(self, database, fix, namespaces, token, extended=False):
        self.database = database
        self.fix = fix
        self.namespaces = namespaces
        self.token = token
        self.extended = extended
        self.status = ''
        
    def _status(self, msg):
        if VERBOSE:
            print msg
        self.status += msg + '\n'
        
    def _checkExists(self, path, dontfix=False, context=None):
        if VERBOSE:
            print 'consistency._checkExists(%s)' % path
        if type(context) == type(''):
            contextElements = self.database.getElements(context, 'get', self.token, namespaces=self.namespaces)
            if len(contextElements) != 1:
                self._status('Non-singleton context: %s' % context)
                raise CannotFix
            context = contextElements[0]
                
        allElements = self.database.getElements(path, 'get', self.token, namespaces=self.namespaces, context=context)
        if len(allElements) == 0:
            if self.fix and not dontfix:
                self._status('Cannot fix yet: should create %s' % path)
                raise CannotFix # Net yet implemented
            else:
                self._status('Missing: %s' % path)
        
    def _checkUnique(self, path, dontfix=False, context=None):
        if VERBOSE:
            print 'consistency._checkUnique(%s)' % path
        if type(context) == type(''):
            contextElements = self.database.getElements(context, 'get', self.token, namespaces=self.namespaces)
            if len(contextElements) != 1:
                self._status('Non-singleton context: %s' % context)
                raise CannotFix
            context = contextElements[0]
                
        allElements = self.database.getElements(path, 'get', self.token, namespaces=self.namespaces, context=context)
        if len(allElements) > 1:
            if self.fix and not dontfix:
                self._status('Cannot fix yet: should remove additional %s' % path)
                raise CannotFix # Net yet implemented
            else:
                self._status('Non-unique: %s' % path)
        
    def _checkSingleton(self, path1, path2, dontfix=False, context=None):
        if VERBOSE:
            print 'consistency._checkSingleton(%s, %s)' % (path1, path2)
        self._checkExists(path1 + '/' + path2, dontfix=dontfix, context=context)
        self._checkUnique(path1 + '/' + path2, dontfix=dontfix, context=context)
        if self.extended:
             self._checkUnique('//' + path2, dontfix=dontfix, context=context)
        
    def _getAllElements(self, path):
        rv = self.database.getElements(path, 'get', self.token, namespaces=self.namespaces)
        if VERBOSE:
            print 'consistency._getAllElements(%s) returns %d items' % (path, len(rv))
        return rv
        
    def check(self):
        if VERBOSE:
            self._status('Starting consistency check')
        try:
            #
            # First set of checks: determine that the infrastructure needed by the capabilities exists
            #
            self._checkExists('/data', dontfix=True)

            self._checkSingleton('/data', 'au:access')
            self._checkSingleton('/data/au:access', 'au:defaultCapabilities')
            self._checkSingleton('/data/au:access', 'au:exportedCapabilities')
            self._checkSingleton('/data/au:access', 'au:revokedCapabilities')
            self._checkSingleton('/data/au:access', 'au:unusedCapabilities')
            self._checkSingleton('/data/au:access', 'au:sharedKeys')

            self._checkExists('/data/identities')
            self._checkUnique('/data/identities')
        
            self._checkExists('/data/identities/admin')
            self._checkUnique('/data/identities/admin')
        
            for userElement in self._getAllElements('/data/identities/*'):
                userName = userElement.tagName
                if ':' in userName or '{' in userName:
                    continue # This is not a user but a capability
                self._checkUnique(userName, context='/data/identities', dontfix=True)
            
            self._checkExists('/data/actions')
            self._checkUnique('/data/actions')
            
            self._checkExists("/data/identities/admin/au:capability[cid='0']", dontfix=True)
            
            #
            # Second set of checks: test that capability tree is indeed a tree
            #
            
            allCapIDs = self.database.getValues('//au:capability/cid', token=self.token, namespaces=self.namespaces)
            if len(allCapIDs) != len(set(allCapIDs)):
                for c in set(allCapIDs):
                    allCapIDs.remove(c)
                for c in allCapIDs:
                    self._status('Non-unique cid: %s' % c)
                raise CannotFix
            allCaps = self._getAllElements('//au:capability')
        except CannotFix:
            self._status('* No further fixes attempted')
        self._status('Consistency check finished')
        rv = self.status
        self.status = ''
        return rv
        
