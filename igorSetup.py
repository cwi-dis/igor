#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals
from builtins import zip
from builtins import range
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
req_extensions      = req_ext
x509_extensions     = x509_ext
string_mask         = utf8only
prompt              = no
distinguished_name = subject

[ subject ]
%s

# Section x509_ext is used when generating a self-signed certificate. I.e., openssl req -x509 ...
[ x509_ext ]

##subjectKeyIdentifier        = hash
##authorityKeyIdentifier  = keyid,issuer

# You only need digitalSignature below. *If* you don't allow
#   RSA Key transport (i.e., you use ephemeral cipher suites), then
#   omit keyEncipherment because that's key transport.
##basicConstraints        = CA:FALSE
##keyUsage            = digitalSignature, keyEncipherment
subjectAltName          = @alternate_names
##nsComment           = "OpenSSL Generated Certificate"

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

class IgorSetup(object):
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
        self.igorDir = os.path.abspath(os.path.dirname(igor.__file__))
        # Default database directory
        self.plugindir = os.path.join(self.database, 'plugins')
        self.stdplugindir = os.path.join(self.database, 'std-plugins')
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
                print("%s: No Igor database at %s" % (self.progname, self.database), file=sys.stderr)
                return False

            if not hasattr(self, 'cmd_' + cmd):
                print('%s: Unknown command "%s". Use help for help.' % (self.progname, cmd), file=sys.stderr)
                return False
            handler = getattr(self, 'cmd_' + cmd)
            ok = handler(*args)
        if not ok:
            return False
        return True
        
    def postprocess(self, run=False, verbose=False, subprocessArgs={}):
        if self.runcmds:
            if run:
                for cmd in self.runcmds:
                    if verbose:
                        print('+', cmd, file=sys.stderr)
                    subprocess.check_call(cmd, shell=True, **subprocessArgs)
            else:
                print('# Run the following commands:')
                print('(')
                for cmd in self.runcmds: print('\t', cmd)
                print(')')
        self.runcmds = []
        
    def cmd_help(self):
        """help - this message"""
        print(USAGE % dict(prog=self.progname), file=sys.stderr)
        for name in dir(self):
            if not name.startswith('cmd_'): continue
            handler = getattr(self, name)
            print(handler.__doc__)
        return True        

    def cmd_initialize(self):
        """initialize - create empty igor database"""
        src = os.path.join(self.igorDir, 'igorDatabase.empty')
        if os.path.exists(self.database):
            print('%s: %s already exists!' % (self.progname, self.database), file=sys.stderr)
            return False
        shutil.copytree(src, self.database)
        os.symlink(os.path.join(self.igorDir, 'std-plugins'), os.path.join(self.database, 'std-plugins'))
        return True

    def cmd_list(self):
        """list - show all installed plugins"""
        names = os.listdir(self.plugindir)
        names.sort()
        for name in names:
            if name[0] == '.' or name == 'readme.txt': continue
            filename = os.path.join(self.plugindir, name)
            if not os.path.isdir(filename):
                print(filename, '(error: does not exist, or not a directory)')
            elif os.path.islink(filename):
                print(filename, '(symlinked)')
            else:
                print(filename)
        return True

    def cmd_add(self, *pathnames):
        """add pathname [...] - add plugin (copy) from given pathname"""
        if not pathnames:
            print("%s: add requires a pathname" % self.progname, file=sys.stderr)
            return False
        for pluginpath in pathnames:
            basedir, pluginname = os.path.split(pluginpath)
            if not pluginname:
                basedir, pluginname = os.path.split(pluginpath)
            ok = self._installplugin(self.database, pluginpath, pluginname, shutil.cptree)
            if not ok:
                return False
        return True

    def cmd_addstd(self, *pluginnames):
        """addstd name[=srcname] [...] - add standard plugin srcname (linked) with given name"""
        if not pluginnames:
            print("%s: addstd requires a plugin name" % self.progname, file=sys.stderr)
            return False
        for pluginname in pluginnames:
            if type(pluginname) == type(()):
                pluginname, pluginsrcname = pluginname
            elif '=' in pluginname:
                pluginname = tuple(pluginname.split('='))
                pluginname, pluginsrcname = pluginname
            else:
                pluginsrcname = pluginname
            pluginsrcpath = os.path.join('..', 'std-plugins', pluginsrcname)
            ok = self._installplugin(self.database, pluginsrcpath, pluginname, os.symlink)
            if not ok:
                return False
        return True

    def cmd_updatestd(self):
        """updatestd - update all standard plugins to newest version (for igor < 0.85)"""
        names = os.listdir(self.plugindir)
        names.sort()
        for name in names:
            if name[0] == '.' or name == 'readme.txt': continue
            pluginpath = os.path.join(self.plugindir, name)
            if  os.path.islink(pluginpath):
                print('Updating', pluginpath)
                os.unlink(pluginpath)
                pluginsrcpath = os.path.join('..', 'std-plugins', name)
                ok = self._installplugin(self.database, pluginsrcpath, name, os.symlink)
                if not ok: return False
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
                print("%s: not symlink or directory: %s" % (self.progname, pluginpath), file=sys.stderr)
                return False
        return True
                    
    def cmd_liststd(self):
        """liststd - list all available standard plugins"""
        stdplugindir = os.path.join(self.database, 'std-plugins')
        names = os.listdir(stdplugindir)
        names.sort()
        for name in names:
            if name[0] == '.' or name == 'readme.txt': continue
            print(name)
        return True
                
    def cmd_certificate(self, *hostnames):
        """certificate hostname [...] - create https certificate for Igor using Igor as CA"""
        if not hostnames:
            print("%s: certificate requires all hostnames for igor, for example igor.local localhost 127.0.0.1 ::1" % self.progname, file=sys.stderr)
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

    def cmd_certificateSelfsigned(self, subject, *hostnames):
        """certificateSelfSigned subject hostname [...] - create self-signed https certificate for Igor (deprecated)"""
        if not len(hostnames):
            print("%s: certificateSelfSigned requires DN and all hostnames for igor, for example /C=NL/O=igor/CN=igor.local igor.local localhost 127.0.0.1 ::1" % self.progname, file=sys.stderr)
            return False
        altnames = ["DNS.%d = %s" % (i_n[0]+1, i_n[1]) for i_n in zip(list(range(len(hostnames))), hostnames)]
        altnames = '\n'.join(altnames)
        subject = subject.replace('/','\n')
        confData = OPENSSL_CONF % (subject, altnames)
    
        confFilename = os.path.join(self.database, 'igor.sslconf')
        keyFilename = os.path.join(self.database, 'igor.key')
        certFilename = os.path.join(self.database, 'igor.crt')
    
        open(confFilename, 'w').write(confData)
        sslCommand = OPENSSL_COMMAND % (confFilename, keyFilename, certFilename)
        self.runcmds += [sslCommand]
        return True

    def cmd_runatboot(self):
        """runatboot - make igorServer run at system boot (Linux or OSX, requires sudo permission)"""
        return self._runat('runatboot')
        
    def cmd_runatlogin(self):
        """runatlogin - make igorServer run at user login (OSX only)"""
        return self._runat('runatlogin')
        
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
        elif sys.platform in ('linux','linux2') and when == 'runatboot':
            template = os.path.join(self.igorDir, 'bootScripts', 'initscript-igor')
            dest = '/etc/init.d/igor'
            self.runcmds += [
                "sudo update-rc.d igor defaults",
                "sudo service igor start"
                ]
        else:
            print("%s: don't know how to enable Igor %s for platform %s" % (self.progname, when, sys.platform), file=sys.stderr)
            return False
        if os.path.exists(dest):
            print("%s: already exists: %s" % (self.progname, dest), file=sys.stderr)
            return False
        templateData = open(template).read()
        bootData = templateData % args
        open(dest, 'w').write(bootData)
        if sys.platform in ('linux', 'linux2'):
            os.chmod(dest, 0o755)
        return True
   
    def cmd_start(self):
        """start - start service (using normal OSX or Linux commands)"""
        return self._startstop('start')
   
    def cmd_stop(self):
        """stop - stop service (using normal OSX or Linux commands)"""
        return self._startstop('stop')
   
    def cmd_rebuild(self):
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
        elif sys.platform in ('linux', 'linux2'):
            daemonFile = '/etc/init.d/igor'
        else:
            print("%s: don't know about daemon mode on platform %s" % (self.progname, sys.platform), file=sys.stderr)
            return False
        if not os.path.exists(daemonFile):
            print("%s: it seems igor is not configured for runatboot or runatlogin" % self.progname, file=sys.stderr)
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
                print("%s: use 'rebuild' option only in an Igor source directory" % self.progname, file=sys.stderr)
            self.runcmds += [
                "%s setup.py build" % sys.executable,
                "sudo %s setup.py install" % sys.executable
                ]
        if when in ('rebuild', 'edit', 'rebuildedit', 'start'):
            if sys.platform == 'darwin':
                self.runcmds += ["sudo launchctl load %s" % daemonFile]
            else:
                self.runcmds += ["sudo service igor start"]
        return True
    
    def _installplugin(self, database, src, pluginname, cpfunc):
        dstdir = os.path.join(database, 'plugins')
        dst = os.path.join(dstdir, pluginname)
        if os.path.exists(dst):
            print("%s: already exists: %s" % (self.progname, dst), file=sys.stderr)
            return False
        if not os.path.exists(os.path.join(dstdir, src)):
            print("%s: does not exist: %s" % (self.progname, src), file=sys.stderr)
            return False
        cpfunc(src, dst)
        # Sometimes (only under travis?) the symlink seems to fail
        try:
            os.listdir(dst)
        except OSError:
            print("%s: creation of %s failed" % (self.progname, dst), file=sys.stderr)
            return False
        xmlfrag = os.path.join(dst, 'database-fragment.xml')
        if os.path.exists(xmlfrag):
            fp = open(xmlfrag)
            fragData = fp.read()
            fp.close()
            fragData = fragData.replace('{plugin}', pluginname)
            fragDest = dst + '.xml'
            fp = open(fragDest, 'w')
            fp.write(fragData)
            fp.close()
            print("%s: igor will install %s on the next restart" % (self.progname, fragDest), file=sys.stderr)
        return True

def argumentParser():
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument("-d", "--database", metavar="DIR", help="Database and scripts are stored in DIR (default: ~/.igor, environment IGORSERVER_DIR)")
    parser.add_argument("-r", "--run", action="store_true", help="Run any needed shell commands (default is to print them only)")
    parser.add_argument("action", help="Action to perform: help, initialize, ...", default="help")
    parser.add_argument("arguments", help="Arguments to the action", nargs="*")
    return parser
    
def main():
    parser = argumentParser()
    args = parser.parse_args()
    m = IgorSetup(database=args.database, progname=sys.argv[0])
    if not m.main(args.action, args.arguments):
        sys.exit(1)
    m.postprocess(args.run, verbose=True)

if __name__ == '__main__':
    main()
    
