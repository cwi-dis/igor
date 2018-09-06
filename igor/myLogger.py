from __future__ import print_function
from __future__ import unicode_literals
from builtins import object
import logging
import logging.handlers
import sys
import os

logging.basicConfig()

DEBUG=False

# Send stdout and stderr to the logger as well.
class StreamToLogger(object):
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass         

def install(logSpec=None, nologfile=False, nologstderr=False, logdir='.'):
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)
    if DEBUG: print('myLogger: rootLogger=', rootLogger)
    if DEBUG: rootLogger.info('myLogger: rootlogger info() rootLogger=%s' % repr(rootLogger))
    if not nologfile:
        oldHandlers = rootLogger.handlers[:]
        handler = logging.handlers.TimedRotatingFileHandler(os.path.join(logdir, 'igor.log'), when='D', backupCount=9)
        formatter = logging.Formatter("%(name)s:%(levelname)s:%(message)s")
        handler.setFormatter(formatter)
        rootLogger.addHandler(handler)
        if DEBUG: print('myLogger: added filehandler')
        if DEBUG: rootLogger.info('myLogger: added filehandler info() call')
        if not nologstderr:
            rootLogger.addHandler(logging.StreamHandler())
            if DEBUG: print('xxxjack added streamhandler')
            if DEBUG: rootLogger.info('myLogger: added streamhandler info() call')
        sys.stdout = StreamToLogger(logging.getLogger('stdout'), logging.INFO)
        if DEBUG: print('myLogger: redirected stdout')
        if DEBUG: rootLogger.info('myLogger: redirected stdout info() call')
        sys.stderr = StreamToLogger(logging.getLogger('stderr'), logging.INFO)
        if DEBUG: print('myLogger: redirected stderr')
        if DEBUG: rootLogger.info('myLogger: redirected stderr info() call')
        for h in oldHandlers:
            rootLogger.removeHandler(h)
        if DEBUG: print('myLogger: removed old handlers')
        if DEBUG: rootLogger.info('myLogger: removed old handlers info() call')
    if logSpec == None:
        return
    for ll in logSpec.split(','):
        if ':' in ll:
            loggerToModify = logging.getLogger(ll.split(':')[0])
            newLevel = getattr(logging, ll.split(':')[1])
        else:
            loggerToModify = rootLogger
            newLevel = getattr(logging, ll)
        loggerToModify.setLevel(newLevel)
