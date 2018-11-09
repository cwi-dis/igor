"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os
import iotsaControl
import json

from builtins import object
class IotsaPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        self.wifi = iotsaControl.api.IotsaWifi()
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
        
    def findNetworks(self, token=None):
        rv = self.wifi.findNetworks()
        return json.dumps(rv)
    
    def findTargets(self, token=None):
        rv = self.wifi.findNetworks()
        return json.dumps(rv)
    
def igorPlugin(igor, pluginName, pluginData):
    return IotsaPlugin(igor, pluginName, pluginData)
