"""Test liveness of hosts"""
import socket
import web
import time

DATABASE_ACCESS=None

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

def systemHealth(ignore=None, duration=0):
    if ignore:
        # Request to ignore a specific service for some time.
        targetPath = "services/%s/ignoreErrorUntil" % ignore
        if duration:
            ignoreUntil = time.time() + float(duration)
            DATABASE_ACCESS.put_key(targetPath, 'text/plain', None, str(int(ignoreUntil)), 'text/plain', replace=True)
        else:
            try:
                DATABASE_ACCESS.delete_key(targetPath)
            except web.HTTPError:
                pass
            
    services = DATABASE_ACCESS.get_key("services/*", "application/x-python-object", "multi")
    # That call should return a dict of {xpath:{content}} for all matching elements
    for xp, content in services.items():
        serviceName = xp[xp.rindex('/')+1:]
        hasError = 'errorMessage' in content
        hasIgnore = 'ignoreErrorUntil' in content
        if hasError and hasIgnore:
            # Check whether the ignore is still valid, delete if not
            ignoreUntil = int(content['ignoreErrorUntil'])
            if ignoreUntil < time.time():
                hasIgnore = False
                DATABASE_ACCESS.delete_key(xp + '/ignoreErrorUntil')
        if hasIgnore:
            hasError = False
        targetPath = "environment/systemHealth/messages/" + serviceName
        if hasError:
            # Copy error into environment/systemHealth
            DATABASE_ACCESS.put_key(targetPath, 'text/plain', None, content['errorMessage'], 'text/plain', replace=True)
        else:
            # Remove error from environment/systemHealth if it is there currently
            try:
                DATABASE_ACCESS.delete_key(targetPath)
            except web.HTTPError:
                pass
