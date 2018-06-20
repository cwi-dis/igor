#!/usr/bin/env python
import sys
import igor
import os
import os.path
import shutil
import getpass
import tempfile
import subprocess

USAGE="""
Usage: %s command [args]

Initialize or use igor Certificate Authority.

help - this message
initialize - Create root and intermediate keys/certs

"""

class IgorCA:
    def __init__(self, argv0):
        self.argv0 = argv0
        # Find username even when sudoed
        username = os.environ.get("SUDO_USER", getpass.getuser())
        # Igor package source directory
        self.igorDir = os.path.dirname(igor.__file__)
        #
        # Default self.database directory, CA directory and key/cert for signing.
        #
        self.database = os.path.join(os.path.expanduser('~'+username), '.igor')
        self.caDatabase = os.path.join(self.database, 'ca')
        self.intKeyFile = os.path.join(self.caDatabase, 'intermediate', 'private', 'intermediate.key.pem')
        self.intCertFile = os.path.join(self.caDatabase, 'intermediate', 'certs', 'intermediate.cert.pem')
        self.intAllCertFile = os.path.join(self.caDatabase, 'intermediate', 'certs', 'ca-chain.cert.pem')
        self.intConfigFile = os.path.join(self.caDatabase, 'intermediate', 'openssl.cnf')

    def runSSLCommand(self, *args):
        args = ('openssl',) + args
        print >>sys.stderr, '+', ' '.join(args)
        sts = subprocess.call(args)
        if sts != 0:
            print >>sys.stderr, '%s: openssl returned status %d' % (self.argv0, sts)
            return False
        return True
    
    def main(self, command, args):
        if not os.path.exists(self.database):
            print >>sys.stderr, "%s: No Igor self.database at %s" % (self.argv0, self.database)
            sys.exit(1)
        
        if command == 'initialize':
            if os.path.exists(self.intKeyFile) and os.path.exists(self.intCertFile) and os.path.exists(self.intAllCertFile):
                print >>sys.stderr, '%s: Intermediate key and certificate already exist in %s' % (self.argv0, self.caDatabase)
                sys.exit(1)
            self.initialize()

        #
        # All other commands require the self.database to exist and be populated with the keys
        #
        if not os.path.exists(self.caDatabase):
            print >>sys.stderr, "%s: No Igor CA self.database at %s" % (self.argv0, self.caDatabase)
            sys.exit(1)
        if not (os.path.exists(self.intKeyFile) and os.path.exists(self.intCertFile) and os.path.exists(self.intAllCertFile)):
            print >>sys.stderr, "%s: Intermediate key, certificate and chain don't exist in %s" % (self.argv0, self.caDatabase)
            sys.exit(1)
        
    
        runcmds = []
    
        if command == 'list':
            print >>sys.stderr, 'not yet implemented'
            sys.exit(1)
        elif command == 'getRoot':
            sys.stdout.write(open(self.intAllCertFile).read())
            sys.exit(0)
        elif command == 'self':
            self.selfSignSelf(args)
            sys.exit(0)
        elif command == 'sign':
            print >>sys.stderr, 'not yet implemented'
            sys.exit(1)
        elif command == 'gen':
            print >>sys.stderr, 'not yet implemented'
            sys.exit(1)
        else:
            print >>sys.stderr, '%s: Unknown command: %s' % (self.argv0, command)
            print >>sys.stderr, USAGE % self.argv0
            sys.exit(1)
    
    def initialize(self):
        """Initialize CA infrastructure, optionally root key/cert and intermediate key/cert"""
        #
        # Create infrastructure if needed
        #
        if not os.path.exists(self.caDatabase):
            # Old igor, probably: self.caDatabase doesn't exist yet
            print
            print '=============== Creating CA directories and infrastructure'
            src = os.path.join(self.igorDir, 'igorDatabase.empty')
            caSrc = os.path.join(src, 'ca')
            print >>sys.stderr, '%s: Creating %s' % (self.argv0, caSrc)
            shutil.copytree(caSrc, self.caDatabase)
        #
        # Create openssl.cnf files from openssl.cnf.in
        #
        for caGroup in ('root', 'intermediate'):
            print
            print '=============== Creating config for', caGroup
            caGroupDir = os.path.join(self.caDatabase, caGroup)
            caGroupConf = os.path.join(caGroupDir, 'openssl.cnf')
            caGroupConfIn = os.path.join(caGroupDir, 'openssl.cnf.in')
            if os.path.exists(caGroupConf):
                print >> sys.stderr, '%s: %s already exists' % (self.argv0, caGroupConf)
                sys.exit(1)
            data = open(caGroupConfIn).read()
            data = data.replace('%INSTALLDIR%', self.database)
            open(caGroupConf, 'w').write(data)
        #
        # Create root key and certificate
        #
        rootKeyFile = os.path.join(self.caDatabase, 'root', 'private', 'ca.key.pem')
        rootCertFile = os.path.join(self.caDatabase, 'root', 'certs', 'ca.cert.pem')
        rootConfigFile = os.path.join(self.caDatabase, 'root', 'openssl.cnf')
        if  os.path.exists(rootKeyFile) and os.path.exists(rootCertFile) and os.path.exists(rootConfigFile):
            print
            print '=============== Root key and certificate already exist'
        else:
            print
            print '=============== Creating root key and certificate'
            ok = self.runSSLCommand('genrsa', '-aes256', '-out', rootKeyFile, '4096')
            if not ok:
                sys.exit(1)
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
                sys.exit(1)
            os.chmod(rootCertFile, 0400)
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', rootCertFile)
        if not ok:
            sys.exit(1)
        #
        # Create intermediate key, CSR and certificate
        #
        print
        print '=============== Creating intermediate key and certificate'
        ok = self.runSSLCommand('genrsa', '-out', self.intKeyFile, '4096')
        os.chmod(self.intKeyFile, 0400)
        if not ok:
            sys.exit(1)
        intCsrFile = os.path.join(self.caDatabase, 'intermediate', 'certs', 'intermediate.csr.pem')
        ok = self.runSSLCommand('req', 
            '-config', self.intConfigFile, 
            '-key', self.intKeyFile, 
            '-new', 
            '-sha256', 
            '-out', intCsrFile
            )
        if not ok:
            sys.exit(1)
        ok = self.runSSLCommand('ca',
            '-config', rootConfigFile,
            '-extensions', 'v3_intermediate_ca',
            '-days', '3650',
            '-notext',
            '-md', 'sha256',
            '-in', intCsrFile,
            '-out', self.intCertFile
            )
        if not ok:
            sys.exit(1)
        os.chmod(self.intCertFile, 0400)
        #
        # Verify the intermediate certificate
        #
        ok = self.runSSLCommand('verify',
            '-CAfile', rootCertFile,
            self.intCertFile
            )
        if not ok:
            sys.exit(1)
        #
        # Concatenate
        #
        ofp = open(self.intAllCertFile, 'w')
        ofp.write(open(self.intCertFile).read())
        ofp.write(open(rootCertFile).read())
        ofp.close()
        #
        # And finally print the chained file
        #
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', self.intAllCertFile)
        if not ok:
            sys.exit(1)
    
        sys.exit(0)

    def selfSignSelf(self, allNames):
        """Create an Igor server key and certificate and sign it with the intermediate Igor CA key"""
        if len(allNames) < 1:
            print >>sys.stderr, '%s: self requires ALL names (commonName first) as arguments' % self.argv0
            print >> sys.stderr, 'for example: %s self igor.local localhost 127.0.0.1' % self.argv0
            sys.exit(1)
        # Construct commonName and subjectAltNames
        commonName = allNames[0]
        altNames = map(lambda x: 'DNS:' + x, allNames)
        altNames = 'subjectAltName = ' + ','.join(altNames)

        igorKeyFile = os.path.join(self.database, 'igor.key')
        igorCsrFile = os.path.join(self.database, 'igor.csr')
        igorCsrConfigFile = os.path.join(self.database, 'igor.csrconfig')
        igorCertFile = os.path.join(self.database, 'igor.crt')
        if os.path.exists(igorKeyFile) and os.path.exists(igorCertFile):
            print >>sys.stderr, '%s: igor.key and igor.crt already exist in %s' % (self.argv0, self.database)
            sys.exit(1)
        #
        # Create key
        #
        ok = self.runSSLCommand('genrsa', '-out', igorKeyFile, '2048')
        if not ok:
            sys.exit(1)
        os.chmod(igorKeyFile, 0400)
        #
        # Create CSR config file
        #
        ofp = open(igorCsrConfigFile, 'w')
        ofp.write(open(self.intConfigFile).read())
        ofp.write('\n[SAN]\n\n%s\n' % altNames)
        #
        # Create CSR
        #
        ok = self.runSSLCommand('req',
            '-reqexts', 'SAN',
            '-extensions', 'SAN',
            '-config', igorCsrConfigFile,
            '-key', igorKeyFile,
            '-new',
            '-sha256',
            '-out', igorCsrFile
            )
        if not ok:
            sys.exit(1)
        #
        # Sign CSR
        #
        ok = self.runSSLCommand('ca',
            '-config', self.intConfigFile,
            '-extensions', 'server_cert',
            '-days', '3650',
            '-notext',
            '-md', 'sha256',
            '-in', igorCsrFile,
            '-out', igorCertFile
            )
        if not ok:
            sys.exit(1)
        # Verify it
        ok = self.runSSLCommand('x509', '-noout', '-text', '-in', igorCertFile)
        if not ok:
            sys.exit(1)

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '--help'):
        print >>sys.stderr, USAGE % sys.argv[0]
        sys.exit(1)
       
    m = IgorCA(sys.argv[0])
    return m.main(sys.argv[1], sys.argv[2:])
    
if __name__ == '__main__':
    main()
