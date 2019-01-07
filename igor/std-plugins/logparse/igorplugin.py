from __future__ import print_function
from __future__ import unicode_literals
import sys
import fileinput
import dateutil.parser
import datetime
import re

def dologparse(logfiles, goodREs, badREs, timeparser, timeformat):
    if type(logfiles) != type([]):
        logfiles = [logfiles]
    if goodREs == None: goodREs = []
    if type(goodREs) != type([]):
        goodREs = [goodREs]
    if badREs == None: badREs = []
    if type(badREs) != type([]):
        badREs = [badREs]
    # Build list of all regular expressions (compiled)
    allres = []
    for r in goodREs:
        allres.append(('good', re.compile(r)))
    for r in badREs:
        allres.append(('bad', re.compile(r)))
    # Process all lines in all files, in order
    lastMatch = None
    lastType = None
    for line in fileinput.input(logfiles):
        for tp, cr in allres:
            match = cr.match(line)
            if match != None:
                lastMatch = match
                lastType = tp
                break
    rv = {}
    if lastType == 'good':
        rv['alive'] = True
    elif lastType == 'bad':
        rv['alive'] = False
    if lastMatch:
        subgroups = lastMatch.groupdict()
        if 'time' in subgroups:
            srcTime = subgroups['time']
            if timeparser:
                dt = datetime.datetime.strptime(srcTime, timeparser)
            else:
                dt = dateutil.parser.parse(srcTime)
            if timeformat:
                dstTime = dt.strftime(timeformat)
            else:
                dstTime = dt.isoformat()
            rv['lastActivity'] = dstTime
        if 'message' in subgroups:
            rv['errorMessage'] = subgroups['message']
    return rv
        
def logparse(name=None, service='services/%s', path=None, max=0, good=None, bad=None, timeparser=None, timeformat=None, token=None, callerToken=None):
    pass

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Search log file(s) for most recent good and/or bad conditions",
        epilog="Use (?P<time>...) and (?P<message>) to extract messages from regular expressions"
        )
    parser.add_argument("-g", "--good", metavar="REGEX", action='append', help="Regular expression for lines corresponding to good events")
    parser.add_argument("-b", "--bad", metavar="REGEX", action='append', help="Regular expression for lines corresponding to bad events")
    parser.add_argument("-p", "--timeparser", metavar="FMT", help="Time parse format string (strptime-style), default relaxed ISO-8601")
    parser.add_argument("-f", "--timeformat", metavar="FMT", help="Time format string (strftime-style), default ISO-8601")
    parser.add_argument("logfile", help="Log files to search")
    args = parser.parse_args()
    res = dologparse(args.logfile, args.good, args.bad, args.timeparser, args.timeformat)
    for k, v in list(res.items()):
        print('%s\t%s' % (k, v))
    
if __name__ == '__main__':
    main()
    
