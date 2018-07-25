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
        
class IgorTestHttps(IgorTest):
    igorDir = os.path.join(FIXTURES, 'testIgorHttps')
    igorLogFile = os.path.join(FIXTURES, 'testIgorHttps.log')
    igorPort = 29333
    igorProtocol = "https"
    
if __name__ == '__main__':
    unittest.main()
    
