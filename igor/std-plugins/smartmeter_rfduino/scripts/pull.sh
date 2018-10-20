#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dir=`dirname $0`
dirIgor=$dir/../../..
dirSmartMeter=~jack/src/dis/jack/smartMeter
readtelegram="python $dirSmartMeter/readTelegramBluez.py"
parsetelegram="python $dirSmartMeter/parseTelegram.py"
meter="D1:59:4C:3C:5C:2E random"

$readtelegram $meter | $parsetelegram --json | igorVar --put application/json --checknonempty sensors/$igor_pluginName
