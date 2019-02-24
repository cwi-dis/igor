# passiveSensor - get sensor readings via REST

This plugin periodically polls a REST endpoint and saves the resulting readings in the Igor database.

As distributed it will read sensor data from BLE sensors, using the same REST service as the [BLE plugin](../ble/readme.md), but using different endpoints. For each sensor the most recent reading is remembered.

Currently the BLE server supports the following sensors:

- *nearable*: devices supporting the [Estimote](https://estimote.com) Nearable protocol.
- *ibeacon*: devices supporting the [iBeacon](https://en.wikipedia.org/wiki/IBeacon) protocol originally developed by Apple but now supported by many beacon vendors.
- *cwi_sensortag*: [Texas Instrument CC2650 SensorTag](http://www.ti.com/tool/TIDC-CC2650STK-SENSORTAG) devices running the CWI-DIS firmware (link to be provided later).

The intention is to install this plugin not under its standard name, but under the name of the sensor type (such as *ibeacon* or *nearable*). Sensors are identified by UUID, or BLE Mac address for *cwi_sensortag*.


## requirements

Only tested on a Raspberry PI with an external Bluetooth LE USB dongle and the Bluez bluetooth stack.

Requires the _bleServer_, see ```../../../helpers```.

## schema

* `sensors/passiveSensor/lastActivity`: Time of the last reply of the REST service.
* `sensors/passiveSensor/_name_Device`: Occurs once per *name*-type sensor. Contains information such as *uuid* or *address* and all data the sensor advertises (temperature, accelerometer, rss, etc).
* `status/devices/passiveSensor `: Device status updated on every action.
* `plugindata/passiveSensor`:
	* `protocol`: Usually *http* or *https*.
	* `host`: where the REST service runs, usually *localhost*.
	* `port`: which port the REST service runs on.
	* `endpoint`: Rest of the REST URL after the initial /.
	
## actions

One action:

* Pull data from the REST server into `sensors/passiveSensor` every 2 seconds.
