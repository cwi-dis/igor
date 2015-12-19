import web
import shlex
import subprocess
import os
import re
import uuid

urls = (
	'/scripts/(.*)', 'runScript',
	'/data/(.*)', 'database',
	'/(.*)', 'hello',
)
app = web.application(urls, globals())

class hello:		
	def GET(self, *args, **kwargs):
		return 'Hello, args=' + repr(args) + ', kwargs=' + repr(kwargs) + ', input=' + repr(web.input())

class runScript:		
	def GET(self, command):
		allArgs = web.input()
		if '/' in command:
			return web.HTTPError("401 Cannot use / in command")
		if allArgs.has_key('args'):
			args = shlex.split(allArgs.args)
		else:
			args = []
		command = "./scripts/" + command
		try:
			linked = os.readlink(command)
			command = os.path.join(os.path.dirname(command), linked)
		except OSError:
			pass
		try:
			rv = subprocess.check_call([command] + args)
		except subprocess.CalledProcessError, arg:
			return web.HTTPError("502 Command %s exited with status code=%d" % (command, arg.returncode), {"Content-type": "text/plain"}, arg.output)
		except OSError, arg:
			return web.HTTPError("502 Error running command: %s: %s" % (command, arg.strerror))
		return rv

VALID_KEY = re.compile('[a-zA-Z0-9_-]{1,255}')
def is_valid_key(key):
    """Checks to see if the parameter follows the allow pattern of
    keys.
    """
    if VALID_KEY.match(key) is not None:
        return True
    return False

def validate_key(fn):
    """Decorator for HTTP methods that validates if resource
    name is a valid database key. Used to protect against
    directory traversal.
    """
    def new(*args):
        if not is_valid_key(args[1]):
            return web.badrequest()
        return fn(*args)
    return new
    
class AbstractDB(object):
    """Abstract database that handles the high-level HTTP primitives.
    """
    def GET(self, name):
        if len(name) <= 0:
            rv = '<html><body><b>Keys:</b><br />'
            for key in self.keys():
                rv += ''.join(['<a href="',str(key),'">',str(key),'</a><br />'])
            rv += '</body></html>'
            return rv
        else:
            return self.get_resource(name)

    @validate_key
    def POST(self, name):
        data = web.data()
        self.put_key(str(name), data)
        return str(name)

    @validate_key
    def DELETE(self, name):
        return self.delete_key(str(name))

    def PUT(self, name=None):
        """Creates a new document with the request's data and
        generates a unique key for that document.
        """
        key = str(uuid.uuid4())
        return self.POST(key)

    @validate_key
    def get_resource(self, name):
        result = self.get_key(str(name))
        return result

class MemoryDB(AbstractDB):
    """In memory storage engine.  Lacks persistence."""
    database = {}
    def get_key(self, key):
        try:
            return self.database[key]
        except KeyError:
            return web.notfound()

    def put_key(self, key, data):
        self.database[key] = data

    def delete_key(self, key):
        try:
            del(self.database[key])
        except KeyError:
            return web.notfound()

    def keys(self):
        return self.database.iterkeys()
        
database = MemoryDB
 
if __name__ == "__main__":
	app.run()
		
