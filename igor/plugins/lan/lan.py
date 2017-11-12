"""Test liveness of hosts"""
import socket
import web
import time

DATABASE_ACCESS=None

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

def lan(name=None, service='services/%s', ip=None, port=80, timeout=5, token=None):
    if not name:
        raise myWebError("401 Required argument name missing")
    if not ip:
        ip = name
    alive = True
    try:
        s = socket.create_connection((ip, int(port)), timeout)
    except socket.error:
        alive = False
    if service:
        if '%' in service:
            service = service % name
        if not DATABASE_ACCESS: 
            msg = "502 plugin did not have DATABASE_ACCESS set"
            raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')
        try:
            oldValue = DATABASE_ACCESS.get_key(service + '/alive', 'text/plain', None, token)
        except web.HTTPError:
            web.ctx.status = "200 OK"
            oldValue = 'rabarber'
        xpAlive = 'true' if alive else ''
        if oldValue != xpAlive:
            try:
                rv = DATABASE_ACCESS.put_key(service + '/alive', 'text/plain', None, xpAlive, 'text/plain', token, replace=True)
            except web.HTTPError:
                raise myWebError("501 Failed to store into %s" % (service+'/alive'))
            if alive:
                # If the service is alive we delete any error message and we also reset the "ignore errors" indicator
                try:
                    DATABASE_ACCESS.delete_key(service + '/errorMessage', token)
                except web.HTTPError:
                    web.ctx.status = "200 OK"
                try:
                    DATABASE_ACCESS.delete_key(service + '/ignoreErrorUntil', token)
                except web.HTTPError:
                    web.ctx.status = "200 OK"
            else:
                # If the service is not alive we set an error message
                DATABASE_ACCESS.put_key(service + '/errorMessage', 'text/plain', None, "%s is not available" % name, 'text/plain', token, replace=True)
        if xpAlive == 'true':
            try:
                rv = DATABASE_ACCESS.put_key(service + '/lastActivity', 'text/plain', None, str(int(time.time())), 'text/plain', token, replace=True)
            except web.HTTPError:
                raise myWebError("501 Failed to store into %s" % (service+'/alive'))
    return repr(alive)
