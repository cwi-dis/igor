#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dir=`dirname $0`
bleURL=http://localhost:8081/
igorVar --url $bleURL ble | igorVar --put application/json --checknonempty sensors/ble
