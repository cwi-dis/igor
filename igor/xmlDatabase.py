from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str
from builtins import range
from builtins import object
import xml.dom
import xml.parsers.expat
import xpath
import sys
import traceback
import threading
import time
import os
import re
import math
import datetime
import dateutil.parser
from . import rwlock

TAG_PATTERN = re.compile('^[a-zA-Z_][-_.a-zA-Z0-9]*$')
TAG_PATTERN_WITH_NS = re.compile('^[a-zA-Z_][-_.a-zA-Z0-9:]*$')
ILLEGAL_XML_CHARACTERS_PATTERN = re.compile(u'[\x00-\x08\x0b-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff\ufdd0-\ufddf\ufffe-\uffff]')

#NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }
NAMESPACES = { "own" : "http://jackjansen.nl/igor/owner"}

class DBKeyError(KeyError):
    pass
    
class DBParamError(ValueError):
    pass
    
class DBAccessError(ValueError):
    pass
    
DEBUG=False

class XPathFunctionExtension(xpath.expr.Function):
    string = xpath.expr.string
    number = xpath.expr.number
    boolean = xpath.expr.boolean
    nodeset = xpath.expr.nodeset
    try:
        # Python 2
        function = xpath.expr.Function.function.__func__
    except AttributeError:
        # Python 3
        function = xpath.expr.Function.function

    @function(0, 1, implicit=True, convert=string)
    def f_igor_upper(self, node, pos, size, context, arg):
        return arg.upper()

    @function(0, 2)
    def f_igor_error(self, node, pos, size, context, a1=None, a2=None):
        if a1 is None:
            a1 = "unknown:unknown"
        if a2 is None:
            a2 = "XPath error function called"
        raise xpath.XPathError(a2)
        
    def _str2DateTime(self, str):
        try:
            return dateutil.parser.parse(str)
        except ValueError:
            try:
                timestamp = float(str)
                return datetime.datetime.fromtimestamp(timestamp)
            except ValueError:
                raise xpath.XPathError("Invalid DateTime '%s'" % str)
        
    @function(0, 1)
    def f_igor_timestamp(self, node, pos, size, context, dt=None):
        if dt is None:
            dt = datetime.datetime.now()
        else:
            dt = xpath.expr.string(dt)
            if dt:
                dt = self._str2DateTime(dt)
            else:
                dt = datetime.datetime.now()
        return int(time.mktime(dt.timetuple()))
        
    @function(0, 1)
    def f_igor_dateTime(self, node, pos, size, context, timestamp=None):
        if not timestamp:
            timestamp = time.time()
        else:
            strtimestamp = xpath.expr.string(timestamp)
            if strtimestamp:
                try:
                    dt = dateutil.parser.parse(strtimestamp)
                except ValueError:
                    pass
                else:
                    return strtimestamp
            timestamp = xpath.expr.number(timestamp)
            try:
                timestamp = float(timestamp)
            except TypeError:
                raise xpath.XPathError("dateTime argument must be a number or iso datetime: %s" % strtimestamp)
        if math.isnan(timestamp):
            raise xpath.XPathError("dateTime argument must be a valid number: %s" % strtimestamp)
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.isoformat()
        
    @function(1, 1)
    def f_igor_year_from_dateTime(self, node, pos, size, context, dt):
        dt = self._str2DateTime(dt)
        return dt.year
        
    @function(1, 1)
    def f_igor_month_from_dateTime(self, node, pos, size, context, dt):
        dt = self._str2DateTime(dt)
        return dt.month
        
    @function(1, 1)
    def f_igor_day_from_dateTime(self, node, pos, size, context, dt):
        dt = self._str2DateTime(dt)
        return dt.day
        
    @function(1, 1)
    def f_igor_hours_from_dateTime(self, node, pos, size, context, dt):
        dt = self._str2DateTime(dt)
        return dt.hour
        
    @function(1, 1)
    def f_igor_minutes_from_dateTime(self, node, pos, size, context, dt):
        dt = self._str2DateTime(dt)
        return dt.minute
        
    @function(1, 1)
    def f_igor_seconds_from_dateTime(self, node, pos, size, context, dt):
        dt = self._str2DateTime(dt)
        return dt.second
    
    @function(2, 2)
    def f_igor_dateTime_equal(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1)
        dt2 = self._str2DateTime(dt2)
        return dt1 == dt2
    
    @function(2, 2)
    def f_igor_date_equal(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1).date()
        dt2 = self._str2DateTime(dt2).date()
        return dt1 == dt2
    
    @function(2, 2)
    def f_igor_time_equal(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1).time()
        dt2 = self._str2DateTime(dt2).time()
        return dt1 == dt2
    
    @function(2, 2)
    def f_igor_dateTime_less_than(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1)
        dt2 = self._str2DateTime(dt2)
        return dt1 < dt2
    
    @function(2, 2)
    def f_igor_date_less_than(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1).date()
        dt2 = self._str2DateTime(dt2).date()
        return dt1 < dt2
    
    @function(2, 2)
    def f_igor_time_less_than(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1).time()
        dt2 = self._str2DateTime(dt2).time()
        return dt1 < dt2
    
    @function(2, 2)
    def f_igor_dateTime_greater_than(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1)
        dt2 = self._str2DateTime(dt2)
        return dt1 > dt2
    
    @function(2, 2)
    def f_igor_date_greater_than(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1).date()
        dt2 = self._str2DateTime(dt2).date()
        return dt1 > dt2
    
    @function(2, 2)
    def f_igor_time_greater_than(self, node, pos, size, context, dt1, dt2):
        dt1 = self._str2DateTime(dt1).time()
        dt2 = self._str2DateTime(dt2).time()
        return dt1 > dt2
        
    @function(3,3)
    def f_igor_ifthenelse(self, node, pos, size, context, condition, thenexpr, elseexpr):
        boolCond = xpath.expr.boolean(condition)
        if boolCond:
            return thenexpr
        return elseexpr
      
    @function(2, 2)
    def f_igor_ifelse(self, node, pos, size, context, condition, elseexpr):
        boolCond = xpath.expr.boolean(condition)
        if boolCond:
            return condition
        return elseexpr
      
def installXPathFunctionExtension(klass):
  if not issubclass(xpath.expr.Function, klass):
      class XPathFunctionWithExtension(klass, xpath.expr.Function):
          pass
      xpath.expr.Function = XPathFunctionWithExtension

installXPathFunctionExtension(XPathFunctionExtension)

def nodeSet(node):
    """Return a nodeset containing a single node"""
    return [node]
    
def recursiveNodeSet(node):
    """Return a nodeset containing a node and all its descendents"""
    rv = [node]
    child = node.firstChild
    while child:
        if child.nodeType == child.ELEMENT_NODE:
            rv += recursiveNodeSet(child)
        child = child.nextSibling
    return rv
    
class DBSerializer(object):
    """Baseclass with methods to provide a mutex and a condition variable"""
    def __init__(self):   
        self._callbacks = []
        self._rwlock = rwlock.ReadWriteLock()
        
    def writelock(self):
        return self._rwlock.writelock()
        
    def readlock(self):
        return self._rwlock.readlock()

    def registerCallback(self, callback, location):
        with self.writelock():
            self._callbacks.append((location, callback))
            
    def unregisterCallback(self, callback):
        with self.writelock():
            for i in range(len(self._callbacks)):
                if self._callbacks[i][0] == callback:
                    del self._callbacks[i]
                    return
        
    def _signalNodelist(self, nodelist):
        """Wake up clients waiting for the given nodes and return dictionary with callbacks. Must be called while holding lock."""
        assert self.writelock().locked()
        if DEBUG: print('_signalNodelist(%s)'%repr(nodelist))
        tocallback = {}
        for location, callback in self._callbacks:
            waitnodelist = xpath.find(location, self._doc.documentElement)
            for wn in waitnodelist:
                if wn in nodelist:
                    # Add to callbacks needed
                    if callback in tocallback:
                        tocallback[callback].append(wn)
                    else:
                        tocallback[callback] = [wn]
        return tocallback   
        
    def _runSignalCallbacks(self, callbacks):
        """Second part of signalling: call callbacks. Must be called without holding lock"""
        #assert not self.readlock().locked() and not self.writelock().locked()
        for callback, waitnodes in list(callbacks.items()):
            if DEBUG: print('_runSignalCallbacks calling %s(%s)' % (callback, waitnodes))
            callback(*waitnodes)    
        
class DBImpl(DBSerializer):
    """Main implementation of the database API"""
    
    def __init__(self, filename):
        DBSerializer.__init__(self)
        self.saveLock = threading.Lock()
        self.savedGeneration = None
        self.currentGeneration = 0
        from . import access
        self.access = access.singleton
        self._terminating = False
        self._domimpl = xml.dom.getDOMImplementation()
        self.filename = filename
        self.initialize(filename=filename)
        
    def setChanged(self):
        """Called by external modules when they have changed the database behind our back."""
        self.currentGeneration += 1
        
    def _checkAccess(self, operation, element, token, postChild=None):
        assert self.readlock().locked()
        assert token
        if not self.access:
            return
        ac = self.access.checkerForElement(element)
        if operation == 'post' and postChild:
            # Special case: POST for a child on a parent element is allowed if PUT on that child would be allowed
            path = self._getXPathForElement(element) + '/' + postChild
            ac = self.access.checkerForNewElement(path)
            if ac.allowed('put', token, tentative=True):
                return
        if ac.allowed(operation, token):
            return
        raise DBAccessError

    def _removeBlanks(self, node):
        toDelete = []
        for n in node.childNodes:
            if n.nodeType == n.TEXT_NODE:
                n.nodeValue = n.nodeValue.strip()
                if not n.nodeValue:
                    toDelete.append(n)
            if n.nodeType == n.ELEMENT_NODE:
                self._removeBlanks(n)
        for n in toDelete:
            node.removeChild(n)
                
    def _filterBeforeSave(self, nodeOrDoc, token):
        self._removeBlanks(nodeOrDoc)
        return nodeOrDoc
        
    def saveFile(self):
        with self.writelock():
            if self.savedGeneration == self.currentGeneration:
                # Nothing changed since last save
                return
            newFilename = self.filename + time.strftime('.%Y%m%d%H%M%S')
            if os.path.exists(newFilename):
                for i in range(10):
                    nf2 = '{}.{}'.format(newFilename, i)
                    if not os.path.exists(nf2):
                        newFilename = nf2
                        break
                else:
                    raise DBParamError('Cannot create tempfile {}'.format(newFilename))
            with self.saveLock:
                docToSave = self._filterBeforeSave(self._doc, self.access.tokenForIgor())
            docToSave.writexml(open(newFilename, 'w'), addindent="\t", newl="\n")
            os.link(newFilename, newFilename +'.tolink')
            os.rename(newFilename + '.tolink', self.filename)
            # Remove outdated saves
            dir,file = os.path.split(self.filename)
            allOldDatabases = []
            for fn in os.listdir(dir):
                if fn.startswith(file + '.'):
                    allOldDatabases.append(fn)
            allOldDatabases.sort()
            for fn in allOldDatabases[:-10]:
                os.unlink(os.path.join(dir, fn))

            self.savedGeneration = self.currentGeneration
            print('xmlDatabase: saving to {}'.format(newFilename))
            
    def initialize(self, xmlstring=None, filename=None):
        """Reset the document to a known value (passed as an XML string"""
        if filename:
            newDoc = xml.dom.minidom.parse(filename)
        elif xmlstring:
            newDoc = xml.dom.minidom.parseString(xmlstring)
        else:
            newDoc = self._domimpl.createDocument('', 'root', None)
        self._removeBlanks(newDoc)
        with self.writelock():
            self.currentGeneration += 1
            self._doc = newDoc
    
    def _createElementWithEscaping(self, tag, namespace=None):
        if namespace:
            assert TAG_PATTERN.match(tag)
            nsItems = list(namespace.items())
            assert len(nsItems) == 1
            nsTag, nsUrl = nsItems[0]
            return self._doc.createElementNS(nsUrl, nsTag + ':' + tag)
        if TAG_PATTERN.match(tag) and not tag == "_e":
            return self._doc.createElement(tag)
        rv = self._doc.createElement("_e")
        rv.setAttribute("_e", tag)
        return rv
        
    def _getElementTagWithEscaping(self, element):
        tag = element.tagName
        if tag == '_e':
            escaped = element.getAttribute('_e')
            if escaped: return escaped
        return tag
        
    def _identicalSubTrees(self, element1, element2):
        assert self.readlock().locked()
        if not element1 and not element2: return True
        if not element1 or not element2: return False
        if element1.nodeType != element2.nodeType: return False
        if element1.nodeType == element1.TEXT_NODE:
            return element1.data == element2.data
        if element1.nodeType != element1.ELEMENT_NODE: return True
        if element1.tagName != element2.tagName: return False
        ch1 = element1.firstChild
        ch2 = element2.firstChild
        while ch1 or ch2:
            chEqual = self._identicalSubTrees(ch1, ch2)
            if not chEqual: return False
            ch1 = ch1.nextSibling
            ch2 = ch2.nextSibling
        return True
        
    def getDocument(self, token):
        """Return the whole document (as a DOM element)"""
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.readlock():
            self._checkAccess('get', self._doc.documentElement, token)
            return self._doc.documentElement
        
    def splitXPath(self, location, allowNamespaces=False, stripPredicate=False):
        lastSlashPos = location.rfind('/')
        if lastSlashPos == 0:
            parent = '.'
            child = location[lastSlashPos+1:]
        elif lastSlashPos > 0:
            parent = location[:lastSlashPos]
            child = location[lastSlashPos+1:]
        else:
            parent = '.'
            child = location
        # If wanted strip any predicates from the child
        if stripPredicate and child[-1:] == ']':
            firstBracketPos = child.find('[')
            if firstBracketPos > 0:
                child = child[:firstBracketPos]
        # Test that child is indeed a tag name
        if allowNamespaces:
            if not TAG_PATTERN_WITH_NS.match(child):
                return None, None
        else:
            if not TAG_PATTERN.match(child):
                return None, None
        return parent, child

    def getXPathForElement(self, node):
        # This is a bit tricky, because sometimes we already hold the lock.
        # But, really, this test doesn't say that this thread is actually holding the write lock....
        if self.writelock().locked():        
            return self._getXPathForElement(node)
        with self.readlock():
            return self._getXPathForElement(node)

    def _getXPathForElement(self, node):
        assert self.readlock().locked()
        if node is None or node.nodeType == node.DOCUMENT_NODE:
            return ""
        if node.tagName == "_e":
            print("Warning: getting xpath for escaped json node may not work very well")
        count = 0
        sibling = node.previousSibling
        while sibling:
            if sibling.nodeType == sibling.ELEMENT_NODE and sibling.tagName == node.tagName:
                count += 1
            sibling = sibling.previousSibling
        countAfter = 0
        sibling = node.nextSibling
        while sibling:
            if sibling.nodeType == sibling.ELEMENT_NODE and sibling.tagName == node.tagName:
                countAfter += 1
            sibling = sibling.nextSibling
        if count+countAfter:
            index = '[%d]' % (count+1)
        else:
            index = ''
        return self._getXPathForElement(node.parentNode) + "/" + node.tagName + index

    def xmlFromElement(self, element, stripHidden=False):
        """Return XML representation, possibly after stripping namespaced elements and attributes"""
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.readlock():
            if not stripHidden:
                return element.toxml()
            if element.namespaceURI:
                return ''
            
            def _hasNS(e):
                """Helper method to check whether anything is namespaced in the subtree"""
                if e.namespaceURI:
                    return True
                if e.attributes:
                    for a in e.attributes.values():
                        if a.namespaceURI:
                            return True
                c = e.firstChild
                while c:
                    if c.namespaceURI:
                        return True
                    if _hasNS(c):
                        return True
                    c = c.nextSibling
            if not _hasNS(element):
                return element.toxml()

            copied = element.cloneNode(True)
            def _stripNS(e):
                """Helper method to strip all namespaced items from a subtree"""
                assert not e.namespaceURI
                if e.attributes:
                    toRemoveAttrs =[]
                    for av in e.attributes.values():
                        if av.namespaceURI:
                            toRemoveAttrs.append(av)
                    for av in toRemoveAttrs:
                        e.removeAttributeNode(av)
                toRemove = []
                for c in e.childNodes:
                    if c.namespaceURI:
                        toRemove.append(c)
                for c in toRemove:
                    e.removeChild(c)
                for c in e.childNodes:
                    _stripNS(c)
            _stripNS(copied)
            rv = copied.toxml()
            copied.unlink()
            return rv
        
    def tagAndDictFromElement(self, element, stripHidden=False):
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.readlock():
            return self._tagAndDictFromElement(element, stripHidden)

    def _tagAndDictFromElement(self, element, stripHidden=False):
        assert self.readlock().locked()
        if stripHidden and element.namespaceURI:
            return '', {}
        t = self._getElementTagWithEscaping(element)
        v = {}
        texts = []
        child = element.firstChild
        # It seems in xml.dom the attributes are not in the children list (??!?).
        # Get them from the attributes map
        if element.attributes:
            for attrName, attrValue in element.attributes.items():
                if stripHidden and ':' in attrName:
                    continue
                v['@'+attrName] = attrValue
        while child:
            if stripHidden and child.namespaceURI:
                child = child.nextSibling
                continue
            if child.nodeType == child.ELEMENT_NODE:
                newt, newv = self._tagAndDictFromElement(child, stripHidden)
                # If the element already exists we turn it into a list (if not done before)
                if newt in v:
                    if type(v[newt]) != type([]):
                        v[newt] = [v[newt]]
                    v[newt].append(newv)
                else:
                    v[newt] = newv
            elif child.nodeType == child.ATTRIBUTE_NODE:
                # Note: it seems attributes are not in the children, so this code may be non-functional
                v['@' + child.name] = child.value
            elif child.nodeType == child.TEXT_NODE:
                # Remove leading and trailing whitespace, and only add text node if it is not empty
                d = child.data.strip()
                if d:
                    texts.append(d)
            child = child.nextSibling
        if len(texts) == 1:
            if v:
                v['#text'] = texts[0]
            else:
                v = texts[0]
                try:
                    v = int(v)
                except ValueError:
                    try:
                        v = float(v)
                    except ValueError:
                        pass
                if v == 'null':
                    v = None
                elif v == 'true':
                    v = True
                elif v == 'false':
                    v = False
        elif len(texts) > 1:
            v['#text'] = texts
        return t, v

    def elementFromTagAndData(self, tag, data, namespace=None):
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.readlock():
            return self._elementFromTagAndData(tag, data, namespace)
            
    def _elementFromTagAndData(self, tag, data, namespace=None):
        assert self.readlock().locked()
        newnode = self._createElementWithEscaping(tag, namespace)
        if not isinstance(data, dict):
            # Not key/value, so a raw value. Convert to something string-like
            if data is None:
                data = ''
            if type(data) is type(True):
                data = 'true' if data else ''
            data = "%s" % (data,)
            # Clean illegal unicode characters
            data = ILLEGAL_XML_CHARACTERS_PATTERN.sub('', data)
            newnode.appendChild(self._doc.createTextNode(data))
            return newnode
        for k, v in list(data.items()):
            if k == '#text':
                if not isinstance(v, list):
                    v = [v]
                for string in v:
                    newtextnode = self._doc.createTextNode(string)
                    newnode.appendChild(newtextnode)
            elif k and k[0] == '@':
                attrname = k[1:]
                newattr = self._doc.createAttribute(attrname)
                newattr.value = v
                newnode.appendChild(newattr)
            else:
                if not isinstance(v, list):
                    v = [v]
                for childdef in v:
                    newchild = self._elementFromTagAndData(k, childdef)
                    newnode.appendChild(newchild)
        return newnode
        
    def elementFromXML(self, xmltext):
        try:
            newdoc = xml.dom.minidom.parseString(xmltext)
        except xml.parsers.expat.ExpatError as e:
            raise DBParamError('Not valid xml: %s' % e)            
        except:
            raise DBParamError('Not valid xml: %s' % xmltext)
        return newdoc.firstChild
                
    def delValues(self, location, token, context=None, namespaces=NAMESPACES):
        """Remove a (possibly empty) set of nodes from the document"""
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.writelock():
            self.currentGeneration += 1
            if context == None:
                context = self._doc.documentElement
            nodeList = xpath.find(location, context, namespaces=namespaces)
            for n in nodeList:
                self._checkAccess('delete', n, token)
            parentList = []
            for node in nodeList:
                parentNode = node.parentNode
                parentNode.removeChild(node)
                if not parentNode in parentList:
                    parentList += nodeSet(parentNode)
            callbacks = self._signalNodelist(parentList)
        self._runSignalCallbacks(callbacks)
            
    def getValue(self, location, token, context=None, namespaces=NAMESPACES):
        """Return a single value from the document (as string)"""
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.readlock():
            if context is None:
                context = self._doc.documentElement
            #
            # xxxjack note that there is a security issue here. We only check access
            # if  complete nodeset is returned. If the expression is carefully crafted to
            # return a string it gives access to anything.
            #
            result = xpath.find(location, context, originalContext=[context], namespaces=namespaces)
            if xpath.expr.nodesetp(result):
                for n in result:
                    self._checkAccess('get', n, token)
                return xpath.expr.string(result)
            return result
                    
    def getValues(self, location, token, context=None, namespaces=NAMESPACES):
        """Return a list of node values from the document (as names and strings)"""
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.readlock():
            if context is None:
                context = self._doc.documentElement
            nodeList = xpath.find(location, context, originalContext=[context], namespaces=namespaces)
            for n in nodeList:
                self._checkAccess('get', n, token)
            return self._getValueList(nodeList)
        
    def getElements(self, location, operation, token, context=None, namespaces=NAMESPACES, postChild=None):
        """Return a list of DOM nodes (elements only, for now) that match the location"""
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.readlock():
            if context is None:
                context = self._doc.documentElement
            nodeList = xpath.find(location, context, originalContext=[context], namespaces=namespaces)
            # Check we have access to all those nodes
            for n in nodeList:
                self._checkAccess(operation, n, token, postChild)
            return nodeList
        
    def _getValueList(self, nodelist):
        assert self.readlock().locked()
        rv = []
        for node in nodelist:
            rv.append((self._getXPathForElement(node), xpath.expr.string_value(node)))
        return rv
            
    def addElement(self, parentPath, tag, element, token, context=None, namespaces=NAMESPACES):
        """Add a new element to the database."""
        #
        # Find parent
        #
        # NOTE: we pass the tagname for the child element. This is so put rights on a
        # child that does not exist yet can be checked.
        callbacks = None
        with self.writelock():
            self.currentGeneration += 1
            if context is None:
                context = self._doc.documentElement
            parentElements = xpath.find(parentPath, context, namespaces=namespaces)
            if not parentElements:
                raise DBParamError("Parent not found: %s" % parentPath)
            if len(parentElements) > 1:
                raise DBParamError("Multiple parents: %s" % parentPath)
            parent = parentElements[0]
            self._checkAccess('post', parent, token, tag)        
            #
            # Add new node to the end of the parent
            #
            parent.appendChild(element)
            #
            # Signal both parent and new node
            #
            nodesToSignal = recursiveNodeSet(element)
            nodesToSignal += nodeSet(parent)
            callbacks = self._signalNodelist(nodesToSignal)
        if callbacks:
            self._runSignalCallbacks(callbacks)
    
    def replaceElement(self, oldElement, newElement, token, context=None, namespaces=NAMESPACES):
        """Replace an existing element in the database. Returns True if nothing changed"""
        #
        # We should really do a selective replace here: change only the subtrees that need replacing.
        # That will make the signalling much more fine-grained. Will do so, at some point in the future.
        #
        # For now we replace the first matching node and delete its siblings, but only if the new content
        # is not identical to the old
        #
        callbacks = None
        with self.writelock():
            self.currentGeneration += 1
            self._checkAccess('put', oldElement, token)
            if self._identicalSubTrees(oldElement, newElement):
                return True
            parent = oldElement.parentNode
            parent.replaceChild(newElement, oldElement)
            nodesToSignal = recursiveNodeSet(newElement)
            callbacks = self._signalNodelist(nodesToSignal)
        if callbacks:
            self._runSignalCallbacks(callbacks)
        return False
        
    def mergeElement(self, location, tree, token, plugin=False, context=None, namespaces=NAMESPACES):
        callbacks = None
        assert plugin # No other merges implemented yet
        assert location == '/'
        assert context == None
        #assert not self.readlock().locked() and not self.writelock().locked()        
        with self.writelock():
            self.currentGeneration += 1
            if context == None and location == '/':
                context = self._doc.documentElement
            if not self._elementsMatch(context, tree):
                raise DBParamError('mergeElement: root elements do not match')
            self.mergeNodesToSignal = []
            self._mergeTree(context, tree, token, plugin, namespaces=namespaces)
            if self.mergeNodesToSignal:
                callbacks = self._signalNodelist(self.mergeNodesToSignal)
            self.mergeNodesToSignal = []
        if callbacks:
            self._runSignalCallbacks(callbacks)
            
    def _elementsMatch(self, elt1, elt2):
        return elt1.tagName == elt2.tagName
        
    def _constructXPathForNewChild(self, elt, plugin):
        assert plugin
        rv = elt.tagName
        if elt.hasAttributeNS(NAMESPACES["own"], "plugin"):
            pluginName = elt.getAttributeNS(NAMESPACES["own"], "plugin")
            rv += '[@own:plugin="%s"]' % pluginName
        return rv
        
    def _mergeTree(self, context, newTree, token, plugin, namespaces=NAMESPACES):
        assert self.writelock().locked()
        newChild = newTree.firstChild
        toAdd = []
        while newChild:
            # Ignore non-element children
            if newChild.nodeType != newChild.ELEMENT_NODE:
                newChild = newChild.nextSibling
                continue
            # Check whether the old tree has an element corresponding to this one
            xp = self._constructXPathForNewChild(newChild, plugin)
            matches = xpath.find(xp, context, namespaces=namespaces)
            if not matches:
                # No child exists that matches this child
                toAdd.append(newChild)
            elif len(matches) == 1:
                # A single child in the old tree matches. Recursively descend.
                newContext = matches[0]
                self._mergeTree(newContext, newChild, token, plugin, namespaces=namespaces)
            else:
                raise DBParamError('mergeElement: multiple matches for %s at %s' % (xp, self._getXPathForElement(context)))
            newChild = newChild.nextSibling
        for newChild in toAdd:
            newTree.removeChild(newChild)
            context.appendChild(newChild)
            self.mergeNodesToSignal.append(newChild)
