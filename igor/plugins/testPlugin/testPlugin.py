"""Sample plugin module for homeServer"""

# These will be set upon import
DATABASE=None
COMMANDS=None
app=None

def testPlugin(*args, **kwargs):
    rv = "test-plugin\n"
    rv += "args=%s, kwargs=%s\n" % (repr(args), repr(kwargs))
    rv += "DATABASE=%s\n" % repr(DATABASE)
    rv += "COMMANDS=%s\n" % repr(COMMANDS)
    rv += "app=%s\n" % repr(app)
    return rv
    
    
