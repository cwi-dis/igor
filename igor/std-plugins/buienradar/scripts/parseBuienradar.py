#!/usr/bin/env python
"""Parse buienradar expected rain data.

Pass a URL with longitude/lattitude (maximum 2 digits precision, more does not work)
such as http://gpsgadget.buienradar.nl/data/raintext?lat=52.36&lon=4.87 .

Format of lines returned is
123|13:45
meaning expected rain level is 123 at 13:45.

http://www.buienradar.nl/overbuienradar/gratis-weerdata has description of the format.
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from past.utils import old_div
import sys
import os
import urllib.request, urllib.parse, urllib.error
import datetime
import json

def parselines(input):
    """Return a buienradard input file as (level, (hh, mm)) tuples."""
    for line in input:
        line = line.strip()
        levelStr, hhmmStr = line.split('|')
        hhStr, mmStr = hhmmStr.split(':')
        yield (int(levelStr), (int(hhStr), int(mmStr)))

def nearestTime(hh, mm):
    """Return the expected time that hh:mm refers to, iso format. Needs a bit of work
    because around midnight things may refer to yesterday or tomorrow"""
    now = datetime.datetime.now()
    nowM1 = now - datetime.timedelta(1)
    nowP1 = now + datetime.timedelta(1)
    
    cand = datetime.datetime(now.year, now.month, now.day, hh, mm)
    candM1 = datetime.datetime(nowM1.year, nowM1.month, nowM1.day, hh, mm)
    candP1 = datetime.datetime(nowP1.year, nowP1.month, nowP1.day, hh, mm)
    
    delta = abs(cand - now)
    deltaM1 = abs(candM1 - now)
    deltaP1 = abs(candP1 - now)
    
    if deltaM1 < delta: return candM1.isoformat()
    if deltaP1 < delta: return candP1.isoformat()
    return cand.isoformat()
    
def process(input):
    measurementList = []
    for level, (hh, mm) in parselines(input):
        timestamp = nearestTime(hh, mm)
        intensity = 10**(old_div((level-109),32.0))
        intensity = old_div(int(intensity*100),100.0)
        measurementList.append(dict(time=timestamp, hour=hh, minute=mm, level=level, mm=intensity))
    if not measurementList: return False
    rv = dict(lastActivity=datetime.datetime.now().isoformat(), data=measurementList)
    json.dump(rv, sys.stdout)
    print()
    return True
    
def main():
    if len(sys.argv) == 2:
        input = urllib.request.urlopen(sys.argv[1])
    elif len(sys.argv) == 1:
        input = sys.stdin
    else:
        print("Usage: %s [buienradarurl]" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    if not process(input):
        sys.exit(1)
        
if __name__ == '__main__':
    main()
    
