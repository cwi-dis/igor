import web
import threading
import time
import json

DEBUG=False

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class IgorServlet(threading.Thread):
    endpoints = {}
    
    def __init__(self):
        threading.Thread.__init__(self)
        if DEBUG: print 'igorServlet: IgorServlet.__init__ called for', self
        self.app = web.application((), globals(), autoreload=False)
        
    def run(self):
        self.app.run()
        
    def stop(self):
        self.app.stop()
        return self.join()
        
    def addEndpoint(self, path, mimetype='application/json', get=None, put=None, post=None, delete=None):
        self.endpoints[path] = dict(mimetype=mimetype, get=get, put=put, post=post, delete=delete)
        self.app.add_mapping(path, 'ForwardingClass' )

class ForwardingClass:
    def __init__(self):
       if DEBUG: print 'igorServlet: ForwardingClass.__init__ called for', self

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
    global DEBUG
    DEBUG = True
    if DEBUG: print 'igorServlet: main called'
    
    class HelloClass:
        def __init__(self):
            if DEBUG: print 'HelloClass.__init__ called for', self

        def get_hello(self):
            return 'Hello World from test'
        
    class CounterClass(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            if DEBUG: print 'CounterClass.__init__ called for', self
            self.counter = 0
            self.stopped = False
            
        def run(self):
            while not self.stopped:
                time.sleep(1)
                self.counter += 1
                
        def stop(self):
            self.stopped = 1
            self.join()
            
        def get_count(self):
            return {'counter':self.counter}
            
    s = IgorServlet()
    helloObject = HelloClass()
    counterObject = CounterClass()
    counterObject.start()
    s.addEndpoint('/hello', get=helloObject.get_hello, mimetype='text/plain')
    s.addEndpoint('/helloJSON', get=helloObject.get_hello, mimetype='application/json')
    s.addEndpoint('/count', get=counterObject.get_count, mimetype='text/plain')
    s.addEndpoint('/countJSON', get=counterObject.get_count, mimetype='application/json')
    s.start()
    try:
        while True:
            time.sleep(10)
            if DEBUG: print 'IgorServlet: time passing and still serving...'
    except KeyboardInterrupt:
        pass
    if DEBUG: print 'IgorServlet: stopping server'
    counterObject.stop()
    s.stop()
    s = None
    
if __name__ == '__main__':
    main()
    
