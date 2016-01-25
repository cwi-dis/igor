import web
import shlex
import subprocess
import os
import re
import uuid
import json
import dbimpl
import triggers
import mimetypematch
import copy

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
			
		# Setup userdata for pull script, if available
		env = None
		if allArgs.has_key('user'):
			env = copy.deepcopy(os.environ)
			user = allArgs['user']
			env['user'] = user
			tmpDB = XMLDB()
			try:
				userData = tmpDB.get_key('identities/%s/scriptData/%s' % (user, command), 'application/json', 'content')
			except:
				userData = None
			if userData:
				env['userData'] = userData
				
		command = "./scripts/" + command
		try:
			linked = os.readlink(command)
			command = os.path.join(os.path.dirname(command), linked)
		except OSError:
			pass
		try:
			rv = subprocess.check_output([command] + args, stderr=subprocess.STDOUT, env=env)
		except subprocess.CalledProcessError, arg:
			msg = "502 Command %s exited with status code=%d" % (command, arg.returncode)
			raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n' + arg.output)
		except OSError, arg:
			msg = "502 Error running command: %s: %s" % (command, arg.strerror)
			raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')
		return rv
	
class AbstractDB(object):
	"""Abstract database that handles the high-level HTTP primitives.
	"""
	def GET(self, name):
		"""If no query get the content of a section of the database.
		If there is a query can be used as a 1-url shortcut for POST."""
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
			return method(name, optArgs, mimetype="application/x-www-form-urlencoded")
			
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
				mimetype = web.ctx.env.get('CONTENT_TYPE', 'application/unknown')
		rv = self.put_key(name, self.best_return_mimetype(), variant, data, mimetype, replace=replace)
		return rv

	def POST(self, name, data=None, mimetype=None):
		return self.PUT(name, data, mimetype, replace=False)

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

# NOTE: this is a global variable shared by all instances!
GLOBAL_DB = dbimpl.DBImpl("./data/database.xml")
TRIGGERS = None
triggerTemplate = GLOBAL_DB.getElements('triggers')
if triggerTemplate:
	assert len(triggerTemplate) == 1
	TRIGGERS = triggers.TriggerCollection(GLOBAL_DB)
	TRIGGERS.updateTriggers(triggerTemplate[0])
	del triggerTemplate
	print 'xxxjack installed triggers'

class XMLDB(AbstractDB):
	MIMETYPES = ["application/xml", "application/json", "text/plain"]
	
	def __init__(self):
		self.db = GLOBAL_DB
		self.rootTag = self.db.getDocument().tagName
		
	def get_key(self, key, mimetype, variant):
		"""Get subtree for 'key' as 'mimetype'. Variant can be used
		to state which data should be returned (single node, multinode,
		including refs, etc)"""
		if not key:
			rv = [self.db.getDocument()]
			# This always returns XML, so just continue
		else:
			key = '/%s/%s' % (self.rootTag, key)
			rv = self.db.getElements(key)
		rv = self.convertto(rv, mimetype, variant)
		return rv
		
	def put_key(self, key, mimetype, variant, data, datamimetype, replace=True):
		key = '/%s/%s' % (self.rootTag, key)
		if not variant: variant = 'ref'
		with self.db:
			parentPath, tag = self.db.splitXPath(key)
			element = self.convertfrom(data, tag, datamimetype)
			oldElements = self.db.getElements(key)
			if not oldElements:
				# Does not exist yet. See if we can create it
				if not parentPath or not tag:
					raise web.notfound()
				# Find parent
				parentElements = self.db.getElements(parentPath)
				if not parentElements:
					raise web.notfound()
				if len(parentElements) > 1:
					raise web.BadRequest("Bad request, XPath parent selects multiple items")
				parent = parentElements[0]
				parent.appendChild(element)
			elif len(oldElements) > 1:
				raise web.BadRequest("Bad Request, XPath selects multiple items")
			else:
				oldElement = oldElements[0]
				replace = True # XXXJACK
				if replace:
					parent = oldElement.parentNode
					parent.replaceChild(element, oldElement)
				else:
					raise web.internalError("Selective replace not implemented yet")
			path = self.db.getXPathForElement(element)
			self.db.signalNodelist(element)
			return self.convertto(path, mimetype, variant)
		
	def delete_key(self, key):
		key = '/%s/%s' % (self.rootTag, key)
		self.db.delValues(key)
		return ''
		
	def convertto(self, value, mimetype, variant):
		if variant == 'ref':
			if not isinstance(value, basestring):
				raise web.BadRequest("Bad request, cannot use .VARIANT=ref for this operation")
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
				raise web.BadRequest("Bad request, cannot use .VARIANT=multi for mimetype text/plain")
			elif mimetype == "application/xml":
				rv = "<items>\n"
				for item in value:
					r = self.db.getXPathForElement(item)
					v = item.toxml()
					rv += "<item>\n<ref>%s</ref>\n" % r
					rv += v
					rv += "\n</item>\n"
				rv += "</items>\n"
				return rv
			else:
				raise web.internalError("Unimplemented mimetype for multi, nodeset")
		# Final case: single node return
		if len(value) == 0:
			raise web.notfound()
		if mimetype == "application/json":
			if len(value) > 1:
				raise web.BadRequest("Bad request, cannot return multiple items without .VARIANT=multi")
			t, v = self.db.tagAndDictFromElement(value[0])
			if variant == "content":
				rv = json.dumps(v)
			else:
				rv = json.dumps({t:v})
			return rv+'\n'
		elif mimetype == "text/plain":
			rv = ""
			for item in value:
				v = dbimpl.xpath.expr.string_value(item)
				rv += v
				rv += '\n'
			return rv
		elif mimetype == "application/xml":
			if len(value) > 1:
				raise web.BadRequest("Bad request, cannot return multiple items without .VARIANT=multi")
			return value[0].toxml()+'\n'
		else:
			raise web.internalError("Unimplemented mimetype for default, single node")			
		
	def convertfrom(self, value, tag, mimetype):
		if mimetype == 'application/xml':
			element = self.db.elementFromXML(value)
			if element.tagName != tag:
				raise web.BadRequest("Bad request, toplevel XML tag %s does not match final XPath element %s" % (element.tagName, tag))
			return element
		elif mimetype == 'application/x-www-form-urlencoded':
			element = self.db.elementFromTagAndData(tag, value)
			return element
		elif mimetype == 'application/json':
			valueDict = json.loads(value)
			if not isinstance(valueDict, dict):
				raise web.BadRequest("Bad request, JSON toplevel object must be object")
			element = self.db.elementFromTagAndData(tag, valueDict)
			return element
		elif mimetype == 'text/plain':
			element = self.db.elementFromTagAndData(tag, value)
			return element
		else:
			raise web.InternalError("Conversion from %s not implemented" % mimetype)
		
database = XMLDB
	
if __name__ == "__main__":
	app.run()
		
