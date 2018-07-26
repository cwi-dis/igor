import unittest
import os
import shutil
import sys
import time
import subprocess
import json
import xml.etree.ElementTree as ET
import igorVar
import igorSetup
import igorCA

DEBUG_TEST=False
if DEBUG_TEST:
    igorVar.VERBOSE=True

FIXTURES=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

class IgorTest(unittest.TestCase):
    igorDir = os.path.join(FIXTURES, 'testIgor')
    igorLogFile = os.path.join(FIXTURES, 'testIgor.log')
    igorPort = 19333
    igorProtocol = "http"
    igorVarArgs = {}
    
    @classmethod
    def setUpClass(cls):
        super(IgorTest, cls).setUpClass()

        if DEBUG_TEST: print 'IgorTest: Delete old database and logfile'
        shutil.rmtree(cls.igorDir, True)
        shutil.rmtree(cls.igorLogFile, True)
        
        cls.igorUrl = "%s://localhost:%d/data/" % (cls.igorProtocol, cls.igorPort)
        
        if DEBUG_TEST: print 'IgorTest: Setup database'
        setup = igorSetup.IgorSetup(database=cls.igorDir)
        ok = setup.cmd_initialize()
        assert ok
        setup.postprocess(run=True)
        
        if cls.igorProtocol == 'https':
            if DEBUG_TEST: print 'IgorTest: setup self-signed signature'
            ok = setup.cmd_certificateSelfsigned('/C=NL/O=igor/CN=localhost', 'localhost', '127.0.0.1', '::1')
            assert ok
            setup.postprocess(run=True)
            cls.igorVarArgs['certificate'] = os.path.join(cls.igorDir, 'igor.crt')
            cls.igorVarArgs['noverify'] = True

        if DEBUG_TEST: print 'IgorTest: Check database consistency'
        subprocess.check_call([sys.executable, "-m", "igor", "--check", "--database", cls.igorDir, "--port", str(cls.igorPort)], stdout=open(cls.igorLogFile, 'a'), stderr=subprocess.STDOUT)

        if DEBUG_TEST: print 'IgorTest: Start server'
        cls.igorProcess = subprocess.Popen([sys.executable, "-m", "igor", "--database", cls.igorDir, "--port", str(cls.igorPort)], stdout=open(cls.igorLogFile, 'a'), stderr=subprocess.STDOUT)
        time.sleep(2)
    
    @classmethod
    def tearDownClass(cls):
        # Gracefully stop server
        if DEBUG_TEST: print 'IgorTest: Request server to stop'
        try:
            p = igorVar.IgorServer(cls.igorUrl, **cls.igorVarArgs)
            result = p.get('/internal/stop')
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
        pass
        
    def _igorVar(self):
        return igorVar.IgorServer(self.igorUrl, **self.igorVarArgs)
        
    def test01_get_static(self):
        p = self._igorVar()
        result = p.get('/')
        self.assertTrue(result)
        self.assertEqual(result[0], "<")
        
    def notyet_test01_get_static_nonexistent(self):
        p = self._igorVar()
        result = p.get('/nonexistent.html')
        self.assertTrue(result)
        self.assertEqual(result[0], "<")
        
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
        
    def test41_action(self):
        p = self._igorVar()
        content = {'test41':{'src':'', 'sink':''}}
        action = {'action':dict(name='test41action', url='/data/sandbox/test41/sink', xpath='/data/sandbox/test41/src', method='PUT', data='copy-{.}-copy')}
        p.put('sandbox/test41', json.dumps(content), datatype='application/json')
        p.post('actions/action', json.dumps(action), datatype='application/json')
        p.put('sandbox/test41/src', 'forty-one', datatype='text/plain')
        
        time.sleep(2)
        
        result = p.get('sandbox/test41', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test41':{'src':'forty-one', 'sink':'copy-forty-one-copy'}}
        self.assertEqual(resultDict, wantedContent)
        
    def test42_action(self):
        p = self._igorVar()
        content = {'test42':{'src':''}}
        action = {'action':dict(name='test42action', url='/data/sandbox/test42/sink', xpath='/data/sandbox/test42/src', method='POST', data='{.}')}
        p.put('sandbox/test42', json.dumps(content), datatype='application/json')
        p.post('actions/action', json.dumps(action), datatype='application/json')
        p.put('sandbox/test42/src', '42a', datatype='text/plain')
        p.put('sandbox/test42/src', '42b', datatype='text/plain')
        p.put('sandbox/test42/src', '42c', datatype='text/plain')
        
        time.sleep(2)
        
        result = p.get('sandbox/test42', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test42':{'src':'42c', 'sink':['42a','42b','42c']}}
        self.assertEqual(resultDict, wantedContent)
        
class IgorTestHttps(IgorTest):
    igorDir = os.path.join(FIXTURES, 'testIgorHttps')
    igorLogFile = os.path.join(FIXTURES, 'testIgorHttps.log')
    igorPort = 29333
    igorProtocol = "https"
    
if __name__ == '__main__':
    unittest.main()
    
