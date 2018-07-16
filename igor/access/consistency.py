import random

VERBOSE=False

class CannotFix(Exception):
    pass
    
class StructuralConsistency:
    def __init__(self, database, fix, namespaces, token, extended=False):
        self.database = database
        self.fix = fix
        self.namespaces = namespaces
        self.token = token
        self.extended = extended
        self.status = ''
        self.nChanges = 0
        self.nErrors = 0
        
    def _status(self, msg, isError=True):
        if VERBOSE:
            print msg
        self.status += msg + '\n'
        if isError:
            self.nErrors += 1
        
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
                parentPath, tag = self.database.splitXPath(path, allowNamespaces=True)
                parentElements = self.database.getElements(parentPath, 'post', self.token, namespaces=self.namespaces)
                if len(parentElements) != 1:
                    self._status('Cannot create element: non-singleton parent %s' % parentPath)
                    raise CannotFix
                parentElement = parentElements[0]
                if tag[:3] == 'au:':
                    newElement = self.database.elementFromTagAndData(tag[3:], '', namespace=self.namespaces)
                else:
                    newElement = self.database.elementFromTagAndData(tag, '')
                parentElement.appendChild(newElement)
                self.nChanges += 1
                self._status('Created: %s' % path, isError=False)
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
        
    def _getValues(self, path, context=None):
        if type(context) == type(''):
            contextElements = self.database.getElements(context, 'get', self.token, namespaces=self.namespaces)
            if len(contextElements) != 1:
                self._status('Non-singleton context: %s' % context)
                raise CannotFix
            context = contextElements[0]
        return map(lambda x: x[1], self.database.getValues(path, token=self.token, namespaces=self.namespaces, context=context))

    def _getValue(self, path, context=None):
        values = self._getValues(path, context=context)
        if len(values) == 0:
            return None
        if len(values) == 1:
            return values[0]
        if context and type(context) != type(''):
            context = self.database.getXPathForElement(context)
        self._status('Non-unique value: %s (context=%s)' % (path, context))
        raise CannotFix

    def _checkInfrastructureItem(self, path, item):
        itemTag = item[0]
        itemContent = item[1:]
        itemPath = path + itemTag
        self._checkExists(itemPath)
        self._checkUnique(itemPath)
        for subItem in itemContent:
            self._checkInfrastructureItem(itemPath, subItem)
            
    def check(self):
        databaseTemplate = (
            '/data',
                ('/environment',
                    ('/systemHealth',
                        ('/messages',),
                    ),
                ),
                ('/status',
                    ('/igor',),
                    ('/sensors',),
                    ('/devices',),
                    ('/services',),
                ),
                ('/sensors',),
                ('/devices',),
                ('/services',
                    ('/igor',),
                ),
                ('/people',),
                ('/identities',),
                ('/actions',),
                ('/sandbox',),
                ('/plugindata',),
            )
        if VERBOSE:
            self._status('Starting infrastructure consistency check', isError=False)
        try:
            self._checkInfrastructureItem('', databaseTemplate)
        except CannotFix:
            self._status('* Infrastructure consistency check failed', isError=False)
            raise
        self._status('Infrastructure consistency check finished', isError=False)
        return self.nChanges, self.nErrors, self.status

class CapabilityConsistency(StructuralConsistency):

    def _hasCapability(self, location, **kwargs):
        expr = location + '/au:capability'
        for k, v in kwargs.items():
            subExpr = "[%s='%s']" % (k, v)
            expr += subExpr
        allCaps = self.database.getElements(expr, 'get', token=self.token, namespaces=self.namespaces)
        if len(allCaps) == 0:
            if self.fix:
                self._createCapability(location, kwargs)
                self._status('Fixed: Missing standard capability %s' % expr, isError=False)
            else:
                self._status('Missing standard capability %s' % expr)
        elif len(allCaps) > 1:
                self._status('Duplicate standard capability %s' % expr)
            
    def _createCapability(self, location, content):
        if not 'cid' in content:
            content['cid'] = 'c%d' % random.getrandbits(64)
        if content['cid'] != 'root' and not 'parent' in content:
            content['parent'] = 'root'
        newElement = self.database.elementFromTagAndData('capability', content, namespace=self.namespaces)
        parentElements = self.database.getElements(location, 'post', token=self.token, namespaces=self.namespaces)
        if len(parentElements) != 1:
            self._status('Cannot create capability: non-singleton destination %s' % location)
            raise CannotFix
        parentElement = parentElements[0]
        parentElement.appendChild(newElement)
        self.nChanges += 1
        if content['cid'] == 'root':
            return
        # Update parent, if needed
        parentCid = content['parent']
        parent = self._getAllElements("//au:capability[cid='%s']" % parentCid)
        if len(parent) != 1:
            self._status('Cannot update parent capability: Multiple capabilities with cid=%s' % parentCid)
            raise CannotFix
        parent = parent[0]
        parent.appendChild(self.database.elementFromTagAndData('child', content['cid']))
        
    def _fixParentCapability(self, cap, cid):
        parentCid = 'root'
        cap.appendChild(self.database.elementFromTagAndData('parent', parentCid))
        parent = self._getAllElements("//au:capability[cid='%s']" % parentCid)
        if len(parent) != 1:
            self._status('Cannot update parent capability: Multiple capabilities with cid=%s' % parentCid)
            raise CannotFix
        parent = parent[0]
        parent.appendChild(self.database.elementFromTagAndData('child', cid))
        self.nChanges += 1
        

    def check(self):
        with self.database:
            try:
                StructuralConsistency.check(self)
            
                if VERBOSE:
                    self._status('Starting capability consistency check', isError=False)
                #
                # Very first check: see whether we have the correct namespace declarations
                #
                rootElements = self.database.getElements('/data', 'get', token=self.token)
                if len(rootElements) != 1:
                    self._status('Multiple /data root elements')
                    raise CannotFix
                rootElement = rootElements[0]
                for nsName, nsUrl in self.namespaces.items():
                    have = rootElement.getAttribute('xmlns:' + nsName)
                    if have != nsUrl:
                        if self.fix:
                            rootElement.setAttribute('xmlns:' + nsName, nsUrl)
                            self._status('Added namespace declaration for xmlns:%s=%s' % (nsName, nsUrl), isError=False)
                            self.nChanges += 1
                        else:
                            self._status('Missing namespace declaration xmlns:%s=%s' % (nsName, nsUrl))
                            raise CannotFix
                #
                # First set of checks: determine that the infrastructure needed by the capabilities exists
                #

                self._checkSingleton('/data', 'au:access')
                self._checkSingleton('/data/au:access', 'au:defaultCapabilities')
                self._checkSingleton('/data/au:access', 'au:exportedCapabilities')
                self._checkSingleton('/data/au:access', 'au:revokedCapabilities')
                self._checkSingleton('/data/au:access', 'au:unusedCapabilities')
                self._checkSingleton('/data/au:access', 'au:sharedKeys')

        
                self._checkExists('/data/identities/admin')
                self._checkUnique('/data/identities/admin')
        
                for userElement in self._getAllElements('/data/identities/*'):
                    userName = userElement.tagName
                    if ':' in userName or '{' in userName:
                        continue # This is not a user but a capability
                    self._checkUnique(userName, context='/data/identities', dontfix=True)
            
            
                #
                # Second set - all the default and important capabilities exist
                #
                self._hasCapability('/data/identities/admin', cid='root')
                
                self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-static', obj='/static', get='child')
                self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-environment', obj='/data/environment', get='descendant-or-self')
                self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-status', obj='/data/status', get='descendant-or-self')
                self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-igor', obj='/data/services/igor', get='descendant-or-self')
                self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-accessControl', obj='/internal/accessControl', get='child')

                self._hasCapability('/data/identities', cid='people-people', obj='/data/people', get='descendant-or-self')

                self._hasCapability('/data/identities/admin', cid='admin-data', obj='/data', get='descendant-or-self', put='descendant', post='descendant', delete='descendant')
                self._hasCapability('/data/identities/admin', cid='admin-action', obj='/action', get='descendant')
                self._hasCapability('/data/identities/admin', cid='admin-internal', obj='/internal', get='descendant')
                self._hasCapability('/data/identities/admin', cid='admin-plugin', obj='/plugin', get='descendant')
                self._hasCapability('/data/identities/admin', cid='admin-pluginscript', obj='/pluginscript', get='descendant')
            
                for userElement in self._getAllElements('/data/identities/*'):
                    userName = userElement.tagName
                    if ':' in userName or '{' in userName or userName == 'admin':
                        continue # This is not a user but a capability
                    userPath = '/data/identities/'+userName
                    self._hasCapability(userPath, obj=userPath, get='descendant-or-self', put='descendant', post='descendant', delete='descendant')
                    self._hasCapability(userPath, obj='/data/people/'+userName, put='descendant', post='descendant', delete='descendant')
            
                self._hasCapability('/data/actions', cid='action-plugin', obj='/plugin', get='descendant')
                self._hasCapability('/data/actions', cid='action-pluginscript', obj='/pluginscript', get='descendant')
                self._hasCapability('/data/actions', cid='action-action', obj='/action', get='child')
                #
                # Second set of checks: test that capability tree is indeed a tree
                #
            
                allCapIDs = self._getValues('//au:capability/cid')
                if len(allCapIDs) != len(set(allCapIDs)):
                    for c in set(allCapIDs):
                        allCapIDs.remove(c)
                    for c in allCapIDs:
                        self._status('Non-unique cid: %s' % c)
                    raise CannotFix
                allCaps = self._getAllElements('//au:capability')
                cid2cap = {}
                cid2parent = {}
                # create mapping cid->capability
                for cap in allCaps:
                    cid = self._getValue('cid', cap)
                    if not cid:
                        if self.fix:
                            self._status('Cannot fix yet: Capability %s has no cid' % self.database.getXPathForElement(cap))
                            raise CannotFix
                        else:
                            self._status('Cannot fix yet: Capability %s has no cid' % self.database.getXPathForElement(cap))
                    cid2cap[cid] = cap
                # Check parent/child relation for each capability
                for cap in allCaps:
                    cid = self._getValue('cid', cap)
                    if not cid:
                        continue # Error given earlier already
                    for childCid in self._getValues('child::child', cap):
                        if not childCid in cid2cap:
                            if self.fix:
                                self.database.delValues("child::child[text()='%s']" % childCid, token=self.token, context=cap)
                                self.nChanges += 1
                                self._status('Removed child %s from %s' % (childCid, cid), isError=False)
                            else:
                                self._status('Non-existing child %s in %s' % (childCid, cid))
                        elif childCid in cid2parent:
                            if self.fix:
                                self._status('Cannot fix yet: Child with multiple parents: %s' % childCid)
                                raise CannotFix
                            else:
                                self._status('Child with multiple parents: %s' % childCid)
                        else:
                            cid2parent[childCid] = cid
                # Check child/parent relation for each capability
                for cap in allCaps:
                    cid = self._getValue('cid', cap)
                    if not cid:
                        continue # Error given earlier already
                    if cid == 'root':
                        continue
                    parentCid = self._getValue('child::parent', cap)
                    expectedParent = cid2parent.get(cid)
                    if parentCid != expectedParent:
                        if self.fix:
                            if expectedParent:
                                if parentCid:
                                    self._status('Cannot fix yet: Inconsistent parent for %s (%s versus %s)' % (cid, parentCid, expectedParent))
                                    raise CannotFix
                                else:
                                    self._status('Cannot fix yet: %s has no parent, but is listed as child of %s' % (cid, expectedParent))
                                    raise CannotFix
                            self.database.delValues('child::parent', token=self.token, context=cap)
                            self.nChanges += 1
                            parentCid = None
                        else:
                            if expectedParent and not parentCid:
                                self._status('Capability %s has no parent but listed by %s as child' % (cid, expectedParent))
                            elif parentCid and not expectedParent:
                                self._status('Parent for %s is %s but not listed there as child' % (cid, parentCid))
                            else:
                                self._status('Inconsistent parent for %s (%s versus %s)' % (cid, parentCid, expectedParent))
                    if not parentCid:
                        if self.fix:
                            self._fixParentCapability(cap, cid)
                            self._status('Orphaned capability %s given parent root' % cid, isError=False)
                        else:
                            self._status('Capability %s has no parent' % self.database.getXPathForElement(cap))
                #
                # Third set of checks: are capabilities stored in the correct places
                #
                expectedLocations = (
                    self._getAllElements('/data/au:access/au:defaultCapabilities') +
                    self._getAllElements('/data/au:access/au:exportedCapabilities') +
                    self._getAllElements('/data/au:access/au:unusedCapabilities') +
                    self._getAllElements('/data/identities') +
                    self._getAllElements('/data/identities/*') +
                    self._getAllElements('/data/actions') +
                    self._getAllElements('/data/actions/action') +
                    self._getAllElements('/data/plugindata/*')
                    )
                actualLocations = self._getAllElements('//au:capability/..')
                badLocations = []
                for loc in actualLocations:
                    if not loc in expectedLocations:
                        if not loc in badLocations:
                            badLocations.append(loc)
                for loc in badLocations:
                    parentPath = self.database.getXPathForElement(loc)
                    cidList = self._getValues('au:capabiity/cid', context=loc)
                    if not cidList:
                        self._status('Listed as parent of capabilities but cannot find them: %s' % path)
                        continue
                    for cid in cidList:
                        if self.fix:
                            self._status('Cannot fix yet: Capability %s: in unexpected location %s' % (cid, parentPath))
                            raise CannotFix
                        else:
                            self._status('Capability %s: in unexpected location %s' % (cid, parentPath))
                #
                # Fourth set: that we have all the expected capabilities
                #
                
                
                                
            except CannotFix:
                self._status('* No further fixes attempted', isError=False)
            if self.nChanges:
                self._status('Number of changes made to database: %d' % self.nChanges, isError=False)
            if self.nErrors:
                self._status('Number of errors remaining: %d' % self.nErrors, isError=False)
            self._status('Capability consistency check finished', isError=False)
            rv = self.status
            self.status = ''
            return self.nChanges, self.nErrors, rv
        
