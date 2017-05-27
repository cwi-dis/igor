#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dir=`dirname $0`
dirFitbit=~jack/src/dis/jack/fitbit
case "x$igor_user" in
x)
	echo $0: need user= argument
	exit 1
	;;
esac
case "x$igor_pluginData" in
x)
	echo $0: no pluginData for user=$igor_user
	exit 1
	;;
esac
echo $igor_pluginData | python $dirFitbit/getFitbit.py --stdin | igorVar --put application/json --checkdata --timestamp sensors/fitbit/$igor_user
