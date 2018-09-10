#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import argparse
import urllib.parse
import urllib.request, urllib.parse, urllib.error
import requests
import sys
import os
import time
import json
import base64
import pprint
import xml.etree.ElementTree
import socket
import configparser

class IgorError(EnvironmentError):
    pass
    
CONFIG = configparser.ConfigParser(
    dict(
        url="http://igor.local:9333/data",
        bearer=None,
        access=None,
        credentials=None,
        certificate=None,
        noverify=None,
        verbose=None,
    ))
CONFIG.add_section('igor')
CONFIG.read(os.path.expanduser('~/.igor/igor.cfg'))
# Override from environment:
for k, _ in CONFIG.items('igor'):
    envKey = 'IGORSERVER_' + k.upper()
    if envKey in os.environ:
        CONFIG.set('igor', k, os.environ[envKey])
        
# DEFAULT_URL="http://framboos.local:9333/data"
# if 'IGORSERVER_URL' in os.environ:
#   DEFAULT_URL = os.environ['IGORSERVER_URL']

VERBOSE=False

class IgorServer(object):
    def __init__(self, url, bearer_token=None, access_token=None, credentials=None, certificate=None, noverify=False, printmessages=False):
        self.baseUrl = url
        if url[-1] != '/':
            url = url + '/'
        self.url = url
        self.bearer_token = bearer_token
        self.access_token = access_token
        self.credentials = credentials
        if certificate:
            certificate = os.path.join(os.path.expanduser('~/.igor'), certificate)
        self.certificate = certificate
        self.noverify = not not noverify
        self.printmessages = printmessages or VERBOSE
        
    def get(self, item, variant=None, format=None, query=None):
        if format == None:
            format = 'application/xml'
        return self._action("GET", item, variant, format=format, query=query)
        
    def delete(self, item, variant=None, format=None, query=None):
        if variant == None:
            variant = "ref"
        if format == None:
            format = "text/plain"
        return self._action("DELETE", item, variant, format=format, query=query)
        
    def put(self, item, data, datatype, variant=None, format=None, query=None):
        if format == None:
            format = 'text/plain'
        return self._action("PUT", item, variant, format=format, data=data, datatype=datatype, query=query)
        
    def post(self, item, data, datatype, variant=None, format=None, query=None):
        if format == None:
            format = 'text/plain'
        return self._action("POST", item, variant, format, data=data, datatype=datatype)
        
    def _action(self, method, item, variant, format=None, data=None, datatype=None, query=None):
        # Convert to unicode for Python 2
        try:
            item = unicode(item)
        except NameError:
            pass
        url = urllib.parse.urljoin(self.url, item)
        if query is None:
            query = {}
        else:
            query = dict(query)
        if variant:
            query['.VARIANT'] = variant
        if self.access_token:
            query['access_token'] = self.access_token
        if query:
            assert not '?' in url
            url = url + '?' + urllib.parse.urlencode(query)
        headers = {}
        if format:
            headers['Accept'] = format
        if datatype:
            headers['Content-Type'] = datatype
        if self.bearer_token and self.credentials:
            raise IgorError("both bearer token and credentials specified")
        if self.bearer_token:
            headers['Authorization'] = 'Bearer %s' % self.bearer_token
        if self.credentials:
            headers['Authorization'] = 'Basic %s' % base64.b64encode(self.credentials.encode('utf-8'))
        if VERBOSE:
            if self.certificate or self.noverify:
                print('certificate=%s, noverify=%s' % (repr(self.certificate), repr(self.noverify)))
        kwargs = {}
        if self.noverify:
            kwargs['verify'] = False
        elif self.certificate:
            kwargs['verify'] = self.certificate
        if VERBOSE:
            print(">>> GET", url, file=sys.stderr)
            print("... Headers", headers, file=sys.stderr)
            if data:
                print("... Data", repr(data), file=sys.stderr)
        try:
            r = requests.request(method, url, headers=headers, data=data, **kwargs)
            # reply, content
        except socket.error as e:
            if e.args[1:]:
                argstr = e.args[1]
            else:
                e = repr(e)
            raise IgorError("%s: %s" % (url, argstr))
        except socket.gaierror:
            raise IgorError("%s: unknown host" %  url)
        except requests.exceptions.RequestException as e:
            raise IgorError(*e.args)
        except socket.timeout:
            raise IgorError("%s: timeout during connect" % url)
        if VERBOSE:
            print("<<< Headers", r.headers, file=sys.stderr)
            print("...", r.text, file=sys.stderr)
        if r.status_code != 200:
            msg = "Error %s for %s" % (r.status_code, url)
            if self.printmessages:
                contentLines = r.text.splitlines()
                if len(contentLines) > 1:
                    print(sys.argv[0] + ': ' + msg, file=sys.stderr)
                    print(r.text, file=sys.stderr)
            raise IgorError(msg)
        rv = r.text
        if type(rv) != type(''):
            rv = rv.decode('utf-8')
        return rv
        
def main():
    global VERBOSE
    parser = argparse.ArgumentParser(description="Access Igor home automation service and other http databases")
    parser.add_argument("-u", "--url", help="Base URL of the server (default: %s, environment IGORSERVER_URL)" % CONFIG.get('igor', 'url'), default=CONFIG.get('igor', 'url'))
    parser.add_argument("-e", "--eval", action="store_true", help="Evaluate XPath expression in stead of retrieving variable (by changing /data to /evaluate in URL)")
    parser.add_argument("-v", "--variant", help="Variant of data to get (or put, post)")
    parser.add_argument("-M", "--mimetype", help="Get result as given mimetype")
    parser.add_argument("--text", dest="mimetype", action="store_const", const="text/plain", help="Get result as plain text")
    parser.add_argument("--json", dest="mimetype", action="store_const", const="application/json", help="Get result as JSON")
    parser.add_argument("--xml", dest="mimetype", action="store_const", const="application/xml", help="Get result as XML")
    parser.add_argument("--python", action="store_true", help="Get result as Python (converted from JSON)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print result (only for Python, currently)")
    parser.add_argument("--verbose", action="store_true", help="Print what is happening", default=CONFIG.get('igor', 'verbose'))
    parser.add_argument("--delete", action="store_true", help="Delete variable")
    parser.add_argument("--create", action="store_true", help="Create or clear a variable")
    parser.add_argument("--put", metavar="MIMETYPE", help="PUT data of type MIMETYPE, from --data or stdin")
    parser.add_argument("--post", metavar="MIMETYPE", help="POST data of type MIMETYPE, from --data or stdin")
    parser.add_argument("--data", metavar="DATA", help="POST or PUT DATA, in stead of reading from stdin")
    parser.add_argument("--checkdata", action="store_true", help="Check that data is valid XML or JSON")
    parser.add_argument("--checknonempty", action="store_true", help="Check that data is valid XML or JSON data, and fail silently on empty data")
    parser.add_argument("-0", "--allow-empty", action="store_true", help="Allow empty data from stdin")
    parser.add_argument("--bearer", metavar="TOKEN", help="Add Authorization: Bearer TOKEN header line", default=CONFIG.get('igor', 'bearer'))
    parser.add_argument("--access", metavar="TOKEN", help="Add access_token=TOKEN query argument", default=CONFIG.get('igor', 'access'))
    parser.add_argument("--credentials", metavar="USER:PASS", help="Add Authorization: Basic header line with given credentials", default=CONFIG.get('igor', 'credentials'))
    parser.add_argument("--noverify", action='store_true', help="Disable verification of https signatures", default=CONFIG.get('igor', 'noverify'))
    parser.add_argument("--certificate", metavar='CERTFILE', help="Verify https certificates from given file", default=CONFIG.get('igor', 'certificate'))
    
    parser.add_argument("var", help="Variable to retrieve")
    args = parser.parse_args()
    VERBOSE=args.verbose
    
    url = args.url
    if args.eval:
        url = url.replace("/data", "/evaluate")
    server = IgorServer(url, bearer_token=args.bearer, access_token=args.access, credentials=args.credentials, noverify=args.noverify, certificate=args.certificate)
    if args.python:
        args.mimetype = 'application/json'
    try:
        if args.delete:
            result = server.delete(args.var)
        elif args.create:
            result = server.put(args.var, '{}', 'application/json', variant=args.variant, format=args.mimetype)
        elif args.put:
            data = args.data
            if data is None:
                data = sys.stdin.read()
            if args.checkdata or args.checknonempty:
                # Check that data is valid JSON or XML.
                # If no data is read at all only exit with nonzero status, assume the previous
                # part of the pipeline has already issues an error.
                if not data and args.checknonempty:
                    sys.exit(1)
                if args.put == 'application/json':
                    try:
                        decodedData = json.loads(data)
                        data = json.dumps(decodedData)
                    except ValueError:
                        print("%s: no valid JSON data read from stdin" % sys.argv[0], file=sys.stderr)
                        print(data, file=sys.stderr)
                        sys.exit(1)
                elif args.put == 'application/xml':
                    try:
                        decodedData = xml.etree.ElementTree.fromstring(data)
                    except xml.etree.ElementTree.ParseError:
                        print("%s: no valid XML data read from stdin" % sys.argv[0], file=sys.stderr)
                        print(data, file=sys.stderr)
                        sys.exit(1)
                elif args.checkdata:
                    print("%s: --checkdata only allowed for JSON and XML data", file=sys.stderr)
                    sys.exit(1)
            elif not data and not args.allow_empty:
                print('%s: no data read from stdin' % sys.argv[0], file=sys.stderr)
                sys.exit(1)
            result = server.put(args.var, data, args.put, variant=args.variant, format=args.mimetype)
        elif args.post:
            data = args.data
            if not data:
                data = sys.stdin.read()
            result = server.post(args.var, data, args.post, variant=args.variant, format=args.mimetype)
        else:
            result = server.get(args.var, variant=args.variant, format=args.mimetype)
        if args.python:
            result = json.loads(result)
            if args.pretty:
                pp = pprint.PrettyPrinter()
                result = pp.pformat(result)
            else:
                result = repr(result)
        print(result.strip())
    except IgorError as e:
        print("%s: %s" % (sys.argv[0], e.args[0]), file=sys.stderr)
    
if __name__ == '__main__':
    main()
    
    
