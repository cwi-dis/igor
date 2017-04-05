#!/usr/bin/env python
import sys
import argparse
import igorVar
import httplib2
import traceback


def main():
    parser = argparse.ArgumentParser(description="Control Igor home automation service")
    parser.add_argument("-u", "--url", help="Base URL of the server (default: %s, environment IGORSERVER_URL)" % igorVar.DEFAULT_URL, default=igorVar.DEFAULT_URL)
    parser.add_argument("--verbose", action="store_true", help="Print what is happening")
    parser.add_argument("--bearer", metavar="TOKEN", help="Add Authorization: Bearer TOKEN header line")
    parser.add_argument("--access", metavar="TOKEN", help="Add access_token=TOKEN query argument")
    parser.add_argument("action", help="Action to perform: help, save, stop, restart, command, ...")
    
    args = parser.parse_args()
    igorVar.VERBOSE = args.verbose
    server = igorVar.IgorServer(args.url, bearer_token=args.bearer, access_token=args.access)
    try:
        result = server.get("/internal/%s" % args.action)
    except httplib2.HttpLib2Error as e:
        print >> sys.stderr, "%s: %s" % (sys.argv[0], traceback.format_exception_only(type(e), e.message)[0].strip())
        sys.exit(1)
    sys.stdout.write(result)
    
if __name__ == '__main__':
    main()
    
