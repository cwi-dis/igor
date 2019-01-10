"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os
import lnetatmo

from builtins import object
class NetatmoPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
    
    def pull(self, token=None, callerToken=None):
        authentication = self.pluginData.get('authentication', {})
        if not authentication.get('clientId'):
            return self.igor.app.raiseHTTPError("400 Plugindata authentication does not contain clientId")
        if not authentication.get('clientSecret'):
            return self.igor.app.raiseHTTPError("400 Plugindata authentication does not contain clientSecret")
        if not authentication.get('username'):
            return self.igor.app.raiseHTTPError("400 Plugindata authentication does not contain username")
        if not authentication.get('password'):
            return self.igor.app.raiseHTTPError("400 Plugindata authentication does not contain password")
        # xxxjack could also honor `scope` parameter here...
        try:
            authorization = lnetatmo.ClientAuth(**authentication)
        except lnetatmo.AuthFailure as e:
            return self.igor.app.raiseHTTPError("502 netatmo: {}".format(str(e)))
            
        # xxxjack could also add `station` parameter here for multiple weather statiosn
        # xxxjack could also add other types, such as ThermostatData
        weatherDataAccessor = lnetatmo.WeatherStationData(authorization)
        weatherData = weatherDataAccessor.lastData()
        for stationName in weatherData:
            path = '/data/sensors/{}/{}'.format(self.pluginName, stationName)
            data = weatherData[stationName]
            rv = self.igor.databaseAccessor.put_key(path, 'text/plain', None, data, 'application/x-python-object', token, replace=True)

        return 'ok\n'
    
def igorPlugin(igor, pluginName, pluginData):
    return NetatmoPlugin(igor, pluginName, pluginData)
