from __future__ import unicode_literals
from builtins import object
import json
import igorCA
import os
import sys

DEBUG=False

INDEX_HTML="""<html lang="en">
<head>
	<meta http-equiv="content-type" content="text/html; charset=utf-8">
	<title>Igor Certificate Authority</title>
</head>
<body>
	<h1>Igor Certificate Authority</h1>
	<h2>Root Certificate Chain</h2>
	<p>To trust certificates signed by this Igor CA, download the <a href="ca/root">root certificate chain</a> and install in your browser or system.</p>
	<p>If available, the <a href="/static/crl.pem">Certificate Revocation List</a> can be downloaded too.</p>
	<h2>Listing all Certificates</h2>
	<p>To list certificates signed by this Igor CA, see the <a href="ca/list">certificate listing</a>.</p>
	<p>CRL and Revocation to be done later.</p>
	<h2>Signing a certificate</h2>
	<p>Create a key and CSR (Certificate Signing Request) locally, possibly using the <i>igorCA csr</i> command.</p>
	<p>Enter the CSR in PEM for in the following field and submit.</p>
	<form action="ca/sign">
	<textarea name="csr" rows="8" cols="60"></textarea>
	<br>
	<input type="submit" value="Submit">
	</form>
	<p>The result is the (PEM-encoded) certificate you can use for your service (together with the key form the previous step).</p>
</body>
</html>
"""

class CAPlugin(object):
    def __init__(self, igor):
        self.igor = igor
        self.ca = None
    
    def initCA(self):
        if self.ca: return
        self.ca = igorCA.IgorCA('igor/plugin/ca')
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
        
    def list(self, token=None):
        self.initCA()
        listData = self.ca.do_list()
        return listData
        
    def status(self, token=None):
        self.initCA()
        statusData = self.ca.do_status()
        return statusData

    def dn(self, token=None):
        self.initCA()
        dnData = self.ca.do_dn()
        return dnData
        
    def csrtemplate(self, token=None):
        self.initCA()
        tmplData = self.ca.do_csrtemplate()
        return tmplData
        
    def sign(self, csr, token=None):
        self.initCA()
        cert = self.ca.do_signCSR(csr)
        if not cert:
            self.igor.app.raiseHTTPError('500 Could not sign certificate')
        return self.igor.app.responseWithHeaders(cert, {'Content-type':'application/x-pem-file', 'Content-Disposition':'attachment; filename="certificate.pem"'})
        
    def root(self, token=None):
        self.initCA()
        chain = self.ca.do_getRoot()
        if not chain:
            self.igor.app.raiseHTTPError('500 Could not obtain root certificate chain')
        return self.igor.app.responseWithHeaders(chain, {'Content-type':'application/x-pem-file', 'Content-Disposition':'attachment; filename="igor-root-certificate-chain.pem"'})

    def _generateKeyAndSign(self, names, token=None):
        self._initCA()
        _, keyFile = tempfile.mkstemp(suffix=".key")
        _, csrFile = tempfile.mkstemp(suffix=".csr")
        _, csrConfigFile = tempfile.mkstemp(suffix=".csrconfig")
        csrData = self.ca.do_genCSR(keyFile, csrFile, csrConfigFile, *names)
        certData = self.ca.do_signCSR(csrData)
        keyData = open(keyFile).read()
        print('xxxjack keyFile', keyFile, 'csrFile', csrFile, 'csrConfigFile', csrConfigFile)
#        os.unlink(keyFile)
#        os.unlink(csrFile)
#        os.unlink(csrConfigFile)
        return keyData, certData
        
    def generateKeyAndSign(self, dn, alt1=None, alt2=None, alt3=None, alt4=None, token=None):
        names = [dn]
        if alt1:
            names.append(alt1)
        if alt2:
            names.append(alt2)
        if alt3:
            names.append(alt3)
        if alt4:
            names.append(alt4)
        keyData, certData = self._generateKeyAndSign(names, token)
        return dict(key=keyData, cert=certData)
        
def igorPlugin(igor, pluginName, pluginData):
    return CAPlugin(igor)
    
