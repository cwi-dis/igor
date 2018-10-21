#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi

smartmeter_data=`curl --silent $igor_protocol://$igor_host/p1?format=json`
case x$smartmeter_data in
x'{'*)
	echo $smartmeter_data | igorVar --put application/json sensors/$igor_pluginName
	;;
*)
	echo $smartmeter_data 1>&2
	exit 1
esac
