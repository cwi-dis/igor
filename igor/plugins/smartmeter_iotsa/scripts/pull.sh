#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi

smartmeter_data=`curl --silent $igor_protocol://$igor_host/p1?format=xml`
case x$smartmeter_data in
*smartMeter*)
	echo $smartmeter_data | igorVar --put application/xml --checknonempty sensors/smartMeter
	;;
*)
	echo $smartmeter_data 1>&2
	exit 1
esac
