from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str
from past.builtins import basestring
from builtins import object
import gevent.pywsgi
from flask import Flask, Response, request, abort, redirect, jsonify, make_response, after_this_request, session
import werkzeug.exceptions
import jinja2
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
import xpath
from . import xmlDatabase
import mimetypes
from . import access
import traceback
import shelve
import io
import urllib.parse
import markdown

if sys.version_info[0] < 3:
    def str23compat(item):
        return unicode(str(item))
else:
    def str23compat(item):
        return str(item)

DEBUG=False

_SERVER = None
_WEBAPP = Flask(__name__)
_WEBAPP.secret_key = b'geheimpje'   # Overridden by setSSLInfo in cases where it really matters

class MyWSGICaller:
    """Encapsulates WSGI app call and reply"""
    
    def __init__(self, app, url, method='GET', data=None, headers=None, env=None):
        self.status = None
        self.data = None
        self.headers = {}

        if data and not isinstance(data, str) and not isinstance(data, bytes):
            data = json.dumps(data)
        environ = self._buildRequestEnviron(url, method, data, headers, env)
        rv = app(environ, self._start_response)
        if self.status[:2] != '20':
            print('Warning: %s %s returned %s' % (method, url, self.status) )
        self._feed(rv)
        
    def _start_response(self, status, headers):
        self.status = status
        for k, v in headers:
            self.headers[k] = v
            
    def _feed(self, iter):
        for i in iter:
            if self.data == None:
                self.data = i
            else:
                self.data += i
            
    def _buildRequestEnviron(self, url, method, data, headers, env):
        url = str23compat(url)
        assert url[0] == '/'
        url, query = urllib.parse.splitquery(url)
        query = query or ""
        rv = {
            'REQUEST_METHOD' : method,
            'SCRIPT_NAME' : '',
            'PATH_INFO' : url,
            'QUERY_STRING' : query,
            # CONTENT_TYPE comes later
            'SERVER_NAME' : '0.0.0.0',
            'SERVER_PORT' : '8080',
            'HTTP_HOST' : '0.0.0.0:8080',
            'SERVER_PROTOCOL' : 'HTTP/1.1',
            'wsgi.version' : (1, 0),
            'wsgi.url_scheme' : 'http',
            # wsgi.input comes later
            'wsgi.errors' : sys.stderr,
            'wsgi.multithread' : True,
            'wsgi.multiprocess' : True,
            'wsgi.run_once' : False,
            }
        if headers:
            for k, v in headers.items():
                cgiKey = k.upper()
                cgiKey = cgiKey.replace('-', '_')
                if cgiKey == 'CONTENT_TYPE':
                    rv[cgiKey] = v
                else:
                    rv['HTTP_' + cgiKey] = v
        if env:
            rv.update(env)
        data = data or ''
        if isinstance(data, dict):
            data = urllib.parse.urlencode(data)
        if isinstance(data, str):
            data = data.encode('utf8')
        rv['CONTENT_LENGTH'] = len(data)
        rv['wsgi.input'] = io.BytesIO(data)
        return rv
                    
class MyServer:
    """This class is a wrapper with some extra functionality (setting the port) as well as a
    somewhat-micro-framework-independent interface to the framework"""
    def __init__(self, igor):
        self.igor = igor
        self.server = None
        self.port = None
        self.keyfile = None
        self.certfile = None
        self.jinjaEnv = None
    
    def run(self, port=8080):
        self.port = port
        if self.keyfile or self.certfile:
            kwargs = dict(keyfile=self.keyfile, certfile=self.certfile)
        else:
            kwargs = {}
        self.server = gevent.pywsgi.WSGIServer(("0.0.0.0", self.port), _WEBAPP, **kwargs)
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
            
    def stop(self):
        if self.server:
            self.server.stop()
        
    def setSSLInfo(self, certfile, keyfile):
        """Signal that https is to be used and set key and cert"""
        self.certfile = certfile
        self.keyfile = keyfile
        fp = open(keyfile, 'rb')
        appKey = fp.read(8)
        _SERVER.secret_key = appKey

    def getSessionItem(self, name, default=None):
        """Create persistent session object"""
        return session.get(name, default)
        
    def setSessionItem(self, name, value):
        session[name] = value
        
    def getHTTPError(self):
        """Return excpetion raised by other methods below (for catching)"""
        return werkzeug.exceptions.HTTPException
        
    def resetHTTPError(self):
        """Clear exception"""
        return # Nothing to do for Flask? webpy was: web.ctx.status = "200 OK"
        
    def raiseNotfound(self):
        """404 not found"""
        return abort(404)
        
    def raiseSeeother(self, url):
        """303 See Other"""
        return redirect(url, 303)
        
    def raiseHTTPError(self, message):
        """General http errors"""
        try:
            # If code starts with a numeric string we presume it is an error message
            code = int(message.split()[0])
            # And if it is we re-use it
            code = message
        except ValueError:
            code = 500
        resp = make_response(message+'\n', code)
        return abort(resp)
        
    def stringFromHTTPError(self, e):
        """Return the string representation for an HTTPError"""
        if e.code and e.description:
            return "{} {}".format(e.code, e.description)
        resp = e.get_response()
        if resp.status:
            return str(resp.status)
        return str(resp.status_code)
        
    def responseWithHeaders(self, response, headers):
        """Add headers to the reply"""
        return make_response(response, headers)
            
    def getOperationTraceInfo(self):
        """Return information that helps debugging access control errors in current operation"""
        rv = {}
        try:
            rv['requestPath'] = request.path
        except AttributeError:
            pass
        try:
            rv['action'] = request.environ.get('original_action')
        except AttributeError:
            pass
        try:
            rv['representing'] = request.environ.get('representing')
        except AttributeError:
            pass
        return rv
        
    def request(self, url, method='GET', data=None, headers=None, env=None):
        resp = MyWSGICaller(_WEBAPP.wsgi_app, url=url, method=method, data=data, headers=headers, env=env)
        return resp
        
    def getJinjaTemplate(self, name):
        """Return a Jinja2 template"""
        if self.jinjaEnv == None:
            loader=jinja2.ChoiceLoader([
                jinja2.PackageLoader('igor', 'template'),
                jinja2.FileSystemLoader(_SERVER.igor.pathnames.plugindir)
                ])
            self.jinjaEnv = jinja2.Environment(loader=loader, extensions=['jinja2.ext.do'])
            self.jinjaEnv.globals['igor'] = _SERVER.igor
            self.jinjaEnv.globals['json'] = json
            self.jinjaEnv.globals['time'] = time
            self.jinjaEnv.globals['float'] = float
            self.jinjaEnv.globals['int'] = int
            self.jinjaEnv.globals['type'] = type
        try:
            template = self.jinjaEnv.get_template(name)
        except jinja2.exceptions.TemplateNotFound:
            template = None
        return template

    def tempContext(self, path):
        """Return a temporary context to run a method in, so accessing context works"""
        return _WEBAPP.test_request_context(path)
        
class _DummyReply:
    def __init__(self):
        self.status = '500 Not Implemented Yet'
        self.data = ''    

def WebApp(igor):
    global _SERVER
    assert not _SERVER
    _SERVER = MyServer(igor)
    return _SERVER

def myWebError(msg, code=400):
    resp = make_response(msg, code)
    abort(resp)

def returnReply(rv):
    """Helper function: return reply in a suitable way. Can be Response (return as-is),
    dict or list (return as JSON), None (return empty string), otherwise return as string"""
    if rv == None:
        rv =  Response('', mimetype='text/plain')
    elif isinstance(rv, str):
        rv = Response(rv, mimetype='text/plain')
    elif isinstance(rv, dict) or isinstance(rv, list):
        rv = Response(json.dumps(rv), mimetype='application/json')
    else:
        pass
    return rv
    
@_WEBAPP.route('/', defaults={'name':'index.html'})
@_WEBAPP.route('/<path:name>')    
def get_static(name):
    allArgs = request.values.to_dict()
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    if not name:
        name = 'index.html'
    checker = _SERVER.igor.access.checkerForEntrypoint('/static/' + name)
    if not checker.allowed('get', token):
        myWebError('401 Unauthorized', 401)
    databaseDir = _SERVER.igor.pathnames.staticdir
    programDir = os.path.dirname(__file__)
    
    # First try static files in the databasedir/static
    filename = os.path.join(databaseDir, name)
    if os.path.exists(filename):
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        data = open(filename, 'rb').read()
        return Response(data, mimetype=mimetype)
    # Next try static files in the programdir/static
    filename = os.path.join(programDir, 'static', name)
    if os.path.exists(filename):
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        data = open(filename, 'rb').read()
        return Response(data, mimetype=mimetype)
    # Otherwise try a template
    template = _SERVER.getJinjaTemplate(name)
    if template:
        # Pass an extra kwargs argument containing all arguments (for easier
        # porting of old web.py templates)
        data = template.render(kwargs=allArgs, token=token, **allArgs)
        return Response(data, mimetype="text/html")
            
    abort(404)

@_WEBAPP.route('/internal/<string:command>', defaults={'subcommand':None})
@_WEBAPP.route('/internal/<string:command>/<path:subcommand>') 
def get_command(command, subcommand=None):
    allArgs = request.values.to_dict()
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    checker = _SERVER.igor.access.checkerForEntrypoint(request.environ['PATH_INFO'])
    if not checker.allowed('get', token):
        myWebError('401 Unauthorized', 401)

    try:
        method = getattr(_SERVER.igor.internal, command)
    except AttributeError:
        abort(404)
    if subcommand:
        allArgs['subcommand'] = subcommand
    try:
        rv = method(token=token, **dict(allArgs))
    except TypeError as arg:
        raise #myWebError("400 Error in command method %s parameters: %s" % (command, arg))
    return returnReply(rv)

@_WEBAPP.route('/internal/<string:command>', defaults={'subcommand':None}, methods=["POST"])
@_WEBAPP.route('/internal/<string:command>/<path:subcommand>', methods=["POST"]) 
def post_command(command, subcommand=None):
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    try:
        method = getattr(_SERVER.igor.internal, command)
    except AttributeError:
        abort(404)
    if request.is_json:
        allArgs = request.get_json()
    else:
        allArgs = {}
    if subcommand:
        allArgs['subcommand'] = subcommand
    try:
        rv = method(token=token, **allArgs)
    except TypeError as arg:
        myWebError("400 Error in command method %s parameters: %s" % (command, arg), 400)
    return returnReply(rv)

@_WEBAPP.route('/action/<string:actionname>')
def get_action(actionname):
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    checker = _SERVER.igor.access.checkerForEntrypoint(request.environ['PATH_INFO'])
    if not checker.allowed('get', token):
        myWebError('401 Unauthorized', 401)

    try:
        return _SERVER.igor.internal.runAction(actionname, token)
    except xmlDatabase.DBAccessError:
        myWebError("401 Unauthorized (while running action)", 401)
        
@_WEBAPP.route('/action/<string:pluginname>/<string:actionname>')
def get_plugin_action(pluginname, actionname):
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    checker = _SERVER.igor.access.checkerForEntrypoint(request.environ['PATH_INFO'])
    if not checker.allowed('get', token):
        myWebError('401 Unauthorized', 401)

    try:
        return _SERVER.igor.internal.runPluginAction(pluginname, actionname, token)
    except xmlDatabase.DBAccessError:
        myWebError("401 Unauthorized (while running action)", 401)
        
@_WEBAPP.route('/trigger/<string:triggername>')
def get_trigger(triggername):
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    checker = _SERVER.igor.access.checkerForEntrypoint(request.environ['PATH_INFO'])
    if not checker.allowed('get', token):
        myWebError('401 Unauthorized', 401)

    try:
        return _SERVER.igor.internal.runTrigger(triggername, token)
    except xmlDatabase.DBAccessError:
        myWebError("401 Unauthorized (while running trigger)", 401)
        
@_WEBAPP.route('/plugin/<string:pluginName>', defaults={'methodName':'index'})
@_WEBAPP.route('/plugin/<string:pluginName>/<string:methodName>')
def get_plugin(pluginName, methodName='index'):
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    checker = _SERVER.igor.access.checkerForEntrypoint(request.environ['PATH_INFO'])
    if not checker.allowed('get', token):
        _SERVER.igor.app.raiseHTTPError('401 Unauthorized')
    pluginObject = _SERVER.igor.plugins._getPluginObject(pluginName, token)
    if not pluginObject:
        _SERVER.igor.app.raiseNotfound()
    #
    # Assemble arguments
    #
    allArgs = request.values.to_dict()
    pluginToken = _SERVER.igor.access.tokenForPlugin(pluginName, token=token)
    allArgs['token'] = pluginToken
    allArgs['callerToken'] = token
    #
    # If there is a user argument also get userData
    #
    if 'user' in allArgs:
        user = allArgs['user']
        userData = _SERVER.igor.plugins._getPluginUserData(pluginName, user, pluginToken)
        if userData:
            allArgs['userData'] = userData
    #
    # Find the method and call it.
    #
    try:
        method = getattr(pluginObject, methodName)
    except AttributeError:
        print('----- Method', methodName, 'not found in', pluginObject)
        abort(404)
    try:
        rv = method(**dict(allArgs))
    except werkzeug.exceptions.HTTPException:
        raise
    except xmlDatabase.DBAccessError:
        myWebError("401 Unauthorized (while running plugin)", 401)
    except ValueError as arg:
        myWebError("400 Error in plugin method %s/%s parameters: %s" % (pluginName, methodName, arg), 400)
    except:
        print('Exception in /plugin/%s/%s:' % (pluginName, methodName))
        traceback.print_exc(file=sys.stdout)
        msg = "502 Exception in %s/%s : %s" % (pluginName, methodName, repr(sys.exc_info()[1]))
        myWebError(msg, 502)
    # See what the plugin returned. Could be a flask Response or list/dict, otherwise we convert to string.
    return returnReply(rv)

@_WEBAPP.route('/plugin/<string:pluginName>/page/<string:pageName>')
def get_plugin_page(pluginName, pageName='index'):
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    pluginToken = _SERVER.igor.access.tokenForPlugin(pluginName, token=token)
    checker = _SERVER.igor.access.checkerForEntrypoint(request.environ['PATH_INFO'])
    if not checker.allowed('get', token):
        myWebError('401 Unauthorized', 401)
    # None is ok here, for plugins with pages but without a Python implementation
    pluginObject = _SERVER.igor.plugins._getPluginObject(pluginName, token)

    allArgs = request.values.to_dict()
    allArgs['pluginName'] = pluginName
    allArgs['pluginObject'] = pluginObject
    # Find plugindata and per-user plugindata
    pluginData = _SERVER.igor.plugins._getPluginData(pluginName, pluginToken)
    allArgs['pluginData'] = pluginData
    if 'user' in allArgs:
        user = allArgs['user']
    else:
        user = _SERVER.getSessionItem('user', None)
    if user:
        allArgs['user'] = user
        userData = _SERVER.igor.plugins._getPluginUserData(pluginName, user, pluginToken)
        if userData:
            allArgs['userData'] = userData
    fullPageName = os.path.join(pluginName, pageName)
    if fullPageName[-3:] == '.md':
        # Markdown, probably the readme.
        mdData = open(os.path.join(_SERVER.igor.pathnames.plugindir, fullPageName)).read()
        data = markdown.markdown(mdData)
        return Response(data, mimetype="text/html")
        
    template = _SERVER.getJinjaTemplate(fullPageName)
    if template:
        # Note that we pass the incoming token, not the pluginToken, to the template
        try:
            data = template.render(kwargs=allArgs, token=pluginToken, callerToken=token, **allArgs)
        except werkzeug.exceptions.HTTPException:
            raise
        except xmlDatabase.DBAccessError:
            myWebError("401 Unauthorized (while rendering template)", 401)
        except:
            print('Exception in /plugin/%s/%s:' % (pluginName, pageName))
            traceback.print_exc(file=sys.stdout)
            msg = "502 Exception in %s/page/%s : %s" % (pluginName, pageName, repr(sys.exc_info()[1]))
            myWebError(msg, 502)
        return Response(data, mimetype="text/html")

    abort(404)

@_WEBAPP.route('/plugin/<string:pluginName>/script/<string:scriptName>')    
def get_plugin_script(pluginName, scriptName):
    allArgs = request.values.to_dict()
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    checker = _SERVER.igor.access.checkerForEntrypoint(request.environ['PATH_INFO'])
    if not checker.allowed('get', token):
        myWebError('401 Unauthorized', 401)
    scriptDir = _SERVER.igor.plugins._getPluginScriptDir(pluginName, token)
        
    if '/' in scriptName or '.' in scriptName:
        myWebError("400 Cannot use / or . in scriptName", 400)
        
    if 'args' in allArgs:
        args = shlex.split(allArgs['args'])
    else:
        args = []
    # xxxjack need to check that the incoming action is allowed on this plugin
    # Get the token for the plugin itself
    pluginToken = _SERVER.igor.access.tokenForPlugin(pluginName, token=token)
    # Setup global, per-plugin and per-user data for plugin scripts, if available
    env = copy.deepcopy(os.environ)
    try:
        # Tell plugin about our url, if we know it
        myUrl = _SERVER.igor.databaseAccessor.get_key('services/igor/url', 'application/x-python-object', 'content', pluginToken)
        env['IGORSERVER_URL'] = myUrl
        if myUrl[:6] == 'https:':
            env['IGORSERVER_NOVERIFY'] = 'true'
    except werkzeug.exceptions.HTTPException:
        pass # web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
    pluginData = _SERVER.igor.plugins._getPluginData(pluginName, pluginToken)
    # Put all other arguments into the environment with an "igor_" prefix
    env['igor_pluginName'] = pluginName
    for k, v in list(allArgs.items()):
        if k == 'args': continue
        if not v:
            v = ''
        env['igor_'+k] = v
    # If a user is logged in we use that as default for a user argument
    user = _SERVER.igor.app.getSessionItem('user')
    if user and not 'user' in allArgs:
        allArgs['user'] = user
    # If there's a user argument see if we need to add per-user data
    if 'user' in allArgs:
        user = allArgs['user']
        userData = _SERVER.igor.plugins._getPluginUserData(pluginName, user, pluginToken)
        if userData:
            allArgs['userData'] = userData
        if userData:
            pluginData.update(userData)
    # Pass plugin data in environment, as JSON
    if pluginData:
        env['igor_pluginData'] = json.dumps(pluginData)
        if type(pluginData) == type({}):
            for k, v in list(pluginData.items()):
                env['igor_'+k] = str(v)
    # Finally pass the token as an OTP (which has the form user:pass)
    oneTimePassword = _SERVER.igor.access.produceOTPForToken(pluginToken)
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
        myWebError("404 scriptName not found: %s" % scriptName, 404)
    if interpreter:
        args = [interpreter, scriptName] + args
    else: # Could add windows and .bat here too, if needed
        args = [scriptName] + args
    # Call the command and get the output
    try:
        rv = subprocess.check_output(args, stderr=subprocess.STDOUT, env=env, universal_newlines=True)
        _SERVER.igor.access.invalidateOTPForToken(oneTimePassword)
    except subprocess.CalledProcessError as arg:
        _SERVER.igor.access.invalidateOTPForToken(oneTimePassword)
        msg = "502 Command %s exited with status code=%d" % (scriptName, arg.returncode)
        output = '%s\n\n%s' % (msg, arg.output)
        # Convenience for internal logging: if there is 1 line of output only we append it to the error message.
        argOutputLines = arg.output.split('\n')
        if len(argOutputLines) == 2 and argOutputLines[1] == '':
            msg += ': ' + argOutputLines[0]
            output = ''
        raise myWebError(msg + '\n' + output, 502)
    except OSError as arg:
        _SERVER.igor.access.invalidateOTPForToken(oneTimePassword)
        myWebError("502 Error running command: %s: %s" % (scriptName, arg.strerror), 502)
    return rv

@_WEBAPP.route('/evaluate/<path:command>')
def get_evaluate(command):
    """Evaluate an XPath expression and return the result as plaintext"""
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    return _SERVER.igor.databaseAccessor.get_value(command, token)
    
@_WEBAPP.route('/login', methods=["GET", "POST"])
def getOrPost_login():
    allArgs = request.values.to_dict()
    if 'logout' in allArgs:
        _SERVER.igor.app.setSessionItem('user', None)
        return redirect('/')
    message = None
    username = allArgs.get('username')
    password = allArgs.get('password')
    if username:
        if _SERVER.igor.access.userAndPasswordCorrect(username, password):
            _SERVER.igor.app.setSessionItem('user', username)
            return redirect('/')
        message = "Password and/or username incorrect."
    template = _SERVER.getJinjaTemplate('_login.html')
    data = template.render(**dict(allArgs))
    return Response(data, mimetype="text/html")


@_WEBAPP.route('/data/', defaults={'name':''})
@_WEBAPP.route('/data/<path:name>')
def get_data(name):
    """Abstract database that handles the high-level HTTP GET.
    If no query get the content of a section of the database.
    If there is a query can be used as a 1-url shortcut for POST."""
    optArgs = request.values.to_dict()
    # See whether we have a variant request
    variant = None
    if '.VARIANT' in optArgs:
        variant = optArgs['.VARIANT']
        del optArgs['.VARIANT']
        
    if optArgs and '.METHOD' in optArgs:
        # GET with a query is treated as POST/PUT/DELETE with the query as JSON data,
        # if .METHOD argument states it should be treaded as another method.
        optArgs = dict(optArgs)
        kwargs = {}
        methodName = optArgs.pop('.METHOD')
        methods = {
            'PUT' : putOrPost_data,
            'POST' : putOrPost_data,
            'DELETE' : delete_data,
            }
        method = methods.get(methodName)
        if not method:
            myWebError("400 Unknown .METHOD={}".format(methodName))
        if methodName == 'POST':
            kwargs['replace'] = False
        rv = method(name, optArgs, mimetype="application/x-www-form-urlencoded", **kwargs)
        return rv
        
    token = _SERVER.igor.access.tokenForRequest(request.environ)

    returnType = _best_return_mimetype()
    if not returnType:
        abort(406)
    rv = _SERVER.igor.databaseAccessor.get_key(name, _best_return_mimetype(), variant, token)
    if not isinstance(rv, Response):
        rv = Response(rv, mimetype=returnType)
    return rv

@_WEBAPP.route('/data/<path:name>', methods=["PUT", "POST"])
def putOrPost_data(name, data=None, mimetype=None, replace=True):
    """Replace part of the document with new data, or inster new data
    in a specific location.
    """
    if request.method == 'POST':
        replace = False
    optArgs = request.values.to_dict()
    token = _SERVER.igor.access.tokenForRequest(request.environ)

    # See whether we have a variant request
    variant = None
    if '.VARIANT' in optArgs:
        variant = optArgs['.VARIANT']
        del optArgs['.VARIANT']
    
    if data == None:
        # We either have a url-encoded query in optArgs or read raw data
        if request.values:
            data = request.values.to_dict()
            mimetype = "application/x-www-form-urlencoded"
        else:
            data = request.data
            mimetype = request.environ.get('CONTENT_TYPE', 'application/unknown')
    returnType = _best_return_mimetype()
    rv = _SERVER.igor.databaseAccessor.put_key(name, returnType, variant, data, mimetype, token, replace=replace)
    if not isinstance(rv, Response):
        rv = Response(rv, mimetype=returnType)
    return rv

@_WEBAPP.route('/data/<path:name>', methods=["DELETE"])
def delete_data(name, data=None, mimetype=None):
    token = _SERVER.igor.access.tokenForRequest(request.environ)
    rv = _SERVER.igor.databaseAccessor.delete_key(name, token)
    return rv

def _best_return_mimetype():
    """Return the best mimetype in which to encode the return data, or None"""
    if not _SERVER.igor.databaseAccessor.MIMETYPES:
        return None
    acceptable = request.environ.get("HTTP_ACCEPT")
    if not acceptable:
        return _SERVER.igor.databaseAccessor.MIMETYPES[0]
    return mimetypematch.match(acceptable, _SERVER.igor.databaseAccessor.MIMETYPES)

class XmlDatabaseAccess(object):
    """Class to access the database in a somewhat rest-like manner. Instantiated once, in the igor object."""
    
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
            myWebError("401 Unauthorized", 401)
        except xpath.XPathError as arg:
            myWebError("400 XPath error: %s" % str(arg), 401)
        except xmlDatabase.DBKeyError as arg:
            myWebError("400 Database Key Error: %s" % str(arg), 400)
        except xmlDatabase.DBParamError as arg:
            myWebError("400 Database Parameter Error: %s" % str(arg), 400)
        
    def get_value(self, expression, token):
        """Evaluate a general expression and return the string value"""
        try:
            return self.igor.database.getValue(expression, token=token)
        except xmlDatabase.DBAccessError:
            myWebError("401 Unauthorized", 401)
        except xpath.XPathError as arg:
            myWebError("400 XPath error: %s" % str(arg), 400)
        except xmlDatabase.DBKeyError as arg:
            myWebError("400 Database Key Error: %s" % str(arg), 400)
        except xmlDatabase.DBParamError as arg:
            myWebError("400 Database Parameter Error: %s" % str(arg), 400)
        
    def put_key(self, key, mimetype, variant, data, datamimetype, token, replace=True):
        try:
            if not key:
                myWebError("400 cannot PUT or POST whole document", 400)
            if key[0] != '/':
                key = '/%s/%s' % (self.rootTag, key)
            if not variant: variant = 'ref'
            callbacks = None
            nodesToSignal = []
            # xxxjack this code should move into xmlDatabase, really...
            unchanged = False
            parentPath, tag = self.igor.database.splitXPath(key, stripPredicate=True)
            if not tag:
                myWebError("400 PUT path must end with an element tag", 400)
            element = self.convertfrom(data, tag, datamimetype)
            oldElements = self.igor.database.getElements(key, 'put' if replace else 'post', token)
            if not oldElements:
                #
                # Does not exist yet (so post and put are the same, really). See if we can create it.
                #
                if not parentPath or not tag:
                    myWebError("404 Not Found, parent or tag missing", 404)
                self.igor.database.addElement(parentPath, tag, element, token)
            elif replace:
                #
                # Already exists, and we want to replace it. Check that it exists only once.
                #
                if len(oldElements) > 1:
                    myWebError("400 Bad PUT Request, XPath selects multiple items", 400)
                oldElement = oldElements[0]
                unchanged = self.igor.database.replaceElement(oldElement, element, token)
            else:
                #
                # Already exists, and we want to add a new one
                #
                if len(oldElements) > 1:
                    parent1 = oldElements[0].parentNode
                    for otherNode in oldElements[1:]:
                        if otherNode.parentNode != parent1:
                            myWebError("400 Bad Request, XPath selects multiple items from multiple parents", 400)
                #
                # POST, simply append the new node to the parent (and signal that parent)
                #
                self.igor.database.addElement(parentPath, tag, element, token)
            path = self.igor.database.getXPathForElement(element)
            rv = self.convertto(path, mimetype, variant)
            if not isinstance(rv, Response):
                rv = Response(rv, mimetype=mimetype)
            if unchanged:
                rv.status_code = 200
            return rv
        except xmlDatabase.DBAccessError:
            myWebError("401 Unauthorized", 401)
        except xpath.XPathError as arg:
            myWebError("400 XPath error: %s" % str(arg), 400)
        except xmlDatabase.DBKeyError as arg:
            myWebError("400 Database Key Error: %s" % str(arg), 400)
        except xmlDatabase.DBParamError as arg:
            myWebError("400 Database Parameter Error: %s" % str(arg), 400)
        
    def delete_key(self, key, token):
        try:
            key = '/%s/%s' % (self.rootTag, key)
            self.igor.database.delValues(key, token)
            return ''
        except xmlDatabase.DBAccessError:
            myWebError("401 Unauthorized", 401)
        except xpath.XPathError as arg:
            myWebError("400 XPath error: %s" % str(arg), 400)
        except xmlDatabase.DBKeyError as arg:
            myWebError("400 Database Key Error: %s" % str(arg), 400)
        
    def convertto(self, value, mimetype, variant):
        if variant == 'ref':
            if not isinstance(value, basestring):
                myWebError("400 Bad request, cannot use .VARIANT=ref for this operation", 400)
            if mimetype == "application/json":
                return json.dumps({"ref":value})+'\n'
            elif mimetype == "text/plain":
                return value+'\n'
            elif mimetype == "application/xml":
                return "<ref>%s</ref>\n" % value
            elif mimetype == "application/x-python-object":
                return value
            else:
                myWebError("500 Unimplemented mimetype %s for ref" % mimetype, 500)
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
                myWebError("500 Unimplemented mimetype %s for default or multi, simple value" % mimetype, 500)
        if variant in ('multi', 'multiraw'):
            if mimetype == "application/json":
                rv = []
                for item in value:
                    r = self.igor.database.getXPathForElement(item)
                    t, v = self.igor.database.tagAndDictFromElement(item, stripHidden=(variant != 'multiraw'))
                    rv.append({"ref":r, t:v})
                return json.dumps(rv)+'\n'
            elif mimetype == "text/plain":
                myWebError("400 Bad request, cannot use .VARIANT=multi for mimetype text/plain", 400)
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
                myWebError("500 Unimplemented mimetype %s for multi, nodeset" % mimetype, 500)
        # Final case: single node return (either no variant or variant='raw')
        if len(value) == 0:
            abort(404)
        if mimetype == "application/json":
            if len(value) > 1:
                myWebError("400 Bad request, cannot return multiple items without .VARIANT=multi", 400)
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
                myWebError("400 Bad request, cannot return multiple items without .VARIANT=multi", 400)
            return self.igor.database.xmlFromElement(value[0], stripHidden=(variant != 'raw'))+'\n'
        elif mimetype == 'application/x-python-object':
            if len(value) > 1:
                myWebError("400 Bad request, cannot return multiple items without .VARIANT=multi", 400)
            t, v = self.igor.database.tagAndDictFromElement(value[0], stripHidden=(variant != 'raw'))
            return v

        else:
            myWebError("500 Unimplemented mimetype %s for default, single node" % mimetype, 500)
        
    def convertfrom(self, value, tag, mimetype):
        if mimetype == 'application/xml':
            if type(value) != type(''):
                value = value.decode('utf-8')
            element = self.igor.database.elementFromXML(value)
            if element.tagName != tag:
                myWebError("400 Bad request, toplevel XML tag %s does not match final XPath element %s" % (element.tagName, tag), 400)
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
                if isinstance(value, bytes):
                    value = value.decode('utf8')
                valueDict = json.loads(value)
            except ValueError:
                myWebError("400 No JSON object could be decoded from body", 400)
            if not isinstance(valueDict, dict):
                myWebError("400 Bad request, JSON toplevel object must be object", 400)
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
            myWebError("500 Conversion from %s not implemented" % mimetype, 500)
        
