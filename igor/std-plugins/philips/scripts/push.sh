#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dir=`dirname $0`
python $dir/philips.py $igor_name $igor_value
echo Changed Philips $igor_name to $igor_value
