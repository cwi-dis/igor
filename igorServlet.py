import web
import threading
import time
import json
import argparse
import os
import sys
import jwt

DEBUG=False

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class MyApplication(web.application):
    def run(self, port=8080, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))

class NoLog:
    def __init__(self, application):
        self.app = application
        self.nullfile = open('/dev/null', 'w')
        
    def __call__(self, environ, start_response):
        environ['wsgi.errors'] = self.nullfile
        return self.app(environ, start_response)
            
class IgorServlet(threading.Thread):
    # The following class variables are actually also used by ForwardingClass, below
    endpoints = {}
    useCapabilities = False # Default-default
    issuer = None
    issuerSharedKey = None
    audience = None
    
    @staticmethod
    def argumentParser(parser=None, description=None, port=None, name=None):
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
        self.port = port
        self.name = name
        self.middleware = ()
        self.nolog = nolog
        if nolog:
            self.middleware = (NoLog,)
        self.sslname = sslname
        if not self.sslname:
            self.sslname = self.name
        self.datadir = database

        self.ssl = not nossl
        keyFile = os.path.join(self.datadir, self.sslname + '.key')
        if self.ssl and not os.path.exists(keyFile):
            print >>sys.stderr, 'Warning: Using http in stead of https: no private key file', keyFile
            self.ssl = False
        if self.ssl:
            self.privateKeyFile = keyFile
            self.certificateFile = os.path.join(self.datadir, self.sslname + '.crt')
        else:
            self.privateKeyFile = None
            self.certificateFile = None

        if capabilities != None:
            IgorServlet.useCapabilities = capabilities
        elif noCapabilities != None:
            IgorServlet.useCapabilities = not noCapabilities
        IgorServlet.audience = audience
        IgorServlet.issuer = issuer
        IgorServlet.issuerSharedKey = issuerSharedKey
        
        if DEBUG: print 'igorServlet: IgorServlet.__init__ called for', self
        self.app = MyApplication((), globals(), autoreload=False)
        
    def run(self):
        if self.ssl:
            from web.wsgiserver import CherryPyWSGIServer
            CherryPyWSGIServer.ssl_certificate = self.certificateFile
            CherryPyWSGIServer.ssl_private_key = self.privateKeyFile
        keepStdout = sys.stdout
        self.app.run(self.port, *self.middleware)
        
    def stop(self):
        self.app.stop()
        return self.join()
        
    def addEndpoint(self, path, mimetype='application/json', get=None, put=None, post=None, delete=None):
        self.endpoints[path] = dict(mimetype=mimetype, get=get, put=put, post=post, delete=delete)
        self.app.add_mapping(path, 'ForwardingClass')
        
    def setIssuer(self, issuer, issuerSharedKey):
        IgorServlet.issuer = issuer
        IgorServlet.issuerSharedKey = issuerSharedKey

    def hasIssuer(self):
        return not not IgorServlet.issuer and not not IgorServlet.issuerSharedKey
        
class ForwardingClass:
    def __init__(self):
       if DEBUG: print 'igorServlet: ForwardingClass.__init__ called for', self

    def GET(self):
        return self._method('get')
        
    def PUT(self):
        return self._method('put')
        
    def POST(self):
        return self._method('post')
        
    def DELETE(self):
        return self._method('delete')
        
    def _method(self, method):
        path = web.ctx.path
        endpoint = IgorServlet.endpoints.get(path)
        if not path:
            raise web.notfound()
        entry = endpoint[method]
        if not entry:
            raise web.notfound()
        if IgorServlet.useCapabilities:
            # We are using capability-based access control Check that the caller has the correct
            # rights.
            if not self._checkRights(method, path):
                raise MyWebError('401 Unauthorized')
        methodArgs = {}
        optArgs = web.input()
        if optArgs:
            methodArgs = dict(optArgs)
        else:
            data = web.data()
            if data:
                try:
                    methodArgs = json.loads(data)
                except ValueError:
                    methodArgs = {'data' : data}
        try:
            rv = entry(**methodArgs)
        except TypeError, arg:
            raise myWebError("400 Error in parameters: %s" % arg)
        if endpoint['mimetype'] == 'text/plain':
            rv = str(rv)
        elif endpoint['mimetype'] == 'application/json':
            rv = json.dumps(rv)
        else:
            assert 0, 'Unsupported mimetype %s' % endpoint['mimetype']
        return rv
        
    def _checkRights(self, method, path):
        if DEBUG:  print 'IgorServlet: check access for method %s on %s' % (method, path)
        if not IgorServlet.issuer: 
            if DEBUG: print 'IgorServlet: issuer not set, cannot check access'
            return False
        if not IgorServlet.issuerSharedKey: 
            if DEBUG: print 'IgorServlet: issuerSharedKey not set, cannot check access'
            return False
        # Get capability from headers
        headers = web.ctx.env
        authHeader = headers.get('HTTP_AUTHORIZATION')
        if not authHeader:
            if DEBUG: print 'IgorServlet: no Authorization: header'
            return False
        authFields = authHeader.split()
        if authFields[0].lower() != 'bearer':
            if DEBUG: print 'IgorServlet: no Authorization: bearer header'
            return False
        encoded = authFields[1] # base64.b64decode(authFields[1])
        if DEBUG: print 'IgorServlet: got bearer token data %s' % encoded
        decoded = self._decodeBearerToken(encoded)
        if not decoded:
            # _decodeBearerToken will return None if the key is not from the right issuer or the signature doesn't match.
            return False
        capPath = decoded.get('obj')
        capModifier = decoded.get(method)
        if not capPath:
            if DEBUG: print 'IgorServlet: capability does not contain obj field'
            return False
        if not capModifier:
            if DEBUG: print 'IgorServlet: capability does not have %s right' % method
            return False
        pathHead = path[:len(capPath)]
        pathTail = path[len(capPath):]
        if pathHead != capPath or (pathTail and pathTail[0] != '/'):
            if DEBUG: print 'IgorServlet: capability path %s does not match %s' % (capPath, path)
            return False
        if capModifier == 'self':
            if capPath != path:
                if DEBUG: print 'IgorServlet: capability path %s does not match self for %s' % (capPath, path)
                return False
        elif capModifier == 'child':
            if pathTail.count('/') != 1:
                if DEBUG: print 'IgorServlet: capability path %s does not match direct child for %s' % (capPath, path)
                return False
        elif capModifier == 'descendant':
            if not pathTail.count:
                if DEBUG: print 'IgorServlet: capability path %s does not match descendant for %s' % (capPath, path)
                return False
        elif capModifier == 'descendant-or-self':
            pass
        else:
            if DEBUG: print 'IgorServlet: capability has unkown modifier %s for right %s' % (capModifier, method)
            return False
        if DEBUG:
            print 'IgorServlet: Capability matches'
        return True
        
    def _decodeBearerToken(self, data):
        try:
            content = jwt.decode(data, IgorServlet.issuerSharedKey, issuer=IgorServlet.issuer, audience=IgorServlet.audience, algorithm='RS256')
        except jwt.DecodeError:
            if DEBUG:
                print 'IgorServlet: incorrect signature on bearer token %s' % data
                print 'IgorServlet: content: %s' % jwt.decode(data, verify=False)
            raise myWebError('401 Unauthorized, Incorrect signature on key')
        except jwt.InvalidIssuerError:
            if DEBUG:
                print 'IgorServlet: incorrect issuer on bearer token %s' % data
                print 'IgorServlet: content: %s' % jwt.decode(data, verify=False)
            raise myWebError('401 Unauthorized, incorrect issuer on key')
        except jwt.InvalidAudienceError:
            if DEBUG:
                print 'IgorServlet: incorrect audience on bearer token %s' % data
                print 'IgorServlet: content: %s' % jwt.decode(data, verify=False)
            raise myWebError('401 Unauthorized, incorrect audience on key')
        return content
        
def main():
    global DEBUG
    DEBUG = True
    if DEBUG: print 'igorServlet: main called'
    
    class HelloClass:
        """Example class that returns static data (which may be recomputed every call)"""
        
        def __init__(self):
            if DEBUG: print 'HelloClass.__init__ called for', self

        def get_hello(self):
            return 'Hello World from test'
        
    class CounterClass(threading.Thread):
        """Example active class that returns a counter for the number of seconds it has been running"""
        
        def __init__(self):
            threading.Thread.__init__(self)
            if DEBUG: print 'CounterClass.__init__ called for', self
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
            if DEBUG: print 'IgorServlet: time passing and still serving...'
    except KeyboardInterrupt:
        pass
    #
    # Stop everything when termination has been requested.
    #
    if DEBUG: print 'IgorServlet: stopping server'
    counterObject.stop()
    s.stop()
    s = None
    
if __name__ == '__main__':
    main()
    
