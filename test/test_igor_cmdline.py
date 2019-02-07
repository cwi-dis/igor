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
    igorProtocol = "https"
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
            certFileName = os.path.join(self.igorDir, "igor.crt")
            if os.path.exists(certFileName):
                cmd += ["--certificate", certFileName]
        cmd += list(args)
        with open(logFile, 'a') as logFP:
            print('+', ' '.join(cmd), file=logFP)
            logFP.flush()
            if 'read' in options:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=logFP, universal_newlines=True)
                rv = proc.communicate()
                proc.wait()
                return rv[0]
            elif 'async' in options:
                proc = subprocess.Popen(cmd, stdout=logFP, stderr=subprocess.STDOUT)
                self.processes.append(proc)
                return 0
            else:
                return subprocess.call(cmd, stdout=logFP, stderr=subprocess.STDOUT)
    
    def test_200_igorServer_help(self):
        """check igorServer --help"""
        data = self._runCommand("igor", {"read"}, "--help")
        self.assertIn("show this help message", data)
        
    def test_201_igorSetup_help(self):
        """check igorSetup --help"""
        data = self._runCommand("igorSetup", {"read"}, "--help")
        self.assertIn("show this help message", data)
        
    def test_202_igorControl_help(self):
        """check igorControl --help"""
        data = self._runCommand("igorControl", {"read"}, "--help")
        self.assertIn("show this help message", data)
        
    def test_203_igorVar_help(self):
        """check igorVar --help"""
        data = self._runCommand("igorVar", {"read"}, "--help")
        self.assertIn("show this help message", data)
        
    def test_204_igorCA_help(self):
        """check igorCA --help"""
        data = self._runCommand("igorCA", {"read"}, "--help")
        self.assertIn("show this help message", data)
        
    def test_205_igorServlet_help(self):
        """check igorServlet --help"""
        data = self._runCommand("igorServlet", {"read"}, "--help")
        self.assertIn("show this help message", data)

    def test_206_igorSetup_helpcmd(self):
        """check igorSetup help"""
        data = self._runCommand("igorSetup", {"read"}, "help")
        self.assertIn("help - this message", data)

    def test_207_igorCA_helpcmd(self):
        """check igorCA help"""
        data = self._runCommand("igorCA", {"read"}, "help")
        self.assertIn("Show list of available commands", data)
        
        
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
        
    def test_220_igorSetup_certificateSelfsigned(self):
        """Create self-signed certificate for igor"""
        if self.igorProtocol == "http":
            raise unittest.SkipTest("no https support tested")
        sts = self._runCommand("igorSetup", {"addDir"}, "--run", "certificateSelfsigned", "/CN=%s" % self.igorHostname, self.igorHostname, "localhost", "127.0.0.1")
        self.assertEqual(sts, 0)
        
    def test_230_start_igor(self):
        """Start the igor server"""
        sts = self._runCommand("igor", {"addDir", "addPort", "async"})
        time.sleep(5)
        self.assertEqual(sts, 0)
        
    def test_241_igorControl_helpcmd(self):
        """Try the igorControl help command"""
        data = self._runCommand("igorControl", {"addUrl", "addCredentials", "data", "read"}, "help")
        self.assertIn("Show list of all internal commands", data)
        
    def test_242_igorControl_save(self):
        """Try the igorControl save command"""
        sts = self._runCommand("igorControl", {"addUrl", "addCredentials"}, "save")
        self.assertEqual(sts, 0)
        
    def test_243_igorControl_dump(self):
        """Try the igorControl dump command"""
        sts = self._runCommand("igorControl", {"addUrl", "addCredentials"}, "dump")
        self.assertEqual(sts, 0)
        
    def test_244_igorControl_log(self):
        """Try the igorControl log command"""
        sts = self._runCommand("igorControl", {"addUrl", "addCredentials"}, "log")
        self.assertEqual(sts, 0)
        
    def test_245_igorControl_flush(self):
        """Try the igorControl flush command"""
        sts = self._runCommand("igorControl", {"addUrl", "addCredentials"}, "flush")
        self.assertEqual(sts, 0)
        
    def test_251_igorVar_put_text(self):
        """Use igorVar to put a text/plain value"""
        sts = self._runCommand("igorVar", {"addUrl", "addCredentials"}, "--put", "text/plain", "--data", "text data", "sandbox/text")
        self.assertEqual(sts, 0)

    def test_252_igorVar_put_json(self):
        """Use igorVar to put a application/json value"""
        sts = self._runCommand("igorVar", {"addUrl", "addCredentials"}, "--put", "application/json", "--data", '{"json" : "json data"}', "sandbox/json")
        self.assertEqual(sts, 0)

    def test_253_igorVar_put_xml(self):
        """Use igorVar to put a application/xml value"""
        sts = self._runCommand("igorVar", {"addUrl", "addCredentials"}, "--put", "application/xml", "--data", "<xml>xml data</xml>", "sandbox/xml")
        self.assertEqual(sts, 0)

    def test_254_igorVar_post_text(self):
        """Use igorVar to post two text/plain values"""
        sts = self._runCommand("igorVar", {"addUrl", "addCredentials"}, "--post", "text/plain", "--data", "first post text", "sandbox/posttext")
        self.assertEqual(sts, 0)
        sts = self._runCommand("igorVar", {"addUrl", "addCredentials"}, "--post", "text/plain", "--data", "second post text", "sandbox/posttext")
        self.assertEqual(sts, 0)

    def test_261_igorVar_get_text(self):
        """Use igorVar to get a plaintext value for all three values stored above"""
        data = self._runCommand("igorVar", {"addUrl", "addCredentials", "read"}, "--mimetype", "text/plain", "sandbox/text")
        self.assertIn("text data", data)
        data = self._runCommand("igorVar", {"addUrl", "addCredentials", "read"}, "--mimetype", "text/plain", "sandbox/json")
        self.assertIn("json data", data)
        data = self._runCommand("igorVar", {"addUrl", "addCredentials", "read"}, "--mimetype", "text/plain", "sandbox/xml")
        self.assertIn("xml data", data)
        data = self._runCommand("igorVar", {"addUrl", "addCredentials", "read"}, "--mimetype", "text/plain", "sandbox/posttext")
        self.assertIn("first post text", data)
        self.assertIn("second post text", data)

    def test_299_stop_igor(self):
        """Try the igorControl stop command"""
        sts = self._runCommand("igorControl", {"addUrl", "addCredentials"}, "stop")
        self.assertEqual(sts, 0)
        
        
if __name__ == '__main__':
    unittest.main()
    
