#!/usr/bin/env python
import sys
import igor
import os
import os.path
import shutil

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
    database = os.path.join(os.path.expanduser('~'), '.igor')
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '--help'):
        print >>sys.stderr, USAGE % sys.argv[0]
        sys.exit(1)
        
    if sys.argv[1] == 'initialize':
        igorDir = os.path.dirname(igor.__file__)
        src = os.path.join(igorDir, 'igorDatabase.empty')
        if os.path.exists(database):
            print >>sys.stderr, '%s: %s already exists!' % (sys.argv[0], database)
            sys.exit(1)
        shutil.copytree(src, database)
        sys.exit(0)
    
    if not os.path.exists(database):
        print >>sys.stderr, "%s: No Igor database at", database
    plugindir = os.path.join(database, 'plugins')
    
    if sys.argv[1] == 'list':
        names = os.listdir(plugindir)
        names.sort()
        for name in names:
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
            installplugin(pluginpath, plugindir, pluginname, os.symlink) 
    elif sys.argv[1] == 'addstd':
        if len(sys.argv) < 3:
            print >>sys.stderr, "%s: addstd requires a plugin name" % sys.argv[0]
            sys.exit(1)
        assert 0
        for pluginname in sys.argv[2:]:
            pluginpath = xxxxxx
            installplugin(pluginpath, plugindir, pluginname, os.symlink) 
    elif sys.argv[1] == 'remove':
        if len(sys.argv) < 3:
            print >>sys.stderr, "%s: remove requires a plugin name" % sys.argv[0]
            sys.exit(1)
        assert 0
    elif sys.argv[1] == 'liststd':
        assert 0
    elif sys.argv[1] == 'runatboot':
        assert 0
    elif sys.argv[1] == 'runatlogin':
        assert 0
    else:
        print >>sys.stderr, '%s: unknown command: %s. Use --help for help.' % sys.argv[0]
        sys.exit(1)
    sys.exit(0)
    
def installplugin(src, plugindir, pluginname, cpfunc):
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
        print 'Merge %s into xml database by hand, please' % xmlfrag
    
if __name__ == '__main__':
    main()
