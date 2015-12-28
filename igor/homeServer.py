import web
import shlex
import subprocess
import os
import re
import uuid
import json
import dbimpl

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
	
class AbstractDB(object):
	"""Abstract database that handles the high-level HTTP primitives.
	"""
	def GET(self, name):
		optArgs = web.input()
		if optArgs:
			optArgs = dict(optArgs)
			method = self.POST
			if '.METHOD' in optArgs:
				method = getattr(self, optArgs['.METHOD'])
				del optArgs['.METHOD']
			data = json.dumps(optArgs)
			return method(name, data)
		print 'call getResource'
		rv = self.get_resource(name)
		print 'returned', repr(rv)
		return rv

	def POST(self, name, data=None):
		if data is None: data = web.data()
		print 'data=', repr(data)
		errorreturn = self.put_key(str(name), data)
		if errorreturn: return errorreturn
		return str(name)

	def DELETE(self, name, data=None):
		return self.delete_key(str(name))

	def PUT(self, name=None, data=None):
		"""Creates a new document with the request's data and
		generates a unique key for that document.
		"""
		name = self.create_key(name)
		if not name: return web.notfound()
		key = str(name)
		return self.POST(key, data)

	def get_resource(self, name):
		print 'get_resource', name
		result = self.get_key(name)
		return result

class MemoryDB(AbstractDB):
	"""In memory storage engine.  Lacks persistence."""
	database = {}
	def create_key(self, key=None):
		if str(key) in self.database:
			return key
		return uuid.uuid4()
		
	def get_key(self, key):
		print 'get_key', repr(key)
		if not key:
			return self.keys()
		try:
			return self.database[key]
		except KeyError:
			return web.notfound()

	def put_key(self, key, data):
		self.database[key] = data
		return None

	def delete_key(self, key):
		try:
			del(self.database[key])
		except KeyError:
			return web.notfound()

	def keys(self):
		rv = 'Keys: ' + ' '.join(self.database.keys())
		print 'Keys returning', rv
		return rv
		
class FileDB(AbstractDB):
	"""In memory storage engine.  Lacks persistence."""
	basedir = './data/'
	
	def create_key(self, key):
		# Creating a key that already exists simply returns it
		filename = self.basedir + str(key)
		if os.path.exists(filename):
			return key
		# It doesn't exist yet. See what we must do
		basedir, newname = os.path.split(filename)
		if not os.path.exists(basedir):
			# The parent doesn't exist either. This is an error.
			return None
		if not os.path.isdir(basedir):
			# The parent exists, but is a file. Turn it into a directory.
			tmpname = basedir+'~'
			os.rename(basedir, tmpname)
			os.mkdir(basedir)
			os.rename(tmpname, basedir+'/.data')
		assert os.path.isdir(basedir)
		# If a name was given we use that as-is, otherwise we add a random bit
		if newname:
			# Create the file
			open(filename, 'w')
			return key
		assert key == '' or key[-1] == '/'
		key = key + uuid.uuid4()
		filename = self.basedir + str(key)
		open(filename, 'w')
		return key
		
	def get_key(self, key):
		filename = self.basedir + key
		if os.path.isdir(filename):
			subfilename = filename + '/.data'
			if os.path.exists(subfilename):
				data = open(subfilename).read()
			else:
				# XXXJACK is this a good idea? Possibly not...
				data = 'Keys:'
				for entry in os.listdir(filename):
					if entry[0] != '.':
						data += ' ' + entry
				data += '\n'
			return data
		elif os.path.exists(filename):
			data = open(filename).read()
			return data
		else:
			return web.notfound()

	def put_key(self, key, data):
		filename = self.basedir + key
		print 'put_key', repr(filename)
		if os.path.isdir(filename):
			filename = filename + '/.data'
		if not os.path.exists(filename):
			return web.notfound()
		open(filename, 'w').write(data)
		return None

	def delete_key(self, key):
		assert 0
		try:
			del(self.database[key])
		except KeyError:
			return web.notfound()

	def keys(self):
		return self.database.iterkeys()
		
class XMLDB(AbstractDB):
	def __init__(self):
		self.db = dbimpl.DBImpl("./data/database.xml")


	def create_key(self, key):
		realKey = self.db.hasValue(key)
		if realKey:
			return realKey
		# Otherwise create it
		self.db.setValue(key, "")
		realKey = self.db.hasValue(key)
		assert realKey
		return realKey
		
	def get_key(self, key):
		if not key:
			return self.db.pullDocument()
		return self.db.getValue(key)
		
	def put_key(self, key, data):
		self.db.setValue(key, data)
		return None
		
	def delete_key(self, key):
		self.db.delValues(key)
		return None
		
	def keys(self):
		return ["root"]
		
database = XMLDB
 
if __name__ == "__main__":
	app.run()
		
