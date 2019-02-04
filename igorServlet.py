from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import object
# Enable coverage if installed and enabled through COVERAGE_PROCESS_START environment var
try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass
from flask import Flask, request, abort, make_response
import gevent.pywsgi
import threading
import time
import json
import argparse
import os
import sys
import jwt
import logging

DEBUG=False

def myWebError(msg, code=400):
    resp = make_response(msg, code)
    abort(resp)

class IgorServlet(threading.Thread):
    """Class implementing a REST server for use with Igor.
    
    Objects of this class implement a simple REST server, which can optionally be run in a separate
    thread. After creating the server object (either before the service is running or while it is running)
    the calling application can use ``addEndpoint()`` to create endpoints with callbacks
    for the various http(s) verbs.
    
    The service understands Igor access control (external capabilities and issuer shared
    secret keys) and takes care of implementing the access control policy set by the issuer.
    Callbacks are only made when the REST call carries a capability that allows the specific
    operation.
    
    The service is implemented using *Flask* and *gevent.pywsgi*.
    
    The service can by used by calling ``run()``, which will run forever in the current thread and not return.
    Alternatively you can call ``start()`` which will run the service in a separate thread until
    ``stop()`` is called.
    
    Arguments:
        port (int): the TCP port the service will listen to.
        name (str): name of the service.
        nossl (bool): set to ``True`` to serve http (default: serve https).
        capabilities (bool): set to ``True`` to enable using Igor capability-based access control.
        noCapabilities (bool): set to ``True`` to disable using Igor capability-based access control.
            The default for those two arguments is currently to *not* use capabilities but this is expected
            to change in a future release.
        database (str): the directory containing the SSL key *sslname*\ ``.key`` and certificate *sslname*\ ``.crt``.
            Default is ``'.'``, but ``argumentParser()`` will return ``database='~/.igor'``. This is because
            certificates contain only a host name, not a port or protocol, hence if ``IgorServlet`` is running
            on the same machine as Igor they must share a certificate.
        sslname (str): The name used in the key and certificate filename. Default is ``igor`` for reasons explained above.
        nolog (bool): Set to ``True`` to disable *gevent.pywsgi* apache-style logging of incoming requests to stdout
        audience (str): The ``<aud>`` value trusted in the capabilities. Usually either the hostname or the base URL of this service.
        issuer (str): The ``<iss>`` value trusted in the capabilities. Usually the URL for the Igor running the issuer with ``/issuer`` as endpoint. Can be set after creation.
        issuerSharedKey (str): The secret symmetric key shared between the audience (this program) and the issuer. Can be set after creation.
        
    Note that while it is possible to specify ``capabilities=True`` and ``nossl=True`` at the same time this
    is not a good idea: the capabilities are encrypted but have a known structure, and therefore the *issuerSharedKey*
    would be open to a brute-force attack.
    """
    
    @staticmethod
    def argumentParser(parser=None, description=None, port=None, name=None): # pragma: no cover
        """Static method to create ArgumentParser with common arguments for IgorServlet.
        
        Programs using IgorServlet as their REST interface will likely share a number of command
        line arguments (to allow setting of port, protocol, capability support, etc). This
        method returns such a parser, which will return (from ``parse_args()``) a namespace
        with arguments suitable for IgorServlet.
        
        Arguments:
            parser (argparse.ArgumentParser): optional parser (by default one is created)
            description (str): description for the parser constructor (if one is created)
            port (int): default for the ``--port`` argument (the port the service listens to)
            name (str): name of the service (default taken from ``sys.argv[0]``)
            
        Returns:
            A pre-populated ``argparse.ArgumentParser``
        """
        if parser is None:
            if description is None:
                description = "Mini-server for use with Igor"
            parser = argparse.ArgumentParser(description=description)
            
        DEFAULTDIR=os.path.join(os.path.expanduser('~'), '.igor')
        if 'IGORSERVER_DIR' in os.environ:
            DEFAULTDIR = os.environ['IGORSERVER_DIR']
        if port is None:
            port = 8080
        if name is None:
            name = os.path.basename(os.path.splitext(sys.argv[0])[0])
        
        parser.add_argument("--database", metavar="DIR", help="Config and logfiles in DIR (default: %s, environment IGORSERVER_DIR)" % DEFAULTDIR, default=DEFAULTDIR)
        parser.add_argument("--name", metavar="NAME", help="Program name for use in log and config filenames in database dir(default: %s)" % name, default=name)
        parser.add_argument("--sslname", metavar="NAME", help="Program name to look up SSL certificate and key in database dir (default: igor)", default="igor")
        parser.add_argument("--port", metavar="PORT", type=int, help="Port to serve on (default: %d)" % port, default=port)
        parser.add_argument("--nossl", action="store_true", help="Do no use https (ssl) on the service, even if certificates are available")
        parser.add_argument("--nolog", action="store_true", help="Disable http server logging to stdout")
        parser.add_argument("--noCapabilities", action="store_true", help="Disable access control via capabilities (allowing all access)")
        parser.add_argument("--capabilities", action="store_true", help="Enable access control via capabilities")
        parser.add_argument("--audience", metavar="URL", help="Audience string for this servlet (for checking capabilities and their signature)")
        parser.add_argument("--issuer", metavar="URL", help="Issuer string for this servlet (for checking capabilities and their signature)")
        parser.add_argument("--sharedKey", metavar="B64STRING", help="Secret key shared with issuer (for checking capabilities and their signature)")
        return parser
        
    def __init__(self, port=8080, name='igorServlet', nossl=False, capabilities=None, noCapabilities=None, database=".", sslname='igor', nolog=False, audience=None, issuer=None, issuerSharedKey=None, **kwargs):
        threading.Thread.__init__(self)
        self.endpoints = {}
        self.useCapabilities = False # Default-default
        self.issuer = None
        self.issuerSharedKey = None
        self.audience = None
        self.server = None
        self.port = port
        self.name = name
#        self.middleware = ()
        self.nolog = nolog
        self.sslname = sslname
        if not self.sslname:
            self.sslname = self.name
        self.datadir = database

        self.ssl = not nossl
        keyFile = os.path.join(self.datadir, self.sslname + '.key')
        if self.ssl and not os.path.exists(keyFile):
            print('Warning: Using http in stead of https: no private key file', keyFile, file=sys.stderr)
            self.ssl = False
        if self.ssl:
            self.privateKeyFile = keyFile
            self.certificateFile = os.path.join(self.datadir, self.sslname + '.crt')
        else:
            self.privateKeyFile = None
            self.certificateFile = None

        if capabilities != None:
            self.useCapabilities = capabilities
        elif noCapabilities != None:
            self.useCapabilities = not noCapabilities
        self.audience = audience
        self.issuer = issuer
        self.issuerSharedKey = issuerSharedKey
        
        if DEBUG: print('igorServlet: IgorServlet.__init__ called for', self)
        self.app = Flask(__name__)
        
    def setIssuer(self, issuer, issuerSharedKey):
        """Set URL of issuer trusted by this service and shared symmetric key.
        
        If the issuer and shared key are not known yet during IgorServlet creation they can be
        set later using this method, or changed.
        
        Arguments:
            issuer (str): The ``<iss>`` value trusted in the capabilities. Usually the URL for the Igor running the issuer with ``/issuer`` as endpoint.
            issuerSharedKey (str): The secret symmetric key shared between the audience (this program) and the issuer.
        """
        self.issuer = issuer
        self.issuerSharedKey = issuerSharedKey

    def hasIssuer(self):
        """Return ``True`` if this IgorServlet has an issuer and shared key"""
        return not not self.issuer and not not self.issuerSharedKey
        
    def run(self):
        """Run the REST service.
        
        This will start serving and never return, until ``stop()`` is called (in a callback
        or from another thread).
        """
        if self.ssl:
            kwargs = dict(keyfile=self.privateKeyFile, certfile=self.certificateFile)
        else:
            kwargs = {}
        if self.nolog:
            kwargs['log'] = None
        self.server = gevent.pywsgi.WSGIServer(("0.0.0.0", self.port), self.app, **kwargs)
        self.server.serve_forever(stop_timeout=10)
        
    def stop(self):
        """Stop the REST service.
        
        This will stop the service and ``join()`` the thread that was running it.
        """
        if self.server:
            self.server.stop(timeout=10)
            self.server = None
        return self.join()
        
    def addEndpoint(self, path, mimetype='application/json', get=None, put=None, post=None, delete=None):
        """Add REST endpoint.
        
        Use this call to add an endpoint to this service and supply the corresponding
        callback methods.
        
        When a REST request is made to this endpoint the first things that happens (if
        capability support has been enabled) is that a capability is carried in the request
        and that it is valid (using *audience*, *issuer* and *issuerSecretKey*). Then
        it is checked that the capability gives the right to execute this operation.
        
        Arguments to the REST call (and passed to the callback method) can be supplied
        in three different ways:
        
        - if the request carries a URL query the values are supplied to the callback
          as named parameters.
        - otherwise, if the request contains JSON data this should be an object, and
          the items in the object are passed as named parameters.
        - otherwise, if the request contains data that is not JSON this data is
          passed (as a string) as the ``data`` argument.
          
        Arguments:
            path (str): The new endpoint, starting with ``/``.
            mimetype (str): How the return value of the callback should be encoded.
              Currently ``application/json`` and ``text/plain`` are supported.
            get: Callback for GET calls.
            put: Callback for PUT calls.
            post: Callback for POST calls.
            delete: Callback for DELETE calls.
        """
        self.endpoints[path] = dict(mimetype=mimetype, get=get, put=put, post=post, delete=delete)
        methods = []
        if get:
            methods.append("GET")
        if put:
            methods.append("PUT")
        if post:
            methods.append("POST")
        if delete:
            methods.append("DELETE")
        self.app.add_url_rule(path, path, self._forward, methods=methods)
        
    def _forward(self):
        method = request.method.lower()
        path = request.path
        endpoint = self.endpoints.get(path)
        if not path:
            abort(404)
        entry = endpoint[method]
        if not entry:
            abort(404)
        if self.useCapabilities:
            # We are using capability-based access control Check that the caller has the correct
            # rights.
            if not self._checkRights(method, path):
                abort(401)
        methodArgs = {}
        methodArgs = request.values.to_dict()
        if not methodArgs:
            if request.is_json:
                methodArgs = request.json
            elif request.data:
                data = request.data
                if not isinstance(data, str):
                    assert isinstance(data, bytes)
                    data = data.decode('utf8')
                methodArgs = dict(data=data)
            else:
                methodArgs = {}
        try:
            rv = entry(**methodArgs)
        except TypeError as arg:
            return myWebError("400 Error in parameters: %s" % arg)
        if endpoint['mimetype'] == 'text/plain':
            if type(rv) != type(str):
                rv = "%s" % (rv,)
        elif endpoint['mimetype'] == 'application/json':
            if isinstance(rv, bytes):
                rv = rv.decode('utf8')
            rv = json.dumps(rv)
        else:
            assert 0, 'Unsupported mimetype %s' % endpoint['mimetype']
        # Finally ensure we send utf8 bytes back
        rv = rv.encode('utf-8')
        return rv

    def _checkRights(self, method, path):
        if DEBUG:  print('IgorServlet: check access for method %s on %s' % (method, path))
        if not self.issuer: 
            if DEBUG: print('IgorServlet: issuer not set, cannot check access')
            return False
        if not self.issuerSharedKey: 
            if DEBUG: print('IgorServlet: issuerSharedKey not set, cannot check access')
            return False
        # Get capability from headers
        headers = request.headers
        authHeader = headers.get('Authorization')
        if not authHeader:
            if DEBUG: print('IgorServlet: no Authorization: header')
            return False
        authFields = authHeader.split()
        if authFields[0].lower() != 'bearer':
            if DEBUG: print('IgorServlet: no Authorization: bearer header')
            return False
        encoded = authFields[1] # base64.b64decode(authFields[1])
        if DEBUG: print('IgorServlet: got bearer token data %s' % encoded)
        decoded = self._decodeBearerToken(encoded)
        if not decoded:
            # _decodeBearerToken will return None if the key is not from the right issuer or the signature doesn't match.
            return False
        capPath = decoded.get('obj')
        capModifier = decoded.get(method)
        if not capPath:
            if DEBUG: print('IgorServlet: capability does not contain obj field')
            return False
        if not capModifier:
            if DEBUG: print('IgorServlet: capability does not have %s right' % method)
            return False
        pathHead = path[:len(capPath)]
        pathTail = path[len(capPath):]
        if pathHead != capPath or (pathTail and pathTail[0] != '/'):
            if DEBUG: print('IgorServlet: capability path %s does not match %s' % (capPath, path))
            return False
        if capModifier == 'self':
            if capPath != path:
                if DEBUG: print('IgorServlet: capability path %s does not match self for %s' % (capPath, path))
                return False
        elif capModifier == 'child':
            if pathTail.count('/') != 1:
                if DEBUG: print('IgorServlet: capability path %s does not match direct child for %s' % (capPath, path))
                return False
        elif capModifier == 'descendant':
            if not pathTail.count:
                if DEBUG: print('IgorServlet: capability path %s does not match descendant for %s' % (capPath, path))
                return False
        elif capModifier == 'descendant-or-self':
            pass
        else:
            if DEBUG: print('IgorServlet: capability has unkown modifier %s for right %s' % (capModifier, method))
            return False
        if DEBUG:
            print('IgorServlet: Capability matches')
        return True
        
    def _decodeBearerToken(self, data):
        try:
            content = jwt.decode(data, self.issuerSharedKey, issuer=self.issuer, audience=self.audience, algorithms=['RS256', 'HS256'])
        except jwt.DecodeError:
            if DEBUG:
                print('IgorServlet: incorrect signature on bearer token %s' % data)
                print('IgorServlet: content: %s' % jwt.decode(data, verify=False))
            return myWebError('401 Unauthorized, Incorrect signature on key', 401)
        except jwt.InvalidIssuerError:
            if DEBUG:
                print('IgorServlet: incorrect issuer on bearer token %s' % data)
                print('IgorServlet: content: %s' % jwt.decode(data, verify=False))
            return myWebError('401 Unauthorized, incorrect issuer on key', 401)
        except jwt.InvalidAudienceError:
            if DEBUG:
                print('IgorServlet: incorrect audience on bearer token %s' % data)
                print('IgorServlet: content: %s' % jwt.decode(data, verify=False))
            return myWebError('401 Unauthorized, incorrect audience on key', 401)
        return content

def argumentParser(*args, **kwargs):
    return IgorServlet.argumentParser(*args, **kwargs)
    
def main():  # pragma: no cover
    global DEBUG
    DEBUG = True
    if DEBUG: print('igorServlet: main called')
    
    class HelloClass(object):
        """Example class that returns static data (which may be recomputed every call)"""
        
        def __init__(self):
            if DEBUG: print('HelloClass.__init__ called for', self)

        def get_hello(self):
            return 'Hello World from test'
        
    class CounterClass(threading.Thread):
        """Example active class that returns a counter for the number of seconds it has been running"""
        
        def __init__(self):
            threading.Thread.__init__(self)
            if DEBUG: print('CounterClass.__init__ called for', self)
            self.counter = 0
            self.stopped = False
            
        def run(self):
            while not self.stopped:
                time.sleep(1)
                self.counter += 1
                
        def stop(self):
            self.stopped = 1
            self.join()
            
        def get_count(self):
            return {'counter':self.counter}
    
    #
    # Parse command line arguments and instantiate the web server
    #
    parser = IgorServlet.argumentParser()
    args = parser.parse_args()
    s = IgorServlet(**vars(args))
    #
    # Instantiate and start the worker classes for this example program
    #
    helloObject = HelloClass()
    counterObject = CounterClass()
    #
    # Add the endpoints to the web server
    #
    s.addEndpoint('/hello', get=helloObject.get_hello, mimetype='text/plain')
    s.addEndpoint('/helloJSON', get=helloObject.get_hello, mimetype='application/json')
    s.addEndpoint('/count', get=counterObject.get_count, mimetype='text/plain')
    s.addEndpoint('/countJSON', get=counterObject.get_count, mimetype='application/json')
    #
    # Start the web server and possibly the other servers
    #
    s.start()
    counterObject.start()
    try:
        while True:
            time.sleep(10)
            if DEBUG: print('IgorServlet: time passing and still serving...')
    except KeyboardInterrupt:
        pass
    #
    # Stop everything when termination has been requested.
    #
    if DEBUG: print('IgorServlet: stopping server')
    counterObject.stop()
    s.stop()
    s = None
    
if __name__ == '__main__':
    main()
    
