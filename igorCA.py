#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
# Enable coverage if installed and enabled through COVERAGE_PROCESS_START environment var
try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass
import sys
import igor
import os
import os.path
import shutil
import getpass
import tempfile
import subprocess
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import re
import json
import argparse
import igorVar


#IS_IP=re.compile(r'^[0-9.:]*$') # Not good enough, but does not match hostnames
IS_IP=re.compile(r'^[0-9:]*$') # Matches only IPv6 IP addresses so IPv4 addresses are (incorrectly) seen as hostnames

class SSLConfigParser(configparser.RawConfigParser):
    """SSL Configuration files are case-dependent"""
    
    SECTCRE = re.compile(
        r'\[\s*'                                 # [
        r'(?P<header>[^]\s]+)'                  # very permissive!
        r'\s*\]'                                 # ]
        )

    def optionxform(self, optionstr):
        return optionstr

USAGE="""
Usage: %s command [args]

Initialize or use igor Certificate Authority.
"""

class CAInterface(object):
    """Helper class to implement commands on local CA (using openSSL tool)"""
    
    def __init__(self, parent, database):
        self.parent = parent
        self.caDatabase = os.path.join(database, 'ca')
        self.intKeyFile = os.path.join(self.caDatabase, 'intermediate', 'private', 'intermediate.key.pem')
        self.intCertFile = os.path.join(self.caDatabase, 'intermediate', 'certs', 'intermediate.cert.pem')
        self.intAllCertFile = os.path.join(self.caDatabase, 'intermediate', 'certs', 'ca-chain.cert.pem')
        self.intConfigFile = os.path.join(self.caDatabase, 'intermediate', 'openssl.cnf')
        
    def isLocal(self):
        return True
        
    def isOK(self):
        if not os.path.exists(self.caDatabase):
            print("%s: No Igor CA self.database at %s" % (self.parent.argv0, self.caDatabase), file=sys.stderr)
            return False
        if not (os.path.exists(self.intKeyFile) and os.path.exists(self.intCertFile) and os.path.exists(self.intAllCertFile)):
            print("%s: Intermediate key, certificate and chain don't exist in %s" % (self.parent.argv0, self.caDatabase), file=sys.stderr)
            return False
        return True

    def ca_getRoot(self):
        """Return root certificate (in PEM form)"""
        return open(self.intAllCertFile).read()
        
    def ca_list(self):
        """Return list of all signatures signed"""
        indexFile = os.path.join(self.caDatabase, 'intermediate', 'index.txt')
        try:
            rv = open(indexFile).read()
        except IOError:
            rv = ''
        return rv            

    def ca_signCSR(self, csr):
        #
        # Save the CSR to a file
        #
        _, csrFile = tempfile.mkstemp('.csr')
        open(csrFile, 'w').write(csr)
        #
        # Get commonName and subjectAltName from the CSR
        #
        dnDict = self.parent.get_distinguishedName('req', csrFile)
        if not dnDict:
            return None
        commonName = dnDict['CN']
        altNames = self.parent.get_altNamesFromReq(csrFile)
        #
        # Create signing config file
        #
        csrConfigFile = self.parent.gen_configFile(commonName, altNames)
        if not csrConfigFile:
            return None
        #
        # Sign CSR
        #
        _, certFile = tempfile.mkstemp('.cert')        
        ok = self.parent.runSSLCommand('ca',
            '-config', csrConfigFile,
            '-batch',
            '-extensions', 'server_cert',
            '-days', '3650',
            '-notext',
            '-md', 'sha256',
            '-in', csrFile,
            '-out', certFile
            )
        if not ok:
            return None
        cert = open(certFile).read()
        return cert

    def ca_revoke(self, number):
        certFile = os.path.join(self.caDatabase, 'intermediate', 'newcerts', str(number)+'.pem')
        if not os.path.exists(certFile):
            print("%s: no such certificate: %s" % (self.parent.argv0, certFile), file=sys.stderr)
        ok = self.parent.runSSLCommand('ca', '-config', self.intConfigFile, '-revoke', certFile)
        if ok:
            ok = self.ca_genCRL()
        return ok
    
    def ca_genCRL(self):
        crlFile = os.path.join(self.parent.database, 'static', 'crl.pem')
        ok = self.parent.runSSLCommand('ca', '-config', self.intConfigFile, '-gencrl', '-out', crlFile)
        return ok
        
    def ca_getCRL(self):
        crlFile = os.path.join(self.parent.database, 'static', 'crl.pem')
        return open(crlFile).read()
        
    def get_distinguishedNameForCA(self):
        return self.parent.get_distinguishedName('x509', self.intCertFile)
           
    def get_csrConfigTemplate(self):
        """Return filename for an openssl config file to be used as a template for new reequests"""
        return self.intConfigFile
        
class CARemoteInterface(object):
    """Helper class to implement commands on remote CA (using REST calls to Igor server)"""

    def __init__(self, parent, igorServer):
        self.parent = parent
        # igorServer can either be a URL or an igorServer instance
        if isinstance(igorServer, str):
            igorServer = igorVar.IgorServer(igorServer)
        self.igor = igorServer
        
    def isLocal(self):
        return False
        
    def isOK(self):
        rv = self.igor.get('/plugin/ca/status', format='text/plain')
        rv = rv.strip()
        if rv:
            print("%s: remote CA: %s" % (self.parent.argv0, rv), file=sys.stderr)
        return not rv
        
    def ca_getRoot(self):
        return self.igor.get('/plugin/ca/root', format='text/plain')
        
    def ca_list(self):
        return self.igor.get('/plugin/ca/list', format='text/plain')
           
    def ca_signCSR(self, csr):
        return self.igor.get('/plugin/ca/sign', format='text/plain', query=dict(csr=csr))

    def ca_revoke(self, number):
        rv = self.igor.get('/plugin/ca/revoke', format='text/plain', query=dict(number=number))
        return not rv
        
    def ca_getCRL(self):
        return self.igor.get('/static/crl.pem', format='text/plain')
        
    def get_distinguishedNameForCA(self):
        dnString = self.igor.get('/plugin/ca/dn', format='application/json')
        return json.loads(dnString)
        
    def get_csrConfigTemplate(self):
        rv = self.igor.get('/plugin/ca/csrtemplate', format='text/plain')
        _, configFile = tempfile.mkstemp('.sslconfig')
        open(configFile, 'w').write(rv)
        return configFile
        
class IgorCA(object):
    """Interface to Certificate Authority for Igor.
    
    Arguments:
        argv0 (str): program name (for error messages and such)
        igorServer (str): optional URL for Igor server to use as CA (default: use local CA through openSSL commands)
        keySize (int): default keysize (default default: 2048 bits)
        database (str): for local CA: the location of the Igor database (default: ~/.igor)
    """
    
    def __init__(self, argv0, igorServer=None, keysize=None, database=None):
        self.argv0 = argv0
        self.keysize = keysize
        # Find username even when sudoed
        username = os.environ.get("SUDO_USER", getpass.getuser())
        # Igor package source directory
        self.igorDir = os.path.dirname(igor.__file__)
        #
        # Default self.database directory, CA directory and key/cert for signing.
        #
        if database:
            self.database = database
        elif 'IGORSERVER_DIR' in os.environ:
            self.database = os.environ['IGORSERVER_DIR']
        else:
            self.database = os.path.join(os.path.expanduser('~'+username), '.igor')
        if igorServer:
            self.ca = CARemoteInterface(self, igorServer)
        else:
            self.ca = CAInterface(self, self.database)

    def get_distinguishedName(self, type, configFile):
        """Helper that returns DN in key-value dict (from req or cert file)"""
        fp = subprocess.Popen(['openssl', type, '-in', configFile, '-noout', '-subject'], stdout=subprocess.PIPE, universal_newlines=True)
        data, _ = fp.communicate()
        if not data.startswith('subject='):
            print('%s: unexpected openssl x509 output: %s' % (self.argv0, data), file=sys.stderr)
            return None
        data = data[8:]
        data = data.strip()
        # grr... Some openSSL implementations use / as separator, some use ,
        rv = {}
        if '/' in data:
            dataItems = data.split('/')
            for di in dataItems:
                if not di: continue
                diSplit = di.split('=')
                k = diSplit[0]
                v = '='.join(diSplit[1:])
                rv[k] = v
        else:
            dataItems = data.split(',')
            for di in dataItems:
                if not di: continue
                diSplit = di.split('=')
                k = diSplit[0]
                v = '='.join(diSplit[1:])
                k = k.strip()
                v = v.strip()
                rv[k] = v
        return rv
        
    def runSSLCommand(self, *args):
        args = ('openssl',) + args
        print('+', ' '.join(args), file=sys.stderr)
        sts = subprocess.call(args)
        if sts != 0:
            print('%s: openssl returned status %d' % (self.argv0, sts), file=sys.stderr)
            return False
        return True
    
    def main(self, command, args):
        if command == 'help':
            self.cmd_help()
            sys.exit(0)

        if not os.path.exists(self.database):
            print("%s: No Igor database at %s" % (self.argv0, self.database), file=sys.stderr)
            sys.exit(1)
        
        if command == 'initialize':
            ok = self.cmd_initialize(*args)
            if not ok:
                sys.exit(1)
            sys.exit(0)
        if not self.ca.isOK():
            sys.exit(1)
        
    
        if not hasattr(self, 'cmd_' + command):
            print('%s: Unknown command "%s". Use help for help.' % (self.argv0, command), file=sys.stderr)
            sys.exit(1)
        handler = getattr(self, 'cmd_' + command)
        ok = handler(*args)
        if not ok:
            sys.exit(1)
        sys.exit(0)
    
  
    def get_altNamesFromReq(self, configFile):
        """Helper to get subjectAltName data from a request or certificate"""
        fp = subprocess.Popen(['openssl', 'req', '-in', configFile, '-noout', '-text'], stdout=subprocess.PIPE, universal_newlines=True)
        data, _ = fp.communicate()
        data = data.splitlines()
        while data and not 'X509v3 Subject Alternative Name' in data[0]:
            del data[0]
        if not data:
            return None
        del data[0]
        # Now next line has subjectAltName.
        fields = data[0].split(',')
        rv = []
        for f in fields:
            f = f.strip()
            f = f.replace('IP Address', 'IP')
            rv.append(f)
        return ','.join(rv)
        
    def fix_altNames(self, names):
        """Helper to turn list of hostnames/ip addresses into subjectAltName"""
        altNames = []
        for n in names:
            if IS_IP.match(n):
                altNames.append('IP:' + n)
            else:
                altNames.append('DNS:' + n)
        altNames = ','.join(altNames)
        return altNames
        
    def cmd_help(self, *args):
        """Show list of available commands"""
        print(USAGE % self.argv0)
        for name in dir(self):
            if not name.startswith('cmd_'): continue
            handler = getattr(self, name)
            print('%-10s\t%s' % (name[4:], handler.__doc__))
        return True
    
    def cmd_initialize(self, rootIssuer=None, intermediateIssuer=None):
        """create CA infrastructure, root key and certificate and intermediate key and certificate"""
        if not self.ca.isLocal():
            print("%s: initialize should only be used for local CA" % self.argv0, file=sys.stderr)
            return False
        if not rootIssuer or not intermediateIssuer:
            print("%s: requires both rootIssuer and intermediateIssuer identifiers" % self.argv0, file=sys.stderr)
            return False
        if os.path.exists(self.ca.intKeyFile) and os.path.exists(self.ca.intCertFile) and os.path.exists(self.ca.intAllCertFile):
            print('%s: Intermediate key and certificate already exist in %s' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            return False
        if os.path.exists(self.ca.intKeyFile) or os.path.exists(self.ca.intCertFile) or os.path.exists(self.ca.intAllCertFile):
            print('%s: Some key and certificate files already exist in %s.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            print('%s: Partial initialize failure, maybe? Remove directory %s and try again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            return False
        #
        # Create infrastructure if needed
        #
        if not os.path.exists(self.ca.caDatabase):
            # Old igor, probably: self.ca.caDatabase doesn't exist yet
            print()
            print('=============== Creating CA directories and infrastructure')
            print()
            src = os.path.join(self.igorDir, 'igorDatabase.empty')
            caSrc = os.path.join(src, 'ca')
            print('%s: Creating %s' % (self.argv0, caSrc), file=sys.stderr)
            shutil.copytree(caSrc, self.ca.caDatabase)
        #
        # Create openssl.cnf files from openssl.cnf.in
        #
        for caGroup in ('root', 'intermediate'):
            print()
            print('=============== Creating config for', caGroup)
            print()
            caGroupDir = os.path.join(self.ca.caDatabase, caGroup)
            caGroupConf = os.path.join(caGroupDir, 'openssl.cnf')
            caGroupConfIn = os.path.join(caGroupDir, 'openssl.cnf.in')
            if os.path.exists(caGroupConf):
                print('%s: %s already exists' % (self.argv0, caGroupConf), file=sys.stderr)
                print('%s: Partial initialize failure, maybe? Remove directory %s and try again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
                return False
            # Insert igor directory name into config file
            cfg = SSLConfigParser(allow_no_value=True)
            cfg.readfp(open(caGroupConfIn), caGroupConfIn)
            cfg.set('CA_default', 'igordir', self.database)
            cfg.write(open(caGroupConf, 'w'))
        #
        # Create root key and certificate
        #
        rootKeyFile = os.path.join(self.ca.caDatabase, 'root', 'private', 'ca.key.pem')
        rootCertFile = os.path.join(self.ca.caDatabase, 'root', 'certs', 'ca.cert.pem')
        rootConfigFile = os.path.join(self.ca.caDatabase, 'root', 'openssl.cnf')
        if  os.path.exists(rootKeyFile) and os.path.exists(rootCertFile) and os.path.exists(rootConfigFile):
            print()
            print('=============== Root key and certificate already exist')
            print()
        else:
            print()
            print('=============== Creating root key and certificate')
            print()
            ok = self.runSSLCommand('genrsa', '-out', rootKeyFile, '2048' if self.keysize is None else self.keysize)
            if not ok:
                print('%s: Error during root key generation. Remove directory %s before trying again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
                return False
            os.chmod(rootKeyFile, 0o400)
            ok = self.runSSLCommand('req', 
                '-config', rootConfigFile, 
                '-key', rootKeyFile, 
                '-subj', rootIssuer,
                '-new', 
                '-x509', 
                '-days', '7300', 
                '-sha256', 
                '-extensions', 'v3_ca', 
                '-out', rootCertFile
                )
            if not ok:
                print('%s: Error during root request generation. Remove directory %s before trying again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
                return False
            os.chmod(rootCertFile, 0o400)
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', rootCertFile)
        if not ok:
            print('%s: Error during root certificate signing. Remove directory %s before trying again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            return False
        #
        # Create intermediate key, CSR and certificate
        #
        print()
        print('=============== Creating intermediate key and certificate')
        print()
        ok = self.runSSLCommand('genrsa', '-out', self.ca.intKeyFile, '2048' if self.keysize is None else self.keysize)
        os.chmod(self.ca.intKeyFile, 0o400)
        if not ok:
            print('%s: Error during intermediate key generation. Remove directory %s before trying again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            return False
        intCsrFile = os.path.join(self.ca.caDatabase, 'intermediate', 'certs', 'intermediate.csr.pem')
        ok = self.runSSLCommand('req', 
            '-config', self.ca.intConfigFile, 
            '-key', self.ca.intKeyFile, 
            '-subj', intermediateIssuer,
            '-new', 
            '-sha256', 
            '-out', intCsrFile
            )
        if not ok:
            print('%s: Error during intermediate request generation. Remove directory %s before trying again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            return False
        ok = self.runSSLCommand('ca',
            '-config', rootConfigFile,
            '-extensions', 'v3_intermediate_ca',
            '-days', '3650',
            '-notext',
            '-md', 'sha256',
            '-in', intCsrFile,
            '-out', self.ca.intCertFile
            )
        if not ok:
            print('%s: Error during intermediate certificate signing. Remove directory %s before trying again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            return False
        os.chmod(self.ca.intCertFile, 0o400)
        #
        # Verify the intermediate certificate
        #
        ok = self.runSSLCommand('verify',
            '-CAfile', rootCertFile,
            self.ca.intCertFile
            )
        if not ok:
            print('%s: Error during intermediate certificate verification. Remove directory %s before trying again.' % (self.argv0, self.ca.caDatabase), file=sys.stderr)
            return False
        #
        # Concatenate
        #
        ofp = open(self.ca.intAllCertFile, 'w')
        ofp.write(open(self.ca.intCertFile).read())
        ofp.write(open(rootCertFile).read())
        ofp.close()
        #
        # Now lock out the root directory structure.
        #
        os.chmod(os.path.join(self.ca.caDatabase, 'root'), 0)
        #
        # And finally print the chained file
        #
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', self.ca.intAllCertFile)
        if not ok:
            return False
        print()
        print("=============== Igor CA initialized correctly")
        print()
        return True

    def cmd_dn(self):
        """Return CA distinghuished name as a JSON structure"""
        dnData = self.ca.get_distinguishedNameForCA()
        json.dump(dnData, sys.stdout)
        sys.stdout.write('\n')
        return True
        
    def do_dn(self):
        """Return CA distinghuished name as a JSON structure"""
        dnData = self.ca.get_distinguishedNameForCA()
        return json.dumps(dnData)
                
    def cmd_selfCSR(self, *allNames):
        """Create secret key and CSR for Igor itself. Outputs CSR."""
        csr = self.do_selfCSR(*allNames)
        if not csr:
            return False
        sys.stdout.write(csr)
        return True
        
    def do_genCSR(self, keyFile, csrFile, csrConfigFile, allNames=[], keysize=None):
        """Create key and CSR for a service. Returns CSR."""
        if len(allNames) < 1:
            print('%s: genCSR requires ALL names (commonName first) as arguments' % self.argv0, file=sys.stderr)
            print('for example: %s genCSR igor.local localhost 127.0.0.1' % self.argv0, file=sys.stderr)
            return False
        #
        # Create key
        #
        if keysize == None:
            keysize = self.keysize
        ok = self.runSSLCommand('genrsa', '-out', keyFile, '2048' if keysize is None else str(keysize))
        if not ok:
            return None
        os.chmod(keyFile, 0o400)
        #
        # Construct commonName and subjectAltNames
        #
        commonName = allNames[0]
        altNames = self.fix_altNames(allNames)

        #
        # Create CSR config file
        #
        csrConfigFile = self.gen_configFile(commonName, altNames, csrConfigFile)
        if not csrConfigFile:
            return None
        #
        # Create CSR
        #
        if not csrFile:
            _, csrFile = tempfile.mkstemp('.csr')

        ok = self.runSSLCommand('req',
            '-config', csrConfigFile,
            '-key', keyFile,
            '-new',
            '-sha256',
            '-out', csrFile
            )
        if not ok:
            return None
        csrData = open(csrFile).read()
        return csrData
        
    def do_signCSR(self, csr):
        """Sign a CSR. Returns certificate."""
        return self.ca.ca_signCSR(csr)
        
    def cmd_genCRL(self):
        """Generate CRL in static/crl.pem"""
        if not self.ca.isLocal():
            print("%s: genCRL should only be used for local CA" % self.argv0, file=sys.stderr)
            return False
        ok = self.ca.ca_genCRL()
        return ok
        
    def cmd_getCRL(self):
        """Output the CRL (Certificate Revocation List)"""
        rv = self.ca.ca_getCRL()
        print(rv)
        return True
        
    def cmd_revoke(self, number):
        """Revoke a certificate. Argument is the number of the certificate to revoke (see list). Regenerates CRL as well."""
        ok = self.ca.ca_revoke(number)
        return ok
        
    do_revoke = cmd_revoke
    
    def gen_configFile(self, commonName, altNames, configFile=None):
        """Helper function to create CSR or signing config file"""
        if not configFile:
            _, configFile = tempfile.mkstemp('.sslconfig')

        dnDict = self.ca.get_distinguishedNameForCA()
        if not dnDict:
            return None
        dnDict['CN'] = commonName

        cfg = SSLConfigParser(allow_no_value=True)
        cfgSource = self.ca.get_csrConfigTemplate()
        cfg.readfp(open(cfgSource), cfgSource) # xxxjack
 
        cfg.remove_section('req_distinguished_name')
        cfg.add_section('req_distinguished_name')
        for k, v in list(dnDict.items()):
            cfg.set('req_distinguished_name', k, v)
        # Set to non-interactive
        cfg.set('req', 'prompt', 'no')
        # Add the subjectAltName
        cfg.set('req', 'req_extensions', 'req_ext')
        cfg.add_section('req_ext')
        cfg.set('req_ext', 'subjectAltName', altNames)
        # And add subjectAltName to server_cert section
        cfg.set('server_cert', 'subjectAltName', altNames)
        # Write to CSR config file
        ofp = open(configFile, 'w')
        cfg.write(ofp)
        ofp.close()
        return configFile
        
    def cmd_self(self, *allNames):
        """Create a server key and certificate for Igor itself, and sign it with the intermediate Igor CA key"""
        igorKeyFile = os.path.join(self.database, 'igor.key')
        igorCsrFile = os.path.join(self.database, 'igor.csr')
        igorCsrConfigFile = os.path.join(self.database, 'igor.csrconfig')
        igorCertFile = os.path.join(self.database, 'igor.crt')
        if os.path.exists(igorKeyFile) and os.path.exists(igorCertFile):
            print('%s: igor.key and igor.crt already exist in %s' % (self.argv0, self.database), file=sys.stderr)
            return False
            
        csr = self.do_genCSR(igorKeyFile, igorCsrFile, igorCsrConfigFile, allNames)
        if not csr:
            return False
            
        cert = self.do_signCSR(csr)
        if not cert:
            return False
        open(igorCertFile, 'w').write(cert)

        # Verify it
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', igorCertFile)
        if not ok:
            return False
        return True
                    
    def cmd_getRoot(self):
        """Returns the signing certificate chain (for installation in browser or operating system)"""
        sys.stdout.write(self.ca.ca_getRoot())
        return True
        
    def do_getRoot(self):
        """Returns the signing certificate chain (for installation in browser or operating system)"""
        return self.ca.ca_getRoot()
        
    def cmd_sign(self, csrfile=None, certfile=None):
        """Sign a Certificate Signing Request and return the certificate."""
        if not csrfile or not certfile:
            print("Usage: %s sign csrfile certfile" % sys.argv[0], file=sys.stderr)
            return False
        csrdata = open(csrfile).read()
        certdata = sekf.do_signCSR(csrdata)
        if not certdata:
            return False
        open(certfile, 'w').write(certdata)
        return True
        
    def cmd_gen(self, prefix=None, *allNames):
        """Generate a a server key and certificate for a named service and sign it with the intermediate Igor CA key."""
        if not prefix or not allNames:
            print("Usage: %s gen keyfilenameprefix commonName [subjectAltNames ...]" % sys.argv[0], file=sys.stderr)
            return False
        
        keyFile = prefix + '.key'
        csrFile = prefix + '.csr'
        csrConfigFile = prefix + '.csrConfig'
        certFile = prefix + '.crt'
        if os.path.exists(keyFile) and os.path.exists(certFile):
            print('%s: %s and %s already exist' % (self.argv0, keyFile, certFile), file=sys.stderr)
            return False
            
        csr = self.do_genCSR(keyFile, csrFile, csrConfigFile, allNames)
        if not csr:
            return False
            
        cert = self.do_signCSR(csr)
        if not cert:
            return False
        open(certFile, 'w').write(cert)

        # Verify it
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', certFile)
        if not ok:
            return False
        return True

    def cmd_list(self):
        """Return list of certificates signed."""
        sys.stdout.write(self.ca.ca_list())
        return False
        
    def do_list(self):
        """Return list of certificates signed."""
        return self.ca.ca_list()
        
    def cmd_status(self):
        """Returns nothing if CA status is ok, otherwise error message"""
        return self.ca.isOK()
        
    def do_status(self):
        """Returns nothing if CA status is ok, otherwise error message"""
        if self.ca.isOK():
            return ""
        return "CA server configuration error, or not initialized"
        
    def cmd_csrtemplate(self):
        """Return template config file for for openSSL CSR request"""
        fn = self.ca.get_csrConfigTemplate()
        sys.stdout.write(open(fn).read())
        
    def do_csrtemplate(self):
        """Return template config file for for openSSL CSR request"""
        fn = self.ca.get_csrConfigTemplate()
        return open(fn).read()
     
def argumentParser():
    parser = igorVar.igorArgumentParser(description="Igor Certificate and Key utility")
    parser.add_argument("-s", "--keysize", metavar="BITS", help="Override key size (default: 2048)")
    parser.add_argument("-r", "--remote", action="store_true", help="Use CA on remote Igor (default is on the local filesystem)")
    parser.add_argument("-d", "--database", metavar="DIR", help="(local only) Database and scripts are stored in DIR (default: ~/.igor, environment IGORSERVER_DIR)")
    parser.add_argument("action", help="Action to perform: help, initialize, ...", default="help")
    parser.add_argument("arguments", help="Arguments to the action", nargs="*")
    return parser
       
def main():
    parser = argumentParser()
    args = parser.parse_args()
    igorServer = None
    if args.remote:
        if not args.noSystemRootCertificates and not os.environ.get('REQUESTS_CA_BUNDLE', None):
            # The requests package uses its own set of certificates, ignoring the ones the user has added to the system
            # set. By default, override that behaviour.
            for cf in ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/certs/ca-certificates.crt"]:
                if os.path.exists(cf):
                    os.putenv('REQUESTS_CA_BUNDLE', cf)
                    os.environ['REQUESTS_CA_BUNDLE'] = cf
                    break
        igorServer = igorVar.IgorServer(args.url, bearer_token=args.bearer, access_token=args.access, credentials=args.credentials, noverify=args.noverify, certificate=args.certificate)
    m = IgorCA(sys.argv[0], igorServer, keysize=args.keysize, database=args.database)
    if not args.action:
        return m.main('help', [])
    return m.main(args.action, args.arguments)
    
if __name__ == '__main__':
    main()
