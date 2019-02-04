#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals
# Enable coverage if installed and enabled through COVERAGE_PROCESS_START environment var
try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass
import sys
import os
import argparse
import igorVar
import traceback

def argumentParser():
    parser = igorVar.igorArgumentParser(description="Control Igor home automation service")
    parser.add_argument("action", help="Action to perform: help, save, stop, restart, command, ...")
    parser.add_argument("arguments", help="Arguments to the action", metavar="NAME=VALUE", nargs="*")
    return parser
    
def main():
    parser = argumentParser()    
    args = parser.parse_args()
    igorVar.VERBOSE = args.verbose
    query = {}
    for qstr in args.arguments:
        qname, qvalue = qstr.split('=')
        query[qname] = qvalue
    if not args.noSystemRootCertificates and not os.environ.get('REQUESTS_CA_BUNDLE', None):
        # The requests package uses its own set of certificates, ignoring the ones the user has added to the system
        # set. By default, override that behaviour.
        for cf in ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/certs/ca-certificates.crt"]:
            if os.path.exists(cf):
                os.putenv('REQUESTS_CA_BUNDLE', cf)
                os.environ['REQUESTS_CA_BUNDLE'] = cf
                break
    server = igorVar.IgorServer(args.url, bearer_token=args.bearer, access_token=args.access, credentials=args.credentials, noverify=args.noverify, certificate=args.certificate)
    try:
        result = server.get("/internal/%s" % args.action, query=query)
    except igorVar.IgorError as e:
        print("%s: %s" % (sys.argv[0], e.args[0]), file=sys.stderr)
        sys.exit(1)
    sys.stdout.write(result)
    
if __name__ == '__main__':
    main()
    
