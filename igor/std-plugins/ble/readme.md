# ble - Bluetooth LE plugin

Listens to Bluetooth Low Energy advertisements to determine which devices are in range. 

## requirements

Only tested on a Raspberry PI with an external Bluetooth LE USB dongle and the Bluez bluetooth stack.

Requires the _bleServer_, see ```../../../helpers```.

Stores raw data (mac-address, last time seen) data for all devices in ```sensors/ble```, and current availability by name for specific "known" devices (programmable via ```plugindata/bleDevices```) into ```environment/devices```.

## schema

* `sensors/ble`: Stores per-device entries exactly as they are read from _bleServer_.
* `environment/devices`: Stores availability of known devices.
* `status/devices/ble`: Device status updated on every action.
* `plugindata/bleDevices/bleDevice`: Maps hardware address to name, for known devices (which will be stored in `environment/devices`:
	*	`id`: Mac address (string, 6 colon-separated hex bytes).
	* `name`: User-visible name. 

## actions

Two actions:

* Pull data from _bleServer_ into `sensors/ble` every 60 seconds.
* Update `environment/devices` for known BLE devices.
