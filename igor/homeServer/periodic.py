import re
import urllib
import time
import threading
import Queue

INTERPOLATION=re.compile(r'\{[^}]\}')

class Periodic:
	"""Object to implement calling methods on URLs whenever some XPath changes."""
	
	def __init__(self, hoster, interval, url, method=None, data=None):
		self.hoster = hoster
		self.interval = interval
		self.url = url
		self.method = method
		self.data = data
		
	def callback(self, node=None):
		url = self._evaluate(self.url, node, True)
		data = self._evaluate(self.data, node, False)
		tocall = dict(method=self.method, url=url)
		if data:
			tocall['data'] = data
		# xxxjack can add things like mimetype, credentials, etc
		self.hoster.scheduleCallback(tocall)
		return time.time() + self.interval
		
	def _evaluate(self, text, node, urlencode):
		if not text: return text
		newtext = ''
		while True:
			match = INTERPOLATION.search(text)
			if not match:
				newtext += text
				break
			expression = text[match.start():match.end()]
			assert expression[0] == '{'
			assert expression[-1] == '}'
			expression = expression[1:-1]
			replacement = self.hoster.database.getValue(expression, node)
			if replacement is None: replacement = ''
			replacement = str(replacement)
			if urlencode:
				replacement = urllib.quote_plus(replacement)
			newtext = newtext + text[:match.start()] + replacement
			text = text[match.end():]
		return newtext
				
class PeriodicCollection(threading.Thread):
	def __init__(self, database, scheduleCallback):
		threading.Thread.__init__(self)
		self.daemon = True
		self.periodicQueue = Queue.PriorityQueue()
		self.restarting = threading.Event()
		self.database = database
		self.scheduleCallback = scheduleCallback
		self.start()
		
	def run(self):
		while True:
			nextTime, nextTask = self.periodicQueue.get()
			timeToWait = nextTime-time.time()
			if self.restarting.wait(timeToWait):
				# The queue was cleared.
				self.restarting.clear()
				print 'xxxjack periodics restarting'
				continue
			if not nextTask: continue
			nextTime = nextTask.callback()
			self.periodicQueue.put((nextTime, nextTask))
		
	def updatePeriodics(self, node):
		tag, content = self.database.tagAndDictFromElement(node)
		assert tag == 'periodics'
		# Clear out old queue
		while not self.periodicQueue.empty():
			self.periodicQueue.get()
		# Signal the waiter thread
		self.restarting.set()
		self.periodicQueue.put((1, None))
		self.periodics = []
		newPeriodics = content.get('periodic', [])
		assert type(newPeriodics) == type([])
		for new in newPeriodics:
			assert type(new) == type({})
			assert 'interval' in new
			assert 'url' in new
			interval = new['interval']
			url = new['url']
			method = new.get('method')
			data = new.get('data')
			task = Periodic(self, interval, url, method, data)
			print 'xxxjack new periodic', task, 'for', url, 'interval', interval
			self.periodicQueue.put((time.time(), task))
			
