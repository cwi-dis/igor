# plant - control the position of an internet-connected plant

This plugin interfaces to a Iotsa MotorServer board. This board is a esp8266-based small REST-like web server that controls a stepper motor, thereby allowing the physicl position of something in the house to be controlled over the internet.

The MotorServer repository <https://github.com/dis-git/iotsaMotorServer> contains the source code for the server, as well as schematics and 3D-models of the hardware needed.

## schema
* `environment/energy/electricity`: float, current electricity consumption in kW. Stored here by a plugin like [smartmeter_iotsa](../smartmeter_iotsa/readme.md).
* `devices/plant/pos`: float, wanted cable length in centimeters when written. Current length in cm when read.
* `devices/plant/target`: float (read-only), wanted cable length.
* `devices/plant/speed`: float (read-only), current motor speed.
* `devices/plant/inrange`: integer (read-only), nonzero if the cable is at an ultimate position, as indicated by the end stop microswitches.

## actions

* every minute the current position (and speed, etc) of the plant is retrieved and stored in `devices/plant`.
* Whenever `environment/energy/electricity` changes and if `environment/night` is false `devices/plant/pos` is updated. This action contains the formula to convert kW (unit of electricity use) to cm (unit of plant height).
* Whenever `devices/plant/pos` changes this change is forwarded to the MotorServer.