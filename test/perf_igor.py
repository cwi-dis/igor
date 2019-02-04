from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from past.utils import old_div
import os
import sys
import json
import socket
import urllib.request, urllib.parse, urllib.error
import math
import argparse
import xml.etree.ElementTree as ET
import igorVar
import igorCA
import igorServlet
from .setupAndControl import *

FIXTURES=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

MAX_FLUSH_DURATION=10            # How long we wait for internal actions to be completed
#MAX_EXTERNAL_FLUSH_DURATION=0   # How long we wait for external actions to be completed

MEASUREMENT_MIN_DURATION=2
MEASUREMENT_MIN_COUNT=10

def _meanAndSigma(measurements):
    mean = old_div(sum(measurements),len(measurements))
    sumSquares = sum([(x-mean)**2 for x in measurements])
    sigma = math.sqrt(old_div(sumSquares,(len(measurements)-1)))
    return mean, sigma
            
class IgorPerf(IgorSetupAndControl):
    igorDir = os.path.join(FIXTURES, 'perfIgor')
    igorHostname=socket.gethostname()
    igorHostname2='localhost'
    igorPort = 19433
    igorProtocol = "http"
    igorVarArgs = {}
    igorServerArgs = ["--noCapabilities"]
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
        allPerf = [x for x in dir(self) if x.startswith('perf')]
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
        mean, sigma = _meanAndSigma(self.measurements)
        print('%-50s %5d %6.3f %6.3f' % (self.__class__.__name__ + '.' + name, len(self.measurements), mean, sigma))
        self.startTime = None
        
    def _measurementStart(self):
        assert self.startMeasurement == None
        self.startMeasurement = time.time()
        
    def _measurementStop(self, duration = None):
        assert self.startMeasurement
        if duration is None:
            duration = time.time() - self.startMeasurement
        self.startMeasurement = None
        self.measurements.append(duration)
        return (time.time() - self.startTime >= MEASUREMENT_MIN_DURATION) and (len(self.measurements) >= MEASUREMENT_MIN_COUNT)
        
    def perf01_get_static(self):
        """GET a static HTML page"""
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('/apple-touch-icon.png')
            if self._measurementStop():
                break
        
    def perf02_get_static_nonexistent(self):
        """GET a nonexistent static HTML page"""
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            try:
                result = p.get('/nonexistent.html')
            except igorVar.IgorError:
                pass
            else:
                assert 0, 'accessing nonexistent.html did not raise an IgorError exception'
            if self._measurementStop():
                break
        
    def perf11_get_xml(self):
        """GET a database variable as XML"""
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('environment/systemHealth', format='application/xml')
            if self._measurementStop():
                break
        
    def perf12_get_text(self):
        """GET a database variable as plaintext"""
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('environment/systemHealth', format='text/plain')
            if self._measurementStop():
                break
        
    def perf13_get_json(self):
        """GET a database variable as JSON"""
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('environment/systemHealth', format='application/json')
            if self._measurementStop():
                break
        
    def perf21_put_xml(self):
        """PUT a database variable as XML"""
        p = self._igorVar()
        data = '<test21>21</test21>'
        self._perfStart()
        while True:
            self._measurementStart()
            p.put('sandbox/test21', data, datatype='application/xml')
            if self._measurementStop():
                break
        
    def perf22_put_text(self):
        """PUT a database variable as plaintext"""
        p = self._igorVar()
        data = 'twenty two'
        self._perfStart()
        while True:
            self._measurementStart()
            p.put('sandbox/test22', data, datatype='text/plain')
            if self._measurementStop():
                break
        
    def perf23_put_json(self):
        """PUT a database variable as JSON"""
        p = self._igorVar()
        data = json.dumps({"test23" : 23})
        self._perfStart()
        while True:
            self._measurementStart()
            p.put('sandbox/test23', data, datatype='application/json')
            if self._measurementStop():
                break
        
    def perf31_post_text(self):
        """POST a database variable"""
        p = self._igorVar()
        p.put('sandbox/test31', '', datatype='text/plain')
        data = 'twenty two'
        self._perfStart()
        while True:
            self._measurementStart()
            p.post('sandbox/test31/item', 'thirtyone', datatype='text/plain')
            if self._measurementStop():
                break
        
    def perf61_call_action(self):
        """GET an action from external"""
        pAdmin = self._igorVar(credentials='admin:')
        optBearerToken = self._create_cap_for_call(pAdmin, 'test61action')
        p = self._igorVar(**optBearerToken)
        content = {'test61':{'data' : '0'}}
        action = {'action':dict(name='test61action', url='/data/sandbox/test61/data', method='PUT', data='{/data/sandbox/test61/data + 1}')}
        pAdmin.put('sandbox/test61', json.dumps(content), datatype='application/json')
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self._perfStart()
        while True:
            self._measurementStart()
            result = p.get('/action/test61action')
            if self._measurementStop():
                break
        
    def _create_cap_for_call(self, pAdmin, action):
        """Create capability required to GET an action from extern"""
        return {}
        
    def perf62_call_external(self):
        """GET an action on the external servlet directly"""
        pAdmin = self._igorVar(credentials='admin:')
        newCapID = self._create_caps_for_action(pAdmin, None, obj='/api/get', get='self', delegate='external')
        optBearerToken = self._export_cap_for_servlet(pAdmin, newCapID)
        p = self._igorVar(server=self.servletUrl, **optBearerToken)
        self.servlet.set('sixtytwo')
        
        self._perfStart()
        while True:
            self._measurementStart()
            self.servlet.startTimer()
            p.get('/api/get')
            duration = self.servlet.waitDuration()
            if self._measurementStop(duration=duration):
                break
        
    def _export_cap_for_servlet(self, pAdmin, newCapID):
        """Export a capability for the servlet audience"""
        return {}
        
    def perf63_call_action_external(self):
        """GET an action that does a GET on the external servlet"""
        pAdmin = self._igorVar(credentials='admin:')

        action = {'action':dict(name='test63action', url=self.servletUrl+'/api/get')}
        pAdmin.post('actions/action', json.dumps(action), datatype='application/json')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        self._create_caps_for_action(pAdmin, 'test63action', obj='/api/get', get='self', delegate='external')
        self._flush(pAdmin, MAX_FLUSH_DURATION)

        optBearerToken = self._create_cap_for_call(pAdmin, 'test63action')
        p = self._igorVar(**optBearerToken)

        self._perfStart()
        while True:
            self._measurementStart()        
            self.servlet.startTimer()
            p.get('/action/test63action')
            duration = self.servlet.waitDuration()
            if self._measurementStop(duration=duration):
                break

    def _create_caps_for_action(self, pAdmin, caller, obj, **kwargs):
        """Create capability so that action caller can GET an external action"""
        pass
        
class IgorPerfHttps(IgorPerf):
    igorDir = os.path.join(FIXTURES, 'testIgorHttps')
    igorPort = 19533
    igorProtocol = "https"
    igorServerArgs = ["--noCapabilities"]
    
class IgorPerfCaps(IgorPerf):
    igorDir = os.path.join(FIXTURES, 'testIgorCaps')
    igorPort = 19633
    igorProtocol = "https"
    igorServerArgs = ["--capabilities"]
    igorUseCapabilities = True

    def perf19_get_disallowed(self):
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            try:
                result = p.get('identities', format='application/xml')
            except igorVar.IgorError:
                pass
            else:
                assert 0, 'disallowed access did not raise an IgorError exception'
            if self._measurementStop():
                break
        
    def perf29_put_disallowed(self):
        p = self._igorVar()
        self._perfStart()
        while True:
            self._measurementStart()
            try:
                result = p.put('environment/systemHealth/test29', 'twentynine', datatype='text/plain')
            except igorVar.IgorError:
                pass
            else:
                assert 0, 'disallowed access did not raise an IgorError exception'
            if self._measurementStop():
                break
        
    def perf68_call_external_disallowed(self):
        """Check that a call to the external servlet without a correct capability fails"""
        p = self._igorVar(server=self.servletUrl)
        self.servlet.set('sixtytwo')
        self._perfStart()
        while True:
            self._measurementStart()
            try:
                p.get('/api/get')
            except igorVar.IgorError:
                pass
            else:
                assert 0, 'disallowed access did not raise an IgorError exception'
            if self._measurementStop():
                break

    def _new_capability(self, pAdmin, **kwargs):
        argStr = urllib.parse.urlencode(kwargs)
        rv = pAdmin.get('/internal/accessControl/newToken?' + argStr)
        return rv.strip()
        
    def _new_sharedkey(self, pAdmin, **kwargs):
        argStr = urllib.parse.urlencode(kwargs)
        try:
            rv = pAdmin.get('/internal/accessControl/createSharedKey?' + argStr)
            return rv.strip()
        except igorVar.IgorError:
            if DEBUG_TEST: print('(shared key already exists for %s)' % repr(kwargs))
        return None
        
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
        
def main():
    global MEASUREMENT_MIN_COUNT
    global MEASUREMENT_MIN_DURATION
    parser = argparse.ArgumentParser(description="Performance test of Igor server")
    parser.add_argument("--count", metavar="MIN", type=int, help="Run each test at least MIN times (default: %d)" % MEASUREMENT_MIN_COUNT, default=MEASUREMENT_MIN_COUNT)
    parser.add_argument("--dur", metavar="MIN", type=int, help="Run each test at least MIN seconds (default: %d)" % MEASUREMENT_MIN_DURATION, default=MEASUREMENT_MIN_DURATION)
#    parser.add_argument("test", help="Run this test only (can be classname or classname.methodname)")
    args = parser.parse_args()
    MEASUREMENT_MIN_COUNT = args.count
    MEASUREMENT_MIN_DURATION = args.dur
    perfClasses = [IgorPerf, IgorPerfHttps, IgorPerfCaps]
    for cls in perfClasses:
        try:
            print('%s:' % cls.__name__)
            cls.setUpClass()
            obj = cls()
            obj.run()
        finally:
            cls.tearDownClass()
            
if __name__ == '__main__':
    main()
    
