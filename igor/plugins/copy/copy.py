"""Copy values or subtrees, either locally or remotely.

Currently a quick hack using either direct database access or httplib2, synchronously.
Should use callUrl, so local/remote becomes similar, and some form
of callback mechanism so it can run asynchronously.
"""
import requests
import web
import httplib2

DATABASE_ACCESS=None

def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

def copy(src=None, dst=None, mimetype="text/plain", method='PUT'):
    if not src:
        raise myWebError("401 Required argument name missing")
    if not dst:
        raise myWebError("401 Required argument dst missing")
    
    srcParsed = urlparse.urlparse(src)
    if srcParsed.scheme == '' and srcParsed.netloc == '':
        # Local source
        srcValue = DATABASE_ACCESS.get_key(srcParsed.path, mimetype, None)
    else:
        # Remote source
        h = httplib2.Http()
        resp, srcValue = h.request(src, headers=dict(Accepts=mimetype)
        if resp.status != 200:
            raise myWebError("%d %s (%s)" % (resp.status, resp.reason, src))
    
    dstParsed = urlparse.urlparse(dst)
    if dstParsed.scheme == '' and dstParsed.netloc == '':
        rv = DATABASE_ACCESS.put_key(dstParsed.path, None, srcValue, mimetype, method=='PUT')
    else:
        headers = {'Content-type' : mimetype}
        h = httplib2.Http()
        resp, rv = h.request(dst, method=method, headers=headers, data=srcValue)
        if resp.status != 200:
            raise myWebError("%d %s (%s)" % (resp.status, resp.reason, dst))
    
    return rv
