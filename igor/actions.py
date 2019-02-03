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
import functools
from . import xmlDatabase

INTERPOLATION=re.compile(r'\{[^}]+\}')

DEBUG=False

@functools.total_ordering
class NeverSmaller(object):
    def __le__(self, other):
        return False
        
    def __eq__(self, other):
        return type(other) == NeverSmaller

    def __repr__(self):
        return 'NEVER'

NEVER = NeverSmaller()  
assert NEVER > 1
assert 1 < NEVER
assert NEVER != 0
assert NEVER > 0
assert not (NEVER == 0)
assert time.time() < NEVER
assert not (NEVER < time.time())

class Action(object):
    """Object to implement calling methods on URLs whenever some XPath changes."""
    
    def __init__(self, collection, element):
        self.collection = collection
        self.element = element
        self.actionXPath = self.collection.igor.database.getXPathForElement(self.element)
        tag, self.content = self.collection.igor.database.tagAndDictFromElement(self.element)
        self.content.pop('notBefore', None)
        assert tag == 'action'
        if not 'url' in self.content:
            print("ERROR: action {} misses required url element".format(self.actionXPath))
            self.content['url'] = '/missing-action-url'
        self.interval = self.content.get('interval')
        self.minInterval = self.content.get('minInterval', 0)
        xpaths = self.content.get('xpath',[])
        if type(xpaths) != type([]):
            xpaths = [xpaths]
        self.xpaths = xpaths
        self.multiple = self.content.get('multiple')
        self.aggregate = self.content.get('aggregate')
        self.url = self.content.get('url')
        self.method = self.content.get('method')
        self.data = self.content.get('data')
        self.mimetype = self.content.get('mimetype','text/plain')
        self.condition = self.content.get('condition')
        self.representing = self.content.get('representing')
        self.accessChecker = self.collection.igor.access.checkerForElement(self.element)
        self.token = self.collection.igor.access.tokenForAction(self.element)
        self.nextTime = NEVER
        if self.interval:
            self._scheduleNextRunIn(0)
        self.install()
        
    def __repr__(self):
        return 'Action(0x%x, %s)' % (id(self), repr(self.content))
        
    def __eq__(self, other):
        return id(self) == id(other)
        
    def matches(self, element):
        """Check to see whether this action matches the given element (used during update)"""
        if not self.collection: return False
        tag, content = self.collection.igor.database.tagAndDictFromElement(element)
        content.pop('notBefore', None)
        rv = (content == self.content)
        return rv
        
    def delete(self):
        """Called when an action has been removed (or replaced) in the database"""
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
        self.collection = None
        self.element = None
                
    def callback(self, *nodelist):
        """Schedule the action, if it is runnable at this time, and according to the condition"""
        if not self.collection:
            print('ERROR: %s.callback() called but it is already deleted' % repr(self))
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
            # Note we don't call setChanged() on the database, it isn't worth it.
        nbText = nbElement.firstChild
        if nbText:
            #if DEBUG: print 'Action._willRunNow replace notBefore text data'
            nbText.data = str(earliestNextRun)
        else:
            #if DEBUG: print 'Action._willRunNow create notBefore text node'
            doc = self.element.ownerDocument
            nbText = doc.createTextNode(str(earliestNextRun))
            nbElement.appendChild(nbText)
            # Note we don't call setChanged() on the database, it isn't worth it.
        
    def _scheduleNextRunIn(self, interval):
        """Set the preferred (latest) next time this action should run"""
        nextTime = interval + time.time()
        self.nextTime = self._earliestRunTimeAfter(nextTime)
        if self.collection:
            self.collection.actionTimeChanged()
        
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
        self.nothingBefore = NEVER
        self.lock = threading.RLock()
        self.updateLock = threading.RLock()
        self.actionsChanged = threading.Condition(self.lock)
        self.database = self.igor.database
        self.scheduleCallback = self.igor.urlCaller.callURL
        self.stopping = False
        self.start()
        
    def dump(self):
        rv = 'ActionCollection %s, nothingBefore %s:\n' % (repr(self), self.nothingBefore)
        with self.lock:
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
                self.nothingBefore = NEVER
                toCall = []
                for a in self.actions:
                    if a.nextTime <= time.time():
                        toCall.append(a)
                    if a.nextTime < self.nothingBefore:
                        self.nothingBefore = a.nextTime
                        
                # Release the lock while we're doing the callbacks
                self.lock.release()
                for a in toCall:
                    a.callback()
                self.lock.acquire()
                
                # Repeat the loop if the earliest future time is in the past, by now.
                if self.nothingBefore < time.time():
                    continue
                if self.nothingBefore == NEVER:
                    waitTime = None
                else:
                    waitTime = self.nothingBefore - time.time()
                if DEBUG: print('ActionCollection.run wait(%s)' % waitTime)
                self.actionsChanged.wait(waitTime)
        
    def actionTimeChanged(self):
        """Called by an Action when its nextTime has changed, or when the actions have changed"""
        with self.lock:
            self.nothingBefore = time.time()
            self.actionsChanged.notify()
        
    def updateActions(self, nodelist):
        """Called by upper layers when something has changed in the actions in the database"""
        if DEBUG: print('ActionCollection(%s).updateActions(t=%d)' % (repr(self), time.time()))
        if DEBUG: print(self.dump())
        with self.updateLock:
            with self.lock:
                unchanged = []
                new = []
                removed = []
                added = []
                #
                # Pass one - check which action elements already exist (and are unchanged) and which are new
                #
                for node in nodelist:
                    assert node.tagName == "action"
                    for action in self.actions:
                        if action.matches(node):
                            unchanged.append(action)
                            break
                    else:
                        new.append(node)
                #
                # Pass two - determine which old actions no longer exist (or are changed)
                #
                for action in self.actions:
                    if not action in unchanged:
                        removed.append(action)
                if DEBUG: print('updateActions old %d, new %d, alreadyexist %d removed %d' % (len(self.actions), len(new), len(unchanged), len(removed)))
                assert len(self.actions) <= len(unchanged) + len(removed)
                if len(self.actions) < len(unchanged) + len(removed):
                    print('WARNING: duplicate actions skipped in updateActions')
                    actionSet = set(unchanged)
                    for a in unchanged:
                        if a in actionSet:
                            actionSet.remove(a)
                        else:
                            print('WARNING: duplicate:', a)
                #
                # Pass three - remove old actions
                #
                for action in removed:
                    assert action in self.actions
                    self.actions.remove(action)
                    assert not action in self.actions
            # Now (without holding the normal lock) delete and create the actions, which may update the database.
            #
            # Pass four - create new actions
            #
            for elt in new:
                action = Action(self, elt)
                added.append(action)
            # Pass five - uninstall removed actions
            #
            for action in removed:
                action.uninstall()
            #
            # Pass six - create new actions
            with self.lock:
                #
                # Pass seven - install new actions
                #
                for action in added:
                    self.actions.append(action)
                #
                # Signal the runner thread
                #
                self.actionTimeChanged()
        
    def triggerAction(self, node):
        """Called by the upper layers when a single action needs to be triggered"""
        if DEBUG: print('ActionCollection.triggerAction(%s)' % node)
        tocall = None
        with self.lock:
            for a in self.actions:
                if a.element == node:
                    tocall = a
                    break
            else:
                print('ERROR: triggerAction called for unknown element %s %s' % (repr(node), self.igor.database.getXPathForElement(node)))
                return
        tocall.callback()
            
    def stop(self):
        with self.lock:
            self.stopping = True
            self.actionTimeChanged()
        self.join()
        
