import re
import urllib

INTERPOLATION=re.compile(r'\{[^}]\}')

class Trigger:
	"""Object to implement calling methods on URLs whenever some XPath changes."""
	
	def __init__(self, hoster, trigger, url, method=None, data=None):
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
		self.hoster.database.registerCallback(self.callback, self.trigger)
		
	def uninstall(self):
		self.hoster.database.unregisterCallback(self.callback)
		
	def callback(self, node):
		url = self._evaluate(self.url, node, True)
		data = self._evaluate(self.data, node, False)
		self.hoster.scheduleCallback(self.method, url, data)
		
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
				
class TriggerCollection:
	def __init__(self, database, scheduleCallback):
		self.triggers = []
		self.database = database
		self.scheduleCallback = scheduleCallback
		
	def updateTriggers(self, node):
		tag, content = self.database.tagAndDictFromElement(node)
		print 'xxxjack content=', repr(content)
		assert tag == 'triggers'
		for old in self.triggers:
			old.delete()
		self.triggers = []
		newTriggers = content.get('trigger', [])
		print 'xxxjack newTriggers=', repr(newTriggers)
		assert type(newTriggers) == type([])
		for new in newTriggers:
			assert type(new) == type({})
			assert 'xpath' in new
			assert 'url' in new
			trigger = new['xpath']
			url = new['url']
			method = new.get('method')
			data = new.get('data')
			t = Trigger(self, trigger, url, method, data)
			self.triggers.append(t)
			
