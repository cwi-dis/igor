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

def fixupXmlData(value):
    if not value:
        value = []
    if not isinstance(value, list):
        value = [value]
    return value

DEBUG=False

class YogurtTrigger:
    def __init__(self, action, trigger):
        self.action = action
        parts = trigger.split(".")
        if len(parts) == 1:
            triggeringInstance = self.action.instance
            triggeringStateName = parts[0]
        elif len(parts) == 2:
            triggeringInstance = self.action.instance.lookupTriggerInstance(parts[0])
            triggeringStateName = parts[1]
        else:
            assert 0
        self.xpath = triggeringInstance.lookupXPathForState(triggeringStateName)
        print("Testing Trigger Name:")
        print(triggeringStateName)

    def dump(self):
        return f"\n\t\t\ttrigger on xpath {self.xpath}"

class YogurtAction:
    def __init__(self, instance, on=None, update=None, **kwargs):
        self.instance = instance
        assert on
        assert update
        assert not kwargs
        self.triggers = []
        for trigger in fixupXmlData(on.get("trigger")):
            self.triggers.append(YogurtTrigger(self, trigger))
        self.update = update

    def dump(self):
        rv = f'\n\t\tAction:'
        for t in self.triggers:
            rv += t.dump()
        return rv

class YogurtInstance:
    def __init__(self, actor, name=None, location=None, inputs=None, actions=None, **kwargs):        # in here build the function that puts together XPaths | * all positional param that havent been assigned
        self.actor = actor
        assert name
        assert location
        assert not kwargs
        self.name = name
        self.location = location
        self.inputs = fixupXmlData(inputs)
        self.actions = []
        for a in actions:
            self.actions.append(YogurtAction(self, **a))

    
    
    
    def lookupTriggerInstance(self, name):
        return "The Trigger Instance Look up Output"
    
    def lookupXPathForState(self, name):
        state_local_name = name
        return "State local name: " + state_local_name 

   
    # Function for finding instance states paths
 
    def instantiateActions(self):
        pass
    
    def dump(self):
        print("Instance Name")
        print(self.name)
        print("Instance Location:")
        print(self.location)
        print("Instance actions")
        print(self.actor.actions)
        print("Instance Actors States")
        print(self.actor.states)
        for state in self.actor.states:
            print(state)
        
        print("Test")
        print("Look Up Trigger Instance check:")
        print(lookupTriggerInstance("kitchen_light"))
        rv = f'\n\tInstance {self.name}:\n\t\tlocation={self.location}\n\t\tinputs={self.inputs}'
        for a in self.actions:
            rv += a.dump()
        return rv


class YogurtActor:
    def __init__(self, collection, element):
        self.collection = collection
        self.element = element
        tag, self.content = self.collection.igor.database.tagAndDictFromElement(self.element)
        self.name = self.content.get('name')
        
        self.states = fixupXmlData(self.content.get('states', {}).get('state'))
    
        instances = fixupXmlData(self.content.get('instances', {}).get('instance'))
        print(repr(instances))
        self.actions = fixupXmlData(self.content.get('actions', {}).get('action'))
        self.instances = [YogurtInstance(self, actions = self.actions, **instance) for instance in instances] 
        """
        for key, instance in instances.items():
            obj = YogurtInstance(self, **instance)      #** passes the dictionary keys 
            self.instances[key] = obj
        """

        
        #self.actions = [YogurtInstance(self, **action) for action in actions]
        # self.actions = actions
        # self.trigger = self.content.get('trigger')
        # self.target = self.content.get('target')
        # self.value = self.content.get('value')
            
    def dump(self):
        rv = 'Description of actor %s: \n\tstates=%s\n\tcontent=%s\n\tactions=%s' % (self.name, self.states, repr(self.content), repr(self.actions))
        print(self.actions)
        for i in self.instances:
            rv += i.dump()
        return rv
    
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