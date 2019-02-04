from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
import unittest
import os
import sys
import socket
import shutil
import subprocess
import time

FIXTURES=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

class IgorCmdlineTest(unittest.TestCase):
    igorDir = os.path.join(FIXTURES, 'testIgorCmd')
    igorHostname=socket.gethostname()
    igorHostname2='localhost'
    igorPort = 49333
    igorProtocol = "http"
    igorVarArgs = {}
    igorUseCapabilities = False
    credentials = ['--credentials', 'admin:']
    processes = []
    
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(cls.igorDir, True)
        try:
            os.unlink(os.path.join(FIXTURES, 'test_igor_cmdline.log'))
        except:
            pass
        cls.igorUrl = "%s://%s:%d/data/" % (cls.igorProtocol, cls.igorHostname, cls.igorPort)

    @classmethod
    def tearDownClass(cls):
        time.sleep(5)
        for proc in cls.processes:
            if proc.poll() == None:
                print('Warning: process has not terminated, killing it:', proc)
                proc.terminate()
            proc.wait()

    def _runCommand(self, command, options, *args):
        logFile = os.path.join(FIXTURES, 'test_igor_cmdline.log')
        if 'IGOR_TEST_PYTHON' in os.environ:
            cmdHead = [os.environ['IGOR_TEST_PYTHON']]
        else:
            cmdHead = [sys.executable]
        cmd = cmdHead + ["-m", command]  # "igor", "--nologstderr", "--check", "--database", self.igorDir, "--port", str(selg.igorPort)]
        if 'addDir' in options:
            cmd += ["-d", self.igorDir]
        if 'addUrl' in options:
            cmd += ["-u", self.igorUrl]
        if 'addPort' in options:
            cmd += ["-p", str(self.igorPort)]
        if 'addCredentials' in options:
            cmd += self.credentials
        cmd += list(args)
        with open(logFile, 'a') as logFP:
            print('+', ' '.join(cmd), file=logFP)
            logFP.flush()
            if 'async' in options:
                proc = subprocess.Popen(cmd, stdout=logFP, stderr=subprocess.STDOUT)
                self.processes.append(proc)
                return 0
            else:
                return subprocess.call(cmd, stdout=logFP, stderr=subprocess.STDOUT)
    
    def test_200_igorServer_help(self):
        """check igorServer --help"""
        sts = self._runCommand("igor", {}, "--help")
        self.assertEqual(sts, 0)
        
    def test_201_igorSetup_help(self):
        """check igorSetup --help"""
        sts = self._runCommand("igorSetup", {}, "--help")
        self.assertEqual(sts, 0)
        
    def test_202_igorControl_help(self):
        """check igorControl --help"""
        sts = self._runCommand("igorControl", {}, "--help")
        self.assertEqual(sts, 0)
        
    def test_203_igorVar_help(self):
        """check igorVar --help"""
        sts = self._runCommand("igorVar", {}, "--help")
        self.assertEqual(sts, 0)
        
    def test_204_igorCA_help(self):
        """check igorCA --help"""
        sts = self._runCommand("igorCA", {}, "--help")
        self.assertEqual(sts, 0)
        
    def test_205_igorServlet_help(self):
        """check igorServlet --help"""
        sts = self._runCommand("igorServlet", {}, "--help")
        self.assertEqual(sts, 0)

    def test_206_igorSetup_helpcmd(self):
        """check igorSetup help"""
        sts = self._runCommand("igorSetup", {}, "help")
        self.assertEqual(sts, 0)

    def test_207_igorCA_helpcmd(self):
        """check igorCA help"""
        sts = self._runCommand("igorCA", {}, "help")
        self.assertEqual(sts, 0)
        
        
    #
    # NOTE: these are integration tests, not really unittests. From here on the
    # tests need to be run in order.
    #
    
    def test_210_igorSetup_initialize(self):
        """Initialize database"""
        sts = self._runCommand("igorSetup", {"addDir"}, "initialize")
        self.assertEqual(sts, 0)
        
    def test_211_igorSetup_addstd(self):
        """Add standard plugin"""
        sts = self._runCommand("igorSetup", {"addDir"}, "addstd", "systemHealth")
        self.assertEqual(sts, 0)
        
    def test_212_igorSetup_liststd(self):
        """list standard plugins"""
        sts = self._runCommand("igorSetup", {"addDir"}, "liststd")
        self.assertEqual(sts, 0)
        
    def test_213_igorSetup_list(self):
        """list installed plugins"""
        sts = self._runCommand("igorSetup", {"addDir"}, "list")
        self.assertEqual(sts, 0)
        
#    def test_220_igorSetup_certificateSelfsigned(self):
#        """Create self-signed certificate for igor"""
#        sts = self._runCommand("igorSetup", {"addDir"}, "--run", "certificateSelfsigned", "/CN=%s" % self.igorHostname, self.igorHostname, "localhost", "127.0.0.1")
#        self.assertEqual(sts, 0)
        
    def test_230_start_igor(self):
        """Start the igor server"""
        sts = self._runCommand("igor", {"addDir", "addPort", "async"})
        time.sleep(5)
        self.assertEqual(sts, 0)
        
    def test_231_stop_igor(self):
        """Try the igorControl stop command"""
        sts = self._runCommand("igorControl", {"addUrl", "addCredentials"}, "stop")
        self.assertEqual(sts, 0)
        
        
if __name__ == '__main__':
    unittest.main()
    
