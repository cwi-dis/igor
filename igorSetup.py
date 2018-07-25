#!/usr/bin/env python
import sys
import igor
import os
import os.path
import shutil
import getpass
import tempfile
import argparse
import subprocess

USAGE="""
Usage: %(prog)s [options] command [command-args]

Initialize or modify igor database.
Note: use only on host where igorServer is hosted, and not when it is running.
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
    def __init__(self, database=None, progname='igorSetup'):
        self.progname = progname
        # Find username even when sudoed
        self.username = os.environ.get("SUDO_USER", getpass.getuser())
        # Igor package source directory
        if database:
            self.database = database
        elif 'IGORSERVER_DIR' in os.environ:
            self.database = os.environ['IGORSERVER_DIR']
        else:
            self.database = os.path.join(os.path.expanduser('~'+self.username), '.igor')
        self.igorDir = os.path.dirname(igor.__file__)
        # Default database directory
        self.plugindir = os.path.join(self.database, 'plugins')
        self.runcmds = []
        
    def main(self, cmd=None, args=None):
        if not args:
            args = ()
        self.runcmds = []
        if not cmd or cmd == 'help':
            ok = self.cmd_help()
            
        elif cmd == 'initialize':
            ok = self.cmd_initialize()
        else:
            # For the rest of the commands the Igor database should already exist.
            if not os.path.exists(self.database):
                print >>sys.stderr, "%s: No Igor database at %s" % (self.progname, self.database)
                return False

            if not hasattr(self, 'cmd_' + cmd):
                print >> sys.stderr, '%s: Unknown command "%s". Use help for help.' % (self.progname, cmd)
                return False
            handler = getattr(self, 'cmd_' + cmd)
            ok = handler(*args)
        if not ok:
            return False
        return True
        
    def postprocess(self, run=False, verbose=False):
        if self.runcmds:
            if run:
                for cmd in self.runcmds:
                    if verbose:
                        print >> sys.stderr, '+', cmd
                    subprocess.check_call(cmd, shell=True)
            else:
                print '# Run the following commands:'
                print '('
                for cmd in self.runcmds: print '\t', cmd
                print ')'
        self.runcmds = []
        
    def cmd_help(self):
        """help - this message"""
        print >>sys.stderr, USAGE % dict(prog=self.progname)
        for name in dir(self):
            if not name.startswith('cmd_'): continue
            handler = getattr(self, name)
            print handler.__doc__
        return True        

    def cmd_initialize(self):
        """initialize - create empty igor database"""
        src = os.path.join(self.igorDir, 'igorDatabase.empty')
        if os.path.exists(self.database):
            print >>sys.stderr, '%s: %s already exists!' % (self.progname, self.database)
            return False
        shutil.copytree(src, self.database)
        return True

    def cmd_list(self):
        """list - show all installed plugins"""
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
        return True

    def cmd_add(self, *pathnames):
        """add pathname [...] - add plugin (copy) from given pathname"""
        if not pathnames:
            print >>sys.stderr, "%s: add requires a pathname" % self.progname
            return False
        for pluginpath in pathnames:
            basedir, pluginname = os.path.split(pluginpath)
            if not pluginname:
                basedir, pluginname = os.path.split(pluginpath)
            self.runcmds += self._installplugin(self.database, pluginpath, pluginname, shutil.cptree)
        return True

    def cmd_addstd(self, *pluginnames):
        """addstd name [...] - add standard plugin (linked) with given name"""
        if not pluginnames:
            print >>sys.stderr, "%s: addstd requires a plugin name" % self.progname
            return False
        for pluginname in pluginnames:
            pluginsrcpath = os.path.join(self.igorDir, 'plugins', pluginname)
            self.runcmds += self._installplugin(self.database, pluginsrcpath, pluginname, os.symlink)
        return True

    def cmd_updatestd(self):
        """updatestd - update all standard plugins to newest version"""
        names = os.listdir(self.plugindir)
        names.sort()
        for name in names:
            if name[0] == '.' or name == 'readme.txt': continue
            pluginpath = os.path.join(self.plugindir, name)
            if  os.path.islink(pluginpath):
                print 'Updating', pluginpath
                os.unlink(pluginpath)
                pluginsrcpath = os.path.join(self.igorDir, 'plugins', name)
                self.runcmds += self._installplugin(self.database, pluginsrcpath, name, os.symlink)
        return True

    def cmd_remove(self, *pluginnames):
        """remove name [...] - remove plugin"""
        for pluginname in pluginnames:
            pluginpath = os.path.join(self.plugindir, pluginname)
            if os.path.islink(pluginpath):
                os.unlink(pluginpath)
            elif os.path.isdir(pluginpath):
                shutil.rmtree(pluginpath)
            else:
                print >> sys.stderr, "%s: not symlink or directory: %s" % (self.progname, pluginpath)
                return False
        return True
                    
    def cmd_liststd(self):
        """liststd - list all available standard plugins"""
        stdplugindir = os.path.join(self.igorDir, 'plugins')
        names = os.listdir(stdplugindir)
        names.sort()
        for name in names:
            if name[0] == '.' or name == 'readme.txt': continue
            print name
        return True
                
    def cmd_certificate(self, *hostnames):
        """certificate hostname [...] - create https certificate for Igor using Igor as CA"""
        if not hostnames:
            print >> sys.stderr, "%s: certificate requires all hostnames for igor, for example igor.local localhost 127.0.0.1 ::1" % self.progname
            return False
        import igorCA
        caName = self.progname + ': ' + 'igorCA'
        ca = igorCA.IgorCA(caName, database=self.database)
        msg = ca.do_status()
        if msg:
            # CA Not initialized yet.
            ok = ca.cmd_initialize()
            if not ok:
                return False
        ok = ca.cmd_self(hostnames)
        return ok

    def cmd_certificateSelfsigned(self, *hostnames):
        """certificateSelfSigned hostname [...] - create self-signed https certificate for Igor (deprecated)"""
        if not hostnames:
            print >> sys.stderr, "%s: certificateSelfSigned requires all hostnames for igor, for example igor.local localhost 127.0.0.1 ::1" % self.progname
            return False
        altnames = map(lambda (i, n): "DNS.%d = %s" % (i+1, n), zip(range(len(hostnames)), hostnames))
        altnames = '\n'.join(altnames)
        confData = OPENSSL_CONF % altnames
    
        confFilename = os.path.join(self.database, 'igor.sslconf')
        keyFilename = os.path.join(self.database, 'igor.key')
        certFilename = os.path.join(self.database, 'igor.crt')
    
        open(confFilename, 'wb').write(confData)
        sslCommand = OPENSSL_COMMAND % (confFilename, keyFilename, certFilename)
        self.runcmds += [sslCommand]
        return True

    def cmd_runatboot(self):
        """runatboot - make igorServer run at system boot (Linux or OSX, requires sudo permission)"""
        return self._runat('boot')
        
    def cmd_runatlogin(self):
        """runatlogin - make igorServer run at user login (OSX only)"""
        return self._runat('login')
        
    def _runat(self, when):
        args = dict(
            user=self.username,
            igorDir=self.igorDir,
            database=self.database
            )
        if sys.platform == 'darwin' and when == 'runatboot':
            template = os.path.join(self.igorDir, 'bootScripts', 'nl.cwi.dis.igor.plist')
            dest = '/Library/LaunchDaemons/nl.cwi.dis.igor.plist'
            self.runcmds += [
                "sudo launchctl load %s" % dest,
                ]
        elif sys.platform == 'darwin' and when == 'runatlogin':
            template = os.path.join(self.igorDir, 'bootScripts', 'nl.cwi.dis.igor.plist')
            dest = os.path.join(os.path.expanduser('~'), 'Library/LaunchAgents/nl.cwi.dis.igor.plist')
            self.runcmds += [
                "launchctl load %s" % dest,
                ]
        elif sys.platform == 'linux2' and when == 'runatboot':
            template = os.path.join(self.igorDir, 'bootScripts', 'initscript-igor')
            dest = '/etc/init.d/igor'
            self.runcmds += [
                "sudo update-rc.d igor defaults",
                "sudo service igor start"
                ]
        else:
            print >>sys.stderr, "%s: don't know how to enable Igor %s for platform %s" % (self.progname, when, sys.platform)
            return False
        if os.path.exists(dest):
            print >> sys.stderr, "%s: already exists: %s" % (self.progname, dest)
            return False
        templateData = open(template).read()
        bootData = templateData % args
        open(dest, 'w').write(bootData)
        if sys.platform == 'linux2':
            os.chmod(dest, 0755)
        return True
   
    def cmd_start(self):
        """start - start service (using normal OSX or Linux commands)"""
        return self._startstop('start')
   
    def cmd_stop(self):
        """stop - stop service (using normal OSX or Linux commands)"""
        return self._startstop('stop')
   
    def cmd_srebuild(self):
        """rebuild - stop, rebuild and start the service (must be run in source directory)"""
        return self._startstop('rebuild')
   
    def cmd_edit(self):
        """edit - stop, edit the database and restart the service"""
        return self._startstop('edit')
   
    def cmd_rebuildedit(self):
        """rebuildedit - stop, edit database, rebuild and start the service (must be run in source directory)"""
        return self._startstop('rebuildedit')
        
    def _startstop(self, when):
        if sys.platform == 'darwin':
            daemonFile = '/Library/LaunchDaemons/nl.cwi.dis.igor.plist'
            if not os.path.exists(daemonFile):
                daemonFile = os.path.join(os.path.expanduser('~'), 'Library/LaunchAgents/nl.cwi.dis.igor.plist')
        elif sys.platform == 'linux2':
            daemonFile = '/etc/init.d/igor'
        else:
            print >>sys.stderr, "%s: don't know about daemon mode on platform %s" % (self.progname, sys.platform)
            return False
        if not os.path.exists(daemonFile):
            print >>sys.stderr, "%s: it seems igor is not configured for runatboot or runatlogin" % self.progname
            return False
        if when in ('stop', 'rebuild', 'edit', 'rebuildedit'):
            self.runcmds += ["igorControl save"]
            if sys.platform == 'darwin':
                self.runcmds += ["sudo launchctl unload %s" % daemonFile]
            else:
                self.runcmds += ["sudo service igor stop"]
        if when in ('edit', 'rebuildedit'):
            xmlDatabase = os.path.join(self.database, 'database.xml')
            self.runcmds += ["$EDITOR %s" % xmlDatabase]
        if when in ('rebuild', 'rebuildedit'):
            if not os.path.exists("setup.py"):
                print >> sys.stderr, "%s: use 'rebuild' option only in an Igor source directory" % self.progname
            self.runcmds += [
                "python setup.py build",
                "sudo python setup.py install"
                ]
        if when in ('rebuild', 'edit', 'rebuildedit', 'start'):
            if sys.platform == 'darwin':
                self.runcmds += ["sudo launchctl load %s" % daemonFile]
            else:
                self.runcmds += ["sudo service igor start"]
        return True
    
    def _installplugin(self, database, src, pluginname, cpfunc):
        dst = os.path.join(database, 'plugins', pluginname)
        if os.path.exists(dst):
            print >>sys.stderr, "%s: already exists: %s" % (self.progname, dst)
            return []
        if not os.path.exists(src):
            print >>sys.stderr, "%s: does not exist: %s" % (self.progname, src)
            return []
        cpfunc(src, dst)
        xmlfrag = os.path.join(dst, 'database-fragment.xml')
        if os.path.exists(xmlfrag):
            runcmd = '"%s" "%s" "%s"' % (os.environ.get("EDITOR", "edit"), xmlfrag, os.path.join(database, 'database.xml'))
            return [runcmd]
        return []
    
def main():
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument("-d", "--database", metavar="DIR", help="Database and scripts are stored in DIR (default: ~/.igor, environment IGORSERVER_DIR)")
    parser.add_argument("-r", "--run", action="store_true", help="Run any needed shell commands (default is to print them only)")
    parser.add_argument("action", help="Action to perform: help, initialize, ...", default="help")
    parser.add_argument("arguments", help="Arguments to the action", nargs="*")
    args = parser.parse_args()
    m = IgorSetup(database=args.database, progname=sys.argv[0])
    if not m.main(args.action, args.arguments):
        sys.exit(1)
    m.postprocess(args.run, verbose=True)

if __name__ == '__main__':
    main()
    
