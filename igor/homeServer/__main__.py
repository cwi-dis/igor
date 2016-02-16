import webApp
import xmlDatabase
import triggers
import periodic
import sseListener
import callUrl
import os
import argparse
import sys
reload(sys)
sys.setdefaultencoding('utf8')

DATADIR=os.path.dirname(__file__)

class HomeServer:
	def __init__(self, datadir, port=8080):
		#
		# Create the database, and tell the web application about it
		#
		self.port = port
		self.app = webApp.app
		self.database = xmlDatabase.DBImpl(os.path.join(datadir, 'database.xml'))
		webApp.DATABASE = self.database # Have to set in a module-global variable, to be fixed some time...
		webApp.SCRIPTDIR = os.path.join(datadir, 'scripts')
		webApp.PLUGINDIR = os.path.join(datadir, 'plugins')
	
		#
		# Create and start the asynchronous URL accessor
		#
		self.urlCaller = callUrl.URLCaller(self.app)
		self.urlCaller.start()
		
		#
		# Startup other components
		#
		self.triggerHandler = None
		self.updateTriggers()
		self.periodicHandler = None
		self.updatePeriodics()
		self.eventSources = None
		self.updateEventSources()
	
	def run(self):
		print 'xxxjack run app'
		self.app.run(port=self.port)
		
	def updateTriggers(self):
		"""Create any triggers that are defined in the database"""
		startupTriggers = self.database.getElements('triggers')
		if len(startupTriggers):
			if len(startupTriggers) > 1:
				raise web.HTTPError('401 only one <triggers> element allowed')
			if not self.triggerHandler:
				self.triggerHandler = triggers.TriggerCollection(self.database, self.urlCaller.callURL)
			self.triggerHandler.updateTriggers(startupTriggers[0])
		elif self.triggerHandler:
			self.triggerHandler.updateTriggers([])

	def updatePeriodics(self):
		"""Create any periodic event handlers defined in the database"""
		startupPeriodics = self.database.getElements('periodics')
		if len(startupPeriodics):
			if len(startupPeriodics) > 1:
				raise web.HTTPError('401 only one <periodics> element allowed')
			if not self.periodicHandler:
				self.periodicHandler = periodic.PeriodicCollection(self.database, self.urlCaller.callURL)
			self.periodicHandler.updatePeriodics(startupPeriodics[0])
		elif self.periodicHandler:
			self.periodicHandler.updatePeriodics([])

	def updateEventSources(self):
		"""Create any SSE event sources that are defined in the database"""
		eventSources = self.database.getElements('eventSources')
		if len(eventSources):
			if len(eventSources) > 1:
				raise web.HTTPError('401 only one <eventSources> element allowed')
			if not self.eventSources:
				self.eventSources = sseListener.EventSourceCollection(self.database, self.urlCaller.callURL)
			self.eventSources.updateEventSources(eventSources[0])
		elif self.eventSources:
			self.eventSources.updateEventSources([])

	
def main():
	DEFAULTDIR="homeServerDatabase"
	parser = argparse.ArgumentParser(description="Run the home automation server")
	parser.add_argument("-d", "--database", metavar="DIR", help="Database and scripts are stored in DIR (default: %s)" % DEFAULTDIR)
	parser.add_argument("-p", "--port", metavar="PORT", type=int, help="Port to serve on (default: 8080)", default=8080)
	args = parser.parse_args()
	datadir = args.database
	if not datadir:
		datadir = os.path.join(os.getcwd(), "homeServerDatabase")
		if not os.path.exists(datadir):
			datadir = os.path.join(os.path.dirname(__file__), "homeServerDatabase")
		if not os.path.exists(datadir):
			print 'Database not found:', datadir
			sys.exit(1)
	print 'xxxjack datadir is', datadir
	homeServer = HomeServer(datadir, args.port)
	homeServer.run()
	
main()

	
