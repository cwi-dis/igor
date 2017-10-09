import threading
import httplib2
import Queue
import urlparse
import time
import sys
import traceback

DEBUG=False

class CheckableQueue(Queue.Queue):
    """We only check to forestall doing double work. So we don't
    really care about the race condition..."""
    
    def __contains__(self, item):
        with self.mutex:
            return item in self.queue

class URLCallRunner(threading.Thread):
    def __init__(self, app, what):
        threading.Thread.__init__(self)
        self.daemon = True
        self.app = app
        self.queue = CheckableQueue()
        self.what = what
        self.stopping = False

    def run(self):
        while not self.stopping:
            tocall = self.queue.get()
            if tocall == None: continue # To implement stop
            method = tocall['method']
            url = tocall['url']
            data = tocall.get('data')
            headers = {}
            if 'mimetype' in tocall:
                headers['Content-type'] = tocall['mimetype']
            # xxxjack should also have credentials, etc
            if headers == {}: headers = None
            if not method:
                method = 'GET'
            try:
                resultStatus = ""
                resultData = ""
                datetime = time.strftime('%d/%b/%Y %H:%M:%S')
                parsedUrl = urlparse.urlparse(url)
                if DEBUG: print 'URLCaller.run calling', url, 'method', method, 'headers', headers, 'data', data
                if parsedUrl.scheme == '' and parsedUrl.netloc == '':
                    # Local. Call the app directly.
                    # xxxjack have to work out exceptions
                    rep = self.app.request(url, method=method, data=data, headers=headers)
                    resultStatus = rep.status
                    resultData = rep.data
                else:
                    # Remote.
                    # xxxjack have to work out exceptions
                    h = httplib2.Http()
                    resp, content = h.request(url, method, body=data, headers=headers)
                    resultStatus = "%s %s" % (resp.status, resp.reason)
                    resultData = content
            except httplib2.HttpLib2Error as e:
                resultStatus = '502 URLCaller: %s' % traceback.format_exception_only(type(e), e.message)[0].strip()
            except:
                resultStatus = '502 URLCaller: exception while calling URL'
                print 'URLCaller: exception while calling URL'
                traceback.print_exc(file=sys.stdout)
            print '- - - [%s] "- %s %s" - %s' % (datetime, method, url, resultStatus)
            success = resultStatus[:3] == '200'
            if not success or DEBUG:
                if resultData:
                    print 'Output:'
                    resultLines = resultData.splitlines()
                    for line in resultLines:
                        print '\t'+line
            representing = tocall.get('representing')
            if representing:
                args = dict(representing=representing, success=success, resultData=resultData)
                self.app.request('/internal/updateStatus', method='GET', data=json.dumps(args), headers={'Content-type':'application/json'})
                
    def dump(self):
        rv = 'URLCaller %s (%s):\n' % (repr(self), self.what)
        for qel in self.queue.queue:
            rv += '\t' + repr(qel) + '\n'
        return rv
        
    def callURL(self, tocall):
        if DEBUG: print 'URLCaller.callURL(%s)' % repr(tocall)
        if tocall.get('aggregate'):
            # We should aggregate this action, so don't insert if already in the queue
            if tocall in self.queue:
                if DEBUG: print '(skipped because aggregate is true)'
                return
        self.queue.put(tocall)

    def stop(self):
        self.stopping = True
        self.queue.put(None)
        self.join()
        
class URLCaller:
    def __init__(self, app):
        self.dataRunner = URLCallRunner(app, 'internal actions')
        self.extRunner = URLCallRunner(app, 'network actions')
        self.otherRunner = URLCallRunner(app, 'scripting and plugin actions')
        
    def start(self):
        self.dataRunner.start()
        self.extRunner.start()
        self.otherRunner.start()
        
    def stop(self):
        self.dataRunner.stop()
        self.extRunner.stop()
        self.otherRunner.stop()

    def dump(self):
        rv = (self.dataRunner.dump() + '\n' + 
            self.extRunner.dump() + '\n' +
            self.otherRunner.dump())
        return rv
        
    def callURL(self, tocall):
        url = tocall['url']
        parsedUrl = urlparse.urlparse(url)
        if parsedUrl.scheme:
            self.extRunner.callURL(tocall)
        elif parsedUrl.path.startswith('/data/'):
            self.dataRunner.callURL(tocall)
        else:
            self.otherRunner.callURL(tocall)
        
