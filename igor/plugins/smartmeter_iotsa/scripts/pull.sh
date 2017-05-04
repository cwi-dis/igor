#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi

curl --silent http://$igor_host/p1?format=xml | igorVar --put application/xml sensors/smartMeter
