from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
import unittest
import os
import sys
import json
import socket
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
import igorVar
import igorCA
import igorServlet
from .setupAndControl import *

FIXTURES=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

MAX_FLUSH_DURATION=10            # How long we wait for internal actions to be completed
MAX_EXTERNAL_FLUSH_DURATION=0   # How long we wait for external actions to be completed


            
class IgorTest(unittest.TestCase, IgorSetupAndControl):
    igorDir = os.path.join(FIXTURES, 'testIgor')
    igorHostname=socket.gethostname()
    igorHostname2='localhost'
    igorPort = 19333
    igorProtocol = "http"
    igorVarArgs = {}
    igorServerArgs = ["--noCapabilities"]
    igorUseCapabilities = False
    
    @classmethod
    def setUpClass(cls):
        super(IgorTest, cls).setUpClass()
        cls.setUpIgor()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownIgor()
        super(IgorTest, cls).tearDownClass()
       
    def test_001_get_static_jinja(self):
        """GET a static HTML page generated from a template"""
        p = self._igorVar()
        result = p.get('/')
        self.assertTrue(result)
        self.assertEqual(result[0], "<")
        
    def test_001a_get_static_global(self):
        """GET a static page from the global (package) pages"""
        p = self._igorVar()
        result = p.get('/readme.global.txt')
        self.assertEqual(result.count('test01a'), 1)
        
    def test_001b_get_static_local(self):
        """GET a static page from the local (./static in the data dir) pages"""
        p = self._igorVar()
        result = p.get('/readme.txt')
        self.assertEqual(result.count('test01b'), 1)
        
    def test_002_get_static_nonexistent(self):
        """GET a nonexistent static HTML page"""
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.get, '/nonexistent.html')
        
    def test_003_get_internal(self):
        pAdmin = self._igorVar(credentials='admin:')
        result = pAdmin.get('/internal/version')
        self.assertTrue(result)
        
    def test_004_get_internal_fail(self):
        pAdmin = self._igorVar(credentials='admin:')
        self.assertRaises(igorVar.IgorError, pAdmin.get, '/internal/fail')

    def test_005_get_plugin(self):
        pAdmin = self._igorVar(credentials='admin:')
        result = pAdmin.get('/plugin/testPlugin')
        self.assertTrue(result)
            
    def test_006_get_plugin_subpath(self):
        pAdmin = self._igorVar(credentials='admin:')
        result = pAdmin.get('/plugin/testPlugin/method2')
        self.assertTrue(result)
            
    def test_007_get_plugin_fail(self):
        pAdmin = self._igorVar(credentials='admin:')
        self.assertRaises(igorVar.IgorError, pAdmin.get, '/plugin/nonexistent')
            
    def test_009_get_plugin_othername(self):
        pAdmin = self._igorVar(credentials='admin:')
        result = pAdmin.get('/plugin/test2plugin')
        self.assertTrue(result)
            
    def test_011_get_xml(self):
        """GET a database variable as XML"""
        p = self._igorVar()
        result = p.get('environment/systemHealth', format='application/xml')
        self.assertTrue(result)
        root = ET.fromstring(result)
        self.assertEqual(root.tag, "systemHealth")
        
    def test_012_get_text(self):
        """GET a database variable as plaintext"""
        p = self._igorVar()
        result = p.get('environment/systemHealth', format='text/plain')
        self.assertTrue(result)
        
    def test_013_get_json(self):
        """GET a database variable as JSON"""
        p = self._igorVar()
        result = p.get('environment/systemHealth', format='application/json')
        self.assertTrue(result)
        root = json.loads(result)
        self.assertIsInstance(root, dict)
        self.assertEqual(list(root.keys()), ["systemHealth"])
        
    def test_014_get_xml_unknownquery(self):
        p = self._igorVar()
        result = p.get('environment/systemHealth', format='application/xml', query={'unknownKey':'unknownValue'})
        self.assertTrue(result)
        root = ET.fromstring(result)
        self.assertEqual(root.tag, "systemHealth")
        
    @unittest.skip("capabilities-only")
    def test_019_get_disallowed(self):
        """Check that GET on a variable for which you have no capability fails"""

    def test_021_put_xml(self):
        """PUT a database variable as XML"""
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
        
    def test_022_put_text(self):
        """PUT a database variable as plaintext"""
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
        
    def test_023_put_json(self):
        """PUT a database variable as JSON"""
        p = self._igorVar()
        data = json.dumps({"test23" : 23})
        p.put('sandbox/test23', data, datatype='application/json')
        result = p.get('sandbox/test23', format='application/json')
        resultDict = json.loads(result)
        self.assertEqual({"test23" : 23}, resultDict)
        result2 = p.get('sandbox/test23', format='application/xml')
        self.assertEqual("<test23>23</test23>", result2.strip())
        
    def test_024_put_multi(self):
        """PUT a database variable twice and check that it has changed"""
        p = self._igorVar()
        data = '<test24>24</test24>'
        p.put('sandbox/test24', data, datatype='application/xml')
        result = p.get('sandbox/test24', format='application/xml')
        self.assertEqual(data.strip(), result.strip())
        data = '<test24>twentyfour</test24>'
        p.put('sandbox/test24', data, datatype='application/xml')
        result = p.get('sandbox/test24', format='application/xml')
        self.assertEqual(data.strip(), result.strip())
        
    def test_025_get_xpath(self):
        p = self._igorVar()
        data = '<test25><sub1><key>1</key></sub1><sub2a><key>2</key></sub2a><sub2b><key>2</key></sub2b></test25>'
        p.put('sandbox/test25', data, datatype='application/xml')
        result1 = p.get("sandbox/test25//*[key='1']", format="application/json")
        result1value = json.loads(result1)
        self.assertEqual(result1value, {'sub1':{'key':1}})
        result2 = p.get("sandbox/test25//*[key='2']", format="application/json", variant="multi")
        result2value = json.loads(result2)
        self.assertEqual(result2value, [{'ref':'/data/sandbox/test25/sub2a', 'sub2a':{'key':2}}, {'ref':'/data/sandbox/test25/sub2b', 'sub2b':{'key':2}}])
        result3 = p.get("sandbox/test25//*[key='3']", format="application/json", variant="multi")
        result3value = json.loads(result3)
        self.assertEqual(result3value, [])
        
    @unittest.skip("capabilities-only")
    def test_029_put_disallowed(self):
        """Check that PUT on a variable for which you have no capability fails"""

    def test_031_post_text(self):
        """POST a database variable twice and check that both get through"""
        p = self._igorVar()
        p.put('sandbox/test31', '', datatype='text/plain')
        p.post('sandbox/test31/item', 'thirty', datatype='text/plain')
        p.post('sandbox/test31/item', 'one', datatype='text/plain')
        result = p.get('sandbox/test31/item', format='text/plain')
        self.assertEqual('thirtyone', ''.join(result.split()))
        
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
        
    def test_032_delete(self):
        """DELETE a database variable"""
        p = self._igorVar()
        p.put('sandbox/test32', 'thirtytwo', datatype='text/plain')
        result = p.get('sandbox/test32', format='text/plain')
        self.assertEqual(result.strip(), 'thirtytwo')
        p.delete('sandbox/test32')
        self.assertRaises(igorVar.IgorError, p.get, 'sandbox/test32')

    @unittest.skip("capabilities-only")
    def test_039_delete_disallowed(self):
        """Check that DELETE on a variable for which you have no capability fails"""

    @unittest.skip("capabilities-only")
    def test_040_newcap(self):
        """Create a new capability in the default set and check that a PUT now works"""

    @unittest.skip("capabilities-only")
    def test_041_newcap_external(self):
        """Create a new capability, export it, carry it in a request and check that the request is allowed"""

    @unittest.skip("capabilities-only")
    def test_042_list_capabilities(self):
        """Test UI for listing all capabilities"""

    def test_051_internal_dump(self):
        """Call /internal/dump"""
        pAdmin = self._igorVar(credentials='admin:')
        data = pAdmin.get('/internal/dump')
        
    def test_052_internal_log(self):
        """Call /internal/log"""
        pAdmin = self._igorVar(credentials='admin:')
        data = pAdmin.get('/internal/log')
        
    def test_053_internal_help(self):
        """Call /internal/help"""
        pAdmin = self._igorVar(credentials='admin:')
        data = pAdmin.get('/internal/help')
        
    def test_054_evaluate(self):
        """Use evaluate to call an Igor XPath function"""
        pAdmin = self._igorVar(credentials='admin:')
        data = pAdmin.get('/evaluate/igor_upper("lowercase")')
        self.assertEqual(data.count("LOWERCASE"), 1)
        
    def test_055_raw_data(self):
        """Ensure raw database can be accessed, and is larger than non-raw (because of the added elements and attributes)"""
        pAdmin = self._igorVar(credentials='admin:')
        data = pAdmin.get('/data/')
        rawData = pAdmin.get('/data/', query={'.VARIANT' : 'raw'})
        self.assertTrue(not not data)
        self.assertTrue(not not rawData)
        self.assertTrue(len(rawData) > len(data))
        
    def test_056_user_password(self):
        """Ensure that a user with a password can be added, and that user has access to its own data"""
        pAdmin = self._igorVar(credentials='admin:')
        pAdmin.get('/plugin/user/add', query=dict(username='user056', password='password056'))
        pUser = self._igorVar(credentials='user056:password056')
        userData = pUser.get('identities/user056')
        self.assertIn('user056', userData)
        
    @unittest.skip("capabilities-only")
    def test_057_user_password_bad(self):
        """Ensure that a user with a password can be added, and that user has access to its own data, and after changing the password no longer"""

    @unittest.skip("capabilities-only")
    def test_058_user_capability(self):
        """Ensure that we can delegate a capability to a user, transfer it and revoke it again"""

    @unittest.skip("capabilities-only")
    def test_059_user_capability_recursive_revoke(self):
        """Ensure that we can delegate a capability to a user, delegate that to another user, it and revoke it again"""

    def test_061_call_action(self):
        """GET an action from external and check that it is executed"""
        pAdmin = self._igorVar(credentials='admin:')
        optBearerToken = self._create_cap_for_call(pAdmin, 'test61action')
        p = self._igorVar(**optBearerToken)
        content = {'test61':{'data' : '0'}}
        action = {'action':dict(name='test61action', url='/data/sandbox/test61/data', method='PUT', data='{/data/sandbox/test61/data + 1}')}
        pAdmin.put('sandbox/test61', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

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
        """Create capability required to GET an action from extern"""
        return {}
        
    def test_062_call_external(self):
        """GET an action on the external servlet directly"""
        pAdmin = self._igorVar(credentials='admin:')
        newCapID = self._create_caps_for_action(pAdmin, None, obj='/api', get='child', put='child', delegate='external')
        optBearerToken = self._export_cap_for_servlet(pAdmin, newCapID)
        p = self._igorVar(server=self.servletUrl, **optBearerToken)
        # Set internally, get externally
        self.servlet.set('sixtytwo')
        self.servlet.startTimer()
        value = p.get('/api/get')
        duration = self.servlet.waitDuration()
        self.assertEqual(value, '"sixtytwo"')
        self.assertNotEqual(duration, None)
        # Set externally, get internally
        p.put('/api/set', 'sixty-two', datatype='text/plain')
        value = self.servlet.get()
        self.assertEqual(value, 'sixty-two')
        
    def _export_cap_for_servlet(self, pAdmin, newCapID):
        """Export a capability for the servlet audience"""
        return {}
        
    def test_063_call_action_external(self):
        """GET an action that does a GET on the external servlet"""
        pAdmin = self._igorVar(credentials='admin:')

        action = {'action':dict(name='test63action', url=self.servletUrl+'/api/get')}
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self._create_caps_for_action(pAdmin, 'test63action', obj='/api/get', get='self', delegate='external')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        optBearerToken = self._create_cap_for_call(pAdmin, 'test63action')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p = self._igorVar(**optBearerToken)
        
        self.servlet.startTimer()
        p.get('/action/test63action')

        duration = self.servlet.waitDuration()
        self.assertNotEqual(duration, None)
        
    def test_064_call_plugin_action(self):
        """Check that calling a plugin action works"""
        pAdmin = self._igorVar(credentials='admin:')
        result = pAdmin.get('/action/testPlugin/add-tested')
        self.assertTrue(result)
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        result = pAdmin.get('devices/testPlugin/tested')
        self.assertTrue(result)

    @unittest.skip("capabilities-only")
    def test_068_call_external_disallowed(self):
        """Check that a call to the external servlet without a correct capability fails"""

    @unittest.skip("capabilities-only")
    def test_069_call_action_external_disallowed(self):    
        """Check that an action calling to the external servlet without a correct capability fails"""
        
    def test_071_action(self):
        """Check that a PUT action runs when the trigger variable is updated"""
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test71':{'src':'', 'sink':''}}
        action = {'action':dict(name='test71action', url='/data/sandbox/test71/sink', xpath='/data/sandbox/test71/src', method='PUT', data='copy-{.}-copy')}
        p.put('sandbox/test71', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        
        p.put('sandbox/test71/src', 'seventy-one', datatype='text/plain')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        
        result = p.get('sandbox/test71', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test71':{'src':'seventy-one', 'sink':'copy-seventy-one-copy'}}
        self.assertEqual(resultDict, wantedContent)
        
    def test_072_action_post(self):
        """Check that a POST action runs when the trigger variable is updated"""
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
        
    def test_073_action_indirect(self):
        """Check that an action can run another action when the trigger variable is updated"""
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

    def test_074_action_external_get(self):
        """Check that triggering an action that GETs an external action works"""
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test74':{'src':'', 'sink':''}}
        action1 = {'action':dict(name='test74first', url=self.servletUrl+'/api/get', xpath='/data/sandbox/test74/src')}
        p.put('sandbox/test74', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self._create_caps_for_action(pAdmin, 'test74first', obj='/api/get', get='self')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        
        self.servlet.startTimer()
        p.put('sandbox/test74/src', 'seventy-four', datatype='text/plain')
        
        duration = self.servlet.waitDuration()
        if DEBUG_TEST: print('IgorTest: indirect external action took', duration, 'seconds')
        self.assertNotEqual(duration, None)

    def _create_caps_for_action(self, pAdmin, caller, obj, **kwargs):
        """Create capability so that action caller can GET an external action"""
        pass
                
    def test_075_action_external_get_arg(self):
        """Check that triggering an action that GETs an external action with a variable works"""
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test75':{'src':''}}
        action1 = {'action':dict(name='test75first', url=self.servletUrl+'/api/set?value={.}', method='GET', xpath='/data/sandbox/test75/src')}
        p.put('sandbox/test75', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self._create_caps_for_action(pAdmin, 'test75first', obj='/api/set', get='self')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self.servlet.startTimer()
        p.put('sandbox/test75/src', 'seventy-five', datatype='text/plain')
        
        duration = self.servlet.waitDuration()
        self.assertNotEqual(duration, None)
        if DEBUG_TEST: print('IgorTest: indirect external action took', duration, 'seconds')
        result = self.servlet.get()
        self.assertEqual(result, 'seventy-five')
        
    def test_076_action_external_put(self):
        """Check that triggering an action that PUTs an external action with a variable works"""
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test76':{'src':''}}
        action1 = {'action':dict(name='test76first', url=self.servletUrl+'/api/set', method='PUT', mimetype='text/plain', data='{.}', xpath='/data/sandbox/test76/src')}
        p.put('sandbox/test76', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self._create_caps_for_action(pAdmin, 'test76first', obj='/api/set', put='self')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self.servlet.startTimer()
        p.put('sandbox/test76/src', 'seventy-six', datatype='text/plain')
        
        duration = self.servlet.waitDuration()
        self.assertNotEqual(duration, None)
        if DEBUG_TEST: print('IgorTest: indirect external action took', duration, 'seconds')
        result = self.servlet.get()
        self.assertEqual(result, 'seventy-six')
        
    def test_081_call_plugin(self):
        """Test that a plugin can run, and read and write the database"""
        pAdmin = self._igorVar(credentials='admin:')
        optBearerToken = self._create_cap_for_plugin(pAdmin, 'copytree')
        p = self._igorVar(**optBearerToken)
        content = {'test81' : {'src':'eighty-one', 'sink':''}}
        p.put('sandbox/test81', json.dumps(content), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.get('/plugin/copytree', query=dict(src='/data/sandbox/test81/src', dst='/data/sandbox/test81/sink'))
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        result = p.get('sandbox/test81', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test81':{'src':'eighty-one', 'sink':'eighty-one'}}
        self.assertEqual(resultDict, wantedContent)

    def _create_cap_for_plugin(self, pAdmin, callee):
        """Create capability required to GET a plugin from extern"""
        return {}

    def test_082_call_action_plugin(self):
        """Test that an action can run a plugin, and that plugin can read and write the database"""
        pAdmin = self._igorVar(credentials='admin:')
        optBearerToken = self._create_cap_for_call(pAdmin, 'test82action')
        p = self._igorVar(**optBearerToken)
        content = {'test82' : {'src':'eighty-two', 'sink':''}}
        action = {'action':dict(name='test82action', url='/plugin/copytree?src=/data/sandbox/test82/src&dst=/data/sandbox/test82/sink')}
        pAdmin.put('sandbox/test82', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        self._create_cap_for_plugin_for_action(pAdmin, 'test82action', 'copytree')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        p.get('/action/test82action')
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        result = p.get('sandbox/test82', format='application/json')
        resultDict = json.loads(result)
        wantedContent = {'test82':{'src':'eighty-two', 'sink':'eighty-two'}}
        self.assertEqual(resultDict, wantedContent)

    def _create_cap_for_plugin_for_action(self, pAdmin, caller, callee):
        pass
                
    def test_083_plugin_access(self):
        """Test that a plugin can read and write its own /data/devices/ data"""
        pAdmin = self._igorVar(credentials="admin:")
        content = {"test84" : "eigthy-four"}
        pAdmin.put("devices/testPlugin/outgoing", json.dumps(content), "application/json")
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        result = pAdmin.get("devices/testPlugin/incoming", format="application/json")
        resultDict = json.loads(result)
        self.assertEqual(resultDict, {'incoming':content})
        
    def test_084_install_all_stdplugins(self):
        """Test that most standard plugins can be installed and removed"""
        pAdmin = self._igorVar(credentials='admin:')
        dontInstall = ["ble"] # Requires Bluetooth hardware
        txtInstalled = pAdmin.get('/internal/pluginControl/list')
        pluginsInstalled = eval(txtInstalled)
        txtStandard = pAdmin.get('/internal/pluginControl/liststd')
        pluginsAvailable = eval(txtStandard)
        added = []
        for p in pluginsAvailable:
            if not p in pluginsInstalled+dontInstall:
                ok = pAdmin.get('/internal/pluginControl/installstd', query=dict(pluginName=p))
                added.append(p)
        for p in added:
            ok = pAdmin.get('/internal/pluginControl/uninstall', query=dict(pluginName=p))
            
    def test_085_plugin_management_page(self):
        """Test that plugin management UI can be accessed"""
        pAdmin = self._igorVar(credentials='admin:')
        pageContent = pAdmin.get('/plugins.html')
        # Determine whether the page has rendered correctly by counting the number of times the systemHealt plugin is referenced
        # in the text. The numbers have been determined experimentally.
        self.assertEqual(pageContent.count('testPlugin'), 9)        
        self.assertEqual(pageContent.count('/testPlugin'), 2)        

    def test_086_plugin_page(self):
        """Test that we can access a plugin template page, and that that page can access the plugin object"""
        pAdmin = self._igorVar(credentials='admin:')
        pageContent = pAdmin.get('/plugin/test2plugin/page/_testpage.html')
        self.assertEqual(pageContent.count('test2plugintail'), 1)
        
    def test_087_plugin_script(self):
        """Test that we can run a plugin script. Additionally, test that the pluginscript can call updateStatus."""
        pAdmin = self._igorVar(credentials='admin:')
        pageContent = pAdmin.get('/plugin/test2plugin/script/concatwithname', query=dict(arg="tail"))
        self.assertEqual(pageContent.count('test2plugintail'), 1)

@unittest.skip("https is tested by IgorTestCaps")
class IgorTestHttps(IgorTest):
    igorDir = os.path.join(FIXTURES, 'testIgorHttps')
    igorPort = 29333
    igorProtocol = "https"
    igorServerArgs = ["--noCapabilities"]
    
class IgorTestCaps(IgorTest):
    igorDir = os.path.join(FIXTURES, 'testIgorCaps')
    igorPort = 39333
    igorProtocol = "https"
    igorServerArgs = ["--capabilities"]
    igorUseCapabilities = True

    def test_019_get_disallowed(self):
        """Check that GET on a variable for which you have no capability fails"""
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.get, 'identities', format='application/xml')
        # Check that the access failure is recorded correctly
        self.assertEqual(p.get("services/igor/accessFailures/accessFailure[requestPath='/data/identities']/operation", format="text/plain"), "get\n")
        
    def test_029_put_disallowed(self):
        """Check that PUT on a variable for which you have no capability fails"""
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.put, 'environment/systemHealth/test29', 'twentynine', datatype='text/plain')
        # Check that the access failure is recorded correctly
        self.assertEqual(p.get("services/igor/accessFailures/accessFailure[requestPath='/data/environment/systemHealth/test29']/operation", format="text/plain"), "post\n")
        
    def test_039_delete_disallowed(self):
        """Check that DELETE on a variable for which you have no capability fails"""
        p = self._igorVar()
        self.assertRaises(igorVar.IgorError, p.delete, 'environment/systemHealth')
        # Check that the access failure is recorded correctly
        self.assertEqual(p.get("services/igor/accessFailures/accessFailure[requestPath='/data/environment/systemHealth']/operation", format="text/plain"), "delete\n")
        
    def _new_capability(self, pAdmin, **kwargs):
        """Create a new capability and return its cid"""
        argStr = urllib.parse.urlencode(kwargs)
        rv = pAdmin.get('/internal/accessControl/newToken?' + argStr)
        return rv.strip()
        
    def test_040_newcap(self):
        """Create a new capability in the default set and check that a PUT now works"""
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
        """Create a new secret shared key between the issuer and an audience or subject"""
        argStr = urllib.parse.urlencode(kwargs)
        try:
            rv = pAdmin.get('/internal/accessControl/createSharedKey?' + argStr)
            return rv.strip()
        except igorVar.IgorError:
            if DEBUG_TEST: print('(shared key already exists for %s)' % repr(kwargs))
        return None
        
    def test_041_newcap_external(self):
        """Create a new capability, export it, carry it in a request and check that the request is allowed"""
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

    def test_042_list_capabilities(self):
        """Test UI for listing all capabilities"""
        pAdmin = self._igorVar(credentials='admin:')
        result = pAdmin.get('/capabilities.html')
        # The following value has been determined experimentally:
        self.assertEqual(result.count('default-status'), 4)

    def test_057_user_password_bad(self):
        """Ensure that a user with a password can be added, and that user has access to its own data, and after changing the password no longer"""
        pAdmin = self._igorVar(credentials='admin:')
        pUser = self._igorVar(credentials='user057:password057')
        pAdmin.get('/plugin/user/add', query=dict(username='user057', password='notpassword057'))
        self.assertRaises(igorVar.IgorError, pUser.get, 'identities/user057')
        pAdmin.get('/plugin/user/password', query=dict(username='user057', password='password057'))
        userData = pUser.get('identities/user057')
        self.assertIn('user057', userData)
        
    def test_058_user_capability(self):
        """Ensure that we can delegate a capability to a user, transfer it and revoke it again"""
        pAdmin = self._igorVar(credentials='admin:')
        pUser = self._igorVar(credentials='user058:password058')
        pUser2 = self._igorVar(credentials='user058a:password058a')
        pAdmin.get('/plugin/user/add', query=dict(username='user058', password='password058'))
        pAdmin.get('/plugin/user/add', query=dict(username='user058a', password='password058a'))
        # Check that neither can access identities
        self.assertRaises(igorVar.IgorError, pUser.get, 'identities')
        self.assertRaises(igorVar.IgorError, pUser2.get, 'identities')
        newCapID = self._new_capability(pAdmin,
            tokenId='admin-data',
            newOwner='/data/identities/user058',
            newPath='/data/identities',
            get='self'
            )
        # Check that user1 can now access identities and user2 cannot.
        data = pUser.get('identities')
        self.assertIn('user058a', data)
        self.assertRaises(igorVar.IgorError, pUser2.get, 'identities')
        # Transfer capability to user2
        pUser.get('/internal/accessControl/passToken', query=dict(tokenId=newCapID, newOwner='/data/identities/user058a'))
        # Check that user1 can now access identities and user2 cannot.
        data = pUser2.get('identities')
        self.assertIn('user058', data)
        self.assertRaises(igorVar.IgorError, pUser.get, 'identities')
        # Revoke the capability
        pAdmin.get('/internal/accessControl/revokeToken', query=dict(tokenId=newCapID, parentId='admin-data'))
        # Check that neither can access identities
        self.assertRaises(igorVar.IgorError, pUser.get, 'identities')
        self.assertRaises(igorVar.IgorError, pUser2.get, 'identities')
        
    def test_059_user_capability_recursive_revoke(self):
        """Ensure that we can delegate a capability to a user, delegate that to another user, it and revoke it again"""
        pAdmin = self._igorVar(credentials='admin:')
        pUser = self._igorVar(credentials='user059:password059')
        pUser2 = self._igorVar(credentials='user059a:password059a')
        pAdmin.get('/plugin/user/add', query=dict(username='user059', password='password059'))
        pAdmin.get('/plugin/user/add', query=dict(username='user059a', password='password059a'))
        # Check that neither can access identities
        self.assertRaises(igorVar.IgorError, pUser.get, 'identities')
        self.assertRaises(igorVar.IgorError, pUser2.get, 'identities')
        newCapID = self._new_capability(pAdmin,
            tokenId='admin-data',
            newOwner='/data/identities/user059',
            newPath='/data/identities',
            get='self',
            delegate='1'
            )
        # Delegate to user2
        newCapID2 = self._new_capability(pUser,
            tokenId=newCapID,
            newOwner='/data/identities/user059a',
            newPath='/data/identities',
            get='self'
            )
        # Check that both can access
        data = pUser.get('identities')
        self.assertIn('user059a', data)
        data = pUser2.get('identities')
        self.assertIn('user059', data)
        # Revoke the original capability
        pAdmin.get('/internal/accessControl/revokeToken', query=dict(tokenId=newCapID, parentId='admin-data'))
        # Check that neither can access identities
        self.assertRaises(igorVar.IgorError, pUser.get, 'identities')
        self.assertRaises(igorVar.IgorError, pUser2.get, 'identities')

    def test_068_call_external_disallowed(self):
        """Check that a call to the external servlet without a correct capability fails"""
        p = self._igorVar(server=self.servletUrl)
        self.servlet.set('sixtytwo')
        self.assertRaises(igorVar.IgorError, p.get, '/api/get')

    def test_069_call_action_external_disallowed(self):    
        """Check that an action calling to the external servlet without a correct capability fails"""
        pAdmin = self._igorVar(credentials='admin:')

        action = {'action':dict(name='test69action', url=self.servletUrl+'/api/get')}
        actionPath = pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        optBearerToken = self._create_cap_for_call(pAdmin, 'test69action')
        p = self._igorVar(**optBearerToken)
        
        self.servlet.startTimer()
        p.get('/action/test69action')

        duration = self.servlet.waitDuration()
        self.assertEqual(duration, None)
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)
        # Check that the access failure is recorded correctly
        self.assertEqual(p.get("services/igor/accessFailures/accessFailure[action='%s']/operation" % actionPath.strip(), format="text/plain"), "get\n")

    # xxxjack need a test that an action can use privilege escalation (by carrying the required capabiity)

    # xxxjack need a test that a plugin can use privilege escalation (by carrying the required capabiity)

    def _create_cap_for_call(self, pAdmin, callee):
        """Create capability required to GET an action from extern"""
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
        
    def _create_cap_for_plugin(self, pAdmin, callee):
        """Create capability required to GET a plugin from extern"""
        newCapID = self._new_capability(pAdmin, 
            tokenId='admin-plugin', 
            newOwner='/data/identities/admin', 
            newPath='/plugin/%s' % callee,
            get='self',
            delegate='1'
            )
        self._new_sharedkey(pAdmin, sub='localhost')
        bearerToken = pAdmin.get('/internal/accessControl/exportToken?tokenId=%s&subject=localhost' % newCapID)        
        return {'bearer_token' : bearerToken }
        
    def _create_cap_for_plugin_for_action(self, pAdmin, caller, callee):
        """Create capability so action caller can call a plugin"""
        newCapID = self._new_capability(pAdmin, 
            tokenId='admin-plugin', 
            newOwner="/data/actions/action[name='%s']" % caller,
            newPath='/plugin/%s' % callee,
            get='self',
            )
        return newCapID
                
    def _create_caps_for_action(self, pAdmin, caller, obj, delegate='1', **kwargs):
        """Create capability so that action caller can GET an external action"""
        igorIssuer = pAdmin.get('/internal/accessControl/getSelfIssuer')
        audience = self.servletUrl
        if not self.servlet.hasIssuer():
            newKey = self._new_sharedkey(pAdmin, aud=audience)
            self.servlet.setIssuer(igorIssuer, newKey)
        if caller:
            newOwner = "/data/actions/action[name='%s']" % caller
        else:
            newOwner = "/data/identities/admin"
        newCapID = self._new_capability(pAdmin, 
            tokenId='external', 
            newOwner=newOwner, 
            newPath=obj,
            aud=audience,
            iss=igorIssuer,
            delegate=delegate,
            **kwargs
            )
        return newCapID
        
    def _export_cap_for_servlet(self, pAdmin, newCapID):
        """Export a capability for a given audience/subject"""
        audience = self.servletUrl
        if not self.servlet.hasIssuer():
            newKey = self._new_sharedkey(pAdmin, aud=audience)
            self.servlet.setIssuer(igorIssuer, newKey)
        bearerToken = pAdmin.get('/internal/accessControl/exportToken?tokenId=%s&subject=localhost&aud=%s' % (newCapID, audience))
        return {'bearer_token' : bearerToken }

if __name__ == '__main__':
    unittest.main()
    
