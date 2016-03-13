import re
import urllib
import time
import threading
import Queue

INTERPOLATION=re.compile(r'\{[^}]+\}')

DEBUG=False

class NEVER:
    """Compares bigger than any number"""
    pass
    
assert NEVER > 1

class Action:
    """Object to implement calling methods on URLs whenever some XPath changes."""
    
    def __init__(self, hoster, element):
        self.hoster = hoster
        self.element = element
        tag, content = self.hoster.database.tagAndDictFromElement(self.element)
        assert tag == 'action'
        assert 'url' in content
        self.interval = content.get('interval')
        self.minInterval = content.get('minInterval', 0)
        xpaths = content.get('xpath',[])
        if type(xpaths) != type([]):
            xpaths = [xpaths]
        self.xpaths = xpaths
        self.multiple = content.get('multiple')
        self.url = content.get('url')
        self.method = content.get('method')
        self.data = content.get('data')
        self.mimetype = content.get('mimetype','text/plain')
        self.condition = content.get('condition')
        self.nextTime = NEVER
        if self.interval:
            self._scheduleNextRunIn(0)
        self.install()
        
    def delete(self):
        self.uninstall()
        self.hoster = None
        
    def dump(self):
        t = self.nextTime
        if t == NEVER:
            t = 'NEVER'
        else:
            t = t - time.time()
        d = dict(t=t, url=self.url, xpaths=self.xpaths, interval=self.interval)
        rv = repr(d)
        return rv
        
    def install(self):
        """Install any xpath triggers needed by this action into the database"""
        for xpath in self.xpaths:
            self.hoster.database.registerCallback(self.callback, xpath)
        
    def uninstall(self):
        """Remove any installed triggers from the database"""
        self.hoster.database.unregisterCallback(self.callback)
                
    def callback(self, *nodelist):
        """Schedule the action, if it is runnable at this time, and according to the condition"""
        if not self.hoster:
            print 'ERROR: Action.callback called without hoster:', self
            return
        # Test whether we are allowed to run, depending on minInterval
        now = time.time()
        if self._earliestRunTimeAfter(now) > now:
            return
        # Run for each node (or once, if no node present because we were not triggered by an xpath)        
        if not nodelist:
            nodelist = [None]
        for node in nodelist:
            # Test whether we are allowed to run according to our condition
            if self.condition:
                shouldRun = self.hoster.database.getValue(self.condition, node)
                if not shouldRun:
                    continue
            # Evaluate URL and paramteres
            url = self._evaluate(self.url, node, True)
            data = self._evaluate(self.data, node, False)
            # Prepare to run
            tocall = dict(method=self.method, url=url)
            if data:
                tocall['data'] = data
            tocall['mimetype'] = self.mimetype
            # xxxjack can add things like mimetype, credentials, etc
            self._willRunNow()
            self.hoster.scheduleCallback(tocall)
            # If we are running from an xpath we only run once (for the first matching node) unless multiple is given
            if not self.multiple:
                break
        # Update our next run time, if we have an interval
        if self.interval:
            self._scheduleNextRunIn(self.interval)
        
    def _earliestRunTimeAfter(self, t):
        """Check whether the action is runnable at this time"""
        nbElements = self.element.getElementsByTagName("notBefore")
        if not nbElements:
            return t
        nbText = nbElements[0].firstChild
        if not nbText:
            return t
        nbString = nbText.nodeValue
        if not nbString:
            return t
        notBefore = int(nbString)
        if notBefore < t:
            return t
        return notBefore
            
    def _willRunNow(self):
        """Action will run. Make sure its notBefore is set"""
        earliestNextRun = int(time.time())
        if self.minInterval:
            earliestNextRun += self.minInterval
        if DEBUG: print 'Action._willRunNow', earliestNextRun
        nbElements = self.element.getElementsByTagName("notBefore")
        if nbElements:
            nbElement = nbElements[0]
        else:
            if DEBUG: print 'Action._willRunNow create notBefore element'
            doc = self.element.ownerDocument
            nbElement = doc.createElement("notBefore")
            self.element.appendChild(nbElement)
        nbText = nbElement.firstChild
        if nbText:
            if DEBUG: print 'Action._willRunNow replace text data'
            nbText.data = unicode(earliestNextRun)
        else:
            if DEBUG: print 'Action._willRunNow create text node'
            doc = self.element.ownerDocument
            nbText = doc.createTextNode(unicode(earliestNextRun))
            nbElement.appendChild(nbText)
        
    def _scheduleNextRunIn(self, interval):
        """Set the preferred (latest) next time this action should run"""
        nextTime = interval + time.time()
        self.nextTime = self._earliestRunTimeAfter(nextTime)
        if self.hoster:
            self.hoster.actionTimeChanged(self)
        
    def _evaluate(self, text, node, urlencode):
        """Interpolate {xpathexpr} expressions in a string"""
        if not text: return text
        text = unicode(text)
        newtext = ''
        while True:
            match = INTERPOLATION.search(text)
            if not match:
                newtext += text
                break
            expression = text[match.start():match.end()]
            assert expression[0] == '{'
            assert expression[-1] == '}'
            expression = expression[1:-1]
            replacement = self.hoster.database.getValue(expression, node)
            if replacement is None: replacement = ''
            replacement = str(replacement)
            if urlencode:
                replacement = urllib.quote_plus(replacement)
            newtext = newtext + text[:match.start()] + replacement
            text = text[match.end():]
        return newtext
        
    def __cmp__(self, other):
        return cmp(self.nextTime, other.nextTime)
        
    def __hash__(self):
        return id(self)
                
class ActionCollection(threading.Thread):
    def __init__(self, database, scheduleCallback):
        threading.Thread.__init__(self)
        self.daemon = True
        self.actionQueue = Queue.PriorityQueue()
        self.actionQueueEvent = threading.Event()
        self.database = database
        self.scheduleCallback = scheduleCallback
        self.start()
        
    def dump(self):
        rv = 'ActionCollection %s:\n' % repr(self)
        for qel in self.actionQueue.queue:
            rv += '\t' + qel.dump() + '\n'
        return rv
        
    def run(self):
        """Thread that triggers timed actions as they become elegible"""
        while True:
            # Get the earliest queue element and run it if its time has come
            nextAction = self.actionQueue.get()
            nextActionTime = nextAction.nextTime
            if nextActionTime != NEVER:
                if nextActionTime < time.time():
                    nextAction.callback()
                    self.actionQueue.put(nextAction)
                    continue
            # If it is not runnable we put it back (probably at the front) and wait
            self.actionQueue.put(nextAction)
            # And wait
            if nextActionTime == NEVER:
                waitTime = None
            else:
                waitTime = nextActionTime - time.time()
            self.actionQueueEvent.wait(waitTime)
            self.actionQueueEvent.clear()
        
    def actionTimeChanged(self, action):
        """Called by an Action when its nextActionTime has changed"""
        self.actionQueue.put(action)
        self.actionQueueEvent.set()
        
    def updateActions(self, node):
        """Called by upper layers when something has changed in the actions in the database"""
        assert node.tagName == 'actions'
        # Clear out old queue
        while not self.actionQueue.empty():
            self.actionQueue.get()
        # Fill the queue with the new actions
        # Now create new triggers
        child = node.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE and child.tagName == 'action':
                action = Action(self, child)
                self.actionQueue.put(action)
            child = child.nextSibling
        # Signal the runner thread
        self.actionQueueEvent.set()
        
    def triggerAction(self, node):
        """Called by the upper layers when a single action needs to be triggered"""
        for a in self.actionQueue.queue:
            if a.element == node:
                a.callback()
                return
        print 'ERROR: triggerAction called for unknown element', repr(node)
            
