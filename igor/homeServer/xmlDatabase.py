import xml.dom
import xpath
import sys
import traceback
import threading
import time
import os
import re
import datetime
import dateutil.parser

TAG_PATTERN = re.compile('^[a-zA-Z_][-_.a-zA-Z0-9]*$')

class DBKeyError(KeyError):
    pass
    
class DBParamError(ValueError):
    pass
    
DEBUG=False

class XPathFunctionExtension(xpath.expr.Function):
    string = xpath.expr.string
    number = xpath.expr.number
    boolean = xpath.expr.boolean
    nodeset = xpath.expr.nodeset
    function = xpath.expr.Function.function.im_func

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
            raise xpath.XPathError("Invalid DateTime")
        
    @function(0, 1)
    def f_igor_timestamp(self, node, pos, size, context, dt=None):
        if dt is None:
            dt = datetime.datetime.now()
        else:
            dt = self._str2DateTime(dt)
        return int(time.time())
        
    @function(0, 1)
    def f_igor_dateTime(self, node, pos, size, context, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
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
    
class DBSerializer:
    """Baseclass with methods to provide a mutex and a condition variable"""
    def __init__(self):   
        self.lockCount = 0
        self._waiting = {}
        self._callbacks = []
        self._lock = threading.RLock()

    def enter(self):
        """Enter the critical section for this database"""
        self._lock.acquire()
        self.lockCount += 1
        
    def leave(self):
        self._lock.release()
        
    def __enter__(self):
        self.enter()
        
    def __exit__(self, *args):
        self.leave()

    def registerCallback(self, callback, location):
        with self:
            self._callbacks.append((location, callback))
            
    def unregisterCallback(self, callback):
        with self:
            for i in range(len(self._callbacks)):
                if self._callbacks[i][0] == callback:
                    del self._callbacks[i]
                    return
            
    def waitLocation(self, location, oldValue=None):
        """Register that we are interested in the given XPath. Returns the semaphore"""
        if not location in self._waiting:
            self._waiting[location] = [threading.Condition(self._lock), 0]
        if not oldValue is None:
            if oldValue < self._waiting[location][1]:
                #print 'DBG waitLocation returning early for', oldValue
                return self._waiting[location][1]
        #print 'DBG waitLocation waiting for', location
        self._waiting[location][0].wait()
        return self._waiting[location][1]
        
    def signalNodelist(self, nodelist):
        """Wake up clients waiting for the given nodes"""
        if DEBUG: print 'signalNodelist(%s)'%repr(nodelist)
        for location, cv in self._waiting.items():
            waitnodelist = xpath.find(location, self._doc.documentElement)
            for wn in waitnodelist:
                if wn in nodelist:
                    #print 'DBG signal for', wn
                    cv[1] += 1
                    cv[0].notify_all()
                    break
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
        for callback, waitnodes in tocallback.items():
            if DEBUG: print 'signalNodelist calling %s(%s)' % (callback, waitnodes)
            callback(*waitnodes)    
        
class DBImpl(DBSerializer):
    """Main implementation of the database API"""
    
    def __init__(self, filename):
        DBSerializer.__init__(self)
        self._terminating = False
        self._domimpl = xml.dom.getDOMImplementation()
        self.filename = filename
        self.initialize(filename=filename)

    def saveFile(self):
        newFilename = self.filename + time.strftime('.%Y%m%d%H%M%S')
        self._doc.writexml(open(newFilename + '~', 'w'))
        os.link(newFilename + '~', newFilename)
        os.rename(newFilename + '~', self.filename)
        # Remove outdated saves
        dir,file = os.path.split(self.filename)
        allOldDatabases = []
        for fn in os.listdir(dir):
            if fn.startswith(file + '.'):
                allOldDatabases.append(fn)
        allOldDatabases.sort()
        for fn in allOldDatabases[:-10]:
            os.unlink(os.path.join(dir, fn))
            

    def signalNodelist(self, nodelist):
        with self:
            #self.saveFile()
            DBSerializer.signalNodelist(self, nodelist)
        
    def getMessageCount(self):
        with self:
            return self.lockCount
        
    def terminate(self):
        with self:
            self._terminating = True
            sys.exit(1)
        
    def is_terminating(self):
        with self:
            return self._terminating
        
    def initialize(self, xmlstring=None, filename=None):
        """Reset the document to a known value (passed as an XML string"""
        with self:
            if filename:
                self._doc = xml.dom.minidom.parse(filename)
            elif xmlstring:
                self._doc = xml.dom.minidom.parseString(xmlstring)
            else:
                self._doc = self._domimpl.createDocument('', 'root', None)
    
    def echo(self, arg):
        """Return the argument (for performance testing)"""
        return arg
        
    def _createElementWithEscaping(self, tag):
        if TAG_PATTERN.match(tag) and not tag == "_e":
            return self._doc.createElement(tag)
        print 'xxxjack create escape for', tag
        rv = self._doc.createElement("_e")
        rv.setAttribute("_e", tag)
        return rv
        
    def _getElementTagWithEscaping(self, element):
        tag = element.tagName
        if tag == '_e':
            escaped = element.getAttribute('_e')
            if escaped: return escaped
        return tag
        
    def identicalSubTrees(self, element1, element2):
        """Return true if the two subtrees are identical (for our purposes)"""
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
            chEqual = self.identicalSubTrees(ch1, ch2)
            if not chEqual: return False
            ch1 = ch1.nextSibling
            ch2 = ch2.nextSibling
        return True
        
    def getXMLDocument(self):
        """Return the whole document (as an XML string)"""
        with self:
            rv = self._doc.toprettyxml()
            return rv
        
    def getDocument(self):
        """Return the whole document (as a DOM element)"""
        with self:
            return self._doc.documentElement
        
    def splitXPath(self, location):
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
        # Test that child is indeed a tag name
        if not TAG_PATTERN.match(child):
            return None, None
        return parent, child

    def getXPathForElement(self, node):
        if node is None or node.nodeType == node.DOCUMENT_NODE:
            return ""
        if node.tagName == "_e":
            print "Warning: getting xpath for escaped json node may not work very well"
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
        return self.getXPathForElement(node.parentNode) + "/" + node.tagName + index

    def tagAndDictFromElement(self, element):
        t = self._getElementTagWithEscaping(element)
        v = {}
        texts = []
        child = element.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE:
                newt, newv = self.tagAndDictFromElement(child)
                # If the element already exists we turn it into a list (if not done before)
                if newt in v:
                    if type(v[newt]) != type([]):
                        v[newt] = [v[newt]]
                    v[newt].append(newv)
                else:
                    v[newt] = newv
            elif child.nodeType == child.ATTRIBUTE_NODE:
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

    def elementFromTagAndData(self, tag, data):
        with self:
            newnode = self._createElementWithEscaping(tag)
            if not isinstance(data, dict):
                # Not key/value, so a raw value. Convert to something string-like
                if type(data) is type(True):
                    data = 'true' if data else ''
                data = unicode(data)
                newnode.appendChild(self._doc.createTextNode(data))
                return newnode
            for k, v in data.items():
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
                        newchild = self.elementFromTagAndData(k, childdef)
                        newnode.appendChild(newchild)
            return newnode
        
    def elementFromXML(self, xmltext):
        newdoc = xml.dom.minidom.parseString(xmltext)
        return newdoc.firstChild
        
    def setValue(self, location, value):
        """Set (or insert) a single node by a given value (passed as a string)"""
        with self:
            # Find the node, if it exists.
            node = xpath.findnode(location, self._doc.documentElement)
            if node is None:
                # Does not exist yet. Try to add it.
                parent, child = self.splitXPath(location)
                if not parent or not child:
                    raise DBKeyError("XPath %s does not refer to unique new or existing location" % location)
                return self.newValue(parent, 'child', child, value)

            # Sanity check
            if node.nodeType == node.DOCUMENT_NODE:
                raise DBParamError('Cannot replace value of /')
            
            # Clear out old contents of the node
            while node.firstChild: node.removeChild(node.firstChild)
        
            if hasattr(value, 'nodeType'):
                # It seems to be a DOM node. Insert it.
                node.appendChild(value)
            else:
                # Insert the new text value
                if not isinstance(value, basestring):
                    value = str(value)
                node.appendChild(self._doc.createTextNode(value))
        
            # Signal anyone waiting
            self.signalNodelist(recursiveNodeSet(node))
        
            # Return the location of the new node
            return getXPathForElement(node)
        
    def newValue(self, location, where, name, value):
        """Insert a single new node into the document (value passed as a string)"""
        with self:
            # Create the new node to be instered
            newnode = self._doc._createElementWithEscaping(name)
            if not isinstance(value, basestring):
                value = str(value)
            newnode.appendChild(self._doc.createTextNode(value))
        
            # Find the node that we want to insert it relative to
            node = xpath.findnode(location, self._doc.documentElement)
            if node is None:
                raise DBKeyError(location)
            
            # Insert it in the right place
            if where == 'before':
                node.parentNode.insertBefore(node, newnode)
            elif where == 'after':
                newnode.nextSibling = node.nextSibling
                node.nextSibling = newnode
            elif where == 'child':
                node.appendChild(newnode)
            else:
                raise DBParamError('where must be before, after or child')

            # Signal anyone waiting
            self.signalNodelist(recursiveNodeSet(newnode)+nodeSet(newnode.parentNode))
        
            # Return the location of the new node
            return getXPathForElement(newnode)
        
    def delValue(self, location):
        """Remove a single node from the document"""
        with self:
            node = xpath.findnode(location, self._doc.documentElement)
            if node is None:
                raise DBKeyError(location)
            parentNode = node.parentNode
            parentNode.removeChild(node)
        
            # Signal anyone waiting
            self.signalNodelist(nodeSet(parentNode))
        
    def delValues(self, location):
        """Remove a (possibly empty) set of nodes from the document"""
        with self:
            nodelist = xpath.find(location, self._doc.documentElement)
            parentList = []
            #print 'xxxjack delValues', repr(nodelist)
            for node in nodelist:
                parentNode = node.parentNode
                parentNode.removeChild(node)
                if not parentNode in parentList:
                    parentList += nodeSet(parentNode)
            self.signalNodelist(parentList)
            
    def hasValue(self, location):
        """Return xpath if the location exists, None otherwise"""
        with self:
            node = xpath.findnode(location, self._doc.documentElement)
            if node:
                return getXPathForElement(node)
            return None
        
    def waitValue(self, location):
        with self:
            node = xpath.findnode(location, self._doc.documentElement)
            if not node:
                self.waitLocation(location)
                node = xpath.findnode(location, self._doc.documentElement)
                assert node
            return getXPathForElement(node)

    def hasValues(self, location, context=None):
        """Return a list of xpaths for the given location"""
        with self:
            if context is None:
                context = self._doc.documentElement
            nodelist = xpath.find(location, context, originalContext=[context])
            return map(getXPathForElement, nodelist)
        
    def getValue(self, location, context=None):
        """Return a single value from the document (as string)"""
        with self:
            if context is None:
                context = self._doc.documentElement
            return xpath.findvalue(location, context, originalContext=[context])
        
    def getValues(self, location, context=None):
        """Return a list of node values from the document (as names and strings)"""
        with self:
            if context is None:
                context = self._doc.documentElement
            nodelist = xpath.find(location, context, originalContext=[context])
            return self._getValueList(nodelist)
        
    def getElements(self, location, context=None):
        """Return a list of DOM nodes (elements only, for now) that match the location"""
        with self:
            if context is None:
                context = self._doc.documentElement
            nodeList = xpath.find(location, context, originalContext=[context])
            return nodeList
        
    def _getValueList(self, nodelist):
        with self:
            rv = []
            for node in nodelist:
                rv.append((getXPathForElement(node), xpath.expr.string_value(node)))
            return rv
        
    def pullValue(self, location):
        """Wait for a value, remove it from the document, return it (as string)"""
        with self:
            node = xpath.findnode(location, self._doc.documentElement)
            if not node:
                self.waitLocation(location)
                node = xpath.findnode(location, self._doc.documentElement)
                assert node
            rv = xpath.expr.string_value(node)
            node.parentNode.removeChild(node)
            self.signalNodelist(nodeSet(parentnode))
            return rv
  
    def pullValues(self, location):
        """Wait for values, remove them from the document, return it (as list of strings)"""
        with self:
            nodelist = xpath.find(location, self._doc.documentElement)
            if not nodelist:
                self.waitLocation(location)
                nodelist = xpath.find(location, self._doc.documentElement)
            assert nodelist
            rv = self._getValueList(nodelist)
            parentList = []
            for node in nodelist:
                parentNode = node.parentNode
                parentNode.removeChild(node)
                if not parentNode in parentList:
                    parentList += nodeSet(parentNode)
            self.signalNodelist(parentList)
            return rv
        
    def trackValue(self, location, generation):
        """Generator. Like waitValue, but keeps on returning changed paths"""
        with self:
            generation = self.waitLocation(location, generation)
            node = xpath.findnode(location, self._doc.documentElement)
            assert node
            return getXPathForElement(node), generation
