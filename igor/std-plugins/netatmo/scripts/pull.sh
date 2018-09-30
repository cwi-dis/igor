#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dirNetAtmo=~jack/src/dis/jack/netAtmo
python $dirNetAtmo/getCurrentWeather.py --json | igorVar --put application/json --checknonempty sensors/netAtmo
