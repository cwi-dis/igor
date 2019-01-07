"""Copy values or subtrees, either locally or remotely.

Currently a quick hack using either direct database access or httplib2, synchronously.
Should use callUrl, so local/remote becomes similar, and some form
of callback mechanism so it can run asynchronously.
"""
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import requests
import httplib2
import urllib.parse

class CopyTree(object):
    def __init__(self, igor):
        self.igor = igor

    def index(self, src=None, dst=None, mimetype="text/plain", method='PUT', token=None, callerToken=None):
        if not src:
            self.igor.app.raiseHTTPError("401 Required argument name missing")
        if not dst:
            self.igor.app.raiseHTTPError("401 Required argument dst missing")
    
        srcParsed = urllib.parse.urlparse(src)
        if srcParsed.scheme == '' and srcParsed.netloc == '':
            # Local source
            srcValue = self.igor.databaseAccessor.get_key(srcParsed.path, mimetype, None, token=callerToken)
        else:
            # Remote source
            h = httplib2.Http()
            resp, srcValue = h.request(src, headers=dict(Accept=mimetype))
            if resp.status != 200:
                self.igor.app.raiseHTTPError("%d %s (%s)" % (resp.status, resp.reason, src))
    
        dstParsed = urllib.parse.urlparse(dst)
        if dstParsed.scheme == '' and dstParsed.netloc == '':
            rv = self.igor.databaseAccessor.put_key(dstParsed.path, 'text/plain', None, srcValue, mimetype, callerToken, method=='PUT')
        else:
            headers = {'Content-type' : mimetype}
            h = httplib2.Http()
            resp, rv = h.request(dst, method=method, headers=headers, data=srcValue)
            if resp.status != 200:
                self.igor.app.raiseHTTPError("%d %s (%s)" % (resp.status, resp.reason, dst))

        return rv

def igorPlugin(igor, pluginName, pluginData):
        return CopyTree(igor)
        
