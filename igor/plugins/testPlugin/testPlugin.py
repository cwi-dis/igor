"""Sample plugin module for Igor"""

# These will be set upon import
DATABASE=None
DATABASE_ACCESS=None
COMMANDS=None
WEBAPP=None

class TestPlugin:
    def __init__(self, pluginName, pluginData):
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        rv = "test-plugin index\n"
        rv += "pluginName=%s, pluginData=%s" % (repr(pluginName), repr(pluginData))
        rv += "args=%s, kwargs=%s\n" % (repr(args), repr(kwargs))
        rv += "DATABASE=%s\n" % repr(DATABASE)
        rv += "DATABASE_ACCESS=%s\n" % repr(DATABASE_ACCESS)
        rv += "COMMANDS=%s\n" % repr(COMMANDS)
        rv += "WEBAPP=%s\n" % repr(WEBAPP)
        return rv
    
    def method2(self, *args, **kwargs):
        rv = "test-plugin method2\n"
        rv += "pluginName=%s, pluginData=%s" % (repr(pluginName), repr(pluginData))
        rv += "args=%s, kwargs=%s\n" % (repr(args), repr(kwargs))
        rv += "DATABASE=%s\n" % repr(DATABASE)
        rv += "DATABASE_ACCESS=%s\n" % repr(DATABASE_ACCESS)
        rv += "COMMANDS=%s\n" % repr(COMMANDS)
        rv += "WEBAPP=%s\n" % repr(WEBAPP)
        return rv
    
    
def igorPlugin(pluginName, pluginData):
    return TestPlugin(pluginName, pluginData)
