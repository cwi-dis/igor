"""Test liveness of hosts"""
import socket
import web
import time
import json

DATABASE_ACCESS=None
COMMANDS=None

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

    if '%' in service:
        service = service % name

    status = dict(alive=(not not alive))
    if not alive:
        status['resultData'] = '%s is not available' % name
    toCall = dict(url='/internal/updateStatus/%s'%service, method='POST', data=json.dumps(status), headers={'Content-type':'application/json'}, token=token)
    COMMANDS.urlCaller.callURL(toCall)
    if alive:
        return 'ok\n'
    return '%s is not available\n' % name
