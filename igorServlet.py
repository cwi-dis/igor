import web
import threading
import time

print 'xxxjack module imported'

urls = ('/test', 'TestClass')
class IgorServlet(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        print 'xxxjack IgorServlet.__init__ called for', self
        self.app = web.application(urls, globals(), autoreload=False)
        
    def run(self):
        self.app.run()
        
    def stop(self):
        self.app.stop()
        return self.join()

class TestClass:
    def __init__(self):
        print 'xxxjack TestClass.__init__ called for', self

    def GET(self):
        print 'starting to serve'
        time.sleep(7)
        print 'done serving'
        return 'Hello World from test'
        
def main():
    print 'xxxjack main called'
    s = IgorServlet()
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
    
