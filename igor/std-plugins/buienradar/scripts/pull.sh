#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dir=`dirname $0`
lat=`expr $igor_lat : '\([0-9]*\.[0-9][0-9]\)[0-9]*'`
lon=`expr $igor_lon : '\([0-9]*\.[0-9][0-9]\)[0-9]*'`

python $dir/parseBuienradar.py "https://gps.buienradar.nl/getrr.php?lat=$lat&lon=$lon"  | igorVar --put application/json sensors/$igor_pluginName
