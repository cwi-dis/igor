"""Test liveness of hosts"""
from __future__ import division
from __future__ import unicode_literals
from builtins import str
from builtins import object
from past.utils import old_div
import socket
import glob
import os
import time
import json

def niceDelta(delta):
    if delta < 60:
        return "%d seconds" % delta
    delta = old_div((delta+1), 60)
    if delta < 60:
        return "%d minutes" % delta
    delta = old_div((delta+1), 60)
    if delta < 48:
        return "%d hours" % delta
    delta = old_div((delta+1), 24)
    if delta < 14:
        return "%d days" % delta
    delta = old_div((delta+1), 7)
    return "%d weeks" % delta
    
class LastFileAccess(object):
    def __init__(self, igor):
        self.igor = igor
        
    def index(self, name=None, service='services/%s', path=None, stamp="mtime", max=0, token=None, callerToken=None):
        if not name or not path:
            self.igor.app.raiseHTTPError("401 Required arguments (name or path) missing")
        message = None
        latest = -1
        alive = None
        for p in glob.iglob(path):
            st = os.stat(p)
            if stamp == 'mtime':
                timestamp = st.st_mtime
            elif stamp == 'ctime':
                timestamp = st.st_ctime
            elif stamp == 'atime':
                timestamp = st.st_atime
            else:
                self.igor.app.raiseHTTPError("401 unknown timestamp type stamp=%s" % stamp)
            if timestamp > latest:
                latest = timestamp
        if latest < 0:
            message = "%s timestamp file (%s) not found" % (name, path)
        else:
            max = int(max)
            if max > 0:
                if latest + max > time.time():
                    alive = True
                else:
                    alive = False
                    delta = time.time() - latest
                    message = "%s has not been active for %s" % (name, niceDelta(delta))

        if '%' in service:
            service = service % name

        # Now fill in fields. Note that we can also have missing fields (which we delete)
        if latest > 0:
            lastSuccess = int(latest)
        else:
            lastSuccess = None
        
        self.igor.internal.updateStatus(representing=service, alive=(not not alive), resultData=message, lastSuccess=lastSuccess, token=token)
        return str(int(time.time()-latest))

def igorPlugin(igor, pluginName, pluginData):
    return LastFileAccess(igor)
