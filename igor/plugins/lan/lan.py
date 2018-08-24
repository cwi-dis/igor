"""Test liveness of hosts"""
import socket
import web
import time
import json


def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class LanPlugin:
    def __init__(self, igor):
        self.igor = igor
        
    def index(self, name=None, service='services/%s', ip=None, port=80, timeout=5, token=None):
        if not name:
            raise myWebError("401 Required argument name missing")
        if not ip:
            ip = name
        alive = True
        detail = ''
        try:
            s = socket.create_connection((ip, int(port)), timeout)
        except socket.gaierror:
            alive = False
            detail = ' (host %s unknown)' % ip
        except socket.timeout:
            alive = False
            detail = ' (timeout connecting to %s)' % ip
        except socket.error, e:
            alive = False
            if e.args[1:]:
                detail = ' (%s)' % e.args[1]
            else:
                detail = ' (%s)' % repr(e)
        if '%' in service:
            service = service % name

        status = dict(alive=(not not alive))
        if not alive:
            status['resultData'] = '%s is not available%s' % (name, detail)
        toCall = dict(url='/internal/updateStatus/%s'%service, method='POST', data=json.dumps(status), headers={'Content-type':'application/json'}, token=token)
        self.igor.internal.urlCaller.callURL(toCall)
        if alive:
            return 'ok\n'
        return '%s is not available%s\n' % (name, detail)
    
def igorPlugin(igor, pluginName, pluginData):
    return LanPlugin(igor)
