#!/bin/bash
dir=`dirname $0`
python $dir/philips.py $igor_name $igor_value
echo Changed Philips $igor_name to $igor_value
