#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi

dhcpleases --json --wrap --ping --arp -i client-hostname -i hardware -i ip-address -i alive -i arp -i ping | igorVar --put application/json sensors/dhcp
