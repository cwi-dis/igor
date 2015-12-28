import inspect
import threading

LOGGING=True
DEBUG=False
TRANSPORT='json'
#TRANSPORT='xmlrpc'

class DBAPI:
    """The API to the database. Really for documentary purposes only, but
    calling __init__ will check that the subclass matches this baseclass
    at least on the name level"""
    def __init__(self):
        ok = True
        bases = inspect.getmro(self.__class__)
        for name in dir(DBAPI):
            if name[0] != '_':
                for base in bases:
                    if name in base.__dict__:
                        if base == DBAPI:
                            print '* ERROR: API mismatch: %s: missing DBAPI member %s' % (self.__class__.__name__, name)
                            ok = False
                        break
        assert ok
    
    def echo(self, arg):
        """Returns the argument. Used for testing basic performance of the transport layer"""
        return arg
                 
    def terminate(self):
        """Terminate the connection manager. XXX Not sure this is part of the API"""
        
    def initialize(self):
        """Reset the document to a known value (passed as an XML string.
        XXX Not sure this is part of the API."""
        
    def getMessageCount(self):
        """Return number of transactions done by the database so far."""
        return 1
    
    def pullDocument(self):
        """Return the whole document (as an XML string)"""
        
    def setValue(self, location, value):
        """Set (or insert) a single node by a given value (passed as a string).
        Return the location (xpath) of the new node"""
        return "/"
        
    def newValue(self, location, where, name, value):
        """Insert a single new node into the document (value passed as a string).
        Return the location (xpath) of the new node"""
        return "/"
                
    def delValue(self, location):
        """Remove a single node from the document"""
        
    def delValues(self, location):
        """Remove a (possibly empty) set of nodes from the document"""
        
    def hasValue(self, location):
        """Return xpath if the location(s) exists, None otherwise"""
        return "/"
        
    def waitValue(self, location):
        """Wait for location(s) to change, then return the location."""
        return "/"

    def hasValues(self, location):
        """Return a list of xpaths for the given location"""
        return ["/"]
        
    def getValue(self, location):
        """Return a single value from the document (as string)"""
        return ""
                
    def getValues(self, location):
        """Return a list of node values from the document (as xpaths and strings)"""
        return [["/", ""]]

    def pullValue(self, location):
        """Wait for a value, remove it from the document, return it (as string)"""
        return ""

    def pullValues(self, location, wait=False):
        """Wait for values, remove them from the document, return it (as list of strings)"""
        return ["/"]
        
    def trackValue(self, location, generation):
        """Generator. Like waitValue, but keeps on returning changed paths"""
        return ["/", 1]
            
class SubTask(threading.Thread):
    """Helper class: thread with a prpoxy connection"""
    def __init__(self):
        threading.Thread.__init__(self)
        self.proxy = DBProxy()
        
    def run(self):
        while True:
            self.runStep()
                  
class WaiterSubTask(SubTask):
    def __init__(self, cv, variable):
        SubTask.__init__(self)
        self.cv = cv
        self.variable = variable
        self.generation = 0
        
    def runStep(self):
        self.generation = self.proxy.trackValue(self.variable, self.generation)
        if LOGGING: print 'Waiter: %s triggered' % self.variable
        self.wakeMaster()
      
    def wakeMaster(self):
        assert self.cv is not None
        self.cv.acquire()
        self.cv.notify()
        self.cv.release()
