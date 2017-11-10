import webApp
import xmlDatabase
import access
import actions
import sseListener
import callUrl
import os
import argparse
import besthostname
import time
import json
import web
import subprocess
import imp
import threading
import cProfile
import pstats
from _version import VERSION

import sys
reload(sys)
sys.setdefaultencoding('utf8')

#
# Helper for profileing multiple threads
# 
PROFILER_STATS = None
def enable_thread_profiling():
    '''Monkey-patch Thread.run to enable global profiling.

    Each thread creates a local profiler; statistics are pooled
    to the global stats object on run completion.'''
    global PROFILER_STATS
    import pstats
    PROFILER_STATS = None
    thread_run = threading.Thread.run

    def profile_run(self):
        print 'xxxjack profile_run'
        self._prof = cProfile.Profile()
        self._prof.enable()
        thread_run(self)
        self._prof.disable()

        if PROFILER_STATS is None:
            PROFILER_STATS = pstats.Stats(self._prof)
        else:
            PROFILER_STATS.add(self._prof)

    threading.Thread.run = profile_run
    print 'xxxjack inserted profiler'
    

class IgorServer:
    def __init__(self, datadir, port=9333, advertise=False, profile=False):
        #
        # Create the database, and tell the web application about it
        #
        self.profile = None
        if profile:
            enable_thread_profiling()
            self.profile = cProfile.Profile()
            self.profile.enable()
        self.port = port
        self.app = webApp.WEBAPP
        self.datadir = datadir
        self.database = xmlDatabase.DBImpl(os.path.join(self.datadir, 'database.xml'))
        webApp.DATABASE = self.database # Have to set in a module-global variable, to be fixed some time...
        webApp.SCRIPTDIR = os.path.join(datadir, 'scripts')
        webApp.PLUGINDIR = os.path.join(datadir, 'plugins')
        webApp.STATICDIR = os.path.join(datadir, 'static')
        webApp.COMMANDS = self
        
        #
        # Create the access control handler
        #
        self.access = None
        self.updateAccess()
        #
        # Create and start the asynchronous URL accessor
        #
        self.urlCaller = callUrl.URLCaller(self.app)
        self.urlCaller.start()
        
        #
        # Fill self data
        #        
        self.fillSelfData()
        #
        # Startup other components
        #
        self.actionHandler = None
        self.updateActions()
        self.eventSources = None
        self.updateEventSources()
        self.triggerHandler = None
        self.updateTriggers()
        #
        # Disable debug
        #
        web.config.debug = False
        #
        # Send start action to start any plugins
        #
        self.urlCaller.callURL(dict(method='GET', url='/action/start', token=self.access.tokenForIgor()))
        if advertise:
            self.advertise(port)
            
    def advertise(self, port):
        if sys.platform == 'darwin':
            cmd = ['dns-sd', '-R', 'igor', '_http._tcp', 'local', str(port)]
        elif sys.platform == 'linux2':
            cmd = ['avahi-publish', '-s', 'igor', '_http._tcp', str(port)]
        else:
            print >> sys.stderr, "Cannot do mdns-advertise on platform", sys.platform
            return
        try:
            self.advertiser = subprocess.Popen(cmd)
        except OSError:
            print >> sys.stderr, "advertisement command failed: %s" % (' '.join(cmd))
    
    
    def fillSelfData(self):
        """Put our details in the database"""
        hostName = besthostname.besthostname()
        url = 'http://%s:%d/data' % (hostName, self.port)
        data = dict(host=hostName, url=url, port=self.port, startTime=int(time.time()), version=VERSION)
        tocall = dict(method='PUT', url='/data/services/igor', mimetype='application/json', data=json.dumps(data), token=self.access.tokenForIgor())
        self.urlCaller.callURL(tocall)
        
    def run(self):
        self.app.run(port=self.port)
        
    def dump(self):
        rv = ''
        if self.urlCaller: rv += self.urlCaller.dump() + '\n'
        if self.actionHandler: rv += self.actionHandler.dump() + '\n'
        if self.eventSources: rv += self.eventSources.dump() + '\n'
        return rv
        
    def log(self):
        logfn = os.path.join(self.datadir, 'igor.log')
        if os.path.exists(logfn):
            return open(logfn).read()
        raise Web.HTTPError('404 Log file not available')
        
    def updateStatus(self, representing=None, success=None, resultData=None):
        """Update status field of some service/sensor/actuator after an action"""
        print 'xxxjack updateStatus(%s, %s, %s) not yet implemented' % (representing, success, resultData)
        
    def updateAccess(self):
        self.access = access.Access()
        
    def updateActions(self):
        """Create any (periodic) event handlers defined in the database"""
        startupActions = self.database.getElements('actions')
        if len(startupActions):
            if len(startupActions) > 1:
                raise web.HTTPError('401 only one <actions> element allowed')
            if not self.actionHandler:
                self.actionHandler = actions.ActionCollection(self.database, self.urlCaller.callURL, self.access)
            self.actionHandler.updateActions(startupActions[0])
        elif self.actionHandler:
            self.actionHandler.updateActions([])
        return 'OK'

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
        return 'OK'

    def updateTriggers(self):
        pass
        
    def runAction(self, actionname):
        if not self.actionHandler:
            raise web.notfound()
        nodes = self.database.getElements('actions/action[name="%s"]'%actionname)
        if not nodes:
            raise web.notfound()
        for node in nodes:
            self.actionHandler.triggerAction(node)
        return 'OK'
    
    def runTrigger(self, triggername):
        raise web.HTTPError("502 triggers not yet implemented")
        if not self.triggerHandler:
            raise web.notfound()
        triggerNodes = self.database.getElements('triggers/%s' % triggername)
        if not triggerNodes:
            raise web.notfound()
        if len(triggerNodes) > 1:
            raise web.HTTPError("502 multiple triggers %s in database" % triggername)
        triggerNode = triggerNodes[0]
        self.triggerHandler.triggerTrigger(triggerNode)
        
    def save(self):
        self.database.saveFile()
        return 'OK'
        
    def started(self):
        return "IgorServer started"
        
    def stop(self):
        global PROFILER_STATS
        if self.actionHandler:
            self.actionHandler.stop()
            self.actionHandler = None
        if self.eventSources:
            self.eventSources.stop()
            self.eventSources = None
        if self.triggerHandler:
            self.triggerHandler.stop()
            self.triggerHandler = None
        if self.urlCaller:
            self.urlCaller.stop()
            self.urlCaller = None
        self.save()
        if self.profile:
            self.profile.disable()
            if PROFILER_STATS is None:
                PROFILER_STATS = pstats.Stats(self.profile)
            else:
                PROFILER_STATS.add(self.profile)
            PROFILER_STATS.dump_stats("igor.profile")
        sys.exit(0)
        
    def restart(self):
        self.save()
        os.closerange(3, MAXFD)
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    def command(self):
        rv = ''
        if 'IGORSERVER_DIR' in os.environ:
            rv = rv + 'export IGORSERVER_DIR=' + repr(os.environ['IGORSERVER_DIR']) + '\n'
        if 'IGORSERVER_PORT' in os.environ:
            rv = rv + 'export IGORSERVER_PORT=%d\n' % int(os.environ['IGORSERVER_PORT'])
        rv = rv + 'exec %s' % repr(sys.executable)
        for a in sys.argv:
            rv += ' ' + repr(a)
        rv += '\n'
        return rv
        
    def help(self):
        rv = 'Internal igor commands:\n'
        rv += 'help - this help\n'
        rv += 'version - return version number\n'
        rv += 'save - Make sure database is saved to disk\n'
        rv += 'restart - Save and restart this Igor (may appear to fail even when executed correctly)\n'
        rv += 'stop - Save and stop this Igor (may appear to fail even when executed correctly)\n'
        rv += 'command - Show command line that started this Igor instance\n'
        rv += 'dump - Show internal run queue of this Igor instance\n'
        rv += 'log - Show httpd-style log file of this Igor instance\n'
        return rv
        
    def version(self):
        return VERSION + '\n'
    
def main():
    DEFAULTDIR=os.path.join(os.path.expanduser('~'), '.igor')
    if 'IGORSERVER_DIR' in os.environ:
        DEFAULTDIR = os.environ['IGORSERVER_DIR']
    DEFAULTPORT=9333
    if 'IGORSERVER_PORT' in os.environ:
        DEFAULTDIR = int(os.environ['IGORSERVER_PORT'])
        
    parser = argparse.ArgumentParser(description="Run the Igor home automation server")
    parser.add_argument("-d", "--database", metavar="DIR", help="Database and scripts are stored in DIR (default: %s, environment IGORSERVER_DIR)" % DEFAULTDIR, default=DEFAULTDIR)
    parser.add_argument("-p", "--port", metavar="PORT", type=int, help="Port to serve on (default: 9333, environment IGORSERVER_PORT)", default=DEFAULTPORT)
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--advertise", action="store_true", help="Advertise service through bonjour/zeroconf")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--profile", action="store_true", help="Enable Python profiler (debugging Igor only)")
    args = parser.parse_args()
    
    if args.version:
        print VERSION
        sys.exit(0)
    if args.debug:
        callUrl.DEBUG = True
        sseListener.DEBUG = True
        actions.DEBUG = True
        xmlDatabase.DEBUG = True
        webApp.DEBUG = True
    datadir = args.database
    try:
        igorServer = IgorServer(datadir, args.port, args.advertise, profile=args.profile)
    except IOError, arg:
        print >>sys.stderr, '%s: Cannot open database: %s' % (sys.argv[0], arg)
        print >>sys.stderr, '%s: Use --help option to see command line arguments' % sys.argv[0]
        sys.exit(1)
    igorServer.run()

#
# We need to hack the import lock. In case we get here via the easy_install igorServer script
# we are inside an __import__(), and we hold the lock. This means other threads cannot import
# and we hang once a web request comes in. We "work around" this by releasing the lock.
#    
hasImportLock = imp.lock_held()
if hasImportLock:
    imp.release_lock()
main()
if hasImportLock:
    imp.acquire_lock()
    

    
