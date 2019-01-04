# Standard Plugins

Igor comes with a set of standard plugins. Some of these can be used as-is, and installed using (for example):

```
   igorSetup addstd copytree
```

Some are more examples that you should copy and adapt to your own need, or use as inspiration. 

Plugins take their name (for use in ```plugindata```, for example) from the name they are installed
under (which can be different than the standard name).
So you can install multiple independent copies (for example as *say* and *sayInBedroom*) 
and use different plugindata to control each copy of the plugin.

Various plugins should be considered standard to Igor operations and usually installed:

* *ca* allows access to the Certificate Authority
* *device* allows adding and removing devices
* *user* allows adding and removing users
* *systemHealth* implements the self-checks and health-checks of Igor
* *user* allows managing users: adding new users, changing passwords, etc
 
## ble

Listens to Bluetooth Low Energy advertisements to determine which devices are in range. See the [ble readme](ble/readme.md) for details.

## buienradar

Stores rain forecast for the coming hour. See [buienradar/readme.md](buienradar/readme.md) for details.

## ca

Certificate Authority. Programming interface to the Igor SSL certificate authority that allows _https:_ access to local services (like Igor itself). See [ca/readme.md](ca/readme.md) for details.

## copytree

Copies subtree ```src``` to ```dst```. Both src and dst can be local or remote, allowing mirroring from one Igor to another (or actually between any two REST servers). Optional arguments ```mimetype``` and ```method``` are available.

## device

Low level API to add devices and their capabilities and secret keys, and allow devices to call certain actions. User interface is provided.
## dhcp

Queries database of DHCP server on local machine and stores all active dhcp leases. See [dhcp/readme.md](dhcp/readme.md) for details.

## fitbit

Retrieves health data from Fitbit devices using the Fitbit cloud API and stores this in ```sensors/fitbit```. See [fitbit/readme.md](fitbit/readme.md) for details.

Note the underscore: the plugin is called `fitbit` because otherwise it would have a name clash with the underlying Python module it uses.

As of October 2018 this is the first plugin to have a user interface through a `setup.html` page, it can be used as an example of such. It is also currently the only plugin that implements _OAuth2_ to retrieve data from external websites.

## homey

Example Homey integration. See [homey/readme.md](homey/readme.md) for details.

Needs work.

## iirfid

Example RFID reader integration. See [iirfid/readme.md](iirfid/readme.md) for details.

## iotsaDiscovery

A plugin to discover devices based on the [iotsa](https://github.com/cwi-dis/iotsa) architecture and configure those devices (install certificates, install Igor capabilities, etc). The _NeoClock_, _Plant_ and _Smartmeter\_iotsa_ devices below are examples of _iotsa_ devices.
User interface is provided.

## kaku

Turns lights (or other devices) on and off using a KlikAanKlikUit device. See [kaku/readme.md](kaku/readme.md) for details.

## lan

Determines whether a local (or remote) internet service is up and running.
See [lan/readme.md](lan/readme.md) for details.

## lastFileAccess

Determine when a file was last modified or accessed (for example to check when some program was last used). 

## lcd

Displays messages on an LCD display. See [lcd/readme.md](lcd/readme.md) for details.

## logparse

Incomplete.

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

## systemHealth

Collects error messages from `services/*`, `devices/*` and `sensors/*` and stores these in `environment/systemHealth`. See [systemHealth/readme.md](systemHealth/readme.md) for details.

## testPlugin

A Python-based plugin that simply shows all the arguments it has been passed. This can be used as the starting point for a python-based plugin.

## timemachine

Checks last time that Apple Time Machine backed up specific machines. See [timemachine/readme.md](timemachine/readme.md) for details.

## user

Low-level interface to add and delete users, including capabilities and such, and change passwords. User interface is provided.

## watchdog

Reboots the host system in case of problems. See [watchdog/readme.md](watchdog/readme.md) for details.

```eval_rst
.. toctree::
   :glob:
   :hidden:
   
   */readme

```
