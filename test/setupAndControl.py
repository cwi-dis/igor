from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import object
# Enable coverage if installed and enabled through COVERAGE_PROCESS_START environment var
try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass
import os
import shutil
import sys
import time
import subprocess
import igorVar
import igorSetup
import igorServlet
import threading
import traceback

DEBUG_TEST=False
PROFILE=False

if os.getenv('IGOR_TEST_DEBUG'):
    DEBUG_TEST=True
if os.getenv('IGOR_TEST_PROFILE'):
    PROFILE=True
if DEBUG_TEST:
    igorVar.VERBOSE=DEBUG_TEST
    igorServlet.DEBUG=DEBUG_TEST

class ServletHelper(object):
    def __init__(self, port, protocol, capabilities, database, audience):
        self.lock = threading.Lock()
        self.requestReceived = threading.Condition(self.lock)
        self.timerStart = None
        self.duration = None
        self.value = 0
        self.server = igorServlet.IgorServlet(
            port=port, 
            nolog=True, 
            nossl=(protocol != 'https'), 
            capabilities=capabilities, noCapabilities=(not capabilities), 
            database=database,
            audience=audience
            )
        self.server.addEndpoint('/api/get', get=self.get)
        self.server.addEndpoint('/api/set', put=self.set, get=self.set)
        self.server.start()
        
    def stop(self):
        self.server.stop()
        self.server = None
        
    def get(self):
        with self.lock:
            if self.timerStart:
                self.duration = time.time() - self.timerStart
                self.timerStart = None
                self.requestReceived.notify()
        return self.value
        
    def set(self, value=None, data=None):
        if value is None:
            value = data
        with self.lock:
            if self.timerStart:
                self.duration = time.time() - self.timerStart
                self.timerStart = None
                self.requestReceived.notify()
        self.value = value
        
    def startTimer(self):
        with self.lock:
            self.duration = None
            self.timerStart = time.time()
        
    def getDuration(self):
        with self.lock:
            rv = self.duration
            self.duration = None
        return rv
        
    def waitDuration(self):
        with self.lock:
            if self.duration is None:
                self.requestReceived.wait(10)
            rv = self.duration
            self.duration = None
        return rv
            
    def hasIssuer(self):
        return self.server.hasIssuer()
        
    def setIssuer(self, issuer, sharedKey):
        return self.server.setIssuer(issuer, sharedKey)
    
class IgorSetupAndControl(object):
    """Mixin class for both testing and performance measurements"""
    
    #
    # Class variables provided by the actual test or performance classes
    #
    
    igorDir = None # os.path.join(FIXTURES, 'testIgor')
    igorHostname=None # socket.gethostname()
    igorHostname2=None # 'localhost'
    igorPort = None # 19333
    igorProtocol = None # "http"
    igorVarArgs = None # {}
    igorServerArgs = None # []
    igorUseCapabilities = None # False
    
    @classmethod
    def setUpIgor(cls):
        if DEBUG_TEST: print('IgorTest: setupIgor', cls)
        if DEBUG_TEST: print('IgorTest: Delete old database and logfile')
        shutil.rmtree(cls.igorDir, True)
        cls.igorUrl = "%s://%s:%d/data/" % (cls.igorProtocol, cls.igorHostname, cls.igorPort)
        cls.servletUrl = "%s://%s:%d" % (cls.igorProtocol, cls.igorHostname, cls.igorPort+1)
        
        if DEBUG_TEST: print('IgorTest: Setup database')
        setup = igorSetup.IgorSetup(database=cls.igorDir)
        ok = setup.cmd_initialize()
        assert ok
        setup.postprocess(run=True)
        ok = setup.cmd_addstd('user', 'copytree', 'testPlugin')
        assert ok
        ok = setup.cmd_addstd(('test2plugin', 'testPlugin'))
        assert ok
        setup.postprocess(run=True)

        logFile = os.path.join(cls.igorDir, 'igor.log')
        logFP = open(logFile, 'a')
        
        if cls.igorProtocol == 'https':
            if DEBUG_TEST: print('IgorTest: setup self-signed signature')
            ok = setup.cmd_certificateSelfsigned('/CN=%s' % cls.igorHostname, cls.igorHostname)
#            ok = setup.cmd_certificateSelfsigned('/CN=%s' % cls.igorHostname, cls.igorHostname, cls.igorHostname2, '127.0.0.1', '::1')
            assert ok
            setup.postprocess(run=True, subprocessArgs=dict(stdout=logFP, stderr=subprocess.STDOUT))
            certFile = os.path.join(cls.igorDir, 'igor.crt')
            cls.igorVarArgs['certificate'] = certFile
#            cls.igorVarArgs['noverify'] = True
#            os.putenv('SSL_CERT_FILE', certFile)
            os.putenv('REQUESTS_CA_BUNDLE', certFile)
#            os.putenv('IGOR_TEST_NO_SSL_VERIFY', '1')

        if DEBUG_TEST: print('IgorTest: Check database consistency')
        if 'IGOR_TEST_PYTHON' in os.environ:
            cmdHead = [os.environ['IGOR_TEST_PYTHON']]
        else:
            cmdHead = [sys.executable]
        cmd = cmdHead + ["-m", "igor", "--nologstderr", "--check", "--database", cls.igorDir, "--port", str(cls.igorPort)]
        sts = subprocess.call(cmd + cls.igorServerArgs)
        if sts:
            print('IgorTest: status=%s returned by command %s' % (str(sts), ' '.join(cmd)))
            print('IgorTest: logfile %s:' % logFile)
            sys.stdout.write(open(logFile).read())
            assert 0
        cmd = cmdHead + ["-m", "igor", "--nologstderr", "--database", cls.igorDir, "--port", str(cls.igorPort)] + cls.igorServerArgs
        if PROFILE:
            cmd += ["--profile"]
        if DEBUG_TEST: print('IgorTest: Start server')
        cls.igorProcess = subprocess.Popen(cmd)
        if DEBUG_TEST: print('IgorTest: Start servlet')
        cls.servlet = ServletHelper(
                port=cls.igorPort+1, 
                protocol=cls.igorProtocol, 
                capabilities=cls.igorUseCapabilities, 
                database=cls.igorDir,
                audience=cls.servletUrl
                )
        time.sleep(10)
    
    @classmethod
    def tearDownIgor(cls):
        if os.environ.get('IGOR_TEST_WAIT'):
            print('igorTest: tests finished.')
            print('igorTest: Waiting with teardown because environment variable IGOR_TEST_WAIT is set.')
            print('igorTest: Type return to continue - ', end=' ')
            sys.stdin.readline()
        # Stop servlet
        if DEBUG_TEST: print('IgorTest: Stop servlet')
        cls.servlet.stop()
        # Gracefully stop server
        if DEBUG_TEST: print('IgorTest: Request server to stop')
        try:
            p = igorVar.IgorServer(cls.igorUrl, credentials='admin:', **cls.igorVarArgs)
            result = p.get('/internal/stop')
        except:
            if DEBUG_TEST: traceback.print_exc()
            print('IgorTest: Ignoring exception during stop request')        
        time.sleep(2)
        
        sts = cls.igorProcess.poll()
        if sts is None:
            print('IgorTest: Terminate server')
            cls.igorProcess.terminate()
            time.sleep(2)
        sts = cls.igorProcess.wait()
        assert sts != None

        
    def _igorVar(self, server=None, **kwargs):
        kwargs = dict(kwargs)
        kwargs.update(self.igorVarArgs)
        if server is None:
            server = self.igorUrl
        return igorVar.IgorServer(server, **kwargs)
        
    def _flush(self, pIgor, maxDuration):
        pIgor.get('/internal/flush?timeout=%d' % maxDuration)
        
