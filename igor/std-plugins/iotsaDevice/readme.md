# iotsaDevice - basic plugin for iotsa device

This plugin interfaces to a Iotsa device. 
Iotsa devices are small internet-enabled appliances, see  <https://github.com/cwi-dis/iotsa> for examples, the source code for the server, as well as schematics and 3D-models of the hardware needed.

## schema
* `devices/iotsaDevice/target`: data to be copied to the device.
* `devices/iotsaDevice/current`: data read from the device.

## actions

* Whenever `devices/iotsaDevice/target` changes this change is forwarded to the device.
* Whenever `/action/action-iotsa` is called (and every 10 minutes anyway) the device data is copied to `current`.
