import web
import threading
import time
import json

print 'xxxjack module imported'

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class IgorServlet(threading.Thread):
    endpoints = {}
    
    def __init__(self):
        threading.Thread.__init__(self)
        print 'xxxjack IgorServlet.__init__ called for', self
        self.app = web.application((), globals(), autoreload=False)
        
    def run(self):
        self.app.run()
        
    def stop(self):
        self.app.stop()
        return self.join()
        
    def addEndpoint(self, path, mimetype='application/json', get=None, put=None, post=None, delete=None):
        self.endpoints[path] = dict(mimetype=mimetype, get=get, put=put, post=post, delete=delete)
        self.app.add_mapping(path, 'ForwardingClass' )

class HelloClass:
    def __init__(self):
        print 'xxxjack Hello.__init__ called for', self

    def get_hello(self):
        return 'Hello World from test'
        
class ForwardingClass:
    def __init__(self):
        print 'xxxjack ForwardingClass.__init__ called for', self

    def GET(self):
        path = web.ctx.path
        endpoint = IgorServlet.endpoints.get(path)
        if not path:
            raise web.notfound()
        entry = endpoint['get']
        if not entry:
            raise web.notfound()
        # xxxjack check path and capability
        methodArgs = {}
        optArgs = web.input()
        if optArgs:
            methodArgs = dict(optArgs)
        else:
            data = web.data()
            if data:
                methodArgs = dict(data)
        try:
            rv = entry(**methodArgs)
        except TypeError, arg:
            raise myWebError("400 Error in parameters: %s" % arg)
        if endpoint['mimetype'] == 'text/plain':
            rv = str(rv)
        elif endpoint['mimetype'] == 'application/json':
            rv = json.dumps(rv)
        else:
            assert 0, 'Unsupported mimetype %s' % endpoint['mimetype']
        return rv
        
def main():
    print 'xxxjack main called'
    s = IgorServlet()
    helloObject = HelloClass()
    s.addEndpoint('/hello', get=helloObject.get_hello, mimetype='application/json')
    s.start()
    try:
        while True:
            time.sleep(10)
            print '... time passing and still serving...'
    except KeyboardInterrupt:
        pass
    print 'xxxjack stopping server'
    s.stop()
    s = None
    
if __name__ == '__main__':
    main()
    
