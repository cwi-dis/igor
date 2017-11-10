# Access control
from xmlDatabase import NAMESPACES
from webApp import myWebError
import xpath

class DummyAccessToken:
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self):
        pass

    def addToRequest(self, *args):
        pass
        
class AccessToken(DummyAccessToken):
    """An access token (or set of tokens) that can be carried by a request"""

    def __init__(self, content):
        self.content = content
        
    def addToRequest(self, *args):
        pass
        
class DummyAccessChecker:
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self):
        pass
        
    def allowed(self):
        return True
           
class AccessChecker(DummyAccessChecker):
    """An object that checks whether an operation (or request) has the right permission"""

    def __init__(self, content):
        self.content = content
        
    def allowed(self):
        return True

class Access:
    def __init__(self):
        pass
        
    def checkerForElement(self, element):
        nodelist = xpath.find("au:requires", element, namespaces=NAMESPACES)
        if not nodelist:
            return DummyAccessChecker()
        if len(nodelist) > 1:
            raise myWebError("500 action has multiple au:requires")
        requiresValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        return AccessChecker(requiresValue)
            
        
    def tokenForAction(self, element):
        nodelist = xpath.find("au:carries", element, namespaces=NAMESPACES)
        if not nodelist:
            return DummyAccessToken()
        if len(nodelist) > 1:
            raise myWebError("500 action has multiple au:carries")
        carriesValue = "".join(t.nodeValue for t in nodelist[0].childNodes if t.nodeType == t.TEXT_NODE)
        return AccessToken(carriesValue)
