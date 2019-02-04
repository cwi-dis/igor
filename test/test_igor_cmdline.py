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

FIXTURES=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

class IgorCmdlineTest(unittest.TestCase):
    igorDir = os.path.join(FIXTURES, 'testIgorCmd')
    igorHostname=socket.gethostname()
    igorHostname2='localhost'
    igorPort = 49333
    igorProtocol = "https"
    igorVarArgs = {}
    igorServerArgs = ["--noCapabilities"]
    igorUseCapabilities = False
    
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
        pass

    def _runCommand(self, command, *args):
        logFile = os.path.join(FIXTURES, 'test_igor_cmdline.log')
        if 'IGOR_TEST_PYTHON' in os.environ:
            cmdHead = [os.environ['IGOR_TEST_PYTHON']]
        else:
            cmdHead = [sys.executable]
        cmd = cmdHead + ["-m", command] + list(args) # "igor", "--nologstderr", "--check", "--database", self.igorDir, "--port", str(selg.igorPort)]
        with open(logFile, 'a') as logFP:
            print('+', ' '.join(cmd), file=logFP, flush=True)
            return subprocess.call(cmd, stdout=logFP, stderr=subprocess.STDOUT)
    
    def test_200_igorServer_help(self):
        """check igorServer --help"""
        sts = self._runCommand("igor", "--help")
        self.assertEqual(sts, 0)
        
    def test_201_igorSetup_help(self):
        """check igorSetup --help"""
        sts = self._runCommand("igorSetup", "--help")
        self.assertEqual(sts, 0)
        
    def test_202_igorControl_help(self):
        """check igorControl --help"""
        sts = self._runCommand("igorControl", "--help")
        self.assertEqual(sts, 0)
        
    def test_203_igorVar_help(self):
        """check igorVar --help"""
        sts = self._runCommand("igorVar", "--help")
        self.assertEqual(sts, 0)
        
    def test_204_igorCA_help(self):
        """check igorCA --help"""
        sts = self._runCommand("igorCA", "--help")
        self.assertEqual(sts, 0)
        
    def test_205_igorServlet_help(self):
        """check igorServlet --help"""
        sts = self._runCommand("igorServlet", "--help")
        self.assertEqual(sts, 0)
        
if __name__ == '__main__':
    unittest.main()
    
