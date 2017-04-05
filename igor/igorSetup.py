#!/usr/bin/env python
import sys

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
"""
def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('help', '--help'):
        print >>sys.stderr, USAGE % sys.argv[0]
        sys.exit(1)
    if sys.argv[1] == 'initialize':
        assert 0
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
    else:
        print >>sys.stderr, '%s: unknown command: %s. Use --help for help.' % sys.argv[0]
        sys.exit(1)
    sys.exit(0)
    
if __name__ == '__main__':
    main()
