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
add pathname - add plugin (copy) from given pathname
addstd name - add standard plugin (linked) with given name
remove name - remove plugin
liststd - list all available standard plugins
runatboot - make igorServer run at system boot (Linux or OSX, requires sudo permission)
runatlogin - make igorServer run at user login (OSX only)
"""
def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '--help'):
        print >>sys.stderr, USAGE % sys.argv[0]
        sys.exit(1)
    if sys.argv[1] == 'initialize':
        igorDir = os.path.dirname(igor.__file__)
        src = os.path.join(igorDir, 'igorDatabase.empty')
        dst = os.path.join(os.path.expanduser('~'), '.igor')
        if os.path.exists(dst):
            print >>sys.stderr, '%s: %s already exists!' % (sys.argv[0], dst)
            sys.exit(1)
        shutil.copytree(src, dst)
    elif sys.argv[1] == 'list':
        assert 0
    elif sys.argv[1] == 'add':
        assert 0
    elif sys.argv[1] == 'addstd':
        assert 0
    elif sys.argv[1] == 'remove':
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
    
if __name__ == '__main__':
    main()
