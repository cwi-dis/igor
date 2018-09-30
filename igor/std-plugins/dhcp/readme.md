# dhcp - Device availability based on wifi

Queries database of DHCP server on local machine and stores all active dhcp leases. Updates human-visible devices whenever a known device has a lease.

## requirements

The plugin parses the internal files of the Linux DHCP service, therefore it only works if the DHCP server runs on the same machine as Igor.

## schema

* `environment/devices`: Updated with known devices, as they are available.
* `devices/dhcp/lease`: information about a single DHCP lease:
	* `hardware`: Hardware MAC-address (string, 6 colon-separated hex bytes).
	* `ip-address`: IP address (string).
	* `client-hostname`: Name of the device, if known to DHCP (string)
	* `arp`: Boolean, true if IP-address is in the ARP-cache.
	* `ping`: Boolean, true if device reacts to ping.
	* `alive`: Boolean, true if either _arp_ or _ping_ (or both) is true.
* `plugindata/wifiDevices/wifiDevice`: MAC-address to name mapping for a single device:
	* `id`: MAC-address (string, 6 colon-separated hex bytes).
	* `name`: user-visible name.

## actions

Three actions:

* Every 60 seconds the DHCP database is parsed and `sensors/dhcp` is filled.
* When a known device availability changes `environment/devices` is updated.
