# iotsa433Device - plugin for iotsa 433MHz home automation bridge

This plugin interfaces to a Iotsa 433MHz home automation sender/receiver.

The rest of the information in this readme is wrong:-)

## schema
* `devices/iotsaDevice/target`: data to be copied to the device.
* `devices/iotsaDevice/current`: data read from the device.

## actions

* Whenever `devices/iotsaDevice/target` changes this change is forwarded to the device.
* Whenever `/action/pull-iotsaDevice` is called the device data is copied to `current`.

## Notes

- Usually you will install this plugin with a different name, and specifically a name that matches the `.local` hostname of the device.
- You will probably have to edit `pluginData/iotsaDevice` manually to set the API endpoint and protocol. An installation user interface (like for other plugins) is still missing.
- If you have a multifunction iotsa device, with multiple API endpoints, it is better to install multiple _iotsaDevice_ plugins, one for each API endpoint, and edit the `pluginData` manually to set correct hostname and endpoint.