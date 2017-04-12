#!/usr/bin/env python
import sys
import igor
import os
import os.path
import shutil
import getpass

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
runatboot - make igorServer run at system boot (Linux or OSX, requires sudo permission)
runatlogin - make igorServer run at user login (OSX only)
"""
def main():
    # Find username even when sudoed
    username = os.environ.get("SUDO_USER", getpass.getuser())
    # Igor package source directory
    igorDir = os.path.dirname(igor.__file__)
    # Default database directory
    database = os.path.join(os.path.expanduser('~'+username), '.igor')
    
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '--help'):
        print >>sys.stderr, USAGE % sys.argv[0]
        sys.exit(1)
        
    if sys.argv[1] == 'initialize':
        src = os.path.join(igorDir, 'igorDatabase.empty')
        if os.path.exists(database):
            print >>sys.stderr, '%s: %s already exists!' % (sys.argv[0], database)
            sys.exit(1)
        shutil.copytree(src, database)
        sys.exit(0)
    
    # For the rest of the commands the Igor database should already exist.
    if not os.path.exists(database):
        print >>sys.stderr, "%s: No Igor database at %s" % (sys.argv[0], database)
        sys.exit(1)
    plugindir = os.path.join(database, 'plugins')
    
    if sys.argv[1] == 'list':
        names = os.listdir(plugindir)
        names.sort()
        for name in names:
            if name[0] == '.' or name == 'readme.txt': continue
            filename = os.path.join(plugindir, name)
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
            installplugin(pluginpath, plugindir, pluginname, os.symlink, igorDir) 
    elif sys.argv[1] == 'addstd':
        if len(sys.argv) < 3:
            print >>sys.stderr, "%s: addstd requires a plugin name" % sys.argv[0]
            sys.exit(1)
        for pluginname in sys.argv[2:]:
            pluginpath = os.path.join(igorDir, 'plugins', pluginname)
            installplugin(pluginpath, plugindir, pluginname, os.symlink, igorDir) 
    elif sys.argv[1] == 'remove':
        if len(sys.argv) < 3:
            print >>sys.stderr, "%s: remove requires a plugin name" % sys.argv[0]
            sys.exit(1)
        for pluginname in sys.argv[2:]:
            pluginpath = os.path.join(plugindir, pluginname)
            if os.path.islink(pluginpath):
                os.unlink(pluginpath)
            elif os.path.isdir(pluginpath):
                shutil.rmtree(pluginpath)
            else:
                print >> sys.stderr, "%s: not symlink or directory: %s" % (sys.argv[0], pluginpath)
                sys.exit(1)
    elif sys.argv[1] == 'liststd':
        stdplugindir = os.path.join(igorDir, 'plugins')
        names = os.listdir(stdplugindir)
        names.sort()
        for name in names:
            if name[0] == '.' or name == 'readme.txt': continue
            print name
    elif sys.argv[1] in ('runatboot', 'runatlogin'):
        args = dict(
            user=username,
            igorDir=igorDir,
            database=database
            )
        if sys.platform == 'darwin' and sys.argv[1] == 'runatboot':
            template = os.path.join(igorDir, 'bootScripts', 'nl.cwi.dis.igor.plist')
            dest = '/Library/LaunchDaemons/nl.cwi.dis.igor.plist'
            runcmds = [
                "sudo launchctl load %s" % dest,
                ]
        elif sys.platform == 'darwin' and sys.argv[1] == 'runatlogin':
            template = os.path.join(igorDir, 'bootScripts', 'nl.cwi.dis.igor.plist')
            dest = os.path.join(os.path.expanduser('~'), 'Library/LaunchAgents/nl.cwi.dis.igor.plist')
            runcmds = [
                "launchctl load %s" % dest,
                ]
        elif sys.platform == 'linux2' and sys.argv[1] == 'runatboot':
            template = os.path.join(igorDir, 'bootScripts', 'initscript-igor')
            dest = '/etc/init.d/igor'
            runcmds = [
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
        print 'Run the following commands:'
        for cmd in runcmds: print cmd
    else:
        print >>sys.stderr, '%s: unknown command: %s. Use --help for help.' % (sys.argv[0], sys.argv[1])
        sys.exit(1)
    sys.exit(0)
    
def installplugin(src, plugindir, pluginname, cpfunc, database):
    dst = os.path.join(plugindir, pluginname)
    if os.path.exists(dst):
        print >>sys.stderr, "%s: already exists: %s" % (sys.argv[0], dst)
        return
    if not os.path.exists(src):
        print >>sys.stderr, "%s: does not exist: %s" % (sys.argv[0], src)
        return
    cpfunc(src, dst)
    xmlfrag = os.path.join(dst, 'database-fragment.xml')
    if os.path.exists(xmlfrag):
        print 'Merge database fragment by hand, please:'
        print '\t', os.environ.get("EDITOR", "edit"), xmlfrag, os.path.join(database, 'database.xml')
    
if __name__ == '__main__':
    main()
