#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dir=`dirname $0`
python $dir/philips.py json | igorVar --put application/json devices/tv
