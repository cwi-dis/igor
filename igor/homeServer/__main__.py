import webApp
import xmlDatabase
import triggers
import actions
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
        self.app = webApp.WEBAPP
        self.database = xmlDatabase.DBImpl(os.path.join(datadir, 'database.xml'))
        webApp.DATABASE = self.database # Have to set in a module-global variable, to be fixed some time...
        webApp.SCRIPTDIR = os.path.join(datadir, 'scripts')
        webApp.PLUGINDIR = os.path.join(datadir, 'plugins')
        webApp.COMMANDS = self
    
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
        self.actionHandler = None
        self.updateActions()
        self.eventSources = None
        self.updateEventSources()
    
    def run(self):
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

    def updateActions(self):
        """Create any (periodic) event handlers defined in the database"""
        startupActions = self.database.getElements('actions')
        if len(startupActions):
            if len(startupActions) > 1:
                raise web.HTTPError('401 only one <actions> element allowed')
            if not self.actionHandler:
                self.actionHandler = actions.ActionCollection(self.database, self.urlCaller.callURL)
            self.actionHandler.updateActions(startupActions[0])
        elif self.actionHandler:
            self.actionHandler.updateActions([])

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

    def runAction(self, actionname):
        if not self.actionHandler:
            raise web.notfound()
        nodes = self.database.getElements('actions/action[name="%s"]'%actionname)
        if not nodes:
            raise web.notfound()
        for node in nodes:
            self.actionHandler.triggerAction(node)
    
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
    homeServer = HomeServer(datadir, args.port)
    homeServer.run()
    
main()

    
