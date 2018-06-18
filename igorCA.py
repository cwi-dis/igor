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

def runSSLCommand(*args):
    args = ('openssl',) + args
    print >>sys.stderr, '+', ' '.join(args)
    sts = subprocess.call(args)
    if sts != 0:
        print >>sys.stderr, '%s: openssl returned status %d' % (sys.argv[0], sts)
        return False
    return True
    
def main():
    # Find username even when sudoed
    username = os.environ.get("SUDO_USER", getpass.getuser())
    # Igor package source directory
    igorDir = os.path.dirname(igor.__file__)
    # Default database directory
    database = os.path.join(os.path.expanduser('~'+username), '.igor')
    caDatabase = os.path.join(database, 'ca')
    
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '--help'):
        print >>sys.stderr, USAGE % sys.argv[0]
        sys.exit(1)
       
    if not os.path.exists(database):
        print >>sys.stderr, "%s: No Igor database at %s" % (sys.argv[0], database)
        sys.exit(1)
        
    if sys.argv[1] == 'initialize':
        src = os.path.join(igorDir, 'igorDatabase.empty')
        if not os.path.exists(caDatabase):
            # Old igor, probably: caDatabase doesn't exist yet
            print
            print '=============== Creating CA directories and infrastructure'
            caSrc = os.path.join(src, 'ca')
            print >>sys.stderr, '%s: Creating %s' % (sys.argv[0], caSrc)
            shutil.copytree(caSrc, caDatabase)
        #
        # Create openssl.cnf files from openssl.cnf.in
        #
        for caGroup in ('root', 'intermediate'):
            print
            print '=============== Creating config for', caGroup
            caGroupDir = os.path.join(caDatabase, caGroup)
            caGroupConf = os.path.join(caGroupDir, 'openssl.cnf')
            caGroupConfIn = os.path.join(caGroupDir, 'openssl.cnf.in')
            if os.path.exists(caGroupConf):
                print >> sys.stderr, '%s: %s already exists' % (sys.argv[0], caGroupConf)
                sys.exit(1)
            data = open(caGroupConfIn).read()
            data = data.replace('%INSTALLDIR%', database)
            open(caGroupConf, 'w').write(data)
        #
        # Create root key and certificate
        #
        print
        print '=============== Creating root key and certificate'
        rootKeyFile = os.path.join(caDatabase, 'root', 'private', 'ca.key.pem')
        ok = runSSLCommand('genrsa', '-aes256', '-out', rootKeyFile, '4096')
        if not ok:
            sys.exit(1)
        rootCertFile = os.path.join(caDatabase, 'root', 'certs', 'ca.cert.pem')
        rootConfigFile = os.path.join(caDatabase, 'root', 'openssl.cnf')
        ok = runSSLCommand('req', 
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
        ok = runSSLCommand('x509', '-noout', '-text', '-in', rootCertFile)
        print
        print '=============== Creating intermediate key and certificate'
        #
        # Create intermediate key, CSR and certificate
        #
        intKeyFile = os.path.join(caDatabase, 'intermediate', 'private', 'intermediate.key.pem')
        ok = runSSLCommand('genrsa', '-aes256', '-out', intKeyFile, '4096')
        if not ok:
            sys.exit(1)
        intCsrFile = os.path.join(caDatabase, 'intermediate', 'certs', 'intermediate.csr.pem')
        intCertFile = os.path.join(caDatabase, 'intermediate', 'certs', 'intermediate.cert.pem')
        intConfigFile = os.path.join(caDatabase, 'intermediate', 'openssl.cnf')
        ok = runSSLCommand('req', 
            '-config', intConfigFile, 
            '-key', intKeyFile, 
            '-new', 
            '-sha256', 
            '-out', intCsrFile
            )
        if not ok:
            sys.exit(1)
        ok = runSSLCommand('ca',
            '-config', rootConfigFile,
            '-extensions', 'v3_intermediate_ca',
            '-days', '3650',
            '-notext',
            '-md', 'sha256',
            '-in', intCsrFile,
            '-out', intCertFile
            )
        if not ok:
            sys.exit(1)
        #
        # Verify the intermediate certificate
        #
        ok = runSSLCommand('verify',
            '-CAfile', rootCertFile,
            intCertFile
            )
        if not ok:
            sys.exit(1)
        #
        # Concatenate
        #
        intAllCertFile = os.path.join(caDatabase, 'intermediate', 'certs', 'ca-chain.cert.pem')
        ofp = open(intAllCertFile, 'w')
        ofp.write(open(intCertFile).read())
        ofp.write(open(rootCertFile).read())
        ofp.close()
        
        sys.exit(0)
    
    if not os.path.exists(caDatabase):
        print >>sys.stderr, "%s: No Igor CA database at %s" % (sys.argv[0], caDatabase)
        sys.exit(1)
        
    
    runcmds = []
    
    if sys.argv[1] == 'list':
        print >>sys.stderr, 'not yet implemented'
        sys.exit(1)
    elif sys.argv[1] == 'self':
        print >>sys.stderr, 'not yet implemented'
        sys.exit(1)
    elif sys.argv[1] == 'sign':
        print >>sys.stderr, 'not yet implemented'
        sys.exit(1)
    elif sys.argv[1] == 'gen':
        print >>sys.stderr, 'not yet implemented'
        sys.exit(1)
    else:
        print >>sys.stderr, '%s: Unknown command: %s' % (sys.argv[0], sys.argv[1])
        print >>sys.stderr, USAGE % sys.argv[0]
        sys.exit(1)
    
if __name__ == '__main__':
    main()
