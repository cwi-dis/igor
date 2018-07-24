#!/usr/bin/env python
import sys
import igor
import os
import os.path
import shutil
import getpass
import tempfile

USAGE="""
Usage: %s command [args]

Initialize or modify igor database.
Note: use only on host where igorServer is hosted, and not when it is running.

help - this message
initialize - create empty igor database
list - show all installed plugins
add pathname [...] - add plugin (copy) from given pathname
addstd name - add standard plugin (linked) with given name
remove name - remove plugin
liststd - list all available standard plugins
updatestd - update all standard plugins to newest version
runatboot - make igorServer run at system boot (Linux or OSX, requires sudo permission)
runatlogin - make igorServer run at user login (OSX only)
start - start service (using normal OSX or Linux commands)
stop - stop service (using normal OSX or Linux commands)
rebuild - stop, rebuild and start the service (must be run in source directory)
edit - stop, edit the database and restart the service
rebuildedit - stop, edit database, rebuild and start the service (must be run in source directory)
certificate - create https certificate for Igor using Igor as CA
certificateSelfSigned - create self-signed https certificate for Igor (deprecated)
"""

OPENSSL_COMMAND='openssl req -config "%s" -new -x509 -sha256 -newkey rsa:2048 -nodes -keyout "%s" -days 365 -out "%s"'
OPENSSL_CONF="""
[ req ]
default_bits        = 2048
default_keyfile     = server-key.pem
distinguished_name  = subject
req_extensions      = req_ext
x509_extensions     = x509_ext
string_mask         = utf8only

# The Subject DN can be formed using X501 or RFC 4514 (see RFC 4519 for a description).
#   Its sort of a mashup. For example, RFC 4514 does not provide emailAddress.
[ subject ]
countryName         = Country Name (2 letter code)
countryName_default     = NL

#stateOrProvinceName     = State or Province Name (full name)
#stateOrProvinceName_default = NY

localityName            = Locality Name (eg, city)
localityName_default        = Amsterdam

organizationName         = Organization Name (eg, company)
organizationName_default    = 

OU = Organizational Unit
OU_default = igor


# Use a friendly name here because its presented to the user. The server's DNS
#   names are placed in Subject Alternate Names. Plus, DNS names here is deprecated
#   by both IETF and CA/Browser Forums. If you place a DNS name here, then you 
#   must include the DNS name in the SAN too (otherwise, Chrome and others that
#   strictly follow the CA/Browser Baseline Requirements will fail).
commonName          = Common Name (e.g. server FQDN or YOUR name)
commonName_default      = 

emailAddress            = Email Address
emailAddress_default        = 

# Section x509_ext is used when generating a self-signed certificate. I.e., openssl req -x509 ...
[ x509_ext ]

subjectKeyIdentifier        = hash
authorityKeyIdentifier  = keyid,issuer

# You only need digitalSignature below. *If* you don't allow
#   RSA Key transport (i.e., you use ephemeral cipher suites), then
#   omit keyEncipherment because that's key transport.
basicConstraints        = CA:FALSE
keyUsage            = digitalSignature, keyEncipherment
subjectAltName          = @alternate_names
nsComment           = "OpenSSL Generated Certificate"

# RFC 5280, Section 4.2.1.12 makes EKU optional
#   CA/Browser Baseline Requirements, Appendix (B)(3)(G) makes me confused
#   In either case, you probably only need serverAuth.
# extendedKeyUsage  = serverAuth, clientAuth

# Section req_ext is used when generating a certificate signing request. I.e., openssl req ...
[ req_ext ]

subjectKeyIdentifier        = hash

basicConstraints        = CA:FALSE
keyUsage            = digitalSignature, keyEncipherment
subjectAltName          = @alternate_names
nsComment           = "OpenSSL Generated Certificate"

# RFC 5280, Section 4.2.1.12 makes EKU optional
#   CA/Browser Baseline Requirements, Appendix (B)(3)(G) makes me confused
#   In either case, you probably only need serverAuth.
# extendedKeyUsage  = serverAuth, clientAuth
[ alternate_names ]

%s
"""
class IgorSetup:
    def __init__(self):
        pass
        
    def main(self):
        # Find username even when sudoed
        self.username = os.environ.get("SUDO_USER", getpass.getuser())
        # Igor package source directory
        self.igorDir = os.path.dirname(igor.__file__)
        # Default database directory
        self.database = os.path.join(os.path.expanduser('~'+self.username), '.igor')
        self.plugindir = os.path.join(self.database, 'plugins')
        self.runcmds = []
    
        if len(sys.argv) < 2 or sys.argv[1] in ('help', '--help'):
            print >>sys.stderr, USAGE % sys.argv[0]
            sys.exit(1)
        
        if sys.argv[1] == 'initialize':
            src = os.path.join(self.igorDir, 'igorDatabase.empty')
            if os.path.exists(self.database):
                print >>sys.stderr, '%s: %s already exists!' % (sys.argv[0], self.database)
                sys.exit(1)
            shutil.copytree(src, self.database)
            sys.exit(0)
    
        # For the rest of the commands the Igor database should already exist.
        if not os.path.exists(self.database):
            print >>sys.stderr, "%s: No Igor database at %s" % (sys.argv[0], self.database)
            sys.exit(1)
    
    
        if sys.argv[1] == 'list':
            names = os.listdir(self.plugindir)
            names.sort()
            for name in names:
                if name[0] == '.' or name == 'readme.txt': continue
                filename = os.path.join(self.plugindir, name)
                if not os.path.isdir(filename):
                    print filename, '(error: does not exist, or not a directory)'
                elif os.path.islink(filename):
                    print filename, '(symlinked)'
                else:
                    print filename
        elif sys.argv[1] == 'add':
            if len(sys.argv) < 3:
                print >>sys.stderr, "%s: add requires a pathname" % sys.argv[0]
                sys.exit(1)
            for pluginpath in sys.argv[2:]:
                basedir, pluginname = os.path.split(pluginpath)
                if not pluginname:
                    basedir, pluginname = os.path.split(pluginpath)
                self.runcmds += self.installplugin(self.database, pluginpath, pluginname, shutil.cptree) 
        elif sys.argv[1] == 'addstd':
            if len(sys.argv) < 3:
                print >>sys.stderr, "%s: addstd requires a plugin name" % sys.argv[0]
                sys.exit(1)
            for pluginname in sys.argv[2:]:
                pluginsrcpath = os.path.join(self.igorDir, 'plugins', pluginname)
                self.runcmds += self.installplugin(self.database, pluginsrcpath, pluginname, os.symlink)
        elif sys.argv[1] == 'updatestd':
            names = os.listdir(self.plugindir)
            names.sort()
            for name in names:
                if name[0] == '.' or name == 'readme.txt': continue
                pluginpath = os.path.join(self.plugindir, name)
                if  os.path.islink(pluginpath):
                    print 'Updating', pluginpath
                    os.unlink(pluginpath)
                    pluginsrcpath = os.path.join(self.igorDir, 'plugins', name)
                    self.runcmds += self.installplugin(self.database, pluginsrcpath, name, os.symlink)
        elif sys.argv[1] == 'remove':
            if len(sys.argv) < 3:
                print >>sys.stderr, "%s: remove requires a plugin name" % sys.argv[0]
                sys.exit(1)
            for pluginname in sys.argv[2:]:
                pluginpath = os.path.join(self.plugindir, pluginname)
                if os.path.islink(pluginpath):
                    os.unlink(pluginpath)
                elif os.path.isdir(pluginpath):
                    shutil.rmtree(pluginpath)
                else:
                    print >> sys.stderr, "%s: not symlink or directory: %s" % (sys.argv[0], pluginpath)
                    sys.exit(1)
        elif sys.argv[1] == 'liststd':
            stdplugindir = os.path.join(self.igorDir, 'plugins')
            names = os.listdir(stdplugindir)
            names.sort()
            for name in names:
                if name[0] == '.' or name == 'readme.txt': continue
                print name
        elif sys.argv[1] == 'certificate':
            hostnames = sys.argv[2:]
            if not hostnames:
                print >> sys.stderr, "%s: certificate requires all hostnames for igor, for example igor.local localhost 127.0.0.1 ::1" % sys.argv[0]
                sys.exit(1)
            self.runcmds += [
                "igorCA initialize # Unless done before",
                "igorCA self "+" ".join(hostnames)
            ]
        elif sys.argv[1] == 'certificateSelfSigned':
            hostnames = sys.argv[2:]
            if not hostnames:
                print >> sys.stderr, "%s: certificateSelfSigned requires all hostnames for igor, for example igor.local localhost 127.0.0.1 ::1" % sys.argv[0]
                sys.exit(1)
            altnames = map(lambda (i, n): "DNS.%d = %s" % (i+1, n), zip(range(len(hostnames)), hostnames))
            altnames = '\n'.join(altnames)
            confData = OPENSSL_CONF % altnames
        
            confFilename = os.path.join(self.database, 'igor.sslconf')
            keyFilename = os.path.join(self.database, 'igor.key')
            certFilename = os.path.join(self.database, 'igor.crt')
        
            open(confFilename, 'wb').write(confData)
            sslCommand = OPENSSL_COMMAND % (confFilename, keyFilename, certFilename)
            self.runcmds += [sslCommand]

        elif sys.argv[1] in ('runatboot', 'runatlogin'):
            args = dict(
                user=self.username,
                igorDir=self.igorDir,
                database=self.database
                )
            if sys.platform == 'darwin' and sys.argv[1] == 'runatboot':
                template = os.path.join(self.igorDir, 'bootScripts', 'nl.cwi.dis.igor.plist')
                dest = '/Library/LaunchDaemons/nl.cwi.dis.igor.plist'
                self.runcmds += [
                    "sudo launchctl load %s" % dest,
                    ]
            elif sys.platform == 'darwin' and sys.argv[1] == 'runatlogin':
                template = os.path.join(self.igorDir, 'bootScripts', 'nl.cwi.dis.igor.plist')
                dest = os.path.join(os.path.expanduser('~'), 'Library/LaunchAgents/nl.cwi.dis.igor.plist')
                self.runcmds += [
                    "launchctl load %s" % dest,
                    ]
            elif sys.platform == 'linux2' and sys.argv[1] == 'runatboot':
                template = os.path.join(self.igorDir, 'bootScripts', 'initscript-igor')
                dest = '/etc/init.d/igor'
                self.runcmds += [
                    "sudo update-rc.d igor defaults",
                    "sudo service igor start"
                    ]
            else:
                print >>sys.stderr, "%s: don't know how to enable Igor %s for platform %s" % (sys.argv[0], sys.argv[1], sys.platform)
                sys.exit(1)
            if os.path.exists(dest):
                print >> sys.stderr, "%s: already exists: %s" % (sys.argv[0], dest)
                sys.exit(1)
            templateData = open(template).read()
            bootData = templateData % args
            open(dest, 'w').write(bootData)
            if sys.platform == 'linux2':
                os.chmod(dest, 0755)
        elif sys.argv[1] in ('start', 'stop', 'rebuild', 'edit', 'rebuildedit'):
            if sys.platform == 'darwin':
                daemonFile = '/Library/LaunchDaemons/nl.cwi.dis.igor.plist'
                if not os.path.exists(daemonFile):
                    daemonFile = os.path.join(os.path.expanduser('~'), 'Library/LaunchAgents/nl.cwi.dis.igor.plist')
            elif sys.platform == 'linux2':
                daemonFile = '/etc/init.d/igor'
            else:
                print >>sys.stderr, "%s: don't know about daemon mode on platform %s" % (sys.argv[0], sys.platform)
                sys.exit(1)
            if not os.path.exists(daemonFile):
                print >>sys.stderr, "%s: it seems igor is not configured for runatboot or runatlogin" % sys.argv[0]
                sys.exit(1)
            if sys.argv[1] in ('stop', 'rebuild', 'edit', 'rebuildedit'):
                self.runcmds += ["igorControl save"]
                if sys.platform == 'darwin':
                    self.runcmds += ["sudo launchctl unload %s" % daemonFile]
                else:
                    self.runcmds += ["sudo service igor stop"]
            if sys.argv[1] in ('edit', 'rebuildedit'):
                xmlDatabase = os.path.join(self.database, 'database.xml')
                self.runcmds += ["$EDITOR %s" % xmlDatabase]
            if sys.argv[1] in ('rebuild', 'rebuildedit'):
                if not os.path.exists("setup.py"):
                    print >> sys.stderr, "%s: use 'rebuild' option only in an Igor source directory" % sys.argv[0]
                self.runcmds += [
                    "python setup.py build",
                    "sudo python setup.py install"
                    ]
            if sys.argv[1] in ('rebuild', 'edit', 'rebuildedit', 'start'):
                if sys.platform == 'darwin':
                    self.runcmds += ["sudo launchctl load %s" % daemonFile]
                else:
                    self.runcmds += ["sudo service igor start"]
        else:
            print >>sys.stderr, '%s: unknown command: %s. Use --help for help.' % (sys.argv[0], sys.argv[1])
            sys.exit(1)
        if self.runcmds:
            print '# Run the following commands:'
            print '('
            for cmd in self.runcmds: print '\t', cmd
            print ')'
        sys.exit(0)
    
    def installplugin(self, database, src, pluginname, cpfunc):
        dst = os.path.join(database, 'plugins', pluginname)
        if os.path.exists(dst):
            print >>sys.stderr, "%s: already exists: %s" % (sys.argv[0], dst)
            return []
        if not os.path.exists(src):
            print >>sys.stderr, "%s: does not exist: %s" % (sys.argv[0], src)
            return []
        cpfunc(src, dst)
        xmlfrag = os.path.join(dst, 'database-fragment.xml')
        if os.path.exists(xmlfrag):
            runcmd = '"%s" "%s" "%s"' % (os.environ.get("EDITOR", "edit"), xmlfrag, os.path.join(database, 'database.xml'))
            return [runcmd]
        return []
    
def main():
    m = IgorSetup()
    m.main()

if __name__ == '__main__':
    main()
    
