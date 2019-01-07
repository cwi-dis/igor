"""Test liveness of hosts"""
from __future__ import unicode_literals
from builtins import object
import socket
import time
import json
import requests

class LanPlugin(object):
    def __init__(self, igor):
        self.igor = igor
        
    def index(self, name=None, service='services/%s', ip=None, port=80, timeout=5, url=None, token=None, callerToken=None):
        if not name:
            self.igor.app.raiseHTTPError("401 Required argument name missing")
        if not ip:
            ip = name
        alive = True
        detail = ''
        if url:
            try:
                reply = requests.get(url)
                if reply.status_code != 200:
                    alive = False
                    detail = ' (http status code %s)' % reply.status_code
            except requests.exceptions.ConnectionError:
                alive = False
                detail = ' (cannot connect to http(s) server)'
            except requests.exceptions.Timeout:
                alive = False
                detail = ' (timeout connecting to http(s) server)'
        else:
            s = None
            try:
                s = socket.create_connection((ip, int(port)), timeout)
            except socket.gaierror:
                alive = False
                detail = ' (host %s unknown)' % ip
            except socket.timeout:
                alive = False
                detail = ' (timeout connecting to %s)' % ip
            except socket.error as e:
                alive = False
                if e.args[1:]:
                    detail = ' (%s)' % e.args[1]
                else:
                    detail = ' (%s)' % repr(e)
            if s:
                s.close()
        if '%' in service:
            service = service % name
        statusLine = '%s is not available%s' % (name, detail)
        self.igor.internal.updateStatus(representing=service, alive=(not not alive), resultData=statusLine, token=token)
        if alive:
            return 'ok\n'
        return '%s is not available%s\n' % (name, detail)
    
def igorPlugin(igor, pluginName, pluginData):
    return LanPlugin(igor)
