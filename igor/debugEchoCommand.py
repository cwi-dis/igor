from __future__ import unicode_literals
def echoCommand(*args, **kwargs):
    rv = "Content-Type: text/plain\n\n"
    rv += "Arguments: %s\n" % repr(args)
    rv += "Keyword arguments: %s\n" % repr(kwargs)
    return rv
    
