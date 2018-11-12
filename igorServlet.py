from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import object
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
        self.issuer = issuer
        self.issuerSharedKey = issuerSharedKey

    def hasIssuer(self):
        return not not self.issuer and not not self.issuerSharedKey
        
    def run(self):
        if self.ssl:
            kwargs = dict(keyfile=self.privateKeyFile, certfile=self.certificateFile)
        else:
            kwargs = {}
        if self.nolog:
            kwargs['log'] = None
        self.server = gevent.pywsgi.WSGIServer(("0.0.0.0", self.port), self.app, **kwargs)
        self.server.serve_forever()
        
    def stop(self):
        if self.server:
            self.server.stop()
            self.server = None
        return self.join()
        
    def addEndpoint(self, path, mimetype='application/json', get=None, put=None, post=None, delete=None):
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

        
def main():
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
    
