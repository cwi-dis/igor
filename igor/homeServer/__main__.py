import webApp
import xmlDatabase
import triggers
import periodic
import callUrl
import os

DATADIR=os.path.dirname(__file__)

class HomeServer:
	def __init__(self):
		#
		# Create the database, and tell the web application about it
		#
		self.app = webApp.app
		self.database = xmlDatabase.DBImpl(os.path.join(DATADIR, 'data', 'database.xml'))
		webApp.DATABASE = self.database	# Have to set in a module-global variable, to be fixed some time...
	
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
	
	def run(self):
		self.app.run()
		
	def updateTriggers(self):
		"""Create any triggers that are defined in the database"""
		startupTriggers = self.database.getElements('triggers')
		if len(startupTriggers):
			if len(startupTriggers) > 1:
				raise web.HTTPError('401 only one <triggerers> element allowed')
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
	
def main():
	homeServer = HomeServer()
	homeServer.run()
	
main()

	
