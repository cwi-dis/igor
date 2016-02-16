import threading
import httplib2
import Queue
import urlparse
import time
import sys

class URLCaller(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.daemon = True
        self.app = app
        self.queue = Queue.Queue()

    def run(self):
        while True:
            tocall = self.queue.get()
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
            parsedUrl = urlparse.urlparse(url)
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
            datetime = time.strftime('%d/%b/%Y %H:%M:%S')
            print '- - - [%s] "- %s %s" - %s' % (datetime, method, url, resultStatus)
            if resultStatus[:3] != '200':
                if resultData:
                    resultLines = resultData.splitlines()
                    for line in resultLines:
                        print '\t'+line
                
        
    def callURL(self, tocall):
        self.queue.put(tocall)
