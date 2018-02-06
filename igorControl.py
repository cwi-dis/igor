#!/usr/bin/env python
import sys
import argparse
import igorVar
import httplib2
import traceback

def main():
    parser = argparse.ArgumentParser(description="Control Igor home automation service")
    parser.add_argument("-u", "--url", help="Base URL of the server (default: %s, environment IGORSERVER_URL)" % igorVar.CONFIG.get('igor', 'url'), default=igorVar.CONFIG.get('igor', 'url'))
    parser.add_argument("--verbose", action="store_true", help="Print what is happening", default=igorVar.CONFIG.get('igor', 'verbose'))
    parser.add_argument("--bearer", metavar="TOKEN", help="Add Authorization: Bearer TOKEN header line", default=igorVar.CONFIG.get('igor', 'bearer'))
    parser.add_argument("--access", metavar="TOKEN", help="Add access_token=TOKEN query argument", default=igorVar.CONFIG.get('igor', 'access'))
    parser.add_argument("--credentials", metavar="USER:PASS", help="Add Authorization: Basic header line with given credentials", default=igorVar.CONFIG.get('igor', 'credentials'))
    parser.add_argument("--noverify", action='store_true', help="Disable verification of https signatures", default=igorVar.CONFIG.get('igor', 'noverify'))
    parser.add_argument("--certificate", metavar='CERTFILE', help="Verify https certificates from given file", default=igorVar.CONFIG.get('igor', 'certificate'))
    parser.add_argument("action", help="Action to perform: help, save, stop, restart, command, ...")
    
    args = parser.parse_args()
    igorVar.VERBOSE = args.verbose
    server = igorVar.IgorServer(args.url, bearer_token=args.bearer, access_token=args.access, credentials=args.credentials, noverify=args.noverify, certificate=args.certificate)
    try:
        result = server.get("/internal/%s" % args.action)
    except httplib2.HttpLib2Error as e:
        print >> sys.stderr, "%s: %s" % (sys.argv[0], traceback.format_exception_only(type(e), e.message)[0].strip())
        sys.exit(1)
    sys.stdout.write(result)
    
if __name__ == '__main__':
    main()
    
