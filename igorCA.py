#!/usr/bin/env python
import sys
import igor
import os
import os.path
import shutil
import getpass
import tempfile
import subprocess
import ConfigParser
import re
import json
import argparse
import igorVar

IS_IP=re.compile(r'^[0-9.:]*$') # Not good enough, but does not match hostnames

class SSLConfigParser(ConfigParser.RawConfigParser):
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

class CAInterface:
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
            print >>sys.stderr, "%s: No Igor CA self.database at %s" % (self.parent.argv0, self.caDatabase)
            return False
        if not (os.path.exists(self.intKeyFile) and os.path.exists(self.intCertFile) and os.path.exists(self.intAllCertFile)):
            print >>sys.stderr, "%s: Intermediate key, certificate and chain don't exist in %s" % (self.parent.argv0, self.caDatabase)
            return False
        return True

    def ca_getRoot(self):
        """Return root certificate (in PEM form)"""
        return open(self.intAllCertFile).read()
        
    def ca_list(self):
        """Return list of all signatures signed"""
        indexFile = os.path.join(self.caDatabase, 'intermediate', 'index.txt')
        return open(indexFile).read()

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

    def get_distinguishedNameForCA(self):
        return self.parent.get_distinguishedName('x509', self.intCertFile)
           
    def get_csrConfigTemplate(self):
        """Return filename for an openssl config file to be used as a template for new reequests"""
        return self.intConfigFile
        
class CARemoteInterface:
    def __init__(self, parent, igorServer):
        self.parent = parent
        self.igor = igorServer
        
    def isLocal(self):
        return False
        
    def isOK(self):
        rv = self.igor.get('/plugin/ca/status', format='text/plain')
        rv = rv.strip()
        if rv:
            print >>sys.stderr, "%s: remote CA: %s" % (self.parent.argv0, rv)
        return not rv
        
    def ca_getRoot(self):
        return self.igor.get('/plugin/ca/root', format='text/plain')
        
    def ca_list(self):
        return self.igor.get('/plugin/ca/list', format='text/plain')
           
    def ca_signCSR(self, csr):
        return self.igor.get('/plugin/ca/sign', format='text/plain', query=dict(csr=csr))

    def get_distinguishedNameForCA(self):
        dnString = self.igor.get('/plugin/ca/dn', format='application/json')
        return json.loads(dnString)
        
    def get_csrConfigTemplate(self):
        rv = self.igor.get('/plugin/ca/csrtemplate', format='text/plain')
        _, configFile = tempfile.mkstemp('.sslconfig')
        open(configFile, 'w').write(rv)
        return configFile
        
class IgorCA:
    def __init__(self, argv0, igorServer=None):
        self.argv0 = argv0
        # Find username even when sudoed
        username = os.environ.get("SUDO_USER", getpass.getuser())
        # Igor package source directory
        self.igorDir = os.path.dirname(igor.__file__)
        #
        # Default self.database directory, CA directory and key/cert for signing.
        #
        self.database = os.path.join(os.path.expanduser('~'+username), '.igor')
        if igorServer:
            self.ca = CARemoteInterface(self, igorServer)
        else:
            self.ca = CAInterface(self, self.database)

    def get_distinguishedName(self, type, configFile):
        """Helper that returns DN in key-value dict (from req or cert file)"""
        fp = subprocess.Popen(['openssl', type, '-in', configFile, '-noout', '-subject'], stdout=subprocess.PIPE)
        data, _ = fp.communicate()
        if not data.startswith('subject='):
            print >>sys.stderr, '%s: unexpected openssl x509 output: %s' % (self.argv0, data)
            return None
        data = data[8:]
        data = data.strip()
        dataItems = data.split('/')
        rv = {}
        for di in dataItems:
            if not di: continue
            diSplit = di.split('=')
            k = diSplit[0]
            v = '='.join(diSplit[1:])
            rv[k] = v
        return rv
        
    def runSSLCommand(self, *args):
        args = ('openssl',) + args
        print >>sys.stderr, '+', ' '.join(args)
        sts = subprocess.call(args)
        if sts != 0:
            print >>sys.stderr, '%s: openssl returned status %d' % (self.argv0, sts)
            return False
        return True
    
    def main(self, command, args):
        if command == 'help':
            self.cmd_help()
            sys.exit(0)

        if not os.path.exists(self.database):
            print >>sys.stderr, "%s: No Igor self.database at %s" % (self.argv0, self.database)
            sys.exit(1)
        
        if command == 'initialize':
            ok = self.cmd_initialize()
            if not ok:
                sys.exit(1)
            sys.exit(0)
        if not self.ca.isOK():
            sys.exit(1)
        
    
        if not hasattr(self, 'cmd_' + command):
            print >> sys.stderr, '%s: Unknown command "%s". Use help for help.' % (self.argv0, command)
            sys.exit(1)
        handler = getattr(self, 'cmd_' + command)
        ok = handler(*args)
        if not ok:
            sys.exit(1)
        sys.exit(0)
    
  
    def get_altNamesFromReq(self, configFile):
        """Helper to get subjectAltName data from a request or certificate"""
        fp = subprocess.Popen(['openssl', 'req', '-in', configFile, '-noout', '-text'], stdout=subprocess.PIPE)
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
        print USAGE % self.argv0
        for name in dir(self):
            if not name.startswith('cmd_'): continue
            handler = getattr(self, name)
            print '%-10s\t%s' % (name[4:], handler.__doc__)
    
    def cmd_initialize(self):
        """create CA infrastructure, root key and certificate and intermediate key and certificate"""
        if not self.ca.isLocal():
            print >>sys.stderr, "%s: initialize should only be used for local CA" % self.argv0
            return False
        if os.path.exists(self.ca.intKeyFile) and os.path.exists(self.ca.intCertFile) and os.path.exists(self.ca.intAllCertFile):
            print >>sys.stderr, '%s: Intermediate key and certificate already exist in %s' % (self.argv0, self.ca.caDatabase)
            return False
        #
        # Create infrastructure if needed
        #
        if not os.path.exists(self.ca.caDatabase):
            # Old igor, probably: self.ca.caDatabase doesn't exist yet
            print
            print '=============== Creating CA directories and infrastructure'
            src = os.path.join(self.igorDir, 'igorDatabase.empty')
            caSrc = os.path.join(src, 'ca')
            print >>sys.stderr, '%s: Creating %s' % (self.argv0, caSrc)
            shutil.copytree(caSrc, self.ca.caDatabase)
        #
        # Create openssl.cnf files from openssl.cnf.in
        #
        for caGroup in ('root', 'intermediate'):
            print
            print '=============== Creating config for', caGroup
            caGroupDir = os.path.join(self.ca.caDatabase, caGroup)
            caGroupConf = os.path.join(caGroupDir, 'openssl.cnf')
            caGroupConfIn = os.path.join(caGroupDir, 'openssl.cnf.in')
            if os.path.exists(caGroupConf):
                print >> sys.stderr, '%s: %s already exists' % (self.argv0, caGroupConf)
                return False
            data = open(caGroupConfIn).read()
            data = data.replace('%INSTALLDIR%', self.database)
            open(caGroupConf, 'w').write(data)
        #
        # Create root key and certificate
        #
        rootKeyFile = os.path.join(self.ca.caDatabase, 'root', 'private', 'ca.key.pem')
        rootCertFile = os.path.join(self.ca.caDatabase, 'root', 'certs', 'ca.cert.pem')
        rootConfigFile = os.path.join(self.ca.caDatabase, 'root', 'openssl.cnf')
        if  os.path.exists(rootKeyFile) and os.path.exists(rootCertFile) and os.path.exists(rootConfigFile):
            print
            print '=============== Root key and certificate already exist'
        else:
            print
            print '=============== Creating root key and certificate'
            ok = self.runSSLCommand('genrsa', '-aes256', '-out', rootKeyFile, '4096')
            if not ok:
                return False
            os.chmod(rootKeyFile, 0400)
            ok = self.runSSLCommand('req', 
                '-config', rootConfigFile, 
                '-key', rootKeyFile, 
                '-new', 
                '-x509', 
                '-days', '7300', 
                '-sha256', 
                '-extensions', 'v3_ca', 
                '-out', rootCertFile
                )
            if not ok:
                return False
            os.chmod(rootCertFile, 0400)
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', rootCertFile)
        if not ok:
            return False
        #
        # Create intermediate key, CSR and certificate
        #
        print
        print '=============== Creating intermediate key and certificate'
        ok = self.runSSLCommand('genrsa', '-out', self.ca.intKeyFile, '4096')
        os.chmod(self.ca.intKeyFile, 0400)
        if not ok:
            return False
        intCsrFile = os.path.join(self.ca.caDatabase, 'intermediate', 'certs', 'intermediate.csr.pem')
        ok = self.runSSLCommand('req', 
            '-config', self.ca.intConfigFile, 
            '-key', self.ca.intKeyFile, 
            '-new', 
            '-sha256', 
            '-out', intCsrFile
            )
        if not ok:
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
            return False
        os.chmod(self.ca.intCertFile, 0400)
        #
        # Verify the intermediate certificate
        #
        ok = self.runSSLCommand('verify',
            '-CAfile', rootCertFile,
            self.ca.intCertFile
            )
        if not ok:
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
    
        return True

    def cmd_dn(self):
        """Return CA distinghuished name as a JSON structure"""
        dnData = self.ca.get_distinguishedNameForCA()
        json.dump(dnData, sys.stdout)
        sys.stdout.write('\n')
        
    def do_dn(self):
        dnData = self.ca.get_distinguishedNameForCA()
        return json.dumps(dnData)
                
    def cmd_selfCSR(self, *allNames):
        """Create secret key and CSR for Igor itself. Outputs CSR."""
        csr = self.do_selfCSR(*allNames)
        if not csr:
            return False
        sys.stdout.write(csr)
        return True
        
    def do_genCSR(self, keyFile, csrFile, csrConfigFile, *allNames):
        """Create key and CSR for a service. Returns CSR."""
        if len(allNames) < 1:
            print >>sys.stderr, '%s: genCSR requires ALL names (commonName first) as arguments' % self.argv0
            print >> sys.stderr, 'for example: %s genCSR igor.local localhost 127.0.0.1' % self.argv0
            return False
        #
        # Create key
        #
        ok = self.runSSLCommand('genrsa', '-out', keyFile, '2048')
        if not ok:
            return None
        os.chmod(keyFile, 0400)
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
        for k, v in dnDict.items():
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
            print >>sys.stderr, '%s: igor.key and igor.crt already exist in %s' % (self.argv0, self.database)
            return False
            
        csr = self.do_genCSR(igorKeyFile, igorCsrFile, igorCsrConfigFile, *allNames)
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
        return self.ca.ca_getRoot()
        
    def cmd_sign(self):
        """Sign a Certificate Signing Request. Not yet implemented."""
        return False
        
    def cmd_gen(self, prefix=None, *allNames):
        """Generate a a server key and certificate for a named service and sign it with the intermediate Igor CA key."""
        if not prefix or not allNames:
            print >>sys.stderr, "Usage: %s gen keyfilenameprefix commonName [subjectAltNames ...]" % sys.argv[0]
            return False
        
        keyFile = prefix + '.key'
        csrFile = prefix + '.csr'
        csrConfigFile = prefix + '.csrConfig'
        certFile = prefix + '.crt'
        if os.path.exists(keyFile) and os.path.exists(certFile):
            print >>sys.stderr, '%s: %s and %s already exist' % (self.argv0, keyFile, certFile)
            return False
            
        csr = self.do_genCSR(keyFile, csrFile, csrConfigFile, *allNames)
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
        return self.ca.ca_list()
        
    def cmd_status(self):
        """Returns nothing if CA status is ok, otherwise error message"""
        return self.ca.isOK()
        
    def do_status(self):
        if self.ca.isOK():
            return ""
        return "CA server configuration error, or not initialized"
        
    def cmd_csrtemplate(self):
        """Return template config file for for openSSL CSR request"""
        fn = self.ca.get_csrConfigTemplate()
        sys.stdout.write(open(fn).read())
        
    def do_csrtemplate(self):
        fn = self.ca.get_csrConfigTemplate()
        return open(fn).read()
        
def main():
    parser = argparse.ArgumentParser(description="Igor Certificate and Key utility")
    parser.add_argument("-r", "--remote", action="store_true", help="Use CA on remote Igor (default is on the local filesystem)")
    parser.add_argument("-u", "--url", help="(remote only) Base URL of the server (default: %s, environment IGORSERVER_URL)" % igorVar.CONFIG.get('igor', 'url'), default=igorVar.CONFIG.get('igor', 'url'))
    parser.add_argument("--bearer", metavar="TOKEN", help="(remote only) Add Authorization: Bearer TOKEN header line", default=igorVar.CONFIG.get('igor', 'bearer'))
    parser.add_argument("--access", metavar="TOKEN", help="(remote only) Add access_token=TOKEN query argument", default=igorVar.CONFIG.get('igor', 'access'))
    parser.add_argument("--credentials", metavar="USER:PASS", help="(remote only) Add Authorization: Basic header line with given credentials", default=igorVar.CONFIG.get('igor', 'credentials'))
    parser.add_argument("--noverify", action='store_true', help="(remote only) Disable verification of https signatures", default=igorVar.CONFIG.get('igor', 'noverify'))
    parser.add_argument("--certificate", metavar='CERTFILE', help="(remote only) Verify https certificates from given file", default=igorVar.CONFIG.get('igor', 'certificate'))
    parser.add_argument("action", help="Action to perform: help, initialize, ...", default="help")
    parser.add_argument("arguments", help="Arguments to the action", nargs="*")
    args = parser.parse_args()
    igorServer = None
    if args.remote:
        igorServer = igorVar.IgorServer(args.url, bearer_token=args.bearer, access_token=args.access, credentials=args.credentials, noverify=args.noverify, certificate=args.certificate)
    m = IgorCA(sys.argv[0], igorServer)
    if not args.action:
        return m.main('help', [])
    return m.main(args.action, args.arguments)
    
if __name__ == '__main__':
    main()
