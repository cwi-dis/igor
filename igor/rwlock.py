"""Readers/writers lock, with reader priority.
Based on <https://gist.github.com/lemiant/10660092> with
an interface that helps use in with statements and using RLocks
in stead of Locks.
"""

import threading

DEBUG=False

class _RWReadLock(object):
    """Helper class to enable with and enter/exit on ReadWriteLock"""
    def __init__(self, mainLock):
        self.__mainLock = mainLock
        
    def __enter__(self):
        self.__mainLock._acquire_read()
        
    def __exit__(self, *args):
        self.__mainLock._release_read()
        
    def locked(self):
        return self.__mainLock._locked_read()
        
class _RWWriteLock(object):
    """Helper class to enable with and enter/exit on ReadWriteLock"""
    def __init__(self, mainLock):
        self.__mainLock = mainLock
        
    def __enter__(self):
        self.__mainLock._acquire_write()
        
    def __exit__(self, *args):
        self.__mainLock._release_write()

    def locked(self):
        return self.__mainLock._locked_write()
        
        
class ReadWriteLock(object):
    """ An implementation of a read-write lock for Python. 
    Any number of readers can work simultaneously but they 
    are mutually exclusive with any writers (which can 
    only have one at a time).
    
    This implementation is reader biased. This can be harmful
    under heavy load because it can starve writers.
    However under light load it will be quite perfomant since
    reads are usually much less resource intensive than writes,
    and because it maximizes concurrency.
    """


    def __init__(self):
        self.__monitor = threading.Lock()
        self.__exclude = threading.Lock()
        self.readers = 0
        self.__readLock = _RWReadLock(self)
        self.__writeLock = _RWWriteLock(self)

    def readlock(self):
        return self.__readLock
        
    def writelock(self):
        return self.__writeLock
        
    def _acquire_read(self):
        with self.__monitor:
            self.readers += 1
            if self.readers == 1:
                self.__exclude.acquire()
            if DEBUG: print('ReadWriteLock(0x%x): acquire_read() readers=%d' % (id(self), self.readers))
                
    def _release_read(self):
        with self.__monitor:
            self.readers -= 1
            if DEBUG: print('ReadWriteLock(0x%x): release_read() readers=%d' % (id(self), self.readers))
            assert self.readers >= 0
            if self.readers == 0:
                self.__exclude.release()

    def _acquire_write(self):
        self.__exclude.acquire()
        if DEBUG: print('ReadWriteLock(0x%x): acquire_write() readers=%d' % (id(self), self.readers))
        assert self.readers <= 1
                
    def _release_write(self):
        if DEBUG: print('ReadWriteLock(0x%x): release_write() readers=%d' % (id(self), self.readers))
        assert self.readers <= 1
        self.__exclude.release()
        
    def _locked_read(self):
        rv = self.readers > 0 or self.__exclude.locked()
        if DEBUG: print("ReadWriteLock(0x%x): locked_read() is %s" % (id(self), rv))
        return rv
        
    def _locked_write(self):
        rv = self.readers <= 1 and self.__exclude.locked()
        if DEBUG: print("ReadWriteLock(0x%x): locked_write() is %s" % (id(self), rv))
        return rv
        
        
