import unittest
import os
import shutil
import sys
import time
import subprocess
import json
import socket
import urllib
import xml.etree.ElementTree as ET
import igorVar
import igorSetup
import igorCA
import igorServlet

DEBUG_TEST=False
if DEBUG_TEST:
    igorVar.VERBOSE=True

FIXTURES=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

MAX_FLUSH_DURATION=10            # How long we wait for internal actions to be completed
MAX_EXTERNAL_FLUSH_DURATION=0   # How long we wait for external actions to be completed

class ServletHelper:
    def __init__(self, port, protocol, capabilities, database):
        self.timerStart = None
        self.duration = None
        self.value = 0
        self.server = igorServlet.IgorServlet(port=port, nolog=True, nossl=(protocol != 'https'), capabilities=capabilities, noCapabilities=(not capabilities), database=database)
        self.server.addEndpoint('/api/get', get=self.get)
        self.server.addEndpoint('/api/set', put=self.set, get=self.set)
        self.server.start()
        
    def stop(self):
        self.server.stop()
        self.server = None
        
    def get(self):
        if self.timerStart:
            self.duration = time.time() - self.timerStart
            self.timerStart = None
        return self.value
        
    def set(self, value=None, data=None):
        if value is None:
            value = data
        if self.timerStart:
            self.duration = time.time() - self.timerStart
            self.timerStart = None
        self.value = value
        
    def startTimer(self):
        self.timerStart = time.time()
        
    def getDuration(self):
        rv = self.duration
        self.duration = None
        return rv
        
    def waitDuration(self):
        count = 0
        while count < 10:
            rv = self.getDuration()
            if rv != None:
                return rv
            time.sleep(1)
            count += 1
    
class IgorTest(unittest.TestCase):
    igorDir = os.path.join(FIXTURES, 'testIgor')
    igorLogFile = os.path.join(FIXTURES, 'testIgor.log')
    igorHostname=socket.gethostname()
    igorHostname2='localhost'
    igorPort = 19333
    igorProtocol = "http"
    igorVarArgs = {}
    igorServerArgs = []
    igorUseCapabilities = False
    
    @classmethod
    def setUpClass(cls):
        super(IgorTest, cls).setUpClass()

        if DEBUG_TEST: print 'IgorTest: Delete old database and logfile'
        shutil.rmtree(cls.igorDir, True)
        if os.path.exists(cls.igorLogFile):
            os.unlink(cls.igorLogFile)
        
        cls.igorUrl = "%s://%s:%d/data/" % (cls.igorProtocol, cls.igorHostname, cls.igorPort)
        cls.servletUrl = "%s://%s:%d/api/" % (cls.igorProtocol, cls.igorHostname, cls.igorPort+1)
        
        if DEBUG_TEST: print 'IgorTest: Setup database'
        setup = igorSetup.IgorSetup(database=cls.igorDir)
        ok = setup.cmd_initialize()
        assert ok
        setup.postprocess(run=True)
        
        if cls.igorProtocol == 'https':
            if DEBUG_TEST: print 'IgorTest: setup self-signed signature'
            ok = setup.cmd_certificateSelfsigned('/CN=%s' % cls.igorHostname, cls.igorHostname)
#            ok = setup.cmd_certificateSelfsigned('/CN=%s' % cls.igorHostname, cls.igorHostname, cls.igorHostname2, '127.0.0.1', '::1')
            assert ok
            setup.postprocess(run=True)
            certFile = os.path.join(cls.igorDir, 'igor.crt')
            cls.igorVarArgs['certificate'] = certFile
#            cls.igorVarArgs['noverify'] = True
            os.putenv('SSL_CERT_FILE', certFile)
            os.putenv('REQUESTS_CA_BUNDLE', certFile)
#            os.putenv('IGOR_TEST_NO_SSL_VERIFY', '1')

        if DEBUG_TEST: print 'IgorTest: Check database consistency'
        cmd = [sys.executable, "-m", "igor", "--check", "--database", cls.igorDir, "--port", str(cls.igorPort)]
        sts = subprocess.call(cmd + cls.igorServerArgs, stdout=open(cls.igorLogFile, 'a'), stderr=subprocess.STDOUT)
        if sts:
            print 'IgorTest: status=%s returned by command %s' % (str(sts), ' '.join(cmd))
            print 'IgorTest: logfile %s:' % cls.igorLogFile
            sys.stdout.write(open(cls.igorLogFile).read())
            assert 0
        if DEBUG_TEST: print 'IgorTest: Start server'
        cls.igorProcess = subprocess.Popen([sys.executable, "-u", "-m", "igor", "--database", cls.igorDir, "--port", str(cls.igorPort)] + cls.igorServerArgs, stdout=open(cls.igorLogFile, 'a'), stderr=subprocess.STDOUT)
        if DEBUG_TEST: print 'IgorTest: Start servlet'
        cls.servlet = ServletHelper(port=cls.igorPort+1, protocol=cls.igorProtocol, capabilities=cls.igorUseCapabilities, database=cls.igorDir)
        time.sleep(2)
    
    @classmethod
    def tearDownClass(cls):
        # Stop servlet
        if DEBUG_TEST: print 'IgorTest: Stop servlet'
        cls.servlet.stop()
        # Gracefully stop server
        if DEBUG_TEST: print 'IgorTest: Request server to stop'
        try:
            p = igorVar.IgorServer(cls.igorUrl, **cls.igorVarArgs)
            result = p.get('/internal/stop', credentials='admin:')
        except:
            if DEBUG_TEST: print 'IgorTest: Ignoring exception during stop request'        
        time.sleep(2)
        
        sts = cls.igorProcess.poll()
        if sts is None:
            if DEBUG_TEST: print 'IgorTest: Terminate server'
            cls.igorProcess.terminate()
            time.sleep(2)
        sts = cls.igorProcess.wait()
        assert sts != None

        super(IgorTest, cls).tearDownClass()
        
    def _igorVar(self, **kwargs):
        kwargs = dict(kwargs)
        kwargs.update(self.igorVarArgs)
        return igorVar.IgorServer(self.igorUrl, **kwargs)
        
    def _flush(self, pIgor, maxDuration):
        pIgor.get('/internal/flush?timeout=%d' % maxDuration)
            
    def test01_get_static(self):
        p = self._igorVar()
        result = p.get('/')
        self.assertTrue(result)
        self.assertEqual(result[0], "<")
        
    def test02_get_static_nonexistent(self):
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.get, '/nonexistent.html')
        
    def test11_get_xml(self):
        p = self._igorVar()
        result = p.get('environment/systemHealth', format='application/xml')
        self.assertTrue(result)
        root = ET.fromstring(result)
        self.assertEqual(root.tag, "systemHealth")
        
    def test12_get_text(self):
        p = self._igorVar()
        result = p.get('environment/systemHealth', format='text/plain')
        self.assertTrue(result)
        
    def test13_get_json(self):
        p = self._igorVar()
        result = p.get('environment/systemHealth', format='application/json')
        self.assertTrue(result)
        root = json.loads(result)
        self.assertIsInstance(root, dict)
        self.assertEqual(root.keys(), ["systemHealth"])
        
    def test21_put_xml(self):
        p = self._igorVar()
        data = '<test21>21</test21>'
        p.put('sandbox/test21', data, datatype='application/xml')
        result = p.get('sandbox/test21', format='application/xml')
        self.assertEqual(data.strip(), result.strip())
        result2 = p.get('sandbox/test21', format='text/plain')
        self.assertEqual('21', result2.strip())
        result3 = p.get('sandbox/test21', format='application/json')
        result3dict = json.loads(result3)
        self.assertEqual({"test21" : 21}, result3dict)
        
    def test22_put_text(self):
        p = self._igorVar()
        data = 'twenty two'
        p.put('sandbox/test22', data, datatype='text/plain')
        result = p.get('sandbox/test22', format='text/plain')
        self.assertEqual(data.strip(), result.strip())
        result2 = p.get('sandbox/test22', format='application/xml')
        self.assertEqual('<test22>twenty two</test22>', result2.strip())
        result3 = p.get('sandbox/test22', format='application/json')
        result3dict = json.loads(result3)
        self.assertEqual({'test22':'twenty two'}, result3dict)
        
    def test23_put_json(self):
        p = self._igorVar()
        data = json.dumps({"test23" : 23})
        p.put('sandbox/test23', data, datatype='application/json')
        result = p.get('sandbox/test23', format='application/json')
        resultDict = json.loads(result)
        self.assertEqual({"test23" : 23}, resultDict)
        result2 = p.get('sandbox/test23', format='application/xml')
        self.assertEqual("<test23>23</test23>", result2.strip())
        
    def test24_put_multi(self):
        p = self._igorVar()
        data = '<test24>24</test24>'
        p.put('sandbox/test24', data, datatype='application/xml')
        result = p.get('sandbox/test24', format='application/xml')
        self.assertEqual(data.strip(), result.strip())
        data = '<test24>twentyfour</test24>'
        p.put('sandbox/test24', data, datatype='application/xml')
        result = p.get('sandbox/test24', format='application/xml')
        self.assertEqual(data.strip(), result.strip())
        
    def test31_post_text(self):
        p = self._igorVar()
        p.put('sandbox/test31', '', datatype='text/plain')
        p.post('sandbox/test31/item', 'thirty', datatype='text/plain')
        p.post('sandbox/test31/item', 'one', datatype='text/plain')
        result = p.get('sandbox/test31/item', format='text/plain')
        self.assertEqual('thirtyone', result.translate(None, ' \n'))
        
        self.assertRaises(igorVar.IgorError, p.get, 'sandbox/test31/item', format='application/xml')
        
        result2 = p.get('sandbox/test31/item', format='application/xml', variant='multi')
        self.assertIn('thirty', result2)
        self.assertIn('one', result2)
        
        result3 = p.get('sandbox/test31/item', format='application/json', variant='multi')
        result3list = json.loads(result3)
        self.assertEqual(len(result3list), 2)
        self.assertIsInstance(result3list, list)
        self.assertEqual(result3list[0]['item'], 'thirty')
        self.assertEqual(result3list[1]['item'], 'one')
        
    def test32_delete(self):
        p = self._igorVar()
        p.put('sandbox/test32', 'thirtytwo', datatype='text/plain')
        result = p.get('sandbox/test32', format='text/plain')
        self.assertEqual(result.strip(), 'thirtytwo')
        p.delete('sandbox/test32')
        self.assertRaises(igorVar.IgorError, p.get, 'sandbox/test32')

    def test61_call_action(self):
        pAdmin = self._igorVar(credentials='admin:')
        optBearerToken = self._create_cap_for_call(pAdmin, 'test61action')
        p = self._igorVar(**optBearerToken)
        content = {'test61':{'data' : '0'}}
        action = {'action':dict(name='test61action', url='/data/sandbox/test61/data', method='PUT', data='{/data/sandbox/test61/data + 1}')}
        pAdmin.put('sandbox/test61', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')

        p.get('/action/test61action')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.get('/action/test61action')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.get('/action/test61action')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        
        result = pAdmin.get('sandbox/test61/data', format='text/plain')
        resultNumber = float(result.strip())
        self.assertEqual(resultNumber, 3)
        
    def _create_cap_for_call(self, pAdmin, action):
        return {}
        
    def test71_action(self):
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test71':{'src':'', 'sink':''}}
        action = {'action':dict(name='test71action', url='/data/sandbox/test71/sink', xpath='/data/sandbox/test71/src', method='PUT', data='copy-{.}-copy')}
        p.put('sandbox/test71', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        p.put('sandbox/test71/src', 'seventy-one', datatype='text/plain')
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        
        result = p.get('sandbox/test71', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test71':{'src':'seventy-one', 'sink':'copy-seventy-one-copy'}}
        self.assertEqual(resultDict, wantedContent)
        
    def test72_action_post(self):
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test72':{'src':''}}
        action = {'action':dict(name='test72action', url='/data/sandbox/test72/sink', xpath='/data/sandbox/test72/src', method='POST', data='{.}')}
        p.put('sandbox/test72', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.put('sandbox/test72/src', '72a', datatype='text/plain')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.put('sandbox/test72/src', '72b', datatype='text/plain')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.put('sandbox/test72/src', '72c', datatype='text/plain')
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        
        result = p.get('sandbox/test72', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test72':{'src':'72c', 'sink':['72a','72b','72c']}}
        self.assertEqual(resultDict, wantedContent)
        
    def test73_action_indirect(self):
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test73':{'src':'', 'sink':''}}
        action1 = {'action':dict(name='test73first', url='/action/test73second', xpath='/data/sandbox/test73/src')}
        action2 = {'action':dict(name='test73second', url='/data/sandbox/test73/sink', method='PUT', data='copy-{/data/sandbox/test73/src}-copy')}
        p.put('sandbox/test73', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action2), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.put('sandbox/test73/src', 'seventy-three', datatype='text/plain')
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        
        result = p.get('sandbox/test73', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test73':{'src':'seventy-three', 'sink':'copy-seventy-three-copy'}}
        self.assertEqual(resultDict, wantedContent)

    def _create_caps_for_action(self, pAdmin, caller, callee):
        pass
        
    def test74_action_external_get(self):
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test74':{'src':'', 'sink':''}}
        action1 = {'action':dict(name='test74first', url=self.servletUrl+'get', xpath='/data/sandbox/test74/src')}
#        action2 = {'action':dict(name='test74second', url='/data/sandbox/test74/sink', method='PUT', data='copy-{/data/sandbox/test74/src}-copy')}
        p.put('sandbox/test74', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')
#        pAdmin.post('actions/action', json.dumps(action2), datatype='application/json')
#        self._create_caps_for_action(pAdmin, 'test74first', 'test74second')
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        self.servlet.startTimer()
        p.put('sandbox/test74/src', 'seventy-four', datatype='text/plain')
        
        duration = self.servlet.waitDuration()
        if DEBUG_TEST: print 'IgorTest: indirect external action took', duration, 'seconds'
        self.assertNotEqual(duration, None)
        
    def test75_action_external_get_arg(self):
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test75':{'src':''}}
        action1 = {'action':dict(name='test75first', url=self.servletUrl+'set?value={.}', method='GET', xpath='/data/sandbox/test75/src')}
        p.put('sandbox/test75', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self.servlet.startTimer()
        p.put('sandbox/test75/src', 'seventy-five', datatype='text/plain')
        
        duration = self.servlet.waitDuration()
        self.assertNotEqual(duration, None)
        if DEBUG_TEST: print 'IgorTest: indirect external action took', duration, 'seconds'
        result = self.servlet.get()
        self.assertEqual(result, 'seventy-five')
        
    def test76_action_external_put(self):
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test76':{'src':''}}
        action1 = {'action':dict(name='test76first', url=self.servletUrl+'set', method='PUT', mimetype='text/plain', data='{.}', xpath='/data/sandbox/test76/src')}
        p.put('sandbox/test76', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self.servlet.startTimer()
        p.put('sandbox/test76/src', 'seventy-six', datatype='text/plain')
        
        duration = self.servlet.waitDuration()
        self.assertNotEqual(duration, None)
        if DEBUG_TEST: print 'IgorTest: indirect external action took', duration, 'seconds'
        result = self.servlet.get()
        self.assertEqual(result, 'seventy-six')
        
class IgorTestHttps(IgorTest):
    igorDir = os.path.join(FIXTURES, 'testIgorHttps')
    igorLogFile = os.path.join(FIXTURES, 'testIgorHttps.log')
    igorPort = 29333
    igorProtocol = "https"
    
class IgorTestCaps(IgorTestHttps):
    igorDir = os.path.join(FIXTURES, 'testIgorCaps')
    igorLogFile = os.path.join(FIXTURES, 'testIgorCaps.log')
    igorPort = 39333
    igorServerArgs = ["--capabilities"]
    igorUseCapabilities = True

    def test19_get_disallowed(self):
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.get, 'identities', format='application/xml')
        
    def test29_put_disallowed(self):
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.put, 'environment/systemHealth/test29', 'twentynine', datatype='text/plain')
        
    def test29_put_disallowed(self):
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.put, 'environment/systemHealth/test29', 'twentynine', datatype='text/plain')

    def test39_delete_disallowed(self):
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.delete, 'environment/systemHealth')
        
    def _new_capability(self, pAdmin, **kwargs):
        argStr = urllib.urlencode(kwargs)
        rv = pAdmin.get('/internal/accessControl/newToken?' + argStr)
        return rv.strip()
        
    def test40_newcap(self):
        pAdmin = self._igorVar(credentials='admin:')
        pAdmin.put('environment/test40', '', datatype='text/plain')
        _ = self._new_capability(pAdmin, 
            tokenId='admin-data', 
            newOwner='/data/au:access/au:defaultCapabilities', 
            newPath='/data/environment/test40',
            get='self',
            put='self'
            )
        p = self._igorVar()
        p.put('environment/test40', 'forty', datatype='text/plain')
        result = p.get('environment/test40', format='text/plain')
        self.assertEqual(result.strip(), 'forty')

    def _new_sharedkey(self, pAdmin, **kwargs):
        argStr = urllib.urlencode(kwargs)
        try:
            rv = pAdmin.get('/internal/accessControl/createSharedKey?' + argStr)
        except igorVar.IgorError:
            if DEBUG_TEST: print '(shared key already exists for %s)' % repr(kwargs)
        
    def test41_newcap_external(self):
        pAdmin = self._igorVar(credentials='admin:')
        pAdmin.put('environment/test41', '', datatype='text/plain')
        newCapID = self._new_capability(pAdmin, 
            tokenId='admin-data', 
            newOwner='/data/identities/admin', 
            newPath='/data/environment/test41',
            get='self',
            put='self',
            delegate='1'
            )
        self._new_sharedkey(pAdmin, sub='localhost')
        bearerToken = pAdmin.get('/internal/accessControl/exportToken?tokenId=%s&subject=localhost' % newCapID)        
        
        p = self._igorVar(bearer_token=bearerToken)
        p.put('environment/test41', 'fortyone', datatype='text/plain')
        result = p.get('environment/test41', format='text/plain')
        self.assertEqual(result.strip(), 'fortyone')
        
    def _create_cap_for_call(self, pAdmin, callee):
        newCapID = self._new_capability(pAdmin, 
            tokenId='admin-action', 
            newOwner='/data/identities/admin', 
            newPath='/action/%s' % callee,
            get='self',
            delegate='1'
            )
        self._new_sharedkey(pAdmin, sub='localhost')
        bearerToken = pAdmin.get('/internal/accessControl/exportToken?tokenId=%s&subject=localhost' % newCapID)        
        return {'bearer_token' : bearerToken }
        
    def _create_caps_for_action(self, pAdmin, caller, callee):
        igorIssuer = pAdmin.get('/internal/accessControl/getSelfIssuer')
        igorAudience = pAdmin.get('/internal/accessControl/getSelfAudience')
        self._new_sharedkey(pAdmin, aud=igorAudience)
        newCapID = self._new_capability(pAdmin, 
            tokenId='external', 
            newOwner="/data/actions/action[name='%s']" % caller, 
            newPath='/action/%s' % callee,
            get='self',
            aud=igorAudience,
            iss=igorIssuer,
            delegate='1'
            )
        

if __name__ == '__main__':
    unittest.main()
    
