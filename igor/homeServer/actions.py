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
    
    def __init__(self, hoster, interval, url, method=None, data=None, mimetype=None, condition=None):
        self.hoster = hoster
        self.interval = interval
        self.url = url
        self.method = method
        self.data = data
        self.mimetype = mimetype
        if not self.mimetype:
            self.mimetype = 'text/plain'
        self.condition = condition
        self.nextTime = NEVER
        if self.interval:
            self.nextTime = time.time()
        self.install()
        
    def delete(self):
        self.uninstall()
        self.hoster = None
        
    def install(self):
        pass
        
    def uninstall(self):
        pass
                
    def callback(self, node=None):
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
        self.actionQueue.put(action)
        self.actionQueueEvent.set()
        
    def updateActions(self, node):
        tag, content = self.database.tagAndDictFromElement(node)
        assert tag == 'actions'
        # Clear out old queue
        while not self.actionQueue.empty():
            self.actionQueue.get()
        # Fill the queue with the new actions
        newActions = content.get('action', [])
        if type(newActions) == type({}):
            newActions = [newActions]
        assert type(newActions) == type([])
        for new in newActions:
            assert type(new) == type({})
            assert 'interval' in new
            assert 'url' in new
            interval = new.get('interval')
            url = new['url']
            condition = new.get('condition')
            method = new.get('method')
            data = new.get('data')
            mimetype = new.get('mimetype')
            action = Action(self, interval, url, method, data, mimetype, condition)
            self.actionQueue.put(action)
        # Signal the runner thread
        self.actionQueueEvent.set()
            
