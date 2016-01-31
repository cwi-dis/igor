import threading
import httplib2
import Queue
import urlparse
import time

class URLCaller(threading.Thread):
	def __init__(self, app):
		threading.Thread.__init__(self)
		self.daemon = True
		self.app = app
		self.queue = Queue.Queue()

	def run(self):
		while True:
			tocall = self.queue.get()
			method = tocall['method']
			url = tocall['url']
			data = tocall.get('data')
			# xxxjack should also have mimetype, credentials, etc
			if not method:
				method = 'GET'
			parsedUrl = urlparse.urlparse(url)
			if parsedUrl.scheme == '' and parsedUrl.netloc == '':
				# Local. Call the app directly.
				# xxxjack have to work out exceptions
				rep = self.app.request(url, method=method, data=data)
				result = rep.status
			else:
				# Remote.
				# xxxjack have to work out exceptions
				h = httplib2.Http()
				resp, content = h.request(url, method, body=data)
				result = "%s %s" % (resp.status, resp.reason)
			datetime = time.ctime()
			print '- - - %s "- %s %s" - %s' % (datetime, method, url, result)
				
		
	def callURL(self, tocall):
		self.queue.put(tocall)
