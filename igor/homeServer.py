import web
import shlex
import subprocess
import os
import re
import uuid
import json
import dbimpl
import mimetypematch

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
			raise web.HTTPError("401 Cannot use / in command")
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
			raise web.HTTPError("502 Command %s exited with status code=%d" % (command, arg.returncode), {"Content-type": "text/plain"}, arg.output)
		except OSError, arg:
			raise web.HTTPError("502 Error running command: %s: %s" % (command, arg.strerror))
		return rv
	
class AbstractDB(object):
	"""Abstract database that handles the high-level HTTP primitives.
	"""
	def GET(self, name):
		print 'xxxjack GET env', web.ctx.env
		optArgs = web.input()
		if optArgs:
			# GET with a query is treated as POST with the query as JSON data,
			# unless the .METHOD argument states it should be treaded as another method.
			optArgs = dict(optArgs)
			method = self.POST
			if '.METHOD' in optArgs:
				method = getattr(self, optArgs['.METHOD'])
				del optArgs['.METHOD']
			data = json.dumps(optArgs)
			return method(name, data, mimetype="application/json")
		returnType = self.best_return_mimetype()
		if not returnType:
			raise web.NotAcceptable()
		web.header("Content-Type", returnType)
		rv = self.get_resource(name, self.best_return_mimetype())
		return rv

	def POST(self, name, data=None, mimetype=None):
		if data is None: 
			data = web.data()
		if not is_acceptable_mimetype(mimetype):
			raise web.HTTPError("415 Unsupported mimetype")
		print 'data=', repr(data)
		errorreturn = self.put_key(str(name), data)
		if errorreturn: return errorreturn
		return str(name)

	def DELETE(self, name, data=None, mimetype=None):
		return self.delete_key(str(name))

	def PUT(self, name=None, data=None, mimetype=None):
		"""Creates a new document with the request's data and
		generates a unique key for that document.
		"""
		name = self.create_key(name)
		if not name: 
			raise web.notfound()
		key = str(name)
		return self.POST(key, data, mimetype)

	def get_resource(self, name, mimetype=None):
		print 'get_resource', name
		result = self.get_key(name, mimetype)
		return result

	def is_acceptable_mimetype(self, mimetype=None):
		"""Test whether the mimetype in the request is of an acceptable type"""
		if not self.MIMETYPES:
			return True
		if not mimetype:
			mimetype = web.ctx.env.get("CONTENT_TYPE")
		if not mimetype:
			return True
		return mimetype in self.MIMETYPES
		
	def best_return_mimetype(self):
		"""Return the best mimetype in which to encode the return data, or None"""
		if not self.MIMETYPES:
			return None
		acceptable = web.ctx.env.get("HTTP_ACCEPT")
		if not acceptable:
			return None
		return mimetypematch.match(acceptable, self.MIMETYPES)
		
class MemoryDB(AbstractDB):
	"""In memory storage engine.  Lacks persistence."""
	MIMETYPES = None
	
	database = {}
	def create_key(self, key=None):
		if str(key) in self.database:
			return key
		return uuid.uuid4()
		
	def get_key(self, key, mimetype=None):
		print 'get_key', repr(key)
		if not key:
			return self.keys()
		try:
			return self.database[key]
		except KeyError:
			raise web.notfound()

	def put_key(self, key, data, mimetype=None):
		self.database[key] = data
		return None

	def delete_key(self, key):
		try:
			del(self.database[key])
		except KeyError:
			raise web.notfound()

	def keys(self):
		rv = 'Keys: ' + ' '.join(self.database.keys())
		print 'Keys returning', rv
		return rv
		
class FileDB(AbstractDB):
	"""In memory storage engine.  Lacks persistence."""
	MIMETYPES = None
	
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
		
	def get_key(self, key, mimetype=None):
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
			raise web.notfound()

	def put_key(self, key, data, mimetype=None):
		filename = self.basedir + key
		print 'put_key', repr(filename)
		if os.path.isdir(filename):
			filename = filename + '/.data'
		if not os.path.exists(filename):
			raise web.notfound()
		open(filename, 'w').write(data)
		return None

	def delete_key(self, key):
		assert 0
		try:
			del(self.database[key])
		except KeyError:
			raise web.notfound()

	def keys(self):
		return self.database.iterkeys()
		
class XMLDB(AbstractDB):
	MIMETYPES = ["application/xml", "application/json", "text/plain"]
	
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
		
	def get_key(self, key, mimetype=None, variant=None):
		if not key:
			rv = self.db.pullDocument()
			# This always returns XML, so just continue
		else:
			rv = self.db.getValue(key)
			# This generally returns plaintext
			if mimetype == "text/plain":
				return rv + '\n'
			# Otherwise convert to XML.
			# Horrendously wrong:-)
			if rv:
				rv = "<value>" + rv + "</value>\n"
		if mimetype and mimetype != "application/xml" and rv:
			rv = self.convertto(rv, mimetype)
		return rv
		
	def put_key(self, key, data, mimetype=None):
		if mimetype and mimetype != "application/xml":
			data = self.convertfrom(data, mimetype)
		self.db.setValue(key, data)
		return None
		
	def delete_key(self, key):
		self.db.delValues(key)
		return None
		
	def keys(self):
		return ["root"]
		
	def convertto(self, value, mimetype, variant):
		if variant == 'ref':
			if not isinstance(value, basestr):
				raise web.BadRequest()
			value = "/data/" + value
			if mimetype == "application/json":
				return json.dumps({"ref":value})
			elif mimetype == "text/plain":
				return value
			elif mimetype == "application/xml":
				return "<ref>%s</ref>" % value
			else:
				raise web.internalError("Unimplemented mimetype for ref")
		# Only nodesets need different treatment for default and multi
		if not isinstance(value, list):
			if mimetype == "application/json":
				return json.dumps(dict(value=value))
			elif mimetype == "text/plain":
				return unicode(value)
			elif mimetype == "application/xml":
				return u"<value>%s</value>" % unicode(value)
			else:
				raise web.internalError("Unimplemented mimetype for default or multi, simple value")
		if variant == 'multi':
			if mimetype == "application/json":
				rv = []
				for item in value:
					r = dbimpl.getXPath(item)
					t, v = dbimpl.asTagAndDict(item)
					rv.append({"ref":r, t:v})
				return json.dumps(rv)
			elif mimetype == "text/plain":
				raise web.BadRequest()
			elif mimetype == "application/xml":
				rv = "<items>\n"
				for item in value:
					r = dbimpl.getXPath(item)
					v = item.toxml()
					rv += "<item>\n<ref>%s</ref>\n"
					rv += v
					rv += "\n</item>\n"
				rv += "</items>\n"
				return rv
			else:
				raise web.internalError("Unimplemented mimetype for multi, nodeset")
		# Final case: single node return
		if mimetype == "application/json":
			if len(value) != 1:
				raise web.BadRequest()
			t, v = dbimpl.asTagAndDict(value[0])
			return json.dumps({t:v})
		elif mimetype == "text/plain":
			rv = ""
			for item in value:
				v = xpath.expr.string_value(item)
				rv += v
				rv += '\n'
			return rv
		elif mimetype == "application/xml":
			if len(value) != 1:
				raise web.BadRequest()
			return value[0].toxml()
		else:
			raise web.internalError("Unimplemented mimetype for default, single node")			
		
	def convertfrom(self, value, mimetype):
		raise web.internalError("Conversion from %s not yet implemented" % mimetype)
		
database = XMLDB

def _getDictForDomNode(item):
	t = item.tagName
	v = {}
	texts = []
	child = item.firstChild
	while child:
		if child.nodeType == ELEMENT_NODE:
			newv, newt = _getDictForDomNode(child)
			v[newv] = newt
		elif child.nodeType == ATTRIBUTE_NODE:
			v['@' + child.name] = child.value
		elif child.nodeType == TEXT_NODE:
			texts.append(child.data)
		child = child.nextSibling
	if len(texts) == 1:
		v['#text'] = texts[0]
	elif len(texts) > 1:
		v['#text'] = texts
	return t, v
	
if __name__ == "__main__":
	app.run()
		
