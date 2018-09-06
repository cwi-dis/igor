from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from past.builtins import cmp
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import re
import urllib.request, urllib.parse, urllib.error
import time
import threading
import queue
from . import xmlDatabase

INTERPOLATION=re.compile(r'\{[^}]+\}')

DEBUG=False

class NEVER(object):
    """Compares bigger than any number"""
    pass
    
assert NEVER > 1

class Action(object):
    """Object to implement calling methods on URLs whenever some XPath changes."""
    
    def __init__(self, collection, element):
        self.collection = collection
        self.element = element
        self.actionXPath = self.collection.igor.database.getXPathForElement(self.element)
        tag, content = self.collection.igor.database.tagAndDictFromElement(self.element)
        assert tag == 'action'
        assert 'url' in content
        self.interval = content.get('interval')
        self.minInterval = content.get('minInterval', 0)
        xpaths = content.get('xpath',[])
        if type(xpaths) != type([]):
            xpaths = [xpaths]
        self.xpaths = xpaths
        self.multiple = content.get('multiple')
        self.aggregate = content.get('aggregate')
        self.url = content.get('url')
        self.method = content.get('method')
        self.data = content.get('data')
        self.mimetype = content.get('mimetype','text/plain')
        self.condition = content.get('condition')
        self.representing = content.get('representing')
        self.accessChecker = self.collection.igor.access.checkerForElement(self.element)
        self.token = self.collection.igor.access.tokenForAction(self.element)
        self.nextTime = NEVER
        if self.interval:
            self._scheduleNextRunIn(0)
        self.install()
        
    def delete(self):
        self.uninstall()
        self.collection = None
        
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
            self.collection.igor.database.registerCallback(self.callback, xpath)
        
    def uninstall(self):
        """Remove any installed triggers from the database"""
        self.collection.igor.database.unregisterCallback(self.callback)
                
    def callback(self, *nodelist):
        """Schedule the action, if it is runnable at this time, and according to the condition"""
        if not self.collection:
            print('ERROR: Action.callback called without actionCollection:', self)
            return
        # Test whether we are allowed to run, depending on minInterval
        now = time.time()
        if self._earliestRunTimeAfter(now) > now:
            return
        # Run for each node (or once, if no node present because we were not triggered by an xpath)        
        if not nodelist:
            nodelist = [None]
        if DEBUG: print('Action%s.callback(%s)' % (repr(self), repr(nodelist)))
        for node in nodelist:
            # Test whether we are allowed to run according to our condition
            if self.condition:
                shouldRun = self.collection.igor.database.getValue(self.condition, token=self.token, context=node)
                if not shouldRun:
                    if DEBUG: print('\t%s: condition failed' % repr(node))
                    continue
            # Evaluate URL and paramters
            try:
                url = self._evaluate(self.url, node, True)
                if DEBUG: print('\t%s: calling %s' % (repr(node), url))
                data = self._evaluate(self.data, node, False)
            except xmlDatabase.DBAccessError:
                actionPath = self.collection.igor.database.getXPathForElement(self.element)
                nodePath = self.collection.igor.database.getXPathForElement(node)
                print("actions: Error: action %s lacks AWT permission for '%s' or '%s'" % (actionPath, self.url, self.data))
                # self.collection.igor.app.request('/internal/updateStatus/%s' % self.representing, method='POST', data=json.dumps(args), headers={'Content-type':'application/json'})
                continue
            # Prepare to run
            tocall = dict(method=self.method, url=url, token=self.token)
            if data:
                tocall['data'] = data
            tocall['mimetype'] = self.mimetype
            tocall['aggregate'] = self.aggregate
            tocall['representing'] = self.representing
            tocall['original_action'] = self.actionXPath
            # xxxjack can add things like mimetype, credentials, etc
            self._willRunNow()
            self.collection.scheduleCallback(tocall)
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
        #if DEBUG: print 'Action%s._willRunNow, t=%d' % (self, earliestNextRun)
        nbElements = self.element.getElementsByTagName("notBefore")
        if nbElements:
            nbElement = nbElements[0]
        else:
            #if DEBUG: print 'Action._willRunNow create notBefore element'
            doc = self.element.ownerDocument
            nbElement = doc.createElement("notBefore")
            self.element.appendChild(nbElement)
        nbText = nbElement.firstChild
        if nbText:
            #if DEBUG: print 'Action._willRunNow replace notBefore text data'
            nbText.data = str(earliestNextRun)
        else:
            #if DEBUG: print 'Action._willRunNow create notBefore text node'
            doc = self.element.ownerDocument
            nbText = doc.createTextNode(str(earliestNextRun))
            nbElement.appendChild(nbText)
        
    def _scheduleNextRunIn(self, interval):
        """Set the preferred (latest) next time this action should run"""
        nextTime = interval + time.time()
        self.nextTime = self._earliestRunTimeAfter(nextTime)
        if self.collection:
            self.collection.actionTimeChanged(self)
        
    def _evaluate(self, text, node, urlencode):
        """Interpolate {xpathexpr} expressions in a string"""
        if not text: return text
        text = str(text)
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
            if expression[0] == '{':
                # Escaped { and }. Unfortunately both must be escaped...
                replacement = expression
            else:
                replacement = self.collection.igor.database.getValue(expression, token=self.token, context=node)
                if replacement is None: replacement = ''
                if type(replacement) == type(True):
                    replacement = 'true' if replacement else ''
                replacement = str(replacement)
                if urlencode:
                    replacement = urllib.parse.quote_plus(replacement)
            newtext = newtext + text[:match.start()] + replacement
            text = text[match.end():]
        return newtext
        
    def __cmp__(self, other):
        return cmp(self.nextTime, other.nextTime)
        
    def __hash__(self):
        return id(self)
                
class ActionCollection(threading.Thread):
    def __init__(self, igor):
        threading.Thread.__init__(self)
        self.igor = igor
        self.daemon = True
        self.actions = []
        self.lock = threading.RLock()
        self.actionsChanged = threading.Condition(self.lock)
        self.database = self.igor.database
        self.scheduleCallback = self.igor.urlCaller.callURL
        self.stopping = False
        self.start()
        
    def dump(self):
        rv = 'ActionCollection %s:\n' % repr(self)
        self.actions.sort()
        for a in self.actions:
            rv += '\t' + a.dump() + '\n'
        return rv
        
    def run(self):
        """Thread that triggers timed actions as they become elegible"""
        with self.lock:
            while not self.stopping:
                #
                # Run all actions that have a scheduled time now (or in the past)
                # and remember the earliest future action time
                #
                if DEBUG: print('ActionCollection.run(t=%d)' % time.time())
                nothingBefore = NEVER
                toCall = []
                for a in self.actions:
                    if a.nextTime <= time.time():
                        toCall.append(a)
                    if a.nextTime < nothingBefore:
                        nothingBefore = a.nextTime
                        
                # Release the lock while we're doing the callbacks
                self.lock.release()
                for a in toCall:
                    a.callback()
                self.lock.acquire()
                
                # Repeat the loop if the earliest future time is in the past, by now.
                if nothingBefore < time.time():
                    continue
                if nothingBefore == NEVER:
                    waitTime = None
                else:
                    waitTime = nothingBefore - time.time()
                self.actionsChanged.wait(waitTime)
        
    def actionTimeChanged(self, action):
        """Called by an Action when its nextTime has changed"""
        with self.lock:
            self.actionsChanged.notify()
        
    def updateActions(self, node):
        """Called by upper layers when something has changed in the actions in the database"""
        if DEBUG: print('ActionCollection.updateActions(t=%d)' % time.time())
        assert node.tagName == 'actions'
        with self.lock:
            # Clear out old queue
            for a in self.actions:
                a.delete()
            self.actions = []
            # Fill the queue with the new actions
            # Now create new triggers
            child = node.firstChild
            while child:
                if child.nodeType == child.ELEMENT_NODE and child.tagName == 'action':
                    action = Action(self, child)
                    self.actions.append(action)
                child = child.nextSibling
            # Signal the runner thread
            self.actionsChanged.notify()
        
    def triggerAction(self, node):
        """Called by the upper layers when a single action needs to be triggered"""
        if DEBUG: print('ActionCollection.triggerAction(%s)' % node)   
        for a in self.actions:
            if a.element == node:
                a.callback()
                return
        print('ERROR: triggerAction called for unknown element', repr(node))
            
    def stop(self):
        with self.lock:
            self.stopping = True
            self.actionsChanged.notify()
        self.join()
        
