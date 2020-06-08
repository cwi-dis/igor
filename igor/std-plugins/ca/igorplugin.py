import json
import igorCA
import os
import sys
import tempfile
import urllib

DEBUG=False

class CAPlugin(object):
    def __init__(self, igor, pluginData):
        self.igor = igor
        self.ca = None
        self.caServerUrl = pluginData.get('ca')
        
    def initCA(self):
        if self.ca: return
        self.ca = igorCA.IgorCA('igor/plugin/ca', igorServer=self.caServerUrl)
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
        
    def list(self, token=None, callerToken=None):
        self.initCA()
        listData = self.ca.do_list()
        return listData
        
    def status(self, token=None, callerToken=None):
        self.initCA()
        statusData = self.ca.do_status()
        return statusData

    def dn(self, token=None, callerToken=None):
        self.initCA()
        dnData = self.ca.do_dn()
        return dnData
        
    def csrtemplate(self, token=None, callerToken=None):
        self.initCA()
        tmplData = self.ca.do_csrtemplate()
        return tmplData
        
    def sign(self, csr, token=None, callerToken=None, returnTo=None):
        self.initCA()
        cert = self.ca.do_signCSR(csr)
        if not cert:
            self.igor.app.raiseHTTPError('500 Could not sign certificate')
        if returnTo:
            q = dict(cert=cert)
            queryString = urllib.parse.urlencode(q)
            if '?' in returnTo:
                returnTo += '&' + queryString
            else:
                returnTo += '?' + queryString
            return self.igor.app.raiseSeeother(returnTo)
        return self.igor.app.responseWithHeaders(cert, {'Content-type':'application/x-pem-file', 'Content-Disposition':'attachment; filename="certificate.pem"'})
        
    def root(self, token=None, callerToken=None):
        self.initCA()
        chain = self.ca.do_getRoot()
        if not chain:
            self.igor.app.raiseHTTPError('500 Could not obtain root certificate chain')
        return self.igor.app.responseWithHeaders(chain, {'Content-type':'application/x-pem-file', 'Content-Disposition':'attachment; filename="igor-root-certificate-chain.pem"'})

    def revoke(self, number, token=None, callerToken=None, returnTo=None):
        self.initCA()
        ok = self.ca.do_revoke(number)
        if not ok:
            return self.igor.app.raiseHTTPError('500 Error while revoking %s' % number)
        if returnTo:
            return self.igor.app.raiseSeeother(returnTo)
        return ''
        
    def _generateKeyAndSign(self, names, keysize=None, token=None, callerToken=None):
        self.initCA()
        _, keyFile = tempfile.mkstemp(suffix=".key")
        _, csrFile = tempfile.mkstemp(suffix=".csr")
        _, csrConfigFile = tempfile.mkstemp(suffix=".csrconfig")
        if not keysize:
            keysize = None
        csrData = self.ca.do_genCSR(keyFile, csrFile, csrConfigFile, allNames=names, keysize=keysize)
        certData = self.ca.do_signCSR(csrData)
        keyData = open(keyFile).read()
        os.unlink(keyFile)
        os.unlink(csrFile)
        os.unlink(csrConfigFile)
        if not keyData:
            return self.igor.app.raiseHTTPError("500 Could not create key")
        if not csrData:
            return self.igor.app.raiseHTTPError("500 Could not certificate signing request")
        if not certData:
            return self.igor.app.raiseHTTPError("500 Could not create certificate")
        return keyData, certData
        
    def generateKeyAndSign(self, names, keysize=None, token=None, callerToken=None, returnTo=None):
        names = names.split()
        keyData, certData = self._generateKeyAndSign(names, keysize, token)
        if returnTo:
            q = dict(key=keyData, cert=certData)
            queryString = urllib.parse.urlencode(q)
            if '?' in returnTo:
                returnTo += '&' + queryString
            else:
                returnTo += '?' + queryString
            return self.igor.app.raiseSeeother(returnTo)
        return self.igor.app.responseWithHeaders(keyData+certData, {"Content-type":"text/plain"})

        
def igorPlugin(igor, pluginName, pluginData):
    return CAPlugin(igor, pluginData)
    
