# kaku - control KlikAanKlikUit devices

Turns lights (or other devices) on and off using a [KlikAanKlikUit](https://www.klikaanklikuit.nl) device. Should be fairly easy to adapt for other vendors, as long as a computer-connectable controller exists.

## requirements

* A KAKU USB controller (and some KAKU outlets)
* The KAKU helper program from ```../../helpers/kaku```, which in turn requires _pyusb_.

## schema

* `environment/switch`: Contains boolean elements stating which switches should be on and off.
* `plugindata/kaku/host`: the hostname or IP address to wich the USB controller is connected, and on which the helper program should be installed (string, default localhost). Must be reachable with _ssh_ without password.
* `plugindata/kaku/switch`: Entry mapping switch names to ids. Can occur multiple times:
	* `name`: human readable name (string).
	* `id`: KAKU switch number (integer).

## actions

Whenever the value of any element in `environment/lights` changes the element name is looked up on `plugindata/kaku/switch` and the corresponding switch is turned on or off.