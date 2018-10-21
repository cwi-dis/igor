#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
plantURL=$igor_protocol://$igor_host/stepper/
igorVar --url $plantURL 0 | igorVar --put application/json --checknonempty devices/$igor_pluginName
