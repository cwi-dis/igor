#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
plantURL=http://plant.local/stepper/
igorVar --url $plantURL 0 | igorVar --put application/json devices/plant
