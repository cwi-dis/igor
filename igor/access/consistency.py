import random

VERBOSE=False

OWN_NAMESPACE="http://jackjansen.nl/igor/owner" # Shoulnd't be here, really...

class CannotFix(Exception):
    pass
    
class StructuralConsistency:
    def __init__(self, igor, fix, namespaces, token, extended=False):
        self.igor = igor
        self.database = self.igor.database
        self.fix = fix
        self.namespaces = namespaces
        self.token = token
        self.extended = extended
        self.status = ''
        self.nChanges = 0
        self.nErrors = 0
        
    def _status(self, msg, isError=True):
        if VERBOSE:
            print(msg)
        self.status += msg + '\n'
        if isError:
            self.nErrors += 1
        
    def _checkExists(self, path, dontfix=False, context=None):
        if VERBOSE:
            print(f'consistency._checkExists({path})')
        if type(context) == type(''):
            contextElements = self.database.getElements(context, 'get', self.token, namespaces=self.namespaces)
            if len(contextElements) != 1:
                self._status(f'Non-singleton context: {context}')
                raise CannotFix
            context = contextElements[0]
                
        allElements = self.database.getElements(path, 'get', self.token, namespaces=self.namespaces, context=context)
        if len(allElements) == 0:
            if self.fix and not dontfix:
                parentPath, tag = self.database.splitXPath(path, allowNamespaces=True)
                parentElements = self.database.getElements(parentPath, 'post', self.token, namespaces=self.namespaces)
                if len(parentElements) != 1:
                    self._status(f'Cannot create element: non-singleton parent {parentPath}')
                    raise CannotFix
                parentElement = parentElements[0]
                if tag[:3] == 'au:':
                    newElement = self.database.elementFromTagAndData(tag[3:], '', namespace=self.namespaces)
                else:
                    newElement = self.database.elementFromTagAndData(tag, '')
                parentElement.appendChild(newElement)
                self.database.setChanged()
                self.nChanges += 1
                self._status(f'Created: {path}', isError=False)
            else:
                self._status(f'Missing: {path}')
        
    def _checkUnique(self, path, dontfix=False, context=None):
        if VERBOSE:
            print(f'consistency._checkUnique({path})')
        if type(context) == type(''):
            contextElements = self.database.getElements(context, 'get', self.token, namespaces=self.namespaces)
            if len(contextElements) != 1:
                self._status(f'Non-singleton context: {context}')
                raise CannotFix
            context = contextElements[0]
                
        allElements = self.database.getElements(path, 'get', self.token, namespaces=self.namespaces, context=context)
        if len(allElements) > 1:
            if self.fix and not dontfix:
                self._status(f'Cannot fix yet: should remove additional {path}')
                raise CannotFix # Net yet implemented
            else:
                self._status(f'Non-unique: {path}')
        
    def _checkSingleton(self, path1, path2, dontfix=False, context=None):
        if VERBOSE:
            print(f'consistency._checkSingleton({path1}, {path2})')
        self._checkExists(path1 + '/' + path2, dontfix=dontfix, context=context)
        self._checkUnique(path1 + '/' + path2, dontfix=dontfix, context=context)
#        if self.extended:
#             self._checkUnique('//' + path2, dontfix=dontfix, context=context)
        
    def _getAllElements(self, path):
        rv = self.database.getElements(path, 'get', self.token, namespaces=self.namespaces)
        if VERBOSE:
            print(f'consistency._getAllElements({path}) returns {len(rv)} items')
        return rv
        
    def _getValues(self, path, context=None):
        if type(context) == type(''):
            contextElements = self.database.getElements(context, 'get', self.token, namespaces=self.namespaces)
            if len(contextElements) != 1:
                self._status(f'Non-singleton context: {context}')
                raise CannotFix
            context = contextElements[0]
        return [x[1] for x in self.database.getValues(path, token=self.token, namespaces=self.namespaces, context=context)]

    def _getValue(self, path, context=None):
        values = self._getValues(path, context=context)
        if len(values) == 0:
            return None
        if len(values) == 1:
            return values[0]
        if context and type(context) != type(''):
            context = self.database.getXPathForElement(context)
        self._status(f'Non-unique value: {path} (context={context})')
        raise CannotFix

    def _checkInfrastructureItem(self, path, item):
        itemTag = item[0]
        itemContent = item[1:]
        itemPath = path + itemTag
        self._checkExists(itemPath)
        self._checkUnique(itemPath)
        for subItem in itemContent:
            self._checkInfrastructureItem(itemPath, subItem)
            
    def _checkNamespaces(self):
        rootElements = self.database.getElements('/data', 'get', token=self.token)
        if len(rootElements) != 1:
            self._status('Multiple /data root elements')
            raise CannotFix
        rootElement = rootElements[0]
        for nsName, nsUrl in list(self.namespaces.items()):
            have = rootElement.getAttribute('xmlns:' + nsName)
            if have != nsUrl:
                if self.fix:
                    rootElement.setAttribute('xmlns:' + nsName, nsUrl)
                    self._status(f'Added namespace declaration for xmlns:{nsName}={nsUrl}', isError=False)
                    self.database.setChanged()
                    self.nChanges += 1
                else:
                    self._status(f'Missing namespace declaration xmlns:{nsName}={nsUrl}')
                    raise CannotFix

    def _checkPlugins(self):
        installedPlugins = set(self.igor.plugins.list())
        allPluginOwnedElements = self.database.getElements('//*[@own:plugin]', 'get', token=self.token)
        mentionedPlugins = set()
        for elt in allPluginOwnedElements:
            owner = elt.getAttributeNS(OWN_NAMESPACE, "plugin")
            if not owner:
                continue
            if owner in installedPlugins:
                mentionedPlugins.add(owner)
                continue
            # The plugin owning this element doesn't exist
            xp = self.database.getXPathForElement(elt)
            if self.fix:
                self.database.delValues(xp, self.token)
                self.database.setChanged()
                self._status(f'Deleted {xp}, belonged to missing plugin {owner}', isError=False)
                self.nChanges += 1
            else:
                self._status(f'Missing plugin "{owner}" owns {xp}')
        for plugin in installedPlugins:
            if plugin in mentionedPlugins:
                continue
            self._status(f'Warning: plugin "{plugin}" does not own anything in the database', isError=False)
        
    def do_check(self):
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
                ('/identities',
                    ('/admin',)
                ),
                ('/actions',),
                ('/sandbox',),
                ('/plugindata',),
            )
        if VERBOSE:
            self._status('Starting infrastructure consistency check', isError=False)
        try:
            #
            # Very first check: see whether we have the correct namespace declarations
            #
            self._checkNamespaces()
            #
            # Check plugins and corresponding own:plugin attributes
            self._checkPlugins()
            #
            # Now check that we have all the needed infrastructural items
            #
            self._checkInfrastructureItem('', databaseTemplate)
        except CannotFix:
            self._status('* Infrastructure consistency check failed', isError=False)
            raise
        #
        # Check that all users are unique and have plugindata entries
        #
        for userElement in self._getAllElements('/data/identities/*'):
            userName = userElement.tagName
            if ':' in userName or '{' in userName:
                continue # This is not a user but a capability
            self._checkUnique(userName, context='/data/identities', dontfix=True)
            self._checkSingleton(f'/data/identities/{userName}', 'plugindata')
    
        #
        # Now check that all plugins exist
        #
        # xxxjack to be done
        self._status('Infrastructure consistency check finished', isError=False)
        return self.nChanges, self.nErrors, self.status

    def check(self):
        try:
            self.do_check()
        except CannotFix:
            self._status('* No further fixes attempted', isError=False)
        if self.nChanges:
            self._status('Number of changes made to database: %d' % self.nChanges, isError=False)
        if self.nErrors:
            self._status('Number of errors remaining: %d' % self.nErrors, isError=False)
        rv = self.status
        self.status = ''
        return self.nChanges, self.nErrors, rv
            
class CapabilityConsistency(StructuralConsistency):

    def _hasCapability(self, location, **kwargs):
        expr = location + '/au:capability'
        for k, v in list(kwargs.items()):
            subExpr = f"[{k}='{v}']"
            expr += subExpr
        allCaps = self.database.getElements(expr, 'get', token=self.token, namespaces=self.namespaces)
        if len(allCaps) == 0:
            # If this is a standard capability check whether it exists with incorrect settings
            if 'cid' in kwargs:
                allCaps = self.database.getElements("//au:capability[cid='{}']".format(kwargs['cid']), 'get', token=self.token, namespaces=self.namespaces)
                if len(allCaps):
                    self._status(f'Standard capability {expr} is in wrong place or has wrong content')
                    raise CannotFix
            if self.fix:
                self._createCapability(location, kwargs)
                self._status(f'Fixed: Missing standard capability {expr}', isError=False)
            else:
                self._status(f'Missing standard capability {expr}')
        elif len(allCaps) > 1:
                self._status(f'Duplicate standard capability {expr}')
            
    def _createCapability(self, location, content):
        if not 'cid' in content:
            content['cid'] = 'c%d' % random.getrandbits(64)
        if content['cid'] != 'root' and not 'parent' in content:
            content['parent'] = 'root'
        newElement = self.database.elementFromTagAndData('capability', content, namespace=self.namespaces)
        parentElements = self.database.getElements(location, 'post', token=self.token, namespaces=self.namespaces)
        if len(parentElements) != 1:
            self._status(f'Cannot create capability: non-singleton destination {location}')
            raise CannotFix
        parentElement = parentElements[0]
        parentElement.appendChild(newElement)
        self.database.setChanged()
        self.nChanges += 1
        if content['cid'] == 'root':
            return
        # Update parent, if needed
        parentCid = content['parent']
        parent = self._getAllElements(f"//au:capability[cid='{parentCid}']")
        if len(parent) != 1:
            self._status(f'Cannot update parent capability: Multiple capabilities with cid={parentCid}')
            raise CannotFix
        parent = parent[0]
        parent.appendChild(self.database.elementFromTagAndData('child', content['cid']))
        self.database.setChanged()
        
    def _fixParentCapability(self, cap, cid):
        parentCid = 'root'
        cap.appendChild(self.database.elementFromTagAndData('parent', parentCid))
        self.database.setChanged()
        parent = self._getAllElements(f"//au:capability[cid='{parentCid}']")
        if len(parent) != 1:
            self._status(f'Cannot update parent capability: Multiple capabilities with cid={parentCid}')
            raise CannotFix
        parent = parent[0]
        parent.appendChild(self.database.elementFromTagAndData('child', cid))
        self.database.setChanged()
        self.nChanges += 1
        
    def _getTokensNeededByElement(self, element, optional=False):
        """Return a list of dictionaries describing the tokens this element needs"""
        nodelist = self.database.getElements("au:needCapability", 'get', self.token, context=element, namespaces=self.namespaces)
        if optional:
            nodelist += self.database.getElements("au:mayNeedCapability", 'get', self.token, context=element, namespaces=self.namespaces)
        tokenDataList = [self.igor.database.tagAndDictFromElement(e)[1] for e in nodelist]
        return tokenDataList

    def do_check(self):
        StructuralConsistency.do_check(self)
    
        if VERBOSE:
            self._status('Starting capability consistency check', isError=False)
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
        
        #
        # Second set - all the default and important capabilities exist
        #
        self._hasCapability('/data/identities/admin', cid='root')
        self._hasCapability('/data/identities/admin', cid='external', delegate='external')
        
        self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-static', obj='/static', get='child')
        self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-environment', obj='/data/environment', get='descendant-or-self')
        self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-status', obj='/data/status', get='descendant-or-self')
        self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-igor', obj='/data/services/igor', get='descendant-or-self')
        self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-accessControl', obj='/internal/accessControl', get='child')
        self._hasCapability('/data/au:access/au:defaultCapabilities', cid='default-sandbox', obj='/data/sandbox', get='descendant-or-self', put='descendant', post='descendant', delete='descendant')

        self._hasCapability('/data/identities', cid='people-people', obj='/data/people', get='descendant-or-self')

        self._hasCapability('/data/identities/admin', cid='admin-data', obj='/data', get='descendant-or-self', put='descendant', post='descendant', delete='descendant', delegate='true')
        self._hasCapability('/data/identities/admin', cid='admin-action', obj='/action', get='descendant', delegate='true')
        self._hasCapability('/data/identities/admin', cid='admin-internal', obj='/internal', get='descendant', delegate='true')
        self._hasCapability('/data/identities/admin', cid='admin-plugin', obj='/plugin', get='descendant', delegate='true')
        self._hasCapability('/data/identities/admin', cid='admin-filesystem', obj='/filesystem', get='self', delegate='true')
    
        for userElement in self._getAllElements('/data/identities/*'):
            userName = userElement.tagName
            if ':' in userName or '{' in userName or userName == 'admin':
                continue # This is not a user but a capability
            userPath = '/data/identities/'+userName
            self._hasCapability(userPath, obj=userPath, get='descendant-or-self', put='descendant', post='descendant', delete='descendant', delegate='true')
            self._hasCapability(userPath, obj='/data/people/'+userName, put='descendant', post='descendant', delete='descendant', delegate='true')
    
        self._hasCapability('/data/actions', cid='action-plugin', obj='/plugin', get='descendant')
        self._hasCapability('/data/actions', cid='action-action', obj='/action', get='descendant')
        self._hasCapability('/data/actions', cid='action-internal', obj='/internal', get='descendant')
        self._hasCapability('/data/actions', cid='action-environment', obj='/data/environment', get='descendant', put='descendant', post='descendant', delete='descendant')
        # Check that actions have the capabilities they need
        for actionElement in self._getAllElements('/data/actions/action'):
            actionXPath = self.database.getXPathForElement(actionElement)
            tokensNeeded = self._getTokensNeededByElement(actionElement, optional=self.extended)
            for item in tokensNeeded:
                self._hasCapability(actionXPath, **item)
        
        # Check that plugins have the capabilities they need.
        for pluginElement in self._getAllElements('/data/plugindata/*'):
            pluginName = pluginElement.tagName
            if ':' in pluginName or '{' in pluginName:
                continue
            pluginDataPath = f'/data/plugindata/{pluginName}'
            # Plugins specify all capabilities they need in their au:needCapability elements
            # But we ensure that it always needs access to its own plugindata
            tokensNeeded = [dict(obj=pluginDataPath, get='descendant-or-self')]
            tokensNeeded += self._getTokensNeededByElement(pluginElement, optional=self.extended)
            for item in tokensNeeded:
                self._hasCapability(pluginDataPath, **item)
        
        #
        # Second set of checks: test that capability tree is indeed a tree
        #
    
        allCapIDs = self._getValues('//au:capability/cid')
        if len(allCapIDs) != len(set(allCapIDs)):
            for c in set(allCapIDs):
                allCapIDs.remove(c)
            for c in allCapIDs:
                self._status(f'Non-unique cid: {c}')
            raise CannotFix
        allCaps = self._getAllElements('//au:capability')
        cid2cap = {}
        cid2parent = {}
        # create mapping cid->capability
        for cap in allCaps:
            cid = self._getValue('cid', cap)
            if not cid:
                if self.fix:
                    self._status(f'Cannot fix yet: Capability {self.database.getXPathForElement(cap)} has no cid')
                    raise CannotFix
                else:
                    self._status(f'Cannot fix yet: Capability {self.database.getXPathForElement(cap)} has no cid')
            cid2cap[cid] = cap
        # Check parent/child relation for each capability
        for cap in allCaps:
            cid = self._getValue('cid', cap)
            if not cid:
                continue # Error given earlier already
            for childCid in self._getValues('child::child', cap):
                if not childCid in cid2cap:
                    if self.fix:
                        self.database.delValues(f"child::child[text()='{childCid}']", token=self.token, context=cap)
                        self.database.setChanged()
                        self.nChanges += 1
                        self._status(f'Removed child {childCid} from {cid}', isError=False)
                    else:
                        self._status(f'Non-existing child {childCid} in {cid}')
                elif childCid in cid2parent:
                    if self.fix:
                        self._status(f'Cannot fix yet: Child with multiple parents: {childCid}')
                        raise CannotFix
                    else:
                        self._status(f'Child with multiple parents: {childCid}')
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
                            self._status(f'Cannot fix yet: Inconsistent parent for {cid} ({parentCid} versus {expectedParent})')
                            raise CannotFix
                        else:
                            self._status(f'Cannot fix yet: {cid} has no parent, but is listed as child of {expectedParent}')
                            raise CannotFix
                    self.database.delValues('child::parent', token=self.token, context=cap)
                    self.database.setChanged()
                    self.nChanges += 1
                    parentCid = None
                else:
                    if expectedParent and not parentCid:
                        self._status(f'Capability {cid} has no parent but listed by {expectedParent} as child')
                    elif parentCid and not expectedParent:
                        self._status(f'Parent for {cid} is {parentCid} but not listed there as child')
                    else:
                        self._status(f'Inconsistent parent for {cid} ({parentCid} versus {expectedParent})')
            if not parentCid:
                if self.fix:
                    self._fixParentCapability(cap, cid)
                    self._status(f'Orphaned capability {cid} given parent root', isError=False)
                else:
                    self._status(f'Capability {self.database.getXPathForElement(cap)} has no parent')
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
            cidList = self._getValues('au:capability/cid', context=loc)
            if not cidList:
                self._status(f'Listed as parent of capabilities but cannot find them: {parentPath}')
                continue
            for cid in cidList:
                if self.fix:
                    self._status(f'Cannot fix yet: Capability {cid}: in unexpected location {parentPath}')
                    raise CannotFix
                else:
                    self._status(f'Capability {cid}: in unexpected location {parentPath}')
        #
        # Fourth set: that we have all the expected capabilities
        #
        
        
        self._status('Capability consistency check finished', isError=False)
