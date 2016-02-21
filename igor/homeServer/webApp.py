import web
import shlex
import subprocess
import os
import sys
import re
import uuid
import json
import mimetypematch
import copy
import imp
import xpath

DATABASE=None   # The database itself. Will be set by main module
SCRIPTDIR=None  # The directory for scripts
PLUGINDIR=None  # The directory for plugins
COMMANDS=None   # The command processor. Will be set by the main module.

urls = (
    '/scripts/([^/]*)', 'runScript',
    '/pluginscripts/([^/]*)/([^/]*)', 'runScript',
    '/data/(.*)', 'xmlDatabaseAccess',
    '/evaluate/(.*)', 'xmlDatabaseEvaluate',
    '/internal/(.*)', 'runCommand',
    '/action/(.*)', 'runAction',
    '/plugin/(.*)', 'runPlugin',
)
class MyApplication(web.application):
    def run(self, port=8080, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))

app = MyApplication(urls, globals())

class runScript:
    """Run a shell script"""
        
    def GET(self, name, arg2=None):
        if arg2:
            # Plugin script command.
            scriptDir = os.path.join(PLUGINDIR, name, 'scripts')
            command = arg2
        else:
            scriptDir = SCRIPTDIR
            command = name
            
        allArgs = web.input()
        if '/' in command:
            raise web.HTTPError("401 Cannot use / in command")
            
        if allArgs.has_key('args'):
            args = shlex.split(allArgs.args)
        else:
            args = []
            
        # Setup per-plugin and per-user data for plugin scripts, if available
        env = copy.deepcopy(os.environ)
        tmpDB = xmlDatabaseAccess()
        try:
            pluginData = tmpDB.get_key('plugindata/%s' % (name), 'application/x-python-object', 'content')
        except web.HTTPError:
            web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
            pluginData = {}
        if allArgs.has_key('user'):
            user = allArgs['user']
            env['user'] = user
            try:
                userData = tmpDB.get_key('identities/%s/plugindata/%s' % (user, name), 'application/x-python-object', 'content')
            except web.HTTPError:
                web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
                userData = {}
            if userData:
                pluginData.update(userData)
        # Pass plugin data in environment, as JSON
        if pluginData:
            env['pluginData'] = json.dumps(pluginData)
                
        # Call the command and get the output
        command = os.path.join(scriptDir, command)
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

class runCommand:
    """Call an internal method"""
    
    def GET(self, command):
        if not COMMANDS:
            raise web.notfound()
        try:
            method = getattr(COMMANDS, command)
        except AttributeError:
            raise web.notfound()
        allArgs = dict(web.input())
        try:
            rv = method(**allArgs)
        except TypeError, arg:
            raise web.HTTPError("401 Error calling command method %s: %s" % (command, arg))
        return rv


class runAction:
    def GET(self, actionname):
        if not COMMANDS:
            raise web.notfound()
        return COMMANDS.runAction(actionname)
        
class runPlugin:
    """Call a plugin method"""
    
    def GET(self, command):
        if command in sys.modules:
            # Imported previously.
            mod = sys.modules[command]
        else:
            # New. Try to import.
            moduleDir = os.path.join(PLUGINDIR, command)
            try:
                mfile, mpath, mdescr = imp.find_module(command, [moduleDir])
                mod = imp.load_module(command, mfile, mpath, mdescr)
            except ImportError:
                raise web.notfound()
            # Tell the new module about the database and the app
            mod.DATABASE = DATABASE
            mod.COMMANDS=COMMANDS
            mod.app = app
        try:
            method = getattr(mod, command)
        except AttributeError:
            raise web.notfound()
            
        allArgs = dict(web.input())
        try:
            rv = method(**allArgs)
        except TypeError, arg:
            raise web.HTTPError("401 Error calling plugin method %s: %s" % (command, arg))
        return rv
    
class xmlDatabaseEvaluate:
    """Evaluate an XPath expression and return the result as plaintext"""
    def GET(self, command):
        tmpDB = xmlDatabaseAccess()
        return tmpDB.get_value(command)
        
class AbstractDatabaseAccess(object):
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
        return self.delete_key(name)

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
            return self.MIMETYPES[0]
        return mimetypematch.match(acceptable, self.MIMETYPES)

class xmlDatabaseAccess(AbstractDatabaseAccess):
    MIMETYPES = ["application/xml", "application/json", "text/plain"]
    
    def __init__(self):
        self.db = DATABASE
        assert DATABASE
        self.rootTag = self.db.getDocument().tagName
        
    def get_key(self, key, mimetype, variant):
        """Get subtree for 'key' as 'mimetype'. Variant can be used
        to state which data should be returned (single node, multinode,
        including refs, etc)"""
        try:
            if not key:
                rv = [self.db.getDocument()]
                # This always returns XML, so just continue
            else:
                key = '/%s/%s' % (self.rootTag, key)
                rv = self.db.getElements(key)
            rv = self.convertto(rv, mimetype, variant)
            return rv
        except xpath.XPathError, arg:
            msg = "401 XPath error: %s" % str(arg)
            raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')
        
    def get_value(self, expression):
        """Evaluate a general expression and return the string value"""
        try:
            return self.db.getValue(expression)
        except xpath.XPathError, arg:
            msg = "401 XPath error: %s" % str(arg)
            raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')
        
    def put_key(self, key, mimetype, variant, data, datamimetype, replace=True):
        try:
            key = '/%s/%s' % (self.rootTag, key)
            if not variant: variant = 'ref'
            nodesToSignal = []
            with self.db:
                parentPath, tag = self.db.splitXPath(key)
                element = self.convertfrom(data, tag, datamimetype)
                oldElements = self.db.getElements(key)
                if not oldElements:
                    #
                    # Does not exist yet. See if we can create it
                    #
                    if not parentPath or not tag:
                        raise web.notfound()
                    #
                    # Find parent
                    #
                    parentElements = self.db.getElements(parentPath)
                    if not parentElements:
                        raise web.notfound()
                    if len(parentElements) > 1:
                        raise web.BadRequest("Bad request, XPath parent selects multiple items")
                    parent = parentElements[0]
                    #
                    # Add new node to the end of the parent
                    #
                    parent.appendChild(element)
                    #
                    # Signal both parent and new node
                    #
                    nodesToSignal.append(element)
                    nodesToSignal.append(parent)
                else:
                    #
                    # Already exists, possibly multiple times. First make sure that if there are
                    # multiple matches they all have the same parent (we will replace all of them by
                    # the single new node, or append it).
                    #
                    if len(oldElements) > 1:
                        parent1 = oldElements[0].parentNode
                        for otherNode in oldElements[1:]:
                            if otherNode.parentNode != parent1:
                                raise web.BadRequest("Bad Request, XPath selects multiple items from multiple parents")
                            
                    oldElement = oldElements[0]
                    if replace:
                        #
                        # We should really do a selective replace here: change only the subtrees that need replacing.
                        # That will make the signalling much more fine-grained. Will do so, at some point in the future.
                        #
                        # For now we replace the first matching node and delete its siblings.
                        #
                        parent = oldElement.parentNode
                        parent.replaceChild(element, oldElement)
                        for otherNode in oldElements[1:]:
                            # Delete other nodes with the same tag
                            parent.removeChild(otherNode)
                    else:
                        #
                        # Simply add the new node to the parent (and signal that parent)
                        parent = oldElement.parentNode
                        parent.appendChild(element)
                        nodesToSignal.append(parent)
                    #
                    # We want to signal the new node
                    nodesToSignal.append(element)
                
                self.db.signalNodelist(nodesToSignal)
                path = self.db.getXPathForElement(element)
                return self.convertto(path, mimetype, variant)
        except xpath.XPathError, arg:
            msg = "401 XPath error: %s" % str(arg)
            raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')
        
    def delete_key(self, key):
        try:
            key = '/%s/%s' % (self.rootTag, key)
            self.db.delValues(key)
            return ''
        except xpath.XPathError, arg:
            msg = "401 XPath error: %s" % str(arg)
            raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')
        
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
            elif mimetype == "application/x-python-object":
                return value
            else:
                raise web.InternalError("Unimplemented mimetype %s for ref" % mimetype)
        # Only nodesets need different treatment for default and multi
        if not isinstance(value, list):
            if mimetype == "application/json":
                return json.dumps(dict(value=value))+'\n'
            elif mimetype == "text/plain":
                return unicode(value)+'\n'
            elif mimetype == "application/xml":
                return u"<value>%s</value>\n" % unicode(value)
            elif mimetype == "application/x-python-object":
                return value
            else:
                raise web.InternalError("Unimplemented mimetype %s for default or multi, simple value" % mimetype)
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
            elif mimetype == "application/x-python-object":
                rv = []
                for item in value:
                    r = self.db.getXPathForElement(item)
                    t, v = self.db.tagAndDictFromElement(item)
                    rv.append(v)
                return rv
            else:
                raise web.InternalError("Unimplemented mimetype %s for multi, nodeset" % mimetype)
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
                v = xpath.expr.string_value(item)
                rv += v
                rv += '\n'
            return rv
        elif mimetype == "application/xml":
            if len(value) > 1:
                raise web.BadRequest("Bad request, cannot return multiple items without .VARIANT=multi")
            return value[0].toxml()+'\n'
        elif mimetype == 'application/x-python-object':
            if len(value) > 1:
                raise web.BadRequest("Bad request, cannot return multiple items without .VARIANT=multi")
            t, v = self.db.tagAndDictFromElement(value[0])
            return v

        else:
            raise web.InternalError("Unimplemented mimetype %s for default, single node" % mimetype)            
        
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
            # xxxjack here comes a special case, and I don't like it.
            # if the JSON dictionary contains exactly one element and its name is the same as the
            # tag name we don't encode.
            if len(valueDict) == 1 and tag in valueDict:
                element = self.db.elementFromTagAndData(tag, valueDict[tag])
            else:
                element = self.db.elementFromTagAndData(tag, valueDict)
            return element
        elif mimetype == 'text/plain':
            element = self.db.elementFromTagAndData(tag, value)
            return element
        else:
            raise web.InternalError("Conversion from %s not implemented" % mimetype)
        
