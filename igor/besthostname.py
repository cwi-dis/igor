"""A method to get the best hostname for this machine"""
from __future__ import unicode_literals
import socket

def besthostname():
    """A method to get the best hostname for this machine"""
    #
    # First find our preferred network interface address
    #
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('google.com', 9999))
    except socket.gaierror:
        return '127.0.0.1'
    ip, _ = s.getsockname()
    #
    # Now get our hostname, adding '.local' if needed
    #
    hostname = socket.getfqdn()
    if not '.' in hostname:
        hostname = hostname + '.local'
    #
    # See if this hostname matches our external IP address, return if so
    #
    try:
        _, _, ipaddrs = socket.gethostbyname_ex(hostname)
    except socket.gaierror:
        ipaddrs = []
    for extip in ipaddrs:
        if extip == ip:
            return hostname
    #
    # Otherwise try a reverse DNS lookup
    #
    try:
        realHostname, _, _ = socket.gethostbyaddr(ip)
        return realHostname
    except socket.gaierror:
        pass
    except socket.herror:
        pass
    #
    # If this is a .local name  we use the hostname
    #
    if hostname[-6:] == '.local':
        return hostname
    #
    # Otherwise return the IP address
    #
    return ip
    
    
