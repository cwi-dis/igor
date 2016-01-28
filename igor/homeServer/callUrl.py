
class URLCaller:
	def __init__(self, app):
		self.app = app

	def start(self):
		pass
		
	def callURL(self, method, url, data):
		print 'xxxjack should call %s on %s with %s' % (method, url, data)
