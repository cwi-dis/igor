import threading
import httplib2
import Queue
import urlparse

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
			print 'xxxjack will call %s on %s with %s' % (method, url, data)
			parsedUrl = urlparse.urlparse(url)
			if parsedUrl.scheme == '' and parsedUrl.netloc == '':
				# Local. Call the app directly.
				# xxxjack have to work out exceptions
				self.app.request(url, method=method, data=data)
				# xxxjack add a log message?
			else:
				# Remote.
				# xxxjack have to work out exceptions
				h = httplib2.Http()
				resp, content = h.request(url, method, body=data)
				# xxxjack add a log message?
				
		
	def callURL(self, tocall):
		self.queue.put(tocall)
