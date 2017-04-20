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

## lan

Determines whether a local (or remote) internet service is up and running.
See [lan/readme.md](lan/readme.md) for details.

## lcd

Displays messages on an LCD display. See [lcd/readme.md](lcd/readme.md) for details.

## neoclock

Driver for NeoClock internet-connected clock. See [neoclock/readme.md](neoclock/readme.md) for details.

## netatmo

Driver for NetAtmo weather stations. See [netatmo/readme.md](netatmo/readme.md) for details.

## philips

Example of controlling a Philips television. See [philips/readme.md](philips/readme.md) for details.

## plant

Move an internet-connected plant up and down. See [plant/readme.md](plant/readme.md) for details.

## say

Speaks messages to the user. See [say/readme.md](say/readme.md) for details.

## smartmeter_iotsa

Reads current energy use in the household using a iotsa SmartMeter reader. See [smartmeter_iotsa/readme.md](smartmeter_iotsa/readme.md) for details.

## smartmeter_rfduino

Older Bluetooth-based version of _smartmeter___iotsa_, reads current energy use in the household using a RFDuino-based SmartMeter reader.

## testPlugin

A Python-based plugin that simply shows all the arguments it has been passed. This can be used as the starting point for a python-based plugin.

## watchdog

Reboots the host system in case of problems. See [watchdog/readme.md](watchdog/readme.md) for details.

