from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import threading
import requests
import queue
import urllib.parse
import time
import sys
import os
import traceback
import json

DEBUG=False

class CheckableQueue(queue.Queue):
    """We only check to forestall doing double work. So we don't
    really care about the race condition..."""
    
    def __contains__(self, item):
        with self.mutex:
            return item in self.queue

class URLCallRunner(threading.Thread):
    def __init__(self, igor, what):
        threading.Thread.__init__(self)
        self.daemon = True
        self.igor = igor
        self.queue = CheckableQueue()
        self.what = what
        self.stopping = False

    def run(self):
        while not self.stopping:
            tocall = self.queue.get()
            if tocall == None: continue # To implement stop
            if callable(tocall):
                # To implement flushing
                tocall()
                continue
            method = tocall['method']
            url = tocall['url']
            token = tocall['token']
            data = tocall.get('data')
            headers = {}
            env = {}
            if 'representing' in tocall:
                env['representing'] = tocall['representing']
            if 'original_action' in tocall:
                env['original_action'] = tocall['original_action']
            if 'mimetype' in tocall:
                headers['Content-type'] = tocall['mimetype']
            if not method:
                method = 'GET'
            try:
                resultStatus = ""
                resultData = ""
                errorMessage = ""
                datetime = time.strftime('%d/%b/%Y %H:%M:%S')
                parsedUrl = urllib.parse.urlparse(url)
                if DEBUG: print('URLCaller.run calling', url, 'method', method, 'headers', headers, 'data', data)
                if parsedUrl.scheme == '' and parsedUrl.netloc == '':
                    # Local. Call the app directly.
                    # xxxjack have to work out exceptions
                    token.addToHeadersAsOTP(headers)
                    if headers == {}: headers = None
                    rep = self.igor.app.request(url, method=method, data=data, headers=headers, env=env)
                    resultStatus = rep.status
                    resultData = rep.data
                    if resultData and type(resultData) != type(''):
                        resultData = resultData.decode('utf-8')
                    if not resultData:
                        resultData = resultStatus
                else:
                    # Remote.
                    addedTokenId = token.addToHeadersFor(headers, url)
                    if headers == {}: headers = None
                    kwargs = {}
                    if os.environ.get('IGOR_TEST_NO_SSL_VERIFY'):
                        kwargs['verify'] = False
                    r = requests.request(method, url, data=data, headers=headers, **kwargs)
                    if r.status_code == 401:
                        # If we get a 401 Unauthorized error we also report it through the access control errors
                        print('401 error from external call, was carrying capability %s' % addedTokenId)
                        failureDescription = dict(operation=method.lower(), path=url, external=True, capID=token.getIdentifiers())
                        if 'representing' in env:
                            failureDescription['representing'] = env['representing']
                        if 'original_action' in env:
                            failureDescription['action'] = env['original_action']
                        self.igor.internal._accessFailure(failureDescription)
                    resultStatus = str(r.status_code)
                    resultData = r.text
                    if resultData and type(resultData) != type(''):
                        resultData = resultData.decode('utf-8')
                    # Stop-gap to get more info in the log, if possible
                    if resultData.count('\n') <= 1 and resultData.startswith(resultStatus):
                        resultStatus = resultData.strip()
            except requests.exceptions.RequestException:
                eType, eValue, _ = sys.exc_info()
                msg = traceback.format_exception_only(eType, eValue)[0].strip()
                resultStatus = '502 URLCaller: %s' % msg
                errorMessage = msg
            except:
                resultStatus = '502 URLCaller: exception while calling URL %s' % url
                print(resultStatus)
                sys.stdout.flush()
                errorMessage = resultStatus
                traceback.print_exc(file=sys.stdout)
            print('- - - [%s] "- %s %s" - %s' % (datetime, method, url, resultStatus), file=sys.stderr)
            alive = resultStatus[:3] == '200'
            if not alive or DEBUG:
                if resultData and resultData.strip() != resultStatus.strip():
                    print('Output:')
                    resultLines = resultData.splitlines()
                    for line in resultLines:
                        print('\t'+line)
                    sys.stdout.flush()
            representing = tocall.get('representing')
            if representing:
                if not alive and not resultData:
                    resultData = errorMessage
                args = dict(alive=alive, resultData=resultData)
                # xxxjack should we add the token here too?
                self.igor.app.request('/internal/updateStatus/%s' % representing, method='POST', data=json.dumps(args), headers={'Content-type':'application/json'})
                
    def dump(self):
        rv = 'URLCaller %s (%s):\n' % (repr(self), self.what)
        for qel in self.queue.queue:
            rv += '\t' + repr(qel) + '\n'
        return rv
        
    def callURL(self, tocall):
        if DEBUG: print('URLCaller.callURL(%s)' % repr(tocall))
        if not callable(tocall):
            assert 'token' in tocall
            if tocall.get('aggregate'):
                # We should aggregate this action, so don't insert if already in the queue
                if tocall in self.queue:
                    if DEBUG: print('(skipped because aggregate is true)')
                    return
        self.queue.put(tocall)

    def stop(self):
        self.stopping = True
        self.queue.put(None)
        try:
            self.join()
        except RuntimeError:
            pass # This can happen if we are actually running via callUrl ourselves...
        
class URLCaller(object):
    def __init__(self, igor):
        self.lock = threading.Lock()
        self.flushedCV = threading.Condition(self.lock)
        self.dataRunner = URLCallRunner(igor, 'internal actions')
        self.extRunner = URLCallRunner(igor, 'network actions')
        self.otherRunner = URLCallRunner(igor, 'scripting and plugin actions')
        
    def start(self):
        self.dataRunner.start()
        self.extRunner.start()
        self.otherRunner.start()
        
    def stop(self):
        self.dataRunner.stop()
        self.extRunner.stop()
        self.otherRunner.stop()
        self.dataRunner.join()
        self.extRunner.join()
        self.otherRunner.join()

    def dump(self):
        rv = (self.dataRunner.dump() + '\n' + 
            self.extRunner.dump() + '\n' +
            self.otherRunner.dump())
        return rv
        
    def callURL(self, tocall):
        url = tocall['url']
        parsedUrl = urllib.parse.urlparse(url)
        if parsedUrl.scheme:
            self.extRunner.callURL(tocall)
        elif parsedUrl.path.startswith('/data/') or parsedUrl.path.startswith('/internal/') or parsedUrl.path.startswith('/action/'):
            self.dataRunner.callURL(tocall)
        else:
            self.otherRunner.callURL(tocall)
        
    def _runnerIsFlushed(self):
        with self.lock:
            self.flushedCV.notify()
            
    def flush(self, timeout=None):
        with self.lock:
            # xxxjack we only wait for internal actions: the other two seem to cause deadlocks...
            self.dataRunner.callURL(self._runnerIsFlushed)
            #self.extRunner.callURL(self._runnerIsFlushed)
            #self.otherRunner.callURL(self._runnerIsFlushed)
            self.flushedCV.wait(timeout)
            #self.flushedCV.wait(timeout)
            #self.flushedCV.wait(timeout)
