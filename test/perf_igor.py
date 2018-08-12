import os
import json
import socket
import urllib
import xml.etree.ElementTree as ET
import igorVar
import igorCA
import igorServlet
from setupAndControl import *

FIXTURES=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

#MAX_FLUSH_DURATION=10            # How long we wait for internal actions to be completed
#MAX_EXTERNAL_FLUSH_DURATION=0   # How long we wait for external actions to be completed

MEASUREMENT_DURATION=3
            
class IgorPerf(IgorSetupAndControl):
    igorDir = os.path.join(FIXTURES, 'perfIgor')
    igorLogFile = os.path.join(FIXTURES, 'perfIgor.log')
    igorHostname=socket.gethostname()
    igorHostname2='localhost'
    igorPort = 19433
    igorProtocol = "http"
    igorVarArgs = {}
    igorServerArgs = []
    igorUseCapabilities = False
    
    @classmethod
    def setUpClass(cls):
        cls.setUpIgor()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownIgor()
       
    def __init__(self):
        self.startTime = None
        self.measurements = []
        self.startMeasurement = None
        
    def run(self):
        allPerf = filter(lambda x: x.startswith('perf'), dir(self))
        allPerf.sort()
        for name in allPerf:
            method = getattr(self, name)
            method()
            self._perfStop(name)
            
    def _perfStart(self):
        assert self.startTime == None
        self.startTime = time.time()
        self.measurements = []
        
    def _perfStop(self, name):
        print '%-50s %5d %6.3f' % (self.__class__.__name__ + '.' + name, len(self.measurements), sum(self.measurements)/len(self.measurements))
        self.startTime = None
        
    def _measurementStart(self):
        assert self.startMeasurement == None
        self.startMeasurement = time.time()
        
    def _measurementStop(self):
        assert self.startMeasurement
        duration = time.time() - self.startMeasurement
        self.startMeasurement = None
        self.measurements.append(duration)
        return time.time() - self.startTime > MEASUREMENT_DURATION
        
    def perf01_get_static(self):
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('/')
            if self._measurementStop():
                break
        
    def perf02_get_static_nonexistent(self):
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            try:
                result = p.get('/nonexistent.html')
            except igorVar.IgorError:
                pass
            if self._measurementStop():
                break
        
    def perf11_get_xml(self):
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('environment/systemHealth', format='application/xml')
            if self._measurementStop():
                break
        
    def perf12_get_text(self):
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('environment/systemHealth', format='text/plain')
            if self._measurementStop():
                break
        
    def perf13_get_json(self):
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('environment/systemHealth', format='application/json')
            if self._measurementStop():
                break
        
    def perf21_put_xml(self):
        p = self._igorVar()
        data = '<test21>21</test21>'
        self._perfStart()
        while True:
            self._measurementStart()
            p.put('sandbox/test21', data, datatype='application/xml')
            if self._measurementStop():
                break
        
    def perf22_put_text(self):
        p = self._igorVar()
        data = 'twenty two'
        self._perfStart()
        while True:
            self._measurementStart()
            p.put('sandbox/test22', data, datatype='text/plain')
            if self._measurementStop():
                break
        
    def perf23_put_json(self):
        p = self._igorVar()
        data = json.dumps({"test23" : 23})
        self._perfStart()
        while True:
            self._measurementStart()
            p.put('sandbox/test23', data, datatype='application/json')
            if self._measurementStop():
                break
        
    def perf31_post_text(self):
        p = self._igorVar()
        p.put('sandbox/test31', '', datatype='text/plain')
        data = 'twenty two'
        self._perfStart()
        while True:
            self._measurementStart()
            p.post('sandbox/test31/item', 'thirtyone', datatype='text/plain')
            if self._measurementStop():
                break
        
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

    def _create_caps_for_action(self, pAdmin, caller, obj, **kwargs):
        pass
        
    def test74_action_external_get(self):
        pAdmin = self._igorVar(credentials='admin:')
        p = self._igorVar()
        content = {'test74':{'src':'', 'sink':''}}
        action1 = {'action':dict(name='test74first', url=self.servletUrl+'/api/get', xpath='/data/sandbox/test74/src')}
        p.put('sandbox/test74', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')

        self._create_caps_for_action(pAdmin, 'test74first', obj='/api/get', get='self')
        
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
        action1 = {'action':dict(name='test75first', url=self.servletUrl+'/api/set?value={.}', method='GET', xpath='/data/sandbox/test75/src')}
        p.put('sandbox/test75', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')

        self._create_caps_for_action(pAdmin, 'test75first', obj='/api/set', get='self')
        
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
        action1 = {'action':dict(name='test76first', url=self.servletUrl+'/api/set', method='PUT', mimetype='text/plain', data='{.}', xpath='/data/sandbox/test76/src')}
        p.put('sandbox/test76', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action1), datatype='application/json')

        self._create_caps_for_action(pAdmin, 'test76first', obj='/api/set', put='self')
        
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self.servlet.startTimer()
        p.put('sandbox/test76/src', 'seventy-six', datatype='text/plain')
        
        duration = self.servlet.waitDuration()
        self.assertNotEqual(duration, None)
        if DEBUG_TEST: print 'IgorTest: indirect external action took', duration, 'seconds'
        result = self.servlet.get()
        self.assertEqual(result, 'seventy-six')
        
class IgorPerfHttps(IgorPerf):
    igorDir = os.path.join(FIXTURES, 'testIgorHttps')
    igorLogFile = os.path.join(FIXTURES, 'testIgorHttps.log')
    igorPort = 29333
    igorProtocol = "https"
    
class IgorPerfCaps(IgorPerfHttps):
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
            return rv.strip()
        except igorVar.IgorError:
            if DEBUG_TEST: print '(shared key already exists for %s)' % repr(kwargs)
        return None
        
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
        
    def _create_caps_for_action(self, pAdmin, caller, obj, **kwargs):
        igorIssuer = pAdmin.get('/internal/accessControl/getSelfIssuer')
        audience = self.servletUrl
        if not self.servlet.hasIssuer():
            newKey = self._new_sharedkey(pAdmin, aud=audience)
            self.servlet.setIssuer(igorIssuer, newKey)
        newCapID = self._new_capability(pAdmin, 
            tokenId='external', 
            newOwner="/data/actions/action[name='%s']" % caller, 
            newPath=obj,
            aud=audience,
            iss=igorIssuer,
            delegate='1',
            **kwargs
            )
        
def main():
    for cls in [IgorPerf, IgorPerfHttps, IgorPerfCaps]:
        try:
            print '%s:' % cls.__name__
            cls.setUpClass()
            obj = cls()
            obj.run()
        finally:
            cls.tearDownClass()
            
if __name__ == '__main__':
    main()
    
