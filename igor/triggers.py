import re
import urllib

INTERPOLATION=re.compile(r'\{[^}]\}')

class Trigger:
	"""Object to implement calling methods on URLs whenever some XPath changes."""
	
	def __init__(self, hoster, trigger, url, method="GET", data=None):
		self.hoster = hoster
		self.trigger = trigger
		self.url = url
		self.method = method
		self.data = data
		self.install()
		
	def delete(self):
		self.uninstall()
		self.hoster = None
		
	def install(self):
		self.hoster.registerCallback(self.callback, self.trigger)
		
	def uninstall(self):
		self.hoster.unregisterCallback(self.callback)
		
	def callback(self, node):
		url = self._evaluate(self.url, node, True)
		data = self._evaluate(self.data, node, False)
		self._scheduleCallback(url, data)
		
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
			replacement = self.hoster.getValue(expression, node)
			if replacement is None: replacement = ''
			replacement = str(replacement)
			if urlencode:
				replacement = urllib.quote_plus(replacement)
			newtext = newtext + text[:match.start()] + replacement
			text = text[match.end():]
		return newtext
		
	def _scheduleCallback(self, url, data):
		print 'XXXJACK should be calling %s on %s with %s' % (self.method, url, data)
		
class TriggerCollection:
	def __init__(self, database):
		self.triggers = []
		self.database = database
		
	def updateTriggers(self, node):
		tag, content = self.database.tagAndDictFromElement(node)
		assert tag == 'triggers'
		for old in self.triggers:
			old.delete()
		self.triggers = []
		newTriggers = self.triggers.get('trigger', [])
		assert type(newTriggers) == type([])
		for new in newTriggers:
			assert type(new) == type({})
			assert 'trigger' in new
			assert 'url' in new
			trigger = new['trigger']
			url = new['url']
			method = new.get('method')
			data = new.get('data')
			t = Trigger(self.database, trigger, url, method, data)
			self.triggers.append(t)
			
