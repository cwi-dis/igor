#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
# Enable coverage if installed and enabled through COVERAGE_PROCESS_START environment var
try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass
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
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

class IgorError(EnvironmentError):
    """Exception raised by this module when an error occurs"""
    pass

VERBOSE=False

class IgorServer(object):
    """Main object used to access an Igor server.
    
    The object is instantiated with parameters that specify how to contact Igor. After that it provides
    an interface similar to ``requests`` to allow REST operations on the Igor database.

    Arguments:
        url (str): URL of Igor, including the /data/ bit. For example ``https://igor.local:9333/data/``.
        bearer_token (str): An Igor external capability that has been supplied to your program and that governs which access rights your program has.
            Passed to Igor in the http ``Authorization: Bearer`` header.
        access_token (str): An alternative (and possibly less safe) way to pass an external capability to Igor, through an ``access_token`` query parameter in the URL.
        credentials (str): A *username:password* string used to authenticate your program to Igor and thereby govern which access rights you have. Passed to
            Igor in the http ``Authorization: Basic`` header.
        certificate (str): If the certificate of the Igor to contact is not trusted system-wide you can supply it here.
        noverify (bool): If you want to use https but bypass certificate verification you can pass ``True`` here.
        printmessages (bool): Be a bit more verbose (on stderr).
    """

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
        """Get a value (or values) from the database.
        
        Relative *item* names are relative to the toplevel ``/data`` element in the
        database. Absolute names are also allowed (so ``/data/environment`` is equivalent
        to ``environment``).
        
        Access to non-database portions of the REST API is allowed, so
        getting ``/action/save`` will have the side-effect of saving the database.
        
        Full XPath syntax is allowed, so something like ``actions/action[name='save']``
        will retrieve the definition of the *save* action. For XPath expressions
        matching multiple elements you must specify *variant='multi'*.
        
        Arguments:
            item (str): The XPath expression defining the value(s) to get.
            variant (str): An optional modifier to specify which data you want returned:
            
                - ``multi`` allows the query to match multiple elements and return all of them (otherwise this is an error)
                - ``raw`` also returns attributes and access-control information (for XML only)
                - ``multiraw`` combines those two
                - ``ref`` returns an XPath reference in stead of the value(s) found
                
            format (str): The mimetype you want returned. Supported are:
            
                - ``text/plain`` plaintext without any structuring information
                - ``application/xml`` an XML string (default)
                - ``application/json`` a JSON string
                
            query (dict): An optional http query to pass in the request. Useful mainly
                when accessing non-database entrypoints in Igor, such as ``/action`` or
                ``/plugin`` entries.
                
        Returns:
            The value of the item, as a string in the format specified by *format*.
            
        Raises:
            IgorError: in case of both communication errors and http errors returned by Igor.
        """
        if format == None:
            format = 'application/xml'
        return self._action("GET", item, variant, format=format, query=query)
        
    def delete(self, item, variant=None, format=None, query=None):
        """Delete an item in the database.
        
        Arguments:
            item (str): the XPath expression defining the item to delete.
            variant (str): Same as for *get()* but not generally useful.
            format (str): Same as for *get()* but not generally useful.
            query (dict): Same as for *get()* but not generally useful.
            
        Returns:
            An empty string in case of success (or in case of the item not existing)
            
        Raises:
            IgorError: in case of both communication errors and http errors returned by Igor.
        """
        if variant == None:
            variant = "ref"
        if format == None:
            format = "text/plain"
        return self._action("DELETE", item, variant, format=format, query=query)
        
    def put(self, item, data, datatype, variant=None, format=None, query=None):
        """Replace or create an item in the database.
        
        If *item* refers to a non-existing location in the database the item is created,
        if the item already exists it is replaced. It is an error to refer to multiple
        existing items.
        
        Arguments:
            item (str): the XPath expression defining the item to delete.
            data (str): new value for the item.
            datatype (str): mimetype of the *data* argument:

                - ``text/plain`` plaintext without any structuring information (default)
                - ``application/xml`` an XML string
                - ``application/json`` a JSON string
            
            variant (str): Same as for *get()* but not generally useful.
            format (str): Same as for *get()* but not generally useful.
            query (dict): Same as for *get()* but not generally useful.
            
        Returns:
            The XPath of the element created (or modified).
            
        Raises:
            IgorError: in case of both communication errors and http errors returned by Igor.
        """
        if format == None:
            format = 'text/plain'
        return self._action("PUT", item, variant, format=format, data=data, datatype=datatype, query=query)
        
    def post(self, item, data, datatype, variant=None, format=None, query=None):
        """Create an item in the database.
        
        Even if *item* refers to an existing location in the database 
        a new item is created, after all items with the same name.
        
        Arguments:
            item (str): the XPath expression defining the item to delete.
            data (str): new value for the item.
            datatype (str): mimetype of the *data* argument:

                - ``text/plain`` plaintext without any structuring information (default)
                - ``application/xml`` an XML string
                - ``application/json`` a JSON string
            
            variant (str): Same as for *get()* but not generally useful.
            format (str): Same as for *get()* but not generally useful.
            query (dict): Same as for *get()* but not generally useful.
            
        Returns:
            The XPath of the element created.
            
        Raises:
            IgorError: in case of both communication errors and http errors returned by Igor.
        """
        if format == None:
            format = 'text/plain'
        return self._action("POST", item, variant, format, data=data, datatype=datatype)
        
    def _action(self, method, item, variant, format=None, data=None, datatype=None, query=None):
        """Low-level REST interface to the database, can be used to do GET, PUT, POST,
        DELETE and other calls under program control.
        
        Arguments:
            method (str): the REST method to call.
            item (str): the XPath expression defining the item to operate on.
            variant (str): Same as for *get()*.
            format (str): Same as for *get()*.
            data (str): new value for the item, same as for *put()*.
            datatype (str): mimetype of the *data* argument, same as for *put()*.
            query (dict): Same as for *get()*.
            
        Returns:
            The REST call result.
            
        Raises:
            IgorError: in case of both communication errors and http errors returned by Igor.
        """
        # Convert to unicode for Python 2
        try:
            item = unicode(item)
        except NameError:
            pass
        url = urllib.parse.urljoin(str(self.url), str(item))
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
            headers['Authorization'] = 'Basic %s' % base64.b64encode(self.credentials.encode('utf-8')).decode('ascii')
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
        if data != None:
            data = data.encode('utf-8')
        try:
            r = requests.request(method, url, headers=headers, data=data, **kwargs)
            # reply, content
        except socket.error as e:
            if e.args[1:]:
                argstr = e.args[1]
            else:
                argstr = repr(e)
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

def igorArgumentDefaults(configFile=None, config=None):
    if configFile:
        if not os.path.exists(configFile):
            print("%s: does not exist" % configFile, file=sys.stderr)
            sys.exit(1)
    else:
        configFile = os.path.expanduser('~/.igor/igor.cfg')
    if config == None:
        config = 'igor'
        
    defaultDefaults = dict(
            url="http://igor.local:9333/data",
            bearer='',
            access='',
            credentials='',
            certificate='',
            noverify='',
            verbose='',
            noSystemRootCertificates='',
        )
    c = configparser.ConfigParser(defaultDefaults)
    c.add_section(config)
    c.read(configFile)
    # Override from environment:
    for k, _ in c.items(config):
        envKey = 'IGORSERVER_' + k.upper()
        if envKey in os.environ:
            c.set(config, k, os.environ[envKey])
    try:
        rv =  dict(c[config])
    except AttributeError:
        # Python 2 ConfigParser doesn't have the dict-like interface
        rv = dict(c.items(config))
    return rv

def igorArgumentParser(description=None):
    """Return argument parser with common arguments for Igor and defaults already filled in.
    
    Used by Igor command line utilities and IgorServlet, and may be useful for other Python programs
    that communicate with Igor.
    """
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument("--configFile", metavar="FILE", help="Get default arguments from ini-style config FILE (default: ~/.igor/igor.cfg)")
    conf_parser.add_argument("--config", metavar="SECTION", help="Get default arguments from config file section [SECTION] (default: igor).")
    args, _ = conf_parser.parse_known_args()

    parser = argparse.ArgumentParser(
        parents=[conf_parser],
        description=description,
        epilog="Argument defaults can also be specified in environment variables like IGORSERVER_URL (for --url), etc."
        )
    parser.set_defaults(**igorArgumentDefaults(configFile=args.configFile, config=args.config))
    parser.add_argument("-u", "--url", help="Base URL of the server (default: %(default)s)")
    parser.add_argument("--verbose", action="store_true", help="Print what is happening")
    parser.add_argument("--bearer", metavar="TOKEN", help="Add Authorization: Bearer TOKEN header line")
    parser.add_argument("--access", metavar="TOKEN", help="Add access_token=TOKEN query argument")
    parser.add_argument("--credentials", metavar="USER:PASS", help="Add Authorization: Basic header line with given credentials")
    parser.add_argument("--noverify", action='store_true', help="Disable verification of https signatures")
    parser.add_argument("--certificate", metavar='CERTFILE', help="Verify https certificates from given file")
    parser.add_argument('--noSystemRootCertificates', action="store_true", help='Do not use system root certificates, use REQUESTS_CA_BUNDLE or what requests package has')
    return parser

def argumentParser():
    parser = igorArgumentParser(description="Access Igor home automation service and other http databases")

    parser.add_argument("-e", "--eval", action="store_true", help="Evaluate XPath expression in stead of retrieving variable (by changing /data to /evaluate in URL)")
    parser.add_argument("-v", "--variant", help="Variant of data to get (or put, post)")
    parser.add_argument("-M", "--mimetype", help="Get result as given mimetype")
    parser.add_argument("--text", dest="mimetype", action="store_const", const="text/plain", help="Get result as plain text")
    parser.add_argument("--json", dest="mimetype", action="store_const", const="application/json", help="Get result as JSON")
    parser.add_argument("--xml", dest="mimetype", action="store_const", const="application/xml", help="Get result as XML")
    parser.add_argument("--python", action="store_true", help="Get result as Python (converted from JSON)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print result (only for Python, currently)")
    parser.add_argument("--delete", action="store_true", help="Delete variable")
    parser.add_argument("--create", action="store_true", help="Create or clear a variable")
    parser.add_argument("--put", metavar="MIMETYPE", help="PUT data of type MIMETYPE, from --data or stdin")
    parser.add_argument("--post", metavar="MIMETYPE", help="POST data of type MIMETYPE, from --data or stdin")
    parser.add_argument("--data", metavar="DATA", help="POST or PUT DATA, in stead of reading from stdin")
    parser.add_argument("--checkdata", action="store_true", help="Check that data is valid XML or JSON")
    parser.add_argument("--checknonempty", action="store_true", help="Check that data is valid XML or JSON data, and fail silently on empty data")
    parser.add_argument("-0", "--allow-empty", action="store_true", help="Allow empty data from stdin")
    
    parser.add_argument("var", help="Variable to retrieve")
    return parser

def main():
    global VERBOSE
    parser = argumentParser()
    
    args = parser.parse_args()
    VERBOSE=args.verbose
    
    url = args.url
    if args.eval:
        url = url.replace("/data", "/evaluate")
    if not args.noSystemRootCertificates and not os.environ.get('REQUESTS_CA_BUNDLE', None):
        # The requests package uses its own set of certificates, ignoring the ones the user has added to the system
        # set. By default, override that behaviour.
        for cf in ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/certs/ca-certificates.crt"]:
            if os.path.exists(cf):
                os.putenv('REQUESTS_CA_BUNDLE', cf)
                os.environ['REQUESTS_CA_BUNDLE'] = cf
                break
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
    
    
