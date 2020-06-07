# iotsaDevice - basic plugin for iotsa device

This plugin interfaces to a Iotsa device. 
Iotsa devices are small internet-enabled appliances, see  <https://github.com/cwi-dis/iotsa> for examples, the source code for the server, as well as schematics and 3D-models of the hardware needed.

## schema
* `devices/iotsaDevice/target`: data to be copied to the device.
* `devices/iotsaDevice/current`: data read from the device.

## simpleActions

* Whenever `devices/iotsaDevice/target` changes this change is forwarded to the device.
* Whenever `/action/pull-iotsaDevice` is called the device data is copied to `current`.

## Notes

- Usually you will install this plugin with a different name, and specifically a name that matches the `.local` hostname of the device.
- You will probably have to edit `pluginData/iotsaDevice` manually to set the API endpoint and protocol. An installation user interface (like for other plugins) is still missing.
- If you have a multifunction iotsa device, with multiple API endpoints, it is better to install multiple _iotsaDevice_ plugins, one for each API endpoint, and edit the `pluginData` manually to set correct hostname and endpoint.