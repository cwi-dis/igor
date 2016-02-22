"""Test liveness of hosts"""
import socket
import web

DATABASE_ACCESS=None

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

def lan(name=None, service='devices/%s/alive', ip=None, port=80):
    if not name:
        raise myWebError("401 Required argument name missing")
    if not ip:
        ip = name
    alive = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, int(port)))
    except socket.error:
        alive = False
    if service:
        if '%' in service:
            service = service % name
        if not DATABASE_ACCESS: 
            msg = "502 plugin did not have DATABASE_ACCESS set"
            raise web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')
        try:
        	oldValue = DATABASE_ACCESS.get_key(service, 'text/plain', None)
        except web.HTTPError:
        	web.ctx.status = "200 OK"
        	oldValue = 'rabarber'
		if oldValue != repr(alive):
			try:
				rv = DATABASE_ACCESS.put_key(service, 'text/plain', None, repr(alive), 'text/plain', replace=True)
			except web.HTTPError:
				raise myWebError("501 Failed to store into %s" % service)
    return repr(alive)
