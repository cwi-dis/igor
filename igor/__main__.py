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
import shelve
import myLogger
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
    def __init__(self, datadir, port=9333, advertise=False, profile=False, nossl=False):
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
        
        shelveFilename = os.path.join(self.datadir, 'igorSessions')
        self.session = web.session.Session(self.app, web.session.ShelfStore(shelve.open(shelveFilename)))
        
        self.ssl = not nossl
        keyFile = os.path.join(self.datadir, 'igor.key')
        if self.ssl and not os.path.exists(keyFile):
            print 'Warning: Using http in stead of https: no private key file', keyFile
            self.ssl = False
        if self.ssl:
            self.privateKeyFile = keyFile
            self.certificateFile = os.path.join(self.datadir, 'igor.crt')
            import OpenSSL.crypto
            certificateData = open(self.certificateFile, 'rb').read()
            certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificateData)
            self.certificateFingerprint = certificate.digest("sha1")
        else:
            self.privateKeyFile = None
            self.certificateFile = None
            self.certificateFingerprint = None

        self.database = xmlDatabase.DBImpl(os.path.join(self.datadir, 'database.xml'))
        webApp.DATABASE = self.database # Have to set in a module-global variable, to be fixed some time...
        webApp.SCRIPTDIR = os.path.join(datadir, 'scripts')
        webApp.PLUGINDIR = os.path.join(datadir, 'plugins')
        webApp.STATICDIR = os.path.join(datadir, 'static')
        webApp.SESSION = self.session
        webApp.COMMANDS = self
        
        #
        # Create the access control handler
        #
        self.access = access.singleton
        self.access.setSession(self.session)
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
        protocol = 'http'
        if self.ssl:
            protocol = 'https'
        url = '%s://%s:%d/data' % (protocol, hostName, self.port)
        oldRebootCount = self.database.getValue('/data/services/igor/rebootCount', token=self.access.tokenForIgor())
        rebootCount = 0
        if oldRebootCount:
            try:
                rebootCount = int(oldRebootCount)+1
            except ValueError:
                pass
        data = dict(host=hostName, url=url, port=self.port, protocol=protocol, startTime=int(time.time()), version=VERSION, ticker=0, rebootCount=rebootCount)
        if self.certificateFingerprint:
            data['fingerprint'] = self.certificateFingerprint
        tocall = dict(method='PUT', url='/data/services/igor', mimetype='application/json', data=json.dumps(data), representing='igor/core', token=self.access.tokenForIgor())
        self.urlCaller.callURL(tocall)
        
    def run(self):
        if self.ssl:
            from web.wsgiserver import CherryPyWSGIServer
            CherryPyWSGIServer.ssl_certificate = self.certificateFile
            CherryPyWSGIServer.ssl_private_key = self.privateKeyFile
        self.app.run(port=self.port)
        
    def dump(self, token=None):
        # xxxjack ignoring token for now
        rv = ''
        if self.urlCaller: rv += self.urlCaller.dump() + '\n'
        if self.actionHandler: rv += self.actionHandler.dump() + '\n'
        if self.eventSources: rv += self.eventSources.dump() + '\n'
        return rv
        
    def log(self, token=None):
        # xxxjack ignoring token for now
        logfn = os.path.join(self.datadir, 'igor.log')
        if os.path.exists(logfn):
            return open(logfn).read()
        raise Web.HTTPError('404 Log file not available')
        
    def updateStatus(self, subcommand=None, representing=None, alive=None, resultData=None, lastActivity=None, lastSuccess=None, token=None):
        """Update status field of some service/sensor/actuator after an action"""
        if subcommand:
            representing = subcommand
        if representing.startswith('/data/'):
            representing = representing[len('/data/'):]
        if lastActivity == None:
            lastActivity = time.time()
        else:
            lastActivity = float(lastActivity)
        if lastSuccess == None and alive:
            lastSuccess = lastActivity
        
        # xxxjack this needs to be done differently. Too much spaghetti.
        dbAccess = webApp.DATABASE_ACCESS
        
        key = 'status/' + representing
        
        # Check whether record exists, otherwise create it (empty)
        try:
            _ = dbAccess.get_key(key, 'application/x-python-object', 'content', token)
        except web.HTTPError:
            web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
            _ = dbAccess.put_key(key, 'application/x-python-object', None, '', 'text/plain', token)
            
        # Fill only entries we want
        _ = dbAccess.put_key(key + '/alive', 'application/x-python-object', None, not not alive, 'application/x-python-object', token)
        _ = dbAccess.put_key(key + '/lastActivity', 'application/x-python-object', None, lastActivity, 'application/x-python-object', token)
        if lastSuccess:
            _ = dbAccess.put_key(key + '/lastSuccess', 'application/x-python-object', None, lastSuccess, 'application/x-python-object', token)
        if alive:
            _ = dbAccess.put_key(key + '/ignoreErrorsUntil', 'application/x-python-object', None, None, 'application/x-python-object', token)
            resultData = ''
        else:
            _ = dbAccess.put_key(key + '/lastFailure', 'application/x-python-object', None, lastActivity, 'application/x-python-object', token)
            if not resultData:
                resultData = '%s failed without error message' % representing
        if type(resultData) == type({}):
            for k, v in resultData.items():
                _ = dbAccess.put_key(key + '/' + k, 'application/x-python-object', None, v, 'application/x-python-object', token)
        else:
            _ = dbAccess.put_key(key + '/errorMessage', 'application/x-python-object', None, resultData, 'application/x-python-object', token)
        return ''
        
    def updateActions(self):
        """Create any (periodic) event handlers defined in the database"""
        startupActions = self.database.getElements('actions', 'get', self.access.tokenForIgor())
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
        eventSources = self.database.getElements('eventSources', 'get', self.access.tokenForIgor())
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
        
    def runAction(self, actionname, token):
        if not self.actionHandler:
            raise web.notfound()
        nodes = self.database.getElements('actions/action[name="%s"]'%actionname, 'get', self.access.tokenForIgor())
        if not nodes:
            raise web.notfound()
        for node in nodes:
            self.actionHandler.triggerAction(node)
        return 'OK'
    
    def runTrigger(self, triggername, token):
        raise web.HTTPError("502 triggers not yet implemented")
        if not self.triggerHandler:
            raise web.notfound()
        triggerNodes = self.database.getElements('triggers/%s' % triggername, 'get', self.access.tokenForIgor())
        if not triggerNodes:
            raise web.notfound()
        if len(triggerNodes) > 1:
            raise web.HTTPError("502 multiple triggers %s in database" % triggername)
        triggerNode = triggerNodes[0]
        self.triggerHandler.triggerTrigger(triggerNode)
        
    def save(self, token):
        """Saves the database to the filesystem"""
        self.database.saveFile()
        return 'OK'
        
    def started(self, token):
        return "IgorServer started"
        
    def queue(self, subcommand, token):
        """Queues an internal command through callUrl (used for save/stop/restart)"""
        self.urlCaller.callURL(dict(method='GET', url='/internal/%s' % subcommand, token=token))
        return 'OK'
        
    def stop(self, token):
        """Exits igorServer after saving"""
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
        self.save(token)
        if self.profile:
            self.profile.disable()
            if PROFILER_STATS is None:
                PROFILER_STATS = pstats.Stats(self.profile)
            else:
                PROFILER_STATS.add(self.profile)
            PROFILER_STATS.dump_stats("igor.profile")
        sys.exit(0)
        
    def restart(self, token):
        self.save(token)
        os.closerange(3, subprocess.MAXFD)
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    def command(self, token):
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
        
    def help(self, token):
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
        
    def version(self, token):
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
    parser.add_argument("-s", "--nossl", action="store_true", help="Do no use https (ssl) on the service, even if certificates are available")
    parser.add_argument("--debug", metavar="MODULE", help="Enable debug output for MODULE (all for all modules)")
    parser.add_argument("--advertise", action="store_true", help="Advertise service through bonjour/zeroconf")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--profile", action="store_true", help="Enable Python profiler (debugging Igor only)")
    parser.add_argument('--logLevel', metavar='SPEC', help="Set log levels (comma-separated list of [loggername:]LOGLEVEL)")
    args = parser.parse_args()
    
    myLogger.install(args.logLevel)
    if args.version:
        print VERSION
        sys.exit(0)
    if args.debug:
        if args.debug in ('callUrl', 'all'): callUrl.DEBUG = True
        if args.debug in ('sseListener', 'all'): sseListener.DEBUG = True
        if args.debug in ('actions', 'all'): actions.DEBUG = True
        if args.debug in ('xmlDatabase', 'all'): xmlDatabase.DEBUG = True
        if args.debug in ('webApp', 'all'): webApp.DEBUG = True
        if args.debug in ('access', 'all'): access.DEBUG = True
    datadir = args.database
    print 'igorServer %s running from %s' % (VERSION, sys.argv[0])
    try:
        igorServer = IgorServer(datadir, args.port, args.advertise, profile=args.profile, nossl=args.nossl)
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
    

    
