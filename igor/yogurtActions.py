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

DEBUG=True
                
class YogurtActionCollection(threading.Thread):
    def __init__(self, igor):
        threading.Thread.__init__(self)
        self.igor = igor
        self.lock = threading.RLock()
        self.stopping = False
        self.start()
        
    def dump(self):
        rv = 'YogurtActionCollection %s, nothing to see here\n' % (repr(self))
        return rv
        
    def run(self):
        """Thread that triggers timed actions as they become elegible"""
        with self.lock:
            while not self.stopping:
                #
                # Run all actions that have a scheduled time now (or in the past)
                # and remember the earliest future action time
                #
                if DEBUG: print('YogurtActionCollection.run(t=%d)' % time.time())
                time.sleep(1)

    def updateActions(self, nodelist):
        """Called by upper layers when something has changed in the actions in the database"""
        if DEBUG: print('YogurtActionCollection(%s).updateActions(t=%d)' % (repr(self), time.time()))
        
    def triggerAction(self, node):
        """Called by the upper layers when a single action needs to be triggered"""
        if DEBUG: print('YogurtActionCollection.triggerAction(%s)' % node)
            
    def stop(self):
        with self.lock:
            self.stopping = True
        self.join()
        
