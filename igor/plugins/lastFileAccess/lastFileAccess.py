"""Test liveness of hosts"""
import socket
import web
import glob
import os
import time
import json

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

def niceDelta(delta):
    if delta < 60:
        return "%d seconds" % delta
    delta = (delta+1) / 60
    if delta < 60:
        return "%d minutes" % delta
    delta = (delta+1) / 60
    if delta < 48:
        return "%d hours" % delta
    delta = (delta+1) / 24
    if delta < 14:
        return "%d days" % delta
    delta = (delta+1) / 7
    return "%d weeks" % delta
    
class LastFileAccess:
    def __init__(self, igor):
        self.igor = igor
        
    def index(self, name=None, service='services/%s', path=None, stamp="mtime", max=0, token=None):
        if not name or not path:
            raise myWebError("401 Required arguments (name or path) missing")
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
                raise myWebError("401 unknown timestamp type stamp=%s" % stamp)
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
        status = dict(alive=(not not alive))
        if latest > 0:
            status['lastSuccess'] = int(latest)
        if message:
            status['resultData'] = message
        toCall = dict(url='/internal/updateStatus/%s'%service, method='POST', data=json.dumps(status), headers={'Content-type':'application/json'}, token=token)
        self.igor.internal.urlCaller.callURL(toCall)
        return str(int(time.time()-latest))

def igorPlugin(igor, pluginName, pluginData):
    return LastFileAccess(igor)
