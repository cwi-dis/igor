import threading
import requests
import Queue
import urlparse
import time
import sys

DEBUG=False

class SSEListener(threading.Thread):
	def __init__(self, url, method='GET'):
		threading.Thread.__init__(self)
		self.daemon = True
		self.queue = Queue.Queue()
		self.conn = None
		self.url = url
		self.method = method
		
		self.eventType = ''
		self.eventData = ''
		self.eventID = ''

	def openConnection(self):
		assert not self.conn
		self.conn = requests.request(self.method, self.url, stream=True)
		if DEBUG: print 'opened connection to %s, redirected to %s' % (self.url, self.conn.url)
		
	def run(self):
		while True:
			if not self.conn:
				self.openConnection()
				if not self.conn:
					datetime = time.strftime('%d/%b/%Y %H:%M:%S')
					resultStatus = "999 Failed to upen URL"
					print '- - - [%s] "- %s %s" - %s' % (datetime, self.method, self.url, resultStatus)
					time.sleep(60)
					continue
			assert self.conn
			line = self.conn.raw.readline()
			if DEBUG: print 'Got %s' % repr(line)
			if not line:
				# connection closed, re-open
				self.conn = None
				continue
			line = line.strip()
			if not line:
				# Empty line. Dispatch collected event
				if not self.eventData:
					if DEBUG: print 'no event data, skip dispatch'
					self.eventType = ''
					continue
				assert self.eventData[-1] == '\n'
				self.eventData = self.eventData[:-1]
				if not self.eventType:
					self.eventType = 'message'
				if DEBUG: print 'dispatching %s %s' % (repr(self.eventType), repr(self.eventData))
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
			if DEBUG: print 'remember %s %s' % (repr(fieldName), repr(fieldValue))
			if fieldName == 'event':
				self.eventType = fieldValue
			elif fieldName == 'data':
				self.eventData += fieldValue + '\n'
			elif fieldName == 'id':
				self.eventID = fieldValue
				
	def dispatch(self, eventType, data, origin, lastEventId):
		print 'Event %s data %s' % (repr(eventType), repr(data))

if __name__ == '__main__':
	s = SSEListener(sys.argv[1])
	s.start()
	while True:
		time.sleep(10)
	
