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
class YogurtInstance:
    def __init__(self, actor):        # in here build the function that puts together XPaths
        self.actor = actor
        self.actions = 
    def instantiateActions(self):
        for action in self.actions:
            self.actor.collection._addAction()


class YogurtActor:
    def __init__(self, collection, element):
        self.collection = collection
        self.element = element
        tag, self.content = self.collection.igor.database.tagAndDictFromElement(self.element)
        self.name = self.content.get('name')
        states = self.content.get('states')
        if not states:
            states = []
        elif not isinstance(states, list):
            states = [states]
        self.states = states
        self.instances = []
        self.localName = self.content.get('localName')
        self.path = self.content.get('path')
        self.ID = self.content.get('ID')
        self.DBpath = self.content.get('DBpath')
        self.input = self.content.get('input')
        self.trigger = self.content.get('trigger')
        self.target = self.content.get('target')
        self.value = self.content.get('value')
        self.type = self.content.get('type')
        self.inputID = self.content.get('inputID')
            
    def dump(self):
        return 'Description of actor %s: \n\tstates=%s\n\tcontent=%s' % (self.name, self.states, repr(self.content))

    def instantiateActions(self):
        for instance in self.instances:
            print('xxx should instantiate instance')
            instance.instantiateActions()

class YogurtActionCollection(threading.Thread):
    def __init__(self, igor, elementList):
        threading.Thread.__init__(self)
        self.igor = igor
        self.actors = []
        for element in elementList:
            self.actors.append(YogurtActor(self, element))
        self.actions = []
        for actor in self.actors:
            actor.instantiateActions()
        
    def dump(self):
        #d = dict(name=self.name, path = self.path, localName = self.localName)
        rv = "YogurtActionCollection: %d actors:" % len(self.actors)
        for a in self.actors:
            rv = rv + '\n' + a.dump()
        return rv
        
    def run(self):
        """Thread that triggers timed actions as they become elegible"""
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
        self.stopping = True
        self.join()

    def _addAction(self):
        """Internal method called when instantiating an action for an instance of an actor"""