from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str
from past.builtins import basestring
from builtins import object
import web
import shlex
import subprocess
import os
import sys
import re
import uuid
import json
import time
from . import mimetypematch
import copy
import imp
import xpath
from . import xmlDatabase
import mimetypes
from . import access
import traceback
import shelve

DEBUG=False

_WEBAPP = None

def monkeypatch_cgi():
    """The Python cgi module has an error under py3 that makes web.py not work. See https://bugs.python.org/issue27777"""
    def read_single(self):
        """Internal: read an atomic part."""
        if self.length >= 0 and self._binary_file:
            self.read_binary()
            self.skip_lines()
        else:
            self.read_lines()
        self.file.seek(0)
    import cgi
    cgi.FieldStorage.read_single = read_single

if sys.version_info[0] == 3:
    monkeypatch_cgi()

urls = (
    '/pluginscript/([^/]+)/([^/]+)', 'runScript',
    '/data/(.*)', 'abstractDatabaseAccess',
    '/evaluate/(.*)', 'abstractDatabaseEvaluate',
    '/internal/([^/]+)', 'runCommand',
    '/internal/([^/]+)/(.+)', 'runCommand',
    '/action/(.+)', 'runAction',
    '/trigger/(.+)', 'runTrigger',
    '/plugin/([^/]+)', 'runPlugin',
    '/plugin/([^/]+)/([^/_]+)', 'runPlugin',
    '/login', 'runLogin',
    '/([^/]*)', 'static',
)
class MyApplication(web.application):
    """This class is a wrapper with some extra functionality (setting the port) as well as a
    somewhat-micro-framework-independent interface to the framework"""
    
    def run(self, port=8080, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))
        
    def setSSLInfo(self, certfile, keyfile):
        """Signal that https is to be used and set key and cert"""
        from web.wsgiserver import CherryPyWSGIServer
        CherryPyWSGIServer.ssl_certificate = certfile
        CherryPyWSGIServer.ssl_private_key = keyfile

    def getSession(self, backingstorefile=None):
        """Create persistent session object"""
        return web.session.Session(self, web.session.ShelfStore(shelve.open(backingstorefile, flag="n")))
        
    def getHTTPError(self):
        """Return excpetion raised by other methods below (for catching)"""
        return web.HTTPError
        
    def resetHTTPError(self):
        """Clear exception"""
        web.ctx.status = "200 OK"
        
    def raiseNotfound(self):
        """404 not found"""
        raise web.notfound()
        
    def raiseSeeother(self, url):
        """303 See Other"""
        raise web.seeother(url)
        
    def raiseHTTPError(self, status, headers={}, data=""):
        """General http errors"""
        if headers == {} and data == "":
            headers = {"Content-type":"text/plain"}
            data = status +'\n\n'
        raise web.HTTPError(status, headers, data)
        
    def addHeaders(self, headers):
        """Add headers to the reply (to be returned shortly)"""
        for k, v in headers.items():
            web.header(k, v)
            
    def getOperationTraceInfo(self):
        """Return information that helps debugging access control errors in current operation"""
        rv = {}
        try:
            rv['requestPath'] = web.ctx.path
        except AttributeError:
            pass
        try:
            rv['action'] = web.ctx.env.get('original_action')
        except AttributeError:
            pass
        try:
            rv['representing'] = web.ctx.env.get('representing')
        except AttributeError:
            pass
        return rv
        
web.config.debug = DEBUG

def WebApp(igor):
    global _WEBAPP
    assert not _WEBAPP
    #
    # Disable debug
    #
    web.config.debug = False
    _WEBAPP = MyApplication(urls, globals(), autoreload=False)
    _WEBAPP.igor = igor
    return _WEBAPP

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class BaseHandler(object):
    """Common base class for our web.py handlers, so everyone has the self.igor reference"""
    def __init__(self):
        self.igor = _WEBAPP.igor
        
class static(BaseHandler):
    def GET(self, name):
        allArgs = web.input()
        token = self.igor.access.tokenForRequest(web.ctx.env)
        if not name:
            name = 'index.html'
        checker = self.igor.access.checkerForEntrypoint('/static/' + name)
        if not checker.allowed('get', token):
            raise myWebError('401 Unauthorized')
        databaseDir = self.igor.pathnames.staticdir
        programDir = os.path.dirname(__file__)
        
        # First try static files in the databasedir/static
        filename = os.path.join(databaseDir, name)
        if os.path.exists(filename):
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            web.header('Content-type', mimetype)
            return open(filename, 'rb').read()
        # Next try static files in the programdir/static
        filename = os.path.join(programDir, 'static', name)
        if os.path.exists(filename):
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            web.header('Content-type', mimetype)
            return open(filename, 'rb').read()
        # Otherwise try a template
        filename = os.path.join(programDir, 'template', name)
        if os.path.exists(filename):
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            web.header('Content-type', mimetype)
            #
            # xxxjack note that the following set of globals basically exports the
            # whole object hierarchy to templates. This means that a template has
            # unlimited powers. This needs to be fixed at some time, so templates
            # can come from untrusted sources.
            #
            globals = dict(
                igor=self.igor,
                token=token,
                json=json,
                str=str,
                repr=repr,
                time=time,
                type=type
                )                
            template = web.template.frender(filename, globals=globals)
            try:
                return template(**dict(allArgs))
            except xmlDatabase.DBAccessError:
                return myWebError("401 Unauthorized (template rendering)")
        raise web.notfound()

class runScript(BaseHandler):
    """Run a shell script"""
        
    def OPTIONS(self, *args):
        web.ctx.headers.append(('Allow', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Methods', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Origin', '*'))
        return ''
        
    def GET(self, pluginName, scriptName):
        allArgs = web.input()
        token = self.igor.access.tokenForRequest(web.ctx.env)
        checker = self.igor.access.checkerForEntrypoint(web.ctx.env['PATH_INFO'])
        if not checker.allowed('get', token):
            raise myWebError('401 Unauthorized')

        scriptDir = os.path.join(self.igor.pathnames.plugindir, pluginName, 'scripts')
            
        if '/' in scriptName or '.' in scriptName:
            raise myWebError("400 Cannot use / or . in scriptName")
            
        if 'args' in allArgs:
            args = shlex.split(allArgs.args)
        else:
            args = []
        # xxxjack need to check that the incoming action is allowed on this plugin
        # Get the token for the plugin itself
        pluginToken = self.igor.access.tokenForPlugin(pluginName)
        # Setup global, per-plugin and per-user data for plugin scripts, if available
        env = copy.deepcopy(os.environ)
        try:
            # Tell plugin about our url, if we know it
            myUrl = self.igor.databaseAccessor.get_key('services/igor/url', 'application/x-python-object', 'content', pluginToken)
            env['IGORSERVER_URL'] = myUrl
            if myUrl[:6] == 'https:':
                env['IGORSERVER_NOVERIFY'] = 'true'
        except web.HTTPError:
            web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
        try:
            pluginData = self.igor.databaseAccessor.get_key('plugindata/%s' % (pluginName), 'application/x-python-object', 'content', pluginToken)
        except web.HTTPError:
            web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
            pluginData = {}
        # Put all other arguments into the environment with an "igor_" prefix
        for k, v in list(allArgs.items()):
            if k == 'args': continue
            if not v:
                v = ''
            env['igor_'+k] = v
        # If a user is logged in we use that as default for a user argument
        if 'user' in self.igor.session and not 'user' in allArgs:
            allArgs.user = self.igor.session.user
        # If there's a user argument see if we need to add per-user data
        if 'user' in allArgs:
            user = allArgs.user
            try:
                userData = self.igor.databaseAccessor.get_key('identities/%s/plugindata/%s' % (user, pluginName), 'application/x-python-object', 'content', token)
            except web.HTTPError:
                web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
                userData = {}
            if userData:
                pluginData.update(userData)
        # Pass plugin data in environment, as JSON
        if pluginData:
            env['igor_pluginData'] = json.dumps(pluginData)
            if type(pluginData) == type({}):
                for k, v in list(pluginData.items()):
                    env['igor_'+k] = str(v)
        # Finally pass the token as an OTP (which has the form user:pass)
        oneTimePassword = self.igor.access.produceOTPForToken(pluginToken)
        env['IGORSERVER_CREDENTIALS'] = oneTimePassword
        # Check whether we need to use an interpreter on the scriptName
        scriptName = os.path.join(scriptDir, scriptName)
        if os.path.exists(scriptName):
            interpreter = None
        elif os.path.exists(scriptName + '.py'):
            scriptName = scriptName + '.py'
            interpreter = "python"
        elif os.name == 'posix' and os.path.exists(scriptName + '.sh'):
            scriptName = scriptName + '.sh'
            interpreter = 'sh'
        else:
            raise myWebError("404 scriptName not found: %s" % scriptName)
        if interpreter:
            args = [interpreter, scriptName] + args
        else: # Could add windows and .bat here too, if needed
            args = [scriptName] + args
        # Call the command and get the output
        try:
            rv = subprocess.check_output(args, stderr=subprocess.STDOUT, env=env)
            self.igor.access.invalidateOTPForToken(oneTimePassword)
        except subprocess.CalledProcessError as arg:
            self.igor.access.invalidateOTPForToken(oneTimePassword)
            msg = "502 Command %s exited with status code=%d" % (scriptName, arg.returncode)
            output = msg + '\n\n' + arg.output
            # Convenience for internal logging: if there is 1 line of output only we append it to the error message.
            argOutputLines = arg.output.split('\n')
            if len(argOutputLines) == 2 and argOutputLines[1] == '':
                msg += ': ' + argOutputLines[0]
                output = ''
            raise web.HTTPError(msg, {"Content-type": "text/plain"}, output)
        except OSError as arg:
            self.igor.access.invalidateOTPForToken(oneTimePassword)
            raise myWebError("502 Error running command: %s: %s" % (scriptName, arg.strerror))
        return rv

class runCommand(BaseHandler):
    """Call an internal method"""
    
    def OPTIONS(self, *args):
        web.ctx.headers.append(('Allow', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Methods', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Origin', '*'))
        return ''
        
    def GET(self, command, subcommand=None):
        allArgs = web.input()
        token = self.igor.access.tokenForRequest(web.ctx.env)
        checker = self.igor.access.checkerForEntrypoint(web.ctx.env['PATH_INFO'])
        if not checker.allowed('get', token):
            raise myWebError('401 Unauthorized')

        try:
            method = getattr(self.igor.internal, command)
        except AttributeError:
            raise web.notfound()
        if subcommand:
            allArgs['subcommand'] = subcommand
        try:
            rv = method(token=token, **dict(allArgs))
        except TypeError as arg:
            raise #myWebError("400 Error in command method %s parameters: %s" % (command, arg))
        return rv

    def POST(self, command, subcommand=None):
        token = self.igor.access.tokenForRequest(web.ctx.env)
        try:
            method = getattr(self.igor.internal, command)
        except AttributeError:
            raise web.notfound()
        argData = web.data()
        if not argData:
            allArgs = {}
        else:
            try:
                allArgs = json.loads(argData)
            except ValueError:
                raise myWebError("POST to /internal/... expects JSON data")
        if subcommand:
            allArgs['subcommand'] = subcommand
        try:
            rv = method(token=token, **allArgs)
        except TypeError as arg:
            raise myWebError("400 Error in command method %s parameters: %s" % (command, arg))
        return rv


class runAction(BaseHandler):
    def OPTIONS(self, *args):
        web.ctx.headers.append(('Allow', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Methods', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Origin', '*'))
        return ''
        
    def GET(self, actionname):
        token = self.igor.access.tokenForRequest(web.ctx.env)
        checker = self.igor.access.checkerForEntrypoint(web.ctx.env['PATH_INFO'])
        if not checker.allowed('get', token):
            raise myWebError('401 Unauthorized')

        try:
            return self.igor.internal.runAction(actionname, token)
        except xmlDatabase.DBAccessError:
            raise myWebError("401 Unauthorized (while running action)")
        
class runTrigger(BaseHandler):
    def OPTIONS(self, *args):
        web.ctx.headers.append(('Allow', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Methods', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Origin', '*'))
        return ''
        
    def GET(self, triggername):
        token = self.igor.access.tokenForRequest(web.ctx.env)
        checker = self.igor.access.checkerForEntrypoint(web.ctx.env['PATH_INFO'])
        if not checker.allowed('get', token):
            raise myWebError('401 Unauthorized')

        try:
            return self.igor.internal.runTrigger(triggername, token)
        except xmlDatabase.DBAccessError:
            raise myWebError("401 Unauthorized (while running trigger)")
        
class runPlugin(BaseHandler):
    """Call a plugin method"""
    
    def OPTIONS(self, *args):
        web.ctx.headers.append(('Allow', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Methods', 'GET'))
        web.ctx.headers.append(('Access-Control-Allow-Origin', '*'))
        return ''
        
    def GET(self, pluginName, methodName='index'):
        token = self.igor.access.tokenForRequest(web.ctx.env)
        checker = self.igor.access.checkerForEntrypoint(web.ctx.env['PATH_INFO'])
        if not checker.allowed('get', token):
            raise myWebError('401 Unauthorized')

        #
        # Import plugin as a submodule of igor.plugins
        #
        import igor.plugins # Make sure the base package exists
        moduleName = 'igor.plugins.'+pluginName
        if moduleName in sys.modules:
            # Imported previously.
            pluginModule = sys.modules[moduleName]
        else:
            # New. Try to import.
            moduleDir = os.path.join(self.igor.pathnames.plugindir, pluginName)
            try:
                mfile, mpath, mdescr = imp.find_module('igorplugin', [moduleDir])
                pluginModule = imp.load_module(moduleName, mfile, mpath, mdescr)
            except ImportError:
                print('------ import failed for', pluginName)
                traceback.print_exc()
                print('------')
                raise web.notfound()
            pluginModule.SESSION = self.igor.session  # xxxjack
            pluginModule.IGOR = self.igor
        allArgs = web.input()

        # xxxjack need to check that the incoming action is allowed on this plugin
        # Get the token for the plugin itself
        pluginToken = self.igor.access.tokenForPlugin(pluginName, token=token)
        allArgs['token'] = pluginToken
        
        # Find plugindata and per-user plugindata
        try:
            pluginData = self.igor.databaseAccessor.get_key('plugindata/%s' % (pluginName), 'application/x-python-object', 'content', pluginToken)
        except web.HTTPError:
            web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
            pluginData = {}
        try:
            factory = getattr(pluginModule, 'igorPlugin')
        except AttributeError:
            raise myWebError("501 Plugin %s problem: misses igorPlugin() method" % (pluginName))
        #
        # xxxjack note that the following set of globals basically exports the
        # whole object hierarchy to plugins. This means that a plugin has
        # unlimited powers. This needs to be fixed at some time, so plugin
        # can come from untrusted sources.
        #
        pluginObject = factory(self.igor, pluginName, pluginData)
        #
        # If there is a user argument also get userData
        #
        if 'user' in allArgs:
            user = allArgs['user']
            try:
                userData = self.igor.databaseAccessor.get_key('identities/%s/plugindata/%s' % (user, pluginName), 'application/x-python-object', 'content', pluginToken)
            except web.HTTPError:
                web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
            else:
                allArgs['userData'] = userData
        #
        # Find the method and call it.
        #
        try:
            method = getattr(pluginObject, methodName)
        except AttributeError:
            print('----- Method', methodName, 'not found in', pluginObject)
            raise web.notfound()
        try:
            rv = method(**dict(allArgs))
        except ValueError as arg:
            raise myWebError("400 Error in plugin method %s/%s parameters: %s" % (pluginName, methodName, arg))
        if rv == None:
            rv = ''
        if not isinstance(rv, basestring):
            rv = str(rv)
        return rv
    
class abstractDatabaseEvaluate(BaseHandler):
    """Evaluate an XPath expression and return the result as plaintext"""
    def GET(self, command):
        token = self.igor.access.tokenForRequest(web.ctx.env)
        return self.igor.databaseAccessor.get_value(command, token)
    
class runLogin(BaseHandler):
    """Login or logout"""
    
    def GET(self):
        return self.getOrPost()
        
    def POST(self):
        return self.getOrPost()
        
    def getOrPost(self):
        allArgs = web.input()
        if 'logout' in allArgs:
            self.igor.session.user = None
            raise web.seeother('/')
        message = None
        username = allArgs.get('username')
        password = allArgs.get('password')
        if username:
            if self.igor.access.userAndPasswordCorrect(username, password):
                self.igor.session.user = username
                raise web.seeother('/')
            message = "Password and/or username incorrect."
        form = web.form.Form(
            web.form.Textbox('username'),
            web.form.Password('password'),
            web.form.Button('login'),
            )
        programDir = os.path.dirname(__file__)
        template = web.template.frender(os.path.join(programDir, 'template', '_login.html'))
        return template(form, self.igor.session.get('user'), message)
              
class abstractDatabaseAccess(BaseHandler):
    """Abstract database that handles the high-level HTTP primitives.
    """
    def OPTIONS(self, *args):
        web.ctx.headers.append(('Allow', 'GET,PUT,POST,DELETE'))
        web.ctx.headers.append(('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE'))
        web.ctx.headers.append(('Access-Control-Allow-Origin', '*'))
        return ''
        
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
            rv = method(name, optArgs, mimetype="application/x-www-form-urlencoded")
            web.header("Content-Length", str(len(rv)))
            return rv
            
        token = self.igor.access.tokenForRequest(web.ctx.env)

        returnType = self.best_return_mimetype()
        if not returnType:
            raise web.NotAcceptable()
        web.header("Content-Type", returnType)
        rv = self.igor.databaseAccessor.get_key(name, self.best_return_mimetype(), variant, token)
        web.header("Content-Length", str(len(rv)))
        return rv

    def PUT(self, name, data=None, mimetype=None, replace=True):
        """Replace part of the document with new data, or inster new data
        in a specific location.
        """
        optArgs = web.input()
        token = self.igor.access.tokenForRequest(web.ctx.env)

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
        rv = self.igor.databaseAccessor.put_key(name, self.best_return_mimetype(), variant, data, mimetype, token, replace=replace)
        web.header("Content-Length", str(len(rv)))
        return rv

    def POST(self, name, data=None, mimetype=None):
        return self.PUT(name, data, mimetype, replace=False)

    def DELETE(self, name, data=None, mimetype=None):
        token = self.igor.access.tokenForRequest(web.ctx.env)
        rv = self.igor.databaseAccessor.delete_key(name, token)
        web.header("Content-Length", str(len(rv)))
        return rv

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
        if not self.igor.databaseAccessor.MIMETYPES:
            return None
        acceptable = web.ctx.env.get("HTTP_ACCEPT")
        if not acceptable:
            return self.igor.databaseAccessor.MIMETYPES[0]
        return mimetypematch.match(acceptable, self.igor.databaseAccessor.MIMETYPES)

class XmlDatabaseAccess(object):
    """Class to access the database in a somewhat rest-like manner. Instantiated once."""
    
    MIMETYPES = ["application/xml", "application/json", "text/plain"]
    
    def __init__(self, igor):
        self.igor = igor
        self.rootTag = self.igor.database.getDocument(self.igor.access.tokenForIgor()).tagName
        
    def get_key(self, key, mimetype, variant, token):
        """Get subtree for 'key' as 'mimetype'. Variant can be used
        to state which data should be returned (single node, multinode,
        including refs, etc)"""
        try:
            if not key:
                rv = [self.igor.database.getDocument(token)]
                # This always returns XML, so just continue
            else:
                if key[0] != '/':
                    key = '/%s/%s' % (self.rootTag, key)
                rv = self.igor.database.getElements(key, 'get', token)
            rv = self.convertto(rv, mimetype, variant)
            return rv
        except xmlDatabase.DBAccessError:
            raise myWebError("401 Unauthorized")
        except xpath.XPathError as arg:
            raise myWebError("400 XPath error: %s" % str(arg))
        except xmlDatabase.DBKeyError as arg:
            raise myWebError("400 Database Key Error: %s" % str(arg))
        except xmlDatabase.DBParamError as arg:
            raise myWebError("400 Database Parameter Error: %s" % str(arg))
        
    def get_value(self, expression, token):
        """Evaluate a general expression and return the string value"""
        try:
            return self.igor.database.getValue(expression, token=token)
        except xmlDatabase.DBAccessError:
            raise myWebError("401 Unauthorized")
        except xpath.XPathError as arg:
            raise myWebError("400 XPath error: %s" % str(arg))
        except xmlDatabase.DBKeyError as arg:
            raise myWebError("400 Database Key Error: %s" % str(arg))
        except xmlDatabase.DBParamError as arg:
            raise myWebError("400 Database Parameter Error: %s" % str(arg))
        
    def put_key(self, key, mimetype, variant, data, datamimetype, token, replace=True):
        try:
            if not key:
                raise myWebError("400 cannot PUT or POST whole document")
            if key[0] != '/':
                key = '/%s/%s' % (self.rootTag, key)
            if not variant: variant = 'ref'
            nodesToSignal = []
            with self.igor.database:
                parentPath, tag = self.igor.database.splitXPath(key)
                if not tag:
                    raise web.BadRequest("PUT path must and with an element tag")
                element = self.convertfrom(data, tag, datamimetype)
                oldElements = self.igor.database.getElements(key, 'put' if replace else 'post', token)
                if not oldElements:
                    #
                    # Does not exist yet. See if we can create it
                    #
                    if not parentPath or not tag:
                        raise web.notfound("404 Not Found, parent or tag missing")
                    #
                    # Find parent
                    #
                    # NOTE: we pass the tagname for the child element. This is so put rights on a
                    # child that does not exist yet can be checked.
                    parentElements = self.igor.database.getElements(parentPath, 'post', token, postChild=tag)
                    if not parentElements:
                        raise web.notfound("404 Parent not found: %s" % parentPath)
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
                    nodesToSignal += xmlDatabase.recursiveNodeSet(element)
                    nodesToSignal += xmlDatabase.nodeSet(parent)
                else:
                    #
                    # Already exists. Check that it exists only once.
                    #
                    if len(oldElements) > 1:
                        parent1 = oldElements[0].parentNode
                        for otherNode in oldElements[1:]:
                            if otherNode.parentNode != parent1:
                                raise web.BadRequest("Bad Request, XPath selects multiple items from multiple parents")
                            
                    oldElement = oldElements[0]
                    if replace:
                        if len(oldElements) > 1:
                            raise web.BadRequest("Bad PUT Request, XPath selects multiple items")
                        #
                        # We should really do a selective replace here: change only the subtrees that need replacing.
                        # That will make the signalling much more fine-grained. Will do so, at some point in the future.
                        #
                        # For now we replace the first matching node and delete its siblings, but only if the new content
                        # is not identical to the old
                        #
                        if self.igor.database.identicalSubTrees(oldElement, element):
                            web.ctx.status = "200 Unchanged"
                        else:
                            parent = oldElement.parentNode
                            parent.replaceChild(element, oldElement)
                            nodesToSignal += xmlDatabase.recursiveNodeSet(element)
                    else:
                        #
                        # POST, simply append the new node to the parent (and signal that parent)
                        #
                        parent = oldElement.parentNode
                        parent.appendChild(element)
                        nodesToSignal += xmlDatabase.recursiveNodeSet(element)
                        nodesToSignal += xmlDatabase.nodeSet(parent)
                    #
                    # We want to signal the new node
                    #
                
                if nodesToSignal: self.igor.database.signalNodelist(nodesToSignal)
                path = self.igor.database.getXPathForElement(element)
                return self.convertto(path, mimetype, variant)
        except xmlDatabase.DBAccessError:
            raise myWebError("401 Unauthorized")
        except xpath.XPathError as arg:
            raise myWebError("400 XPath error: %s" % str(arg))
        except xmlDatabase.DBKeyError as arg:
            raise myWebError("400 Database Key Error: %s" % str(arg))
        except xmlDatabase.DBParamError as arg:
            raise myWebError("400 Database Parameter Error: %s" % str(arg))
        
    def delete_key(self, key, token):
        try:
            key = '/%s/%s' % (self.rootTag, key)
            self.igor.database.delValues(key, token)
            return ''
        except xmlDatabase.DBAccessError:
            raise myWebError("401 Unauthorized")
        except xpath.XPathError as arg:
            raise myWebError("400 XPath error: %s" % str(arg))
        except xmlDatabase.DBKeyError as arg:
            raise myWebError("400 Database Key Error: %s" % str(arg))
        
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
                return str(value)+'\n'
            elif mimetype == "application/xml":
                return u"<value>%s</value>\n" % str(value)
            elif mimetype == "application/x-python-object":
                return value
            else:
                raise web.InternalError("Unimplemented mimetype %s for default or multi, simple value" % mimetype)
        if variant in ('multi', 'multiraw'):
            if mimetype == "application/json":
                rv = []
                for item in value:
                    r = self.igor.database.getXPathForElement(item)
                    t, v = self.igor.database.tagAndDictFromElement(item, stripHidden=(variant != 'multiraw'))
                    rv.append({"ref":r, t:v})
                return json.dumps(rv)+'\n'
            elif mimetype == "text/plain":
                raise web.BadRequest("Bad request, cannot use .VARIANT=multi for mimetype text/plain")
            elif mimetype == "application/xml":
                rv = "<items>\n"
                for item in value:
                    r = self.igor.database.getXPathForElement(item)
                    v = self.igor.database.xmlFromElement(item, stripHidden=(variant != 'multiraw'))
                    rv += "<item>\n<ref>%s</ref>\n" % r
                    rv += v
                    rv += "\n</item>\n"
                rv += "</items>\n"
                return rv
            elif mimetype == "application/x-python-object":
                rv = {}
                for item in value:
                    r = self.igor.database.getXPathForElement(item)
                    t, v = self.igor.database.tagAndDictFromElement(item, stripHidden=(variant != 'multiraw'))
                    rv[r] = v
                return rv
            else:
                raise web.InternalError("Unimplemented mimetype %s for multi, nodeset" % mimetype)
        # Final case: single node return (either no variant or variant='raw')
        if len(value) == 0:
            raise web.notfound()
        if mimetype == "application/json":
            if len(value) > 1:
                raise web.BadRequest("Bad request, cannot return multiple items without .VARIANT=multi")
            t, v = self.igor.database.tagAndDictFromElement(value[0], stripHidden=(variant != 'raw'))
            if variant == "content":
                rv = json.dumps(v)
            else:
                rv = json.dumps({t:v})
            return rv+'\n'
        elif mimetype == "text/plain":
            rv = ""
            for item in value:
                # xxxjack if variant != raw, will this leak information?
                v = xpath.expr.string_value(item)
                rv += v
                rv += '\n'
            return rv
        elif mimetype == "application/xml":
            if len(value) > 1:
                raise web.BadRequest("Bad request, cannot return multiple items without .VARIANT=multi")
            return self.igor.database.xmlFromElement(value[0], stripHidden=(variant != 'raw'))+'\n'
        elif mimetype == 'application/x-python-object':
            if len(value) > 1:
                raise web.BadRequest("Bad request, cannot return multiple items without .VARIANT=multi")
            t, v = self.igor.database.tagAndDictFromElement(value[0], stripHidden=(variant != 'raw'))
            return v

        else:
            raise web.InternalError("Unimplemented mimetype %s for default, single node" % mimetype)            
        
    def convertfrom(self, value, tag, mimetype):
        if mimetype == 'application/xml':
            if type(value) != type(''):
                value = value.decode('utf-8')
            element = self.igor.database.elementFromXML(value)
            if element.tagName != tag:
                raise web.BadRequest("Bad request, toplevel XML tag %s does not match final XPath element %s" % (element.tagName, tag))
            return element
        elif mimetype == 'application/x-www-form-urlencoded':
            # xxxjack here comes a special case, and I don't like it.
            # if the url-encoded data contains exactly one element and its name is the same as the
            # tag name we don't encode.
            if type(value) == type({}) and len(value) == 1 and tag in value:
                value = value[tag]
            element = self.igor.database.elementFromTagAndData(tag, value)
            return element
        elif mimetype == 'application/json':
            try:
                valueDict = json.loads(value)
            except ValueError:
                raise web.BadRequest("No JSON object could be decoded from body")
            if not isinstance(valueDict, dict):
                raise web.BadRequest("Bad request, JSON toplevel object must be object")
            # xxxjack here comes a special case, and I don't like it.
            # if the JSON dictionary contains exactly one element and its name is the same as the
            # tag name we don't encode.
            if len(valueDict) == 1 and tag in valueDict:
                element = self.igor.database.elementFromTagAndData(tag, valueDict[tag])
            else:
                element = self.igor.database.elementFromTagAndData(tag, valueDict)
            return element
        elif mimetype == 'text/plain':
            # xxxjack should check that value is a string or unicode
            if type(value) != type(''):
                value = value.decode('utf-8')
            element = self.igor.database.elementFromTagAndData(tag, value)
            return element
        elif mimetype == 'application/x-python-object':
            element = self.igor.database.elementFromTagAndData(tag, value)
            return element
        else:
            raise web.InternalError("Conversion from %s not implemented" % mimetype)
        
