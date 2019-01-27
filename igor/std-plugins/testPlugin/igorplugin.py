"""Sample plugin module for Igor"""
from __future__ import unicode_literals


from builtins import object
class TestPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        rv = "test-plugin index\n"
        rv += "pluginName=%s, pluginData=%s" % (repr(self.pluginName), repr(self.pluginData))
        rv += "args=%s, kwargs=%s\n" % (repr(args), repr(kwargs))
        rv += "self.igor.database=%s\n" % repr(self.igor.database)
        rv += "self.igor.databaseAccessor=%s\n" % repr(self.igor.databaseAccessor)
        rv += "self.igor.internal=%s\n" % repr(self.igor.internal)
        rv += "self.igor.app=%s\n" % repr(self.igor.app)
        return rv
    
    def method2(self, *args, **kwargs):
        rv = "test-plugin method2\n"
        rv += "pluginName=%s, pluginData=%s" % (repr(self.pluginName), repr(self.pluginData))
        rv += "args=%s, kwargs=%s\n" % (repr(args), repr(kwargs))
        rv += "self.igor.database=%s\n" % repr(self.igor.database)
        rv += "self.igor.databaseAccessor=%s\n" % repr(self.igor.databaseAccessor)
        rv += "self.igor.internal=%s\n" % repr(self.igor.internal)
        rv += "self.igor.app=%s\n" % repr(self.igor.app)
        return rv
    
    def push(self, token=None, callerToken=None):
        dataPath = '/data/devices/%s' % self.pluginName
        data = self.igor.databaseAccessor.get_key(dataPath+'/outgoing', 'application/x-python-object', None, token)
        newData = dict(incoming=data)
        rv = self.igor.databaseAccessor.put_key(dataPath+'/incoming', 'text/plain', None, data, 'application/x-python-object', token, replace=True)
        return rv
    
    def _concat(self, first="", second="", token=None, callerToken=None):
        return first + second
        
def igorPlugin(igor, pluginName, pluginData):
    return TestPlugin(igor, pluginName, pluginData)
