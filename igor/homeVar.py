#!/usr/bin/env python
import argparse
import urlparse
import urllib
import httplib2
import sys

DEFAULT_URL="http://framboos.local:8080/data/"
VERBOSE=False

class HomeServer:
	def __init__(self, url):
		self.url = url
		
	def get(self, item, variant=None, format=None):
		if format == None:
			format = 'application/xml'
		return self._action("GET", item, variant, format)
		
	def delete(self, item, variant=None, format=None):
		if variant == None:
			variant = "ref"
		if format == None:
			format = "text/plain"
		return self._action("DELETE", item, variant, format)
		
	def put(self, item, data, datatype, variant=None, format=None):
		if format == None:
			format = 'text/plain'
		return self._action("PUT", item, variant, format, data=data, datatype=datatype)
		
	def post(self, item, data, datatype, variant=None, format=None):
		if format == None:
			format = 'text/plain'
		return self._action("POST", item, variant, format, data=data, datatype=datatype)
		
	def _action(self, method, item, variant, format=None, data=None, datatype=None):
		url = urlparse.urljoin(self.url, item)
		if variant:
			query = urllib.urlencode({'.VARIANT':variant})
			assert not '?' in url
			url = url + '?' + query
		headers = {}
		if format:
			headers['Accept'] = format
		if datatype:
			headers['Content-Type'] = datatype
		h = httplib2.Http()
		if VERBOSE:
			print >>sys.stderr, ">>> GET", url
			print >>sys.stderr, "... Headers", headers
			if data:
				print >>sys.stderr, "... Data", repr(data)
		reply, content = h.request(url, method=method, headers=headers, body=data)
		if VERBOSE:
			print >>sys.stderr, "<<< Headers", reply
			print >>sys.stderr, "...", repr(content)
		if not 'status' in reply or reply['status'] != '200':
			print >>sys.stderr, "%s: Error %s for %s" % (sys.argv[0], reply['status'], url)
			print >>sys.stderr, content
			sys.exit(1)
		return content
		
def main():
	global VERBOSE
	parser = argparse.ArgumentParser(description="Access homeServer and other http databases")
	parser.add_argument("-u", "--url", help="Base URL of the server (default: %s)", default=DEFAULT_URL)
	parser.add_argument("-v", "--variant", help="Variant of data to get (or put, post)")
	parser.add_argument("-M", "--mimetype", help="Get result as given mimetype")
	parser.add_argument("--text", dest="mimetype", action="store_const", const="text/plain", help="Get result as plain text")
	parser.add_argument("--json", dest="mimetype", action="store_const", const="application/json", help="Get result as JSON")
	parser.add_argument("--xml", dest="mimetype", action="store_const", const="application/xml", help="Get result as XML")
	parser.add_argument("--verbose", action="store_true", help="Print what is happening")
	parser.add_argument("--delete", action="store_true", help="Delete variable")
	parser.add_argument("--create", action="store_true", help="Create or clear a variable")
	parser.add_argument("--put", metavar="MIMETYPE", help="PUT data of type MIMETYPE, from --data or stdin")
	parser.add_argument("--post", metavar="MIMETYPE", help="POST data of type MIMETYPE, from --data or stdin")
	parser.add_argument("--data", metavar="DATA", help="POST or PUT DATA, in stead of reading from stdin")
	parser.add_argument("-0", "--allow-empty", help="Allow empty data from stdin")
	parser.add_argument("var", help="Variable to retrieve")
	args = parser.parse_args()
	VERBOSE=args.verbose
	
	server = HomeServer(args.url)
	if args.delete:
		result = server.delete(args.var)
	elif args.create:
		result = server.put(args.var, '{}', 'application/json', variant=args.variant, format=args.mimetype)
	elif args.put:
		data = args.data
		if not data:
			data = sys.stdin.read()
			if not data and not args.allow_empty:
				print >>sys.stderr, '%s: no data read from stdin' % sys.argv[0]
				sys.exit(1)
		result = server.put(args.var, data, args.put, variant=args.variant, format=args.mimetype)
	elif args.post:
		data = args.data
		if not data:
			data = sys.stdin.read()
		result = server.post(args.var, data, args.post, variant=args.variant, format=args.mimetype)
	else:
		result = server.get(args.var, variant=args.variant, format=args.mimetype)
	print result.strip()
	
if __name__ == '__main__':
	main()
	
	
