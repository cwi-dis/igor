#!/bin/bash
dir=`dirname $0`
python $dir/philips.py json | igorVar --put application/json devices/tv
