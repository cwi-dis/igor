import xml.dom
import xpath
import sys
import traceback
import SimpleXMLRPCServer
import threading
import dbapi
import time

DOCUMENT="""<?xml-stylesheet type="text/xsl" href="dbdump.xsl" ?><root><clients/><services><orchestrator/><optimizer/><vr/></services><cues><lastBored/><soundLevel/><trigger/></cues><streamReady/><restrictions/><decisions/><connections/></root>"""

class DBKeyError(KeyError):
    pass
    
class DBParamError(ValueError):
    pass
    
def _getXPath(node):
    if node is None or node.nodeType == node.DOCUMENT_NODE:
        return ""
    count = 0
    sibling = node.previousSibling
    while sibling:
        if sibling.nodeType == sibling.ELEMENT_NODE and sibling.tagName == node.tagName:
            count += 1
        sibling = sibling.previousSibling
    if count:
        index = '[%d]' % (count+1)
    else:
        index = ''
    return _getXPath(node.parentNode) + "/" + node.tagName + index

class DBSerializer:
    """Baseclass with methods to provide a mutex and a condition variable"""
    def __init__(self):   
        self.lockCount = 0
        self._waiting = {}
        self._lock = threading.RLock()

    def enter(self):
        """Enter the critical section for this database"""
        self._lock.acquire()
        self.lockCount += 1
        
    def leave(self):
        self._lock.release()

    def waitLocation(self, location, oldValue=None):
        """Register that we are interested in the given XPath. Returns the semaphore"""
        if not location in self._waiting:
            self._waiting[location] = [threading.Condition(self._lock), 0]
        if not oldValue is None:
            if oldValue < self._waiting[location][1]:
                print 'DBG waitLocation returning early for', oldValue
                return self._waiting[location][1]
        print 'DBG waitLocation waiting for', location
        self._waiting[location][0].wait()
        if dbapi.LOGGING: print 'waitLocation returned for', location, 'on', self._waiting[location]
        return self._waiting[location][1]
        
    def signalNodelist(self, nodelist):
        """Wake up clients waiting for the given nodes"""
        for location, cv in self._waiting.items():
            waitnodelist = xpath.find(location, self._doc.documentElement)
            for wn in waitnodelist:
                if wn in nodelist:
                    print 'DBG signal for', wn
                    cv[1] += 1
                    cv[0].notify_all()
                    break
        
class DBImpl(dbapi.DBAPI, DBSerializer):
    """Main implementation of the database API"""
    
    def __init__(self):
        dbapi.DBAPI.__init__(self)
        DBSerializer.__init__(self)
        self._terminating = False
        self._domimpl = xml.dom.getDOMImplementation()
        self.initialize(DOCUMENT)
        
    def getMessageCount(self):
        return self.lockCount
        
    def terminate(self):
        self._terminating = True
        sys.exit(1)
        
    def is_terminating(self):
        return self._terminating
        
    def initialize(self, xmlstring=DOCUMENT):
        """Reset the document to a known value (passed as an XML string"""
        if xmlstring:
            self._doc = xml.dom.minidom.parseString(xmlstring)
        else:
            self._doc = self._domimpl.createDocument('', 'root', None)
    
    def echo(self, arg):
        """Return the argument (for performance testing)"""
        return arg
        
    def pullDocument(self):
        """Return the whole document (as an XML string)"""
        rv = self._doc.toprettyxml()
        return rv
        
    def setValue(self, location, value):
        """Set (or insert) a single node by a given value (passed as a string)"""
        
        # Find the node, if it exists.
        node = xpath.findnode(location, self._doc.documentElement)
        if node is None:
            # Does not exist yet. Try to add it.
            lastSlashPos = location.rfind('/')
            if lastSlashPos > 0:
                parent = location[:lastSlashPos]
                child = location[lastSlashPos+1:]
            else:
                parent = '.'
                child = location
            return self.newValue(parent, 'child', child, value)

        # Sanity check
        if node.nodeType == node.DOCUMENT_NODE:
            raise DBParamError('Cannot replace value of /')
            
        # Clear out old contents of the node
        while node.firstChild: node.removeChild(node.firstChild)
        
        # Insert the new text value
        node.appendChild(self._doc.createTextNode(str(value)))
        
        # Signal anyone waiting
        self.signalNodelist([node])
        
        # Return the location of the new node
        return _getXPath(node)
        
    def newValue(self, location, where, name, value):
        """Insert a single new node into the document (value passed as a string)"""
        
        # Create the new node to be instered
        newnode = self._doc.createElement(name)
        newnode.appendChild(self._doc.createTextNode(str(value)))
        
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
        self.signalNodelist([newnode, newnode.parentNode])
        
        # Return the location of the new node
        return _getXPath(newnode)
        
    def delValue(self, location):
        """Remove a single node from the document"""
        node = xpath.findnode(location, self._doc.documentElement)
        if node is None:
            raise DBKeyError(location)
        parentNode = node.parentNode
        parentNode.removeChild(node)
        
        # Signal anyone waiting
        self.signalNodelist([parentNode])
        
    def delValues(self, location):
        """Remove a (possibly empty) set of nodes from the document"""
        nodelist = xpath.find(location, self._doc.documentElement)
        parentList = []
        for node in nodelist:
            parentNode = node.parentNode
            parentNode.removeChild(node)
            if not parentNode in parentList:
                parentList.append(parentNode)
        self.signalNodelist(parentList)
            
    def hasValue(self, location):
        """Return xpath if the location exists, None otherwise"""
        node = xpath.findnode(location, self._doc.documentElement)
        if node:
            return _getXPath(node)
        return None
        
    def waitValue(self, location):
        node = xpath.findnode(location, self._doc.documentElement)
        if not node:
            self.waitLocation(location)
            node = xpath.findnode(location, self._doc.documentElement)
            assert node
        return _getXPath(node)

    def hasValues(self, location):
        """Return a list of xpaths for the given location"""
        nodelist = xpath.find(location, self._doc.documentElement)
        return map(_getXPath, nodelist)
        
    def getValue(self, location):
        """Return a single value from the document (as string)"""
        return xpath.findvalue(location, self._doc.documentElement)
        
    def getValues(self, location):
        """Return a list of node values from the document (as names and strings)"""
        nodelist = xpath.find(location, self._doc.documentElement)
        return self._getValueList(nodelist)
        
    def _getValueList(self, nodelist):
        rv = []
        for node in nodelist:
            rv.append((_getXPath(node), xpath.expr.string_value(node)))
        return rv
        
    def pullValue(self, location):
        """Wait for a value, remove it from the document, return it (as string)"""
        node = xpath.findnode(location, self._doc.documentElement)
        if not node:
            self.waitLocation(location)
            node = xpath.findnode(location, self._doc.documentElement)
            assert node
        rv = xpath.expr.string_value(node)
        node.parentNode.removeChild(node)
        self.signalNodelist([parentnode])
        return rv
  
    def pullValues(self, location):
        """Wait for values, remove them from the document, return it (as list of strings)"""
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
                parentList.append(parentNode)
        self.signalNodelist(parentList)
        return rv
        
    def trackValue(self, location, generation):
        """Generator. Like waitValue, but keeps on returning changed paths"""
        generation = self.waitLocation(location, generation)
        node = xpath.findnode(location, self._doc.documentElement)
        assert node
        return _getXPath(node), generation
        
startRun = time.time()
def TS():
    #now = time.time()
    #subsecond = str(now-int(now))[1:6]
    #return time.strftime("%H:%M:%S", time.localtime(now)) + subsecond
    return "%10.4f" % (time.time()-startRun)
    
class DBDispatcher(DBImpl):
    """Wrapper class that implements XMLRPC dispatch while locking the mutex and
    providing stack traces if wanted"""
    
    def __init__(self):
        self.stacktrace = True
        self.calltrace = dbapi.LOGGING
        DBImpl.__init__(self)
        
    def _dispatch(self, methodname, params):
        try:
            startWait = time.time()
            self.enter()
            startCall = time.time()
            method = SimpleXMLRPCServer.resolve_dotted_attribute(self, methodname, False)
            rv = method(*params)
            now = time.time()
            if self.calltrace:
                print TS(), '-->  %s%s -> %s [wait=%f, exec=%f, %s]' % (methodname, params, rv, startCall-startWait, now-startCall, threading.currentThread().name)
            self.leave()
            return rv
        except:
            if self.calltrace:
                print TS(), 'EXC %s%s' % (methodname, params)
            elif self.stacktrace:
                print TS(), '-->  %s%s' % (methodname, params)
                print TS(), 'EXC %s%s' % (methodname, params)
            if self.stacktrace:
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)
            raise
