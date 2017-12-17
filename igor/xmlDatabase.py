import xml.dom
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

TAG_PATTERN = re.compile('^[a-zA-Z_][-_.a-zA-Z0-9]*$')
ILLEGAL_XML_CHARACTERS_PATTERN = re.compile(u'[\x00-\x08\x0b-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff\ufdd0-\ufddf\ufffe-\uffff]')

#NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }
NAMESPACES = { }

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
        if timestamp is None:
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
    
class DBSerializer:
    """Baseclass with methods to provide a mutex and a condition variable"""
    def __init__(self):   
        self._waiting = {}
        self._callbacks = []
        self._lock = threading.RLock()

    def enter(self):
        """Enter the critical section for this database"""
        self._lock.acquire()
        
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
        import access
        self.access = access.singleton
        self._terminating = False
        self._domimpl = xml.dom.getDOMImplementation()
        self.filename = filename
        self.initialize(filename=filename)
        
    def _checkAccess(self, operation, element, token):
        assert token
        if not self.access:
            return
        ac = self.access.checkerForElement(element)
        if ac.allowed(operation, token):
            return
        raise DBAccessError

    def filterAfterLoad(self, nodeOrDoc, token):
        with self:
            return nodeOrDoc
        
    def filterBeforeSave(self, nodeOrDoc,token):
        with self:
            return nodeOrDoc
        
    def saveFile(self):
        newFilename = self.filename + time.strftime('.%Y%m%d%H%M%S')
        docToSave = self.filterBeforeSave(self._doc, self.access.tokenForIgor())
        docToSave.writexml(open(newFilename + '~', 'w'))
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
        
    def initialize(self, xmlstring=None, filename=None):
        """Reset the document to a known value (passed as an XML string"""
        with self:
            if filename:
                newDoc = xml.dom.minidom.parse(filename)
            elif xmlstring:
                newDoc = xml.dom.minidom.parseString(xmlstring)
            else:
                newDoc = self._domimpl.createDocument('', 'root', None)
            self._doc = self.filterAfterLoad(newDoc, self.access.tokenForIgor())
    
    def _createElementWithEscaping(self, tag):
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
        
    def getDocument(self, token):
        """Return the whole document (as a DOM element)"""
        with self:
            self._checkAccess('get', self._doc.documentElement, token)
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
                if data is None:
                    data = ''
                if type(data) is type(True):
                    data = 'true' if data else ''
                data = unicode(data)
                # Clean illegal unicode characters
                data = ILLEGAL_XML_CHARACTERS_PATTERN.sub('', data)
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
        try:
            newdoc = xml.dom.minidom.parseString(xmltext)
        except:
            raise DBParamError('Not valid xml: %s' % xmltext)
        return newdoc.firstChild
                
    def delValues(self, location, token):
        """Remove a (possibly empty) set of nodes from the document"""
        with self:
            nodeList = xpath.find(location, self._doc.documentElement, namespaces=NAMESPACES)
            for n in nodeList:
                self._checkAccess('delete', n, token)
            parentList = []
            for node in nodeList:
                parentNode = node.parentNode
                parentNode.removeChild(node)
                if not parentNode in parentList:
                    parentList += nodeSet(parentNode)
            self.signalNodelist(parentList)
            
    def getValue(self, location, token, context=None):
        """Return a single value from the document (as string)"""
        with self:
            if context is None:
                context = self._doc.documentElement
            #
            # xxxjack note that there is a security issue here. We only check access
            # if  complete nodeset is returned. If the expression is carefully crafted to
            # return a string it gives access to anything.
            #
            result = xpath.find(location, context, originalContext=[context], namespaces=NAMESPACES)
            if xpath.expr.nodesetp(result):
                for n in result:
                    self._checkAccess('get', n, token)
                return xpath.expr.string(result)
            return result
                    
    def getValues(self, location, token, context=None):
        """Return a list of node values from the document (as names and strings)"""
        with self:
            if context is None:
                context = self._doc.documentElement
            nodeList = xpath.find(location, context, originalContext=[context], namespaces=NAMESPACES)
            for n in nodeList:
                self._checkAccess('get', n, token)
            return self._getValueList(nodeList)
        
    def getElements(self, location, operation, token, context=None):
        """Return a list of DOM nodes (elements only, for now) that match the location"""
        with self:
            if context is None:
                context = self._doc.documentElement
            nodeList = xpath.find(location, context, originalContext=[context], namespaces=NAMESPACES)
            # Check we have access to all those nodes
            for n in nodeList:
                self._checkAccess(operation, n, token)
            return nodeList
        
    def _getValueList(self, nodelist):
        with self:
            rv = []
            for node in nodelist:
                rv.append((self.getXPathForElement(node), xpath.expr.string_value(node)))
            return rv
