import re
import urllib
import time
import threading
import Queue

INTERPOLATION=re.compile(r'\{[^}]+\}')

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
        self.url = content.get('url')
        self.method = content.get('method')
        self.data = content.get('data')
        self.mimetype = content.get('mimetype','text/plain')
        self.condition = content.get('condition')
        self.nextTime = NEVER
        if self.interval:
            self._setNextActionTime(time.time())
        self.install()
        
    def delete(self):
        self.uninstall()
        self.hoster = None
        
    def install(self):
        pass
        
    def uninstall(self):
        pass
                
    def callback(self, node=None):
        if not self.hoster:
            print 'ERROR: Action.callback called without hoster:', self
            return
        if self.condition:
            shouldRun = self.hoster.database.getValue(self.condition, node)
            if not shouldRun:
                return time.time() + self.interval
        url = self._evaluate(self.url, node, True)
        data = self._evaluate(self.data, node, False)
        tocall = dict(method=self.method, url=url)
        if data:
            tocall['data'] = data
        tocall['mimetype'] = self.mimetype
        # xxxjack can add things like mimetype, credentials, etc
        self.hoster.scheduleCallback(tocall)
        self._setNextActionTime(time.time() + self.interval)
        
    def _setNextActionTime(self, nextTime):
        self.nextTime = nextTime
        if self.hoster:
            self.hoster.actionTimeChanged(self)
        
    def _evaluate(self, text, node, urlencode):
        """Interpolate {xpathexpr} expressions in a string"""
        if not text: return text
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
                
class ActionCollection(threading.Thread):
    def __init__(self, database, scheduleCallback):
        threading.Thread.__init__(self)
        self.daemon = True
        self.actionQueue = Queue.PriorityQueue()
        self.actionQueueEvent = threading.Event()
        self.database = database
        self.scheduleCallback = scheduleCallback
        self.start()
        
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
            
