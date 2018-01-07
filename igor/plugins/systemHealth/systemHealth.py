"""Test liveness of hosts"""
import socket
import web
import time

DATABASE_ACCESS=None
PLUGINDATA={}

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
    
class SystemHealthPlugin:
    def __init__(self):
        pass
        
    def index(self, ignore=None, duration=0, returnTo=None, token=None):
        #
        # See if we have a request to ignore errors for a specific service (or sensor)
        #
        if ignore:
            # Request to ignore a specific service for some time.
            targetPath = "status/%s/ignoreErrorUntil" % ignore
            if duration:
                ignoreUntil = time.time() + float(duration)
                DATABASE_ACCESS.put_key(targetPath, 'text/plain', None, str(int(ignoreUntil)), 'text/plain', token, replace=True)
            else:
                try:
                    DATABASE_ACCESS.delete_key(targetPath, token)
                except web.HTTPError:
                    web.ctx.status = "200 OK"
        #
        # Determine whether any sensors have been inactive for too long and set an
        # error message if so.
        #
        badSensors = {}
        if 'sensorMaxInterval' in PLUGINDATA:
            sensorMaxInterval = PLUGINDATA['sensorMaxInterval']
            sensors = DATABASE_ACCESS.get_key("status/sensors/*", "application/x-python-object", "multi", token)
            if sensors:
                for xp, content in sensors.items():
                    if type(content) != type({}):
                        raise myWebError("500 expected nested element for %s in status/sensors" % xp)
                    sensorName = xp[xp.rindex('/')+1:]
                    lastActivity = content.get('lastActivity', None)
                    if lastActivity and sensorName in sensorMaxInterval:
                        laTime = float(lastActivity)
                        miTime = float(sensorMaxInterval[sensorName])
                        if laTime + miTime < time.time():
                            errorMessage = 'No activity from %s sensors for %s' % (sensorName, niceDelta(time.time()-laTime))
                            DATABASE_ACCESS.put_key(xp + '/errorMessage', 'text/plain', None, errorMessage, 'text/plain', token, replace=True)
                            content['errorMessage'] = errorMessage
                            badSensors[xp] = content

        statuses = DATABASE_ACCESS.get_key("status/*/*", "application/x-python-object", "multi", token)
        #
        # For all sensors and services see whether we have an error condition.
        #
        if statuses:
            for xp, content in statuses.items():
                if type(content) != type({}):
                    raise myWebError("500 expected nested element for %s in status/*" % xp)
                serviceName = xp[xp.rindex('/')+1:]
                hasError = content.get('errorMessage')
                hasIgnore = content.get('ignoreErrorUntil')
                if hasError and hasIgnore:
                    # Check whether the ignore is still valid, clear if not
                    ignoreUntil = int(content['ignoreErrorUntil'])
                    if ignoreUntil < time.time():
                        hasIgnore = False
                        DATABASE_ACCESS.put_key(xp + '/ignoreErrorUntil', 'text/plain', None, '', 'text/plain', token, replace=True)
                if hasIgnore:
                    hasError = False
                targetPath = "environment/systemHealth/messages/" + serviceName
                if hasError:
                    # Copy error into environment/systemHealth
                    DATABASE_ACCESS.put_key(targetPath, 'text/plain', None, content['errorMessage'], 'text/plain', token, replace=True)
                else:
                    # Remove error from environment/systemHealth if it is there currently
                    try:
                        DATABASE_ACCESS.delete_key(targetPath, token)
                    except web.HTTPError:
                        web.ctx.status = "200 OK"
                        pass
        if returnTo:
            raise web.seeother(returnTo)

def igorPlugin(pluginName, pluginData):
    return SystemHealthPlugin()
