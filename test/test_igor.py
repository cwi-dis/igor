import unittest
import os
import shutil
import sys
import time
import subprocess
import igorVar
import igorSetup
import igorCA

DEBUG_TEST=True

class IgorTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        super(IgorTest, cls).setUpClass()
        fixtureDir = os.path.abspath(os.path.dirname(__file__))
        cls.igorDir = os.path.join(fixtureDir, 'fixtures', 'testIgor')
        cls.igorPort = 19333
        cls.igorProtocol = "http"
        cls.igorUrl = "%s://localhost:%d/data/" % (cls.igorProtocol, cls.igorPort)
        if DEBUG_TEST: print 'IgorTest: Removing', cls.igorDir
        shutil.rmtree(cls.igorDir, True)
        if DEBUG_TEST: print 'IgorTest: Setup database'
        setup = igorSetup.IgorSetup(database=cls.igorDir)
        ok = setup.cmd_initialize()
        print 'setup returned', ok

        if DEBUG_TEST: print 'IgorTest: Check database consistency'
        subprocess.check_call([sys.executable, "-m", "igor", "--check", "--database", cls.igorDir, "--port", str(cls.igorPort)])

        if DEBUG_TEST: print 'IgorTest: Start server'
        cls.igorProcess = subprocess.Popen([sys.executable, "-m", "igor", "--database", cls.igorDir, "--port", str(cls.igorPort)])
        time.sleep(2)
    
    @classmethod
    def tearDownClass(cls):
        # Gracefully stop server
        if DEBUG_TEST: print 'IgorTest: Request server to stop'
        try:
            p = igorVar.IgorServer(cls.igorUrl)
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

        if DEBUG_TEST: print 'IgorTest: Delete database'
        shutil.rmtree(cls.igorDir, True)
        super(IgorTest, cls).tearDownClass()
        pass
        
    def test01_get_static(self):
        p = igorVar.IgorServer(self.igorUrl)
        result = p.get('/')
        self.assertEqual(result, "")
        
    def test02_get_xml(self):
        p = igorVar.IgorServer(self.igorUrl)
        result = p.get('environment/systemHealth', format='application/xml')
        self.assertEqual(result, "")
        
    def test03_get_text(self):
        p = igorVar.IgorServer(self.igorUrl)
        result = p.get('environment/systemHealth', format='text/plain')
        self.assertEqual(result, "")
        
    def test04_get_json(self):
        p = igorVar.IgorServer(self.igorUrl)
        result = p.get('environment/systemHealth', format='application/json')
        self.assertEqual(result, "")
        
if __name__ == '__main__':
    unittest.main()
    
