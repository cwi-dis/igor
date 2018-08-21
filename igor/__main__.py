import webApp
import xmlDatabase
import access
import actions
import sseListener
import callUrl
import os
import signal
import argparse
import besthostname
import time
import json
import web
import subprocess
import imp
import threading
import traceback
import cProfile
import pstats
import shelve
import myLogger
from _version import VERSION

import sys
reload(sys)
sys.setdefaultencoding('utf8')

_real_stderr = sys.stderr
def _dump_app_stacks(*args):
    _dump_app_stacks_to(_real_stderr)
    _dump_app_stacks_to(sys.stderr)
def _dump_app_stacks_to(file):
    print >> file, "igorServer: QUIT received, dumping all stacks, %d threads:" % len(sys._current_frames())
    for threadId, stack in sys._current_frames().items():
        print >> file, "\nThreadID:", threadId
        traceback.print_stack(stack, file=file)
        print >> file
    print >> file, "igorServer: End of stack dumps"
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
    
class Struct:
    pass
    
# class IgorLogger(wsgilog.WsgiLog):
#     IGOR_LOG_DIR="."
#     IGOR_LOG_FILE="igor.log"
#     IGOR_LOG_INTERVAL=24
#     IGOR_LOG_BACKUPS=9
#     IGOR_LOG_TOPRINT=True
#     def __init__(self, application):
#         wsgilog.WsgiLog.__init__(
#             self,
#             application,
#             logformat = '%(message)s',
#             tofile = True,
#             toprint = self.IGOR_LOG_TOPRINT,
#             file = os.path.join(self.IGOR_LOG_DIR, self.IGOR_LOG_FILE),
#             interval = self.IGOR_LOG_INTERVAL,
#             backups = self.IGOR_LOG_BACKUPS
#             )
# 
class IgorServer:
    def __init__(self, datadir, port=9333, advertise=False, profile=False, nossl=False, nologger=False):
        #
        # Store all pathnames and such
        #
        self.port = port
        self.pathnames = Struct()
        self.pathnames.datadir = datadir
        self.pathnames.scriptdir = os.path.join(datadir, 'scripts')
        self.pathnames.plugindir = os.path.join(datadir, 'plugins')
        self.pathnames.staticdir = os.path.join(datadir, 'static')
        self.pathnames.sessionfile = os.path.join(self.pathnames.datadir, 'igorSessions')
        self.pathnames.privateKeyFile = None
        self.pathnames.certificateFile = None
        #
        # Determine parameters for SSL handling
        #
        self._do_ssl = not nossl
        self.certificateFingerprint = None
        keyFile = os.path.join(self.pathnames.datadir, 'igor.key')
        if self._do_ssl and not os.path.exists(keyFile):
            print >>sys.stderr, 'Warning: Using http in stead of https: no private key file', keyFile
            self._do_ssl = False
        if self._do_ssl:
            self.pathnames.privateKeyFile = keyFile
            self.pathnames.certificateFile = os.path.join(self.pathnames.datadir, 'igor.crt')
            import OpenSSL.crypto
            certificateData = open(self.pathnames.certificateFile, 'rb').read()
            certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificateData)
            self.certificateFingerprint = certificate.digest("sha1")
        #
        # Create some objects that are not intended to be accessed by other objects
        #
        self._do_advertise = advertise
        self._advertiser = None
        self._profiler = None
        if profile:
            enable_thread_profiling()
            self._profiler = cProfile.Profile()
            self._profiler.enable()
        #
        # Create the objects that are intended to be used by other objects
        #
        self.internal = IgorInternal(self)
        
        self.app = webApp.WebApp(self)
        
        self.session = web.session.Session(self.app, web.session.ShelfStore(shelve.open(self.pathnames.sessionfile, flag="n")))

        access.createSingleton() # Has probably been done in main() already
        self.access = access.singleton
        self.access.setSession(self.session)
        self.access.setCommand(self.internal)
    
        self.database = xmlDatabase.DBImpl(os.path.join(self.pathnames.datadir, 'database.xml'))
        self.databaseAccessor = webApp.XmlDatabaseAccess(self)

        self.urlCaller = callUrl.URLCaller(self)
        self.urlCaller.start()
        
        #
        # Fill self data
        #        
        self._fillSelfData()
        #
        # Other components will be started later, in preRun()
        #
        self.actionHandler = None
        self.eventSources = None
        self.triggerHandler = None
        
    def preRun(self):
        self.internal.updateActions()
        self.internal.updateEventSources()
        self.internal.updateTriggers()
        #
        # Disable debug
        #
        web.config.debug = False
        #
        # Send start action to start any plugins
        #
        self.urlCaller.callURL(dict(method='GET', url='/action/start', token=self.access.tokenForIgor()))
        if self._do_advertise:
            self._startAdvertising(self.port)
            
    def _startAdvertising(self, port):
        if self._do_ssl:
            proto = '_https._tcp'
        else:
            proto = '_http._tcp'
        if sys.platform == 'darwin':
            cmd = ['dns-sd', '-R', 'igor', proto, 'local', str(port)]
        elif sys.platform == 'linux2':
            cmd = ['avahi-publish', '-s', 'igor', proto, str(port)]
        else:
            print >> sys.stderr, "Cannot do mdns-advertise on platform", sys.platform
            return
        try:
            self._advertiser = subprocess.Popen(cmd)
        except OSError:
            print >> sys.stderr, "advertisement command failed: %s" % (' '.join(cmd))
    
    
    def _fillSelfData(self):
        """Put our details in the database"""
        hostName = besthostname.besthostname()
        protocol = 'http'
        if self._do_ssl:
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
        if self._do_ssl:
            from web.wsgiserver import CherryPyWSGIServer
            CherryPyWSGIServer.ssl_certificate = self.pathnames.certificateFile
            CherryPyWSGIServer.ssl_private_key = self.pathnames.privateKeyFile
        signal.signal(signal.SIGTERM, self._sigterm_caught)
        self.app.run(self.port)
        print 'Igor terminating'

    def _sigterm_caught(self, signum, frame):
        print 'SIGTERM caught, exiting gracefully...'
        self.stop(save=True, token=self.access.tokenForIgor())
                
    def check(self, fix=False, token=None):
        rv = self.access.consistency(fix=fix, token=self.access.tokenForIgor())
        print rv

    def stop(self, token=None, save=True):
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
        if save:
            self.save(token)
        self.app.stop()
        self.app = None
        if self._profiler:
            self._profiler.disable()
            if PROFILER_STATS is None:
                PROFILER_STATS = pstats.Stats(self._profiler)
            else:
                PROFILER_STATS.add(self._profiler)
            PROFILER_STATS.dump_stats("igor.profile")
        if self._advertiser:
            self._advertiser.terminate()
            self._advertiser = None
        self.internal = None

    def save(self, token=None):
        """Saves the database to the filesystem"""
        self.database.saveFile()
                
class IgorInternal:
    """ Implements all internal commands for Igor"""
    def __init__(self, igor):
        self.igor = igor
        
    def dump(self, token=None):
        """Show internal run queues, action handlers and events"""
        rv = ''
        if self.igor.urlCaller: rv += self.igor.urlCaller.dump() + '\n'
        if self.igor.actionHandler: rv += self.igor.actionHandler.dump() + '\n'
        if self.igor.eventSources: rv += self.igor.eventSources.dump() + '\n'
        return rv
        
    def log(self, token=None):
        """Show current igor log file."""
        # xxxjack ignoring token for now
        logfn = os.path.join(self.igor.pathnames.datadir, 'igor.log')
        if os.path.exists(logfn):
            return open(logfn).read()
        raise web.HTTPError('404 Log file not available')
        
    def updateStatus(self, subcommand=None, representing=None, alive=None, resultData=None, lastActivity=None, lastSuccess=None, token=None):
        """Update status field of some service/sensor/actuator after an action. Not intended for human use"""
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
        
        # xxxjack unsure whether this is correct: do status updates using the igor supertoken.
        token = self.igor.access.tokenForIgor()
        
        key = 'status/' + representing
        
        # Check whether record exists, otherwise create it (empty)
        try:
            _ = self.igor.databaseAccessor.get_key(key, 'application/x-python-object', 'content', token)
        except web.HTTPError:
            web.ctx.status = "200 OK" # Clear error, otherwise it is forwarded from this request
            _ = self.igor.databaseAccessor.put_key(key, 'application/x-python-object', None, '', 'text/plain', token)
            
        # Fill only entries we want
        _ = self.igor.databaseAccessor.put_key(key + '/alive', 'application/x-python-object', None, not not alive, 'application/x-python-object', token)
        _ = self.igor.databaseAccessor.put_key(key + '/lastActivity', 'application/x-python-object', None, lastActivity, 'application/x-python-object', token)
        if lastSuccess:
            _ = self.igor.databaseAccessor.put_key(key + '/lastSuccess', 'application/x-python-object', None, lastSuccess, 'application/x-python-object', token)
        if alive:
            _ = self.igor.databaseAccessor.put_key(key + '/ignoreErrorsUntil', 'application/x-python-object', None, None, 'application/x-python-object', token)
            resultData = ''
        else:
            _ = self.igor.databaseAccessor.put_key(key + '/lastFailure', 'application/x-python-object', None, lastActivity, 'application/x-python-object', token)
            if not resultData:
                resultData = '%s failed without error message' % representing
        if type(resultData) == type({}):
            for k, v in resultData.items():
                _ = self.igor.databaseAccessor.put_key(key + '/' + k, 'application/x-python-object', None, v, 'application/x-python-object', token)
        else:
            _ = self.igor.databaseAccessor.put_key(key + '/errorMessage', 'application/x-python-object', None, resultData, 'application/x-python-object', token)
        return ''
        
    def accessControl(self, subcommand=None, returnTo=None, **kwargs):
        """Low-level access control, key and capability interface. Not intended for human use"""
        if not subcommand:
            raise web.notfound()
        method = getattr(self.igor.access, subcommand, None)
        if not method:
            raise web.notfound()
        rv = method(**kwargs)
        if returnTo and not rv:
            raise web.seeother(returnTo)
        return rv
        
    def updateActions(self, token=None):
        """Recreate event handlers defined in the database. Not intended for human use"""
        startupActions = self.igor.database.getElements('actions', 'get', self.igor.access.tokenForIgor())
        if len(startupActions):
            if len(startupActions) > 1:
                raise web.HTTPError('401 only one <actions> element allowed')
            if not self.igor.actionHandler:
                self.igor.actionHandler = actions.ActionCollection(self.igor)
            self.igor.actionHandler.updateActions(startupActions[0])
        elif self.igor.actionHandler:
            self.igor.actionHandler.updateActions([])
        return 'OK'

    def updateEventSources(self, token=None):
        """Recreate SSE event sources defined in the database. Not intended for human use"""
        eventSources = self.igor.database.getElements('eventSources', 'get', self.igor.access.tokenForIgor())
        if len(eventSources):
            if len(eventSources) > 1:
                raise web.HTTPError('401 only one <eventSources> element allowed')
            if not self.igor.eventSources:
                self.igor.eventSources = sseListener.EventSourceCollection(self.igor.database, )
            self.igor.eventSources.updateEventSources(eventSources[0])
        elif self.igor.eventSources:
            self.igor.eventSources.updateEventSources([])
        return 'OK'

    def updateTriggers(self, token=None):
        """Recreate trigger handlers. Unimplemented. Not intended for human use"""
        pass
        
    def runAction(self, actionname, token):
        """Mechanism behind running actions. Not intended for human use."""
        if not self.igor.actionHandler:
            raise web.notfound()
        nodes = self.igor.database.getElements('actions/action[name="%s"]'%actionname, 'get', self.igor.access.tokenForIgor())
        if not nodes:
            raise web.notfound()
        for node in nodes:
            self.igor.actionHandler.triggerAction(node)
        return 'OK'
    
    def runTrigger(self, triggername, token):
        """Mechanism behind running triggers. Unimplemented. Not intended for human use"""
        raise web.HTTPError("502 triggers not yet implemented")
        if not self.igor.triggerHandler:
            raise web.notfound()
        triggerNodes = self.igor.database.getElements('triggers/%s' % triggername, 'get', self.igor.access.tokenForIgor())
        if not triggerNodes:
            raise web.notfound()
        if len(triggerNodes) > 1:
            raise web.HTTPError("502 multiple triggers %s in database" % triggername)
        triggerNode = triggerNodes[0]
        self.igor.triggerHandler.triggerTrigger(triggerNode)
        
    def save(self, token=None):
        """Saves the database to the filesystem"""
        self.igor.save(token)
        return 'OK'
        
    def started(self, token):
        """Called when Igor has fully started up. Not intended for human use"""
        return "IgorServer started"
        
    def queue(self, subcommand, token):
        """Queues an internal command through callUrl (used for save/stop/restart). Not intended for human use."""
        self.igor.urlCaller.callURL(dict(method='GET', url='/internal/%s' % subcommand, token=token))
        return 'OK'
        
    def flush(self, token=None, timeout=None):
        """Wait until all currently queued urlCaller events have been completed, intended for testing"""
        if timeout:
            timeout = float(timeout)
        self.igor.urlCaller.flush(timeout)
        return 'OK'
        
    def fail(self, token=None):
        """Raises a Python exception, intended for testing"""
        assert 0, 'User-requested failure'
        
    def stop(self, token=None, save=True):
        """Gracefully stop Igor"""
        self.igor.stop(token, save)
        
    def restart(self, token):
        """Attempt to gracefully stop and restart Igor"""
        self.save(token)
        os.closerange(3, subprocess.MAXFD)
        os.execl(sys.executable, sys.executable, *sys.argv)

    def version(self, token):
        """Show Igor version"""
        return VERSION + '\n'
                
    def help(self, token):
        """Show list of all internal commands"""
        commands = []
        for name in dir(self.__class__):
            if name[0] == '_': continue
            handler = getattr(self, name)
            try:
                doc = handler.__doc__
            except AttributeError:
                continue
            if not doc or 'Not intended for human use' in doc:
                continue
            commands.append((name, doc))
        commands.sort()
        rv = 'Internal Igor commands:\n'
        for name, doc in commands:
            rv += '%s - %s\n' % (name, doc)
        return rv
    
def main():
    signal.signal(signal.SIGQUIT, _dump_app_stacks)
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
    parser.add_argument("--noCapabilities", action="store_true", help="Disable access control via capabilities (allowing all access)")
    parser.add_argument("--capabilities", action="store_true", help="Enable access control via capabilities")
    parser.add_argument("--warnCapabilities", action="store_true", help="Disable access control via capabilities, but check anyway (and give warnings)")
    parser.add_argument("--debug", metavar="MODULE", help="Enable debug output for MODULE (all for all modules)")
    parser.add_argument("--advertise", action="store_true", help="Advertise service through bonjour/zeroconf")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--profile", action="store_true", help="Enable Python profiler (debugging Igor only)")
    parser.add_argument("--nologfile", action="store_true", help="Do not install logging to files (output to stdout only)")
    parser.add_argument("--nologstderr", action="store_true", help="Do not install logging to stderr (output to logfile only)")
    parser.add_argument('--logLevel', metavar='SPEC', help="Set log levels (comma-separated list of [loggername:]LOGLEVEL)")
    parser.add_argument('--check', action="store_true", help="Do not run the server, only check the database for consistency")
    parser.add_argument('--fix', action="store_true", help="Do not run the server, only check the database for consistency and possibly fix it if needed")
    args = parser.parse_args()
    
    myLogger.install(args.logLevel, nologfile=args.nologfile, nologstderr=args.nologstderr, logdir=args.database)
    if args.version:
        print >>sys.stderr, VERSION
        sys.exit(0)
    
    useCapabilities = False # Default if neither --capabilities nor --noCapabilities has been specified
    if args.noCapabilities:
        useCapabilities = False
    if args.capabilities:
        useCapabilities = True
    if args.warnCapabilities:
        useCapabilities = True
    access.createSingleton(not useCapabilities, args.warnCapabilities)
    if args.debug:
        if args.debug in ('callUrl', 'all'): callUrl.DEBUG = True
        elif args.debug in ('sseListener', 'all'): sseListener.DEBUG = True
        elif args.debug in ('actions', 'all'): actions.DEBUG = True
        elif args.debug in ('xmlDatabase', 'all'): xmlDatabase.DEBUG = True
        elif args.debug in ('webApp', 'all'): webApp.DEBUG = True
        elif args.debug in ('access', 'all'): access.DEBUG.append(True)
        else:
            print >>sys.stderr, "%s: --debug argument should be modulename or 'all'" % sysargv[0]
            sys.eit(1)
    datadir = args.database
    print >>sys.stderr, 'igorServer %s running from %s' % (VERSION, sys.argv[0])
    try:
        igorServer = IgorServer(datadir, args.port, args.advertise, profile=args.profile, nossl=args.nossl, nologger=args.nologfile)
    except IOError, arg:
        print >>sys.stderr, '%s: Cannot open database: %s' % (sys.argv[0], arg)
        print >>sys.stderr, '%s: Use --help option to see command line arguments' % sys.argv[0]
        sys.exit(1)
    if args.fix or args.check:
        igorServer.check(args.fix)
        igorServer.stop(save=False)
    else:
        igorServer.preRun()
        igorServer.run()

if __name__ == '__main__':
    main()
    
