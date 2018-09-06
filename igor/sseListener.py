from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import threading
import requests
import queue
import urllib.parse
import time
import sys

DEBUG=False

class SSEListener(threading.Thread):
    def __init__(self, url, method='GET'):
        threading.Thread.__init__(self)
        self.daemon = True
        self.conn = None
        self.url = url
        self.method = method
        
        self.eventType = ''
        self.eventData = ''
        self.eventID = ''
        self.alive = True

    def openConnection(self):
        assert not self.conn
        self.conn = requests.request(self.method, self.url, stream=True)
        if DEBUG: print('opened connection to %s, redirected to %s' % (self.url, self.conn.url))
        
    def terminate(self):
        self.alive = False
        self.conn.close()
        
    def stop(self):
        self.terminate()
        self.join()
        
    def run(self):
        while self.alive:
            if not self.conn:
                self.openConnection()
                if not self.conn:
                    self.log("999 Failed to upen URL, sleeping")
                    time.sleep(60)
                    continue
            assert self.conn
            line = self.conn.raw.readline()
            if DEBUG: print('Got %s' % repr(line))
            if not line:
                # connection closed, re-open
                self.conn = None
                continue
            line = line.strip()
            if not line:
                # Empty line. Dispatch collected event
                if not self.eventData:
                    if DEBUG: print('no event data, skip dispatch')
                    self.eventType = ''
                    continue
                assert self.eventData[-1] == '\n'
                self.eventData = self.eventData[:-1]
                if not self.eventType:
                    self.eventType = 'message'
                if DEBUG: print('dispatching %s %s' % (repr(self.eventType), repr(self.eventData)))
                self.dispatch(self.eventType, self.eventData, self.eventID, self.conn.url)
                self.eventType = ''
                self.eventData = ''
                continue
                
            colonIndex = line.find(':')
            if colonIndex == 0:
                # Comment line. Skip.
                continue
            # Parse into fieldname and field value
            if colonIndex < 0:
                fieldName = line
                fieldValue = ''
            else:
                fieldName = line[:colonIndex]
                fieldValue = line[colonIndex+1:]
                if fieldValue and fieldValue[0] == ' ':
                    fieldValue = fieldValue[1:]
            # Remember
            if DEBUG: print('remember %s %s' % (repr(fieldName), repr(fieldValue)))
            if fieldName == 'event':
                self.eventType = fieldValue
            elif fieldName == 'data':
                self.eventData += fieldValue + '\n'
            elif fieldName == 'id':
                self.eventID = fieldValue
                
    def dispatch(self, eventType, data, origin, lastEventId):
        print('Event %s data %s' % (repr(eventType), repr(data)))

    def log(self, message):
        pass
        
class EventSource(SSEListener):
    def __init__(self, collection, srcUrl, dstUrl, srcMethod, dstMethod, mimetype, event):
        SSEListener.__init__(self, srcUrl, srcMethod)
        self.collection = collection
        self.dstUrl = dstUrl
        self.dstMethod = dstMethod
        self.mimetype = mimetype
        self.event = event
        
    def dispatch(self, eventType, data, origin, lastEventId):
        if self.event and eventType != self.event:
            return
        tocall = dict(method=self.dstMethod, url=self.dstUrl, mimetype=self.mimetype, data=data)
        self.collection.scheduleCallback(tocall)

    def log(self, message):
        datetime = time.strftime('%d/%b/%Y %H:%M:%S')
        print('- - - [%s] "- %s %s" - %s' % (datetime, self.method, self.url, message), file=sys.stderr)
    
class EventSourceCollection(object):
    def __init__(self, igor):
        self.igor = igor
        self.eventSources = []
        self.scheduleCallback = self.igor.urlCaller.callURL
        
    def dump(self):
        return ''
        
    def updateEventSources(self, node):
        tag, content = self.igor.database.tagAndDictFromElement(node)
        assert tag == 'eventSources'
        for old in self.eventSources:
            old.delete()
        self.eventSources = []
        newEventSources = content.get('eventSource', [])
        if type(newEventSources) == type({}):
            newEventSources = [newEventSources]
        assert type(newEventSources) == type([])
        for new in newEventSources:
            assert type(new) == type({})
            assert 'src' in new
            assert 'dst' in new
            src = new['src']
            dst = new['dst']
            srcMethod = new.get('srcMethod', 'GET')
            dstMethod = new.get('dstMethod', 'PUT')
            mimetype = new.get('mimetype', 'application/json')
            event = new.get('event')
            t = EventSource(self, src, dst, srcMethod, dstMethod, mimetype, event)
            t.start()
            self.eventSources.append(t)
            
    def stop(self):
        for es in self.eventSources:
            es.stop()

if __name__ == '__main__':
    s = SSEListener(sys.argv[1])
    s.start()
    time.sleep(99999)
    
