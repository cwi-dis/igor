#!/bin/bash
dir=`dirname $0`
bleURL=http://localhost:8081/
igorVar --url $bleURL ble | igorVar --put application/json sensors/ble
