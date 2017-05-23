"""Test liveness of hosts"""
import socket
import web
import glob
import os

DATABASE_ACCESS=None

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
    
    
def lastFileAccess(name=None, service='services/%s', path=None, stamp="mtime", max=0):
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
        message = "%s timestamp file not found" % name
    else:
        if max > 0:
            if latest + max > time.time():
                alive = True
            else:
                alive = False
                delta = time.time() - latest
                message = "%s has not been active for %s" % (name, niceDelta(delta))

    # Now fill in fields. Note that we can also have missing fields (which we delete)
    if '%' in service:
        service = service % name
    if alive == None:
        try:
            DATABASE_ACCESS.delete_key(service + '/alive')
        except web.HTTPError:
            pass
    else:
        xpAlive = 'true' if alive else ''
        try:
            oldValue = DATABASE_ACCESS.get_key(service + '/alive', 'text/plain', None)
        except web.HTTPError:
            web.ctx.status = "200 OK"
            oldValue = 'rabarber'
            if oldValue != xpAlive:
                try:
                    rv = DATABASE_ACCESS.put_key(service + '/alive', 'text/plain', None, xpAlive, 'text/plain', replace=True)
                except web.HTTPError:
                    raise myWebError("501 Failed to store into %s" % (service + '/alive'))
                if alive:
                    # If the service is alive we delete any error message and we also reset the "ignore errors" indicator
                    try:
                        DATABASE_ACCESS.delete_key(service + '/ignoreErrorUntil')
                    except web.HTTPError:
                        pass

    if latest < 0:
        try:
            DATABASE_ACCESS.delete_key(service + '/lastActivity')
        except web.HTTPError:
            pass
    else:
        try:
            rv = DATABASE_ACCESS.put_key(service + '/lastActivity', 'text/plain', None, str(int(latest)), 'text/plain', replace=True)
        except web.HTTPError:
            raise myWebError("501 Failed to store into %s" % (service + '/lastActivity')

    if not message:
        try:
            DATABASE_ACCESS.delete_key(service + '/errorMessage')
        except web.HTTPError:
            pass
    else:
        try:
            rv = DATABASE_ACCESS.put_key(service + '/errorMessage', 'text/plain', None, message, 'text/plain', replace=True)
        except web.HTTPError:
            raise myWebError("501 Failed to store into %s" % (service + '/errorMessage')
