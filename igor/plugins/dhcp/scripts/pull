#!/bin/bash
dir=`dirname $0`
dirDHCP=~jack/src/dis/jack/home

python $dirDHCP/dhcpleases.py --json --wrap --ping --arp -i client-hostname -i hardware -i ip-address -i alive -i arp -i ping | igorVar --put application/json sensors/dhcp
