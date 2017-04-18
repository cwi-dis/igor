# Igor sample plugins

## ble

Listens to Bluetooth Low Energy advertisements to determine which devices are in range. See [ble/readme.md](ble/readme.md) for details.

## buienradar

Stores rain forecast for the coming hour. See [buienradar/readme.md](buienradar/readme.md) for details.

## copytree

Copies subtree ```src``` to ```dst```. Both src and dst can be local or remote, allowing mirroring from one Igor to another (or actually between any two REST servers). Optional arguments ```mimetype``` and ```method``` are available.

## dhcp

Queries database of DHCP server on local machine and stores all active dhcp leases. See [dhcp/readme.md](dhcp/readme.md) for details.

## fitbit

Retrieves health data from Fitbit devices using the Fitbit cloud API and stores this in ```sensors/fitbit```. See [fitbit/readme.md](fitbit/readme.md) for details.
Currently broken.

## homey

Example Homey integration. See [homey/readme.md](homey/readme.md) for details.

Needs work.

## iirfid

Example RFID reader integration. See [iirfid/readme.md](iirfid/readme.md) for details.

## kaku

Turns lights (or other devices) on and off using a KlikAanKlikUit device. See [kaku/readme.md](kaku/readme.md) for details.

, based on values in ```environment/lights/*```. Mapping of light names to switch numbers and other parameters are programmable in ```plugindata/kaku```.

## lan

Determines whether a local (or remote) internet service is up and running.
See [lan/readme.md](lan/readme.md) for details.

, and stores this information in ```devices/_service_/alive```. Parameters are ```name``` (no default), ```ip``` (defaults to _name_), ```port``` (default 80) and ```timeout``` (default 5).

## message

Displays messages on an LCD display. See [message/readme.md](message/readme.md) for details.

Displays any messages stored in ```environment/messages``` on an external LCD display. Requires command line tool ```lcdecho```. Also see _say_.

## neoclock

Driver for NeoClock internet-connected clock. See [neoclock/readme.md](neoclock/readme.md) for details.

Shows 1-hour rain forecast on a NeoClock (see to-be-provided for more details on this device). Also shows warning on NeoClock when any messages appear in ```environment/systemHealth/messages``` and sets a watchdog in the NeoClock so it shows a warning when Igor is not running.

## netatmo

Driver for NetAtmo weather stations. See [netatmo/readme.md](netatmo/readme.md) for details.
Gets local (indoor and outdoor) temperature and other environmental data through the NetAtmo cloud API. Stores the raw data in ```sensors/netAtmo``` and parsed temperatures in ```environment/weather```.

## philips

Example of controlling a Philips television. See [philips/readme.md](philips/readme.md) for details.
 Power on/off is controlled using a IR transmitter (when ```devices/tv/power``` is modified). Other settings are controlled using the Philips Jointspace REST interface, for example by modifying ```devices/tv/channel```.

## plant

Move an internet-connected plant up and down. See [plant/readme.md](plant/readme.md) for details.

Moves a plant up and down, so the height of the plant reflects the current electricity consumption in the house as read from ```environment/energy/electricity``` (see _smartmeter_ for details).

Requires a device for moving the plant (obviously:-), details to-be-provided.

## say

Speaks messages to the user. See [say/readme.md](say/readme.md) for details.

Speaks any messages stored in ```environment/messages``` on an OSX computer using the ```say``` command line tool. OSX machine to use can be ssh-accessible. Also see _lcd_.

## smartmeter_iotsa

Reads current energy use in the household using a iotsa SmartMeter reader. See [smartmeter_iotsa/readme.md](smartmeter_iots/readme.md) for details.
(requires dutch P1 energy meter and specialised hardware, link to-be-provided) and stores the raw data in ```sensors/smartMeter```. Electricity use is obtained from this and stored in ```environment/energy/electricity```.


## smartmeter_rfduino

Older Bluetooth-based version of _smartmeter_iotsa_, reads current energy use in the household using a RFDuino-based SmartMeter reader (requires dutch P1 energy meter and specialised hardware, link to-be-provided) and stores the raw data in ```sensors/smartMeter```. Electricity use is obtained from this and stored in ```environment/energy/electricity```.

## testPlugin

A Python-based plugin that simply shows all the arguments it has been passed.

## watchdog

Reboots the host system in case of problems. See [watchdog/readme.md](watchdog/readme.md) for details.

A plugin that opens the Linux watchdog device ```/dev/watchdog```. The parameter ```timeout``` specifies after how many seconds the watchdog will fire and reboot the system, unless the watchdog plugin is accessed again before that timeout. Can be used to make the Igor machine reboot when Igor hangs, or when anomalous conditions are detected (and there is reason to believe a reboot will resolve these issues:-).

