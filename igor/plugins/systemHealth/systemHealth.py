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
    
def systemHealth(ignore=None, duration=0):
    #
    # See if we have a request to ignore errors for a specific service (or sensor)
    #
    if ignore:
        # Request to ignore a specific service for some time.
        targetPath = "%s/ignoreErrorUntil" % ignore
        if duration:
            ignoreUntil = time.time() + float(duration)
            DATABASE_ACCESS.put_key(targetPath, 'text/plain', None, str(int(ignoreUntil)), 'text/plain', replace=True)
        else:
            try:
                DATABASE_ACCESS.delete_key(targetPath)
            except web.HTTPError:
                web.ctx.status = "200 OK"
    #
    # Determine whether any sensors have been inactive for too long and set an
    # error message if so.
    #
    badSensors = {}
    if 'sensorMaxInterval' in PLUGINDATA:
        sensorMaxInterval = PLUGINDATA['sensorMaxInterval']
        sensors = DATABASE_ACCESS.get_key("sensors/*", "application/x-python-object", "multi")
        for xp, content in sensors.items():
            sensorName = xp[xp.rindex('/')+1:]
            lastActivity = content.get('lastActivity', None)
            if lastActivity and sensorName in sensorMaxInterval:
                laTime = float(lastActivity)
                miTime = float(sensorMaxInterval[sensorName])
                if laTime + miTime < time.time():
                    errorMessage = 'No activity from %s sensors for %s' % (sensorName, niceDelta(time.time()-laTime))
                    DATABASE_ACCESS.put_key(xp + '/errorMessage', 'text/plain', None, errorMessage, 'text/plain', replace=True)
                    content['errorMessage'] = errorMessage
                    badSensors[xp] = content
                else:
                    # Delete any old error messages
                    try:
                        DATABASE_ACCESS.delete_key(xp + '/errorMessage')
                    except web.HTTPError:
                        web.ctx.status = "200 OK"

    services = DATABASE_ACCESS.get_key("services/*", "application/x-python-object", "multi")
    devices = DATABASE_ACCESS.get_key("devices/*", "application/x-python-object", "multi")
    #
    # For all sensors and services see whether we have an error condition.
    #
    for xp, content in services.items() + devices.items() + badSensors.items():
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
                web.ctx.status = "200 OK"
                pass
