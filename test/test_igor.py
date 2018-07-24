import unittest
import igorVar
import igorSetup
import igorCA
import os

class IgorTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        super(IgorTest, cls).setUpClass()
        fixtureDir = os.path.abspath(os.path.dirname(__file__))
        cls.igorDir = os.path.join(fixtureDir, 'fixtures', 'testIgor')
        setup = igorSetup.IgorSetup(database=cls.igorDir)
        ok = setup.cmd_initialize()
        print 'setup returned', ok
        # create database
        # check database
        # start server
        print 'hihi setupclass'
        pass
    
    @classmethod
    def tearDownClass(cls):
        # Gracefully stop server
        # kill server
        # delete database
        print 'hihi teardownclass'
        super(IgorTest, cls).tearDownClass()
        pass
        

    def test1(self):
        self.assertEqual(1, 1)
        
if __name__ == '__main__':
    unittest.main()
    
