import re
import urllib

INTERPOLATION=re.compile(r'\{[^}]+\}')

class Trigger:
    """Object to implement calling methods on URLs whenever some XPath changes."""
    
    def __init__(self, hoster, element): # , url, method=None, data=None, mimetype=None, condition=None):
        self.hoster = hoster
        self.element = element
        tag, content = self.hoster.database.tagAndDictFromElement(self.element)
        assert tag == 'trigger'
        assert 'xpath' in content
        assert 'url' in content
        xpaths = content['xpath']
        if type(xpaths) != type([]):
            xpaths = [xpaths]
        self.xpaths = xpaths
        self.url = content['url']
        self.condition = content.get('condition')
        self.multiple = content.get('multiple')
        self.method = content.get('method')
        self.data = content.get('data')
        self.mimetype = content.get('mimetype', 'text/plain')
        self.install()
        
    def delete(self):
        self.uninstall()
        self.hoster = None
        
    def install(self):
        for xpath in self.xpaths:
            self.hoster.database.registerCallback(self.callback, xpath)
        
    def uninstall(self):
        self.hoster.database.unregisterCallback(self.callback)
        
    def callback(self, *nodelist):
        if not self.hoster:
            print 'ERROR: Trigger.callback called without hoster:', self
            return
        for node in nodelist:
            if self.condition:
                shouldRun = self.hoster.database.getValue(self.condition, node)
                if not shouldRun:
                    continue
            url = self._evaluate(self.url, node, True)
            data = self._evaluate(self.data, node, False)
            tocall = dict(method=self.method, url=url)
            if data:
                tocall['data'] = data
            tocall['mimetype'] = self.mimetype
            # xxxjack can add things like credentials, etc
            self.hoster.scheduleCallback(tocall)
            if not self.multiple:
                break
        
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
        assert node.tagName == 'triggers'
        # Remove old triggers first
        for old in self.triggers:
            old.delete()
        self.triggers = []
        # Now create new triggers
        child = node.firstChild
        while child:
            if child.nodeType == child.ELEMENT_NODE and child.tagName == 'trigger':
                t = Trigger(self, child)
                self.triggers.append(t)
            child = child.nextSibling
            
