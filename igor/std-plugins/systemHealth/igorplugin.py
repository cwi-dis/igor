"""Test liveness of hosts"""
from __future__ import division
from __future__ import unicode_literals
from builtins import str
from builtins import object
from past.utils import old_div
import socket
import time

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
    
class SystemHealthPlugin(object):
    def __init__(self, igor, pluginData):
        self.igor = igor
        self.pluginData = pluginData
        
    def index(self, ignore=None, duration=0, returnTo=None, token=None, callerToken=None):
        #
        # See if we have a request to ignore errors for a specific service (or sensor)
        #
        if ignore:
            # Request to ignore a specific service for some time.
            targetPath = "status/%s/ignoreErrorUntil" % ignore
            if duration:
                ignoreUntil = time.time() + float(duration)
                self.igor.databaseAccessor.put_key(targetPath, 'text/plain', None, str(int(ignoreUntil)), 'text/plain', token, replace=True)
            else:
                try:
                    self.igor.databaseAccessor.delete_key(targetPath, token)
                except self.igor.app.getHTTPError():
                    self.igor.app.resetHTTPError()
        #
        # Determine whether any sensors have been inactive for too long and set an
        # error message if so.
        #
        badSensors = {}
        if 'sensorMaxInterval' in self.pluginData:
            sensorMaxInterval = self.pluginData['sensorMaxInterval']
            sensors = self.igor.databaseAccessor.get_key("status/sensors/*", "application/x-python-object", "multi", token)
            if sensors:
                for xp, content in list(sensors.items()):
                    if type(content) != type({}):
                        self.igor.app.raiseHTTPError("500 expected nested element for %s in status/sensors" % xp)
                    sensorName = xp[xp.rindex('/')+1:]
                    lastActivity = content.get('lastActivity', None)
                    if lastActivity and sensorName in sensorMaxInterval:
                        laTime = float(lastActivity)
                        miTime = float(sensorMaxInterval[sensorName])
                        if laTime + miTime < time.time():
                            errorMessage = 'No activity from %s sensors for %s' % (sensorName, niceDelta(time.time()-laTime))
                            self.igor.databaseAccessor.put_key(xp + '/errorMessage', 'text/plain', None, errorMessage, 'text/plain', token, replace=True)
                            content['errorMessage'] = errorMessage
                            badSensors[xp] = content

        statuses = self.igor.databaseAccessor.get_key("status/*/*", "application/x-python-object", "multi", token)
        #
        # For all sensors and services see whether we have an error condition.
        #
        if statuses:
            for xp, content in list(statuses.items()):
                if type(content) != type({}):
                    self.igor.app.raiseHTTPError("500 expected nested element for %s in status/*" % xp)
                serviceName = xp[xp.rindex('/')+1:]
                hasError = content.get('errorMessage')
                hasIgnore = content.get('ignoreErrorUntil')
                if hasError and hasIgnore:
                    # Check whether the ignore is still valid, clear if not
                    ignoreUntil = int(content['ignoreErrorUntil'])
                    if ignoreUntil < time.time():
                        hasIgnore = False
                        self.igor.databaseAccessor.put_key(xp + '/ignoreErrorUntil', 'text/plain', None, '', 'text/plain', token, replace=True)
                if hasIgnore:
                    hasError = False
                targetPath = "environment/systemHealth/messages/" + serviceName
                if hasError:
                    # Copy error into environment/systemHealth
                    self.igor.databaseAccessor.put_key(targetPath, 'text/plain', None, content['errorMessage'], 'text/plain', token, replace=True)
                else:
                    # Remove error from environment/systemHealth if it is there currently
                    try:
                        self.igor.databaseAccessor.delete_key(targetPath, token)
                    except self.igor.app.getHTTPError():
                        self.igor.app.resetHTTPError()
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)

def igorPlugin(igor, pluginName, pluginData):
    return SystemHealthPlugin(igor, pluginData)
