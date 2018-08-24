"""Sample plugin module for Igor"""


class TestPlugin:
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        rv = "test-plugin index\n"
        rv += "pluginName=%s, pluginData=%s" % (repr(pluginName), repr(pluginData))
        rv += "args=%s, kwargs=%s\n" % (repr(args), repr(kwargs))
        rv += "self.igor.database=%s\n" % repr(self.igor.database)
        rv += "self.igor.databaseAccessor=%s\n" % repr(self.igor.databaseAccessor)
        rv += "self.igor.internal=%s\n" % repr(self.igor.internal)
        rv += "self.igor.app=%s\n" % repr(self.igor.app)
        return rv
    
    def method2(self, *args, **kwargs):
        rv = "test-plugin method2\n"
        rv += "pluginName=%s, pluginData=%s" % (repr(pluginName), repr(pluginData))
        rv += "args=%s, kwargs=%s\n" % (repr(args), repr(kwargs))
        rv += "self.igor.database=%s\n" % repr(self.igor.database)
        rv += "self.igor.databaseAccessor=%s\n" % repr(self.igor.databaseAccessor)
        rv += "self.igor.internal=%s\n" % repr(self.igor.internal)
        rv += "self.igor.app=%s\n" % repr(self.igor.app)
        return rv
    
    
def igorPlugin(igor, pluginName, pluginData):
    return TestPlugin(igor, pluginName, pluginData)
