import webApp
import xmlDatabase
import triggers
import periodic
import callUrl
import os

DATADIR=os.path.dirname(__file__)

def main():
	#
	# Create the database, and tell the web application about it
	#
	app = webApp.app
	database = xmlDatabase.DBImpl(os.path.join(DATADIR, 'data', 'database.xml'))
	webApp.DATABASE = database	# Have to set in a module-global variable, to be fixed some time...
	
	#
	# Create and start the asynchronous URL accessor
	#
	urlCaller = callUrl.URLCaller(app)
	urlCaller.start()
	
	#
	# Create any triggers that are already defined in the database
	#
	startupTriggers = database.getElements('triggers')
	if len(startupTriggers):
		assert len(startupTriggers) == 1
		triggerer = triggers.TriggerCollection(database, urlCaller.callURL)
		triggerer.updateTriggers(startupTriggers[0])
	del startupTriggers
	#
	# Create the manager for the periodic events
	#
	startupPeriodics = database.getElements('periodics')
	if len(startupPeriodics):
		assert len(startupPeriodics) == 1
		periodics = periodic.PeriodicCollection(database, urlCaller.callURL)
		periodics.updatePeriodics(startupPeriodics[0])
	del startupPeriodics
	#
	# Run the http server
	#
	app.run()
	
main()

	
