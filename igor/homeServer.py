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
		"""If no query get the content of a section of the database.
		If there is a query can be used as a 1-url shortcut for POST."""
		print 'xxxjack GET env', web.ctx.env
		optArgs = web.input()

		# See whether we have a variant request
		variant = None
		if '.VARIANT' in optArgs:
			variant = optArgs['.VARIANT']
			del optArgs['.VARIANT']
			
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
		rv = self.get_key(name, self.best_return_mimetype(), variant)
		return rv

	def PUT(self, name, data=None, mimetype=None, replace=True):
		"""Replace part of the document with new data, or inster new data
		in a specific location.
		"""
		print 'xxxjack PUT env', web.ctx.env
		optArgs = web.input()

		# See whether we have a variant request
		variant = None
		if '.VARIANT' in optArgs:
			variant = optArgs['.VARIANT']
			del optArgs['.VARIANT']
		
		if not data:
			# We either have a url-encoded query in optArgs or read raw data
			if optArgs:
				data = dict(optArgs)
				mimetype = "application/x-www-form-urlencoded"
			else:
				data = web.data()
				mimetype = "application/unknown" # XXXJACK get from Content-Type	
		rv = self.put_key(name, self.best_return_mimetype(), variant, data, mimetype, replace=replace)
		return rv

	def POST(self, name, data=None, mimetype=None):
		self.PUT(name, data, mimetype, replace=False)

	def DELETE(self, name, data=None, mimetype=None):
		return self.delete_key(str(name))

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
		
	def get_key(self, key, mimetype, variant):
		"""Get subtree for 'key' as 'mimetype'. Variant can be used
		to state which data should be returned (single node, multinode,
		including refs, etc)"""
		if not key:
			rv = [self.db.getDocument()]
			# This always returns XML, so just continue
		else:
			rv = self.db.getElements(key)
		rv = self.convertto(rv, mimetype, variant)
		return rv
		
	def put_key(self, key, mimetype, variant, data, datamimetype, replace=True):
		if datamimetype and datamimetype != "application/xml":
			data = self.convertfrom(data, key, mimetype)
		element = xyzzy
		oldElements = self.db.getElements(key)
		if not oldElements:
			# Does not exist yet. See if we can create it
			parentPath, tag = self.db.splitXPath(key)
			if not parentPath or not tag:
				raise web.notfound()
			# Find parent
			parentElements = self.db.getElements(parentPath)
			if not parentElements:
				raise web.notfound()
			if len(parentElements) > 1:
				raise xyzzy
			parent = parentElements[0]
			parent.appendChild(element)
			return
		if len(oldElements) > 1:
			raise xyzzy
		oldElement = oldElements[0]
		replace = True # XXXJACK
		if replace:
			parent = oldElement.parentNode
			parent.replaceChild(element, oldElement)
		else:
			raise web.internalError("Selective replace not implemented yet")
		path = self.db.getXPathForElement(element)
		return self.convertto(path, mimetype, variant)
		
	def delete_key(self, key):
		self.db.delValues(key)
		return None
		
	def convertto(self, value, mimetype, variant):
		if variant == 'ref':
			if not isinstance(value, basestr):
				raise web.BadRequest()
			value = "/data/" + value
			if mimetype == "application/json":
				return json.dumps({"ref":value})+'\n'
			elif mimetype == "text/plain":
				return value+'\n'
			elif mimetype == "application/xml":
				return "<ref>%s</ref>\n" % value
			else:
				raise web.internalError("Unimplemented mimetype for ref")
		# Only nodesets need different treatment for default and multi
		if not isinstance(value, list):
			if mimetype == "application/json":
				return json.dumps(dict(value=value))+'\n'
			elif mimetype == "text/plain":
				return unicode(value)+'\n'
			elif mimetype == "application/xml":
				return u"<value>%s</value>\n" % unicode(value)
			else:
				raise web.internalError("Unimplemented mimetype for default or multi, simple value")
		if variant == 'multi':
			if mimetype == "application/json":
				rv = []
				for item in value:
					r = self.db.getXPathForElement(item)
					t, v = self.db.tagAndDictFromElement(item)
					rv.append({"ref":r, t:v})
				return json.dumps(rv)+'\n'
			elif mimetype == "text/plain":
				raise web.BadRequest()
			elif mimetype == "application/xml":
				rv = "<items>\n"
				for item in value:
					r = self.db.getXPathForElement(item)
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
			t, v = self.db.tagAndDictFromElement(value[0])
			return json.dumps({t:v})+'\n'
		elif mimetype == "text/plain":
			rv = ""
			for item in value:
				v = dbimpl.xpath.expr.string_value(item)
				rv += v
				rv += '\n'
			return rv
		elif mimetype == "application/xml":
			if len(value) != 1:
				raise web.BadRequest()
			return value[0].toxml()+'\n'
		else:
			raise web.internalError("Unimplemented mimetype for default, single node")			
		
	def convertfrom(self, value, tag, mimetype):
		if mimetype == 'application/xml':
			element = self.db.newElementFromXML(value)
			if element.tagName != tag:
				raise web.BadRequest()
			return element
		elif mimetype == 'application/json':
			valueDict = json.loads(value)
			if not isinstance(valueDict, dict):
				raise web.BadRequest()
			element = self.db.elementFromTagAndDict(tag, valueDict)
			return element
		elif mimetype == 'text/plain':
			element = self.db.elementFromTagAndText(tag, value)
			return element
		else:
			raise web.internalError("Conversion from %s not implemented" % mimetype)
		
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
		
