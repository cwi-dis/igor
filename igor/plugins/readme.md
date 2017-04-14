# Igor sample plugins

## ble

Listens to Bluetooth Low Energy advertisements to determine which devices are in range. Stores raw data (mac-address, last time seen) data for all devices in ```sensors/ble```, and current availability by name for specific "known" devices (programmable via ```plugindata/bleDevices```) into ```environment/devices```.

## buienradar

Stores rain forecast for the coming hour in ```sensors/buienradar```, based on GPS location from ```plugindata/buienradar```. Uses buienradar.nl so will only work in the Netherlands.

## copytree

Copies subtree ```src``` to ```dst```. Both src and dst can be local or remote, allowing mirroring from one Igor to another (or actually between any two REST servers). Optional arguments ```mimetype``` and ```method``` are available.

## dhcp

Queries database of DHCP server on local machine and stores all active dhcp leases (by mac-address and ip-address) in ```sensors/dhcp```and current availability by name for specific "known" devices (programmable via ```plugindata/wifiDevices```) into ```environment/devices```.

## fitbit

Retrieves health data from Fitbit devices using the Fitbit cloud API and stores this in ```sensors/fitbit```. Currently broken.

## homey

Example Homey integration. Needs work.

## iirfid

Example RFID reader integration. Requires special hardware (probably only available at CWI). Stores all presented tags in ```sensors/rfid```, sequentially. Tags that are known (by hardware address, stored in ```plugindata/rfid```) are also stored in ```sensors/tags```. RFID reader device and other parameters are settable in ```plugindata/iirfid```.

## kaku

Turns lights (or other devices) on and off using a KlikAanKlikUit device, based on values in ```environment/lights/*```. Mapping of light names to switch numbers and other parameters are programmable in ```plugindata/kaku```.

## lan

Determines whether a local (or remote) internet service is up and running, and stores this information in ```devices/_service_/alive```. Parameters are ```name``` (no default), ```ip``` (defaults to _name_), ```port``` (default 80) and ```timeout``` (default 5).

## message

Displays any messages stored in ```environment/messages``` on an external LCD display. Requires command line tool ```lcdecho```. Also see _say_.

## neoclock

Shows 1-hour rain forecast on a NeoClock (see to-be-provided for more details on this device). Also shows warning on NeoClock when any messages appear in ```environment/systemHealth/messages``` and sets a watchdog in the NeoClock so it shows a warning when Igor is not running.

## netatmo

Gets local (indoor and outdoor) temperature and other environmental data through the NetAtmo cloud API. Stores the raw data in ```sensors/netAtmo``` and parsed temperatures in ```environment/weather```.

## philips

Example of controlling a Philips television. Power on/off is controlled using a IR transmitter (when ```devices/tv/power``` is modified). Other settings are controlled using the Philips Jointspace REST interface, for example by modifying ```devices/tv/channel```.

## plant

Moves a plant up and down, so the height of the plant reflects the current electricity consumption in the house as read from ```environment/energy/electricity``` (see _smartmeter_ for details).

Requires a device for moving the plant (obviously:-), details to-be-provided.

## say

Speaks any messages stored in ```environment/messages``` on an OSX computer using the ```say``` command line tool. OSX machine to use can be ssh-accessible. Also see _lcd_.

## smartmeter_iotsa

Reads current energy use in the household using a iotsa SmartMeter reader (requires dutch P1 energy meter and specialised hardware, link to-be-provided) and stores the raw data in ```sensors/smartMeter```. Electricity use is obtained from this and stored in ```environment/energy/electricity```.


## smartmeter_rfduino

Older Bluetooth-based version of _smartmeter_iotsa_, reads current energy use in the household using a RFDuino-based SmartMeter reader (requires dutch P1 energy meter and specialised hardware, link to-be-provided) and stores the raw data in ```sensors/smartMeter```. Electricity use is obtained from this and stored in ```environment/energy/electricity```.

## testPlugin

A Python-based plugin that simply shows all the arguments it has been passed.

## watchdog

A plugin that opens the Linux watchdog device ```/dev/watchdog```. The parameter ```timeout``` specifies after how many seconds the watchdog will fire and reboot the system, unless the watchdog plugin is accessed again before that timeout. Can be used to make the Igor machine reboot when Igor hangs, or when anomalous conditions are detected (and there is reason to believe a reboot will resolve these issues:-).

