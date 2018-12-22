# Igor plugins

Igor comes with a set of standard plugins. Some of these can be used as-is, and installed using (for example):

```
igorSetup addstd copytree
```

Some are more examples that you should copy and adapt to your own need, or use as inspiration. 

Plugins take their name (for use in `plugindata`, for example) from the name they are installed under. So you can install multiple independent copies (for example as _say_ and _sayInBedroom_) and use different plugindata to control each copy of the plugin.

Various plugins should be considered standard to Igor operations and usually installed:

- _ca_ allows access to the Certificate Authority
- _device_ allows adding and removing devices
- _user_ allows adding and removing users
- _systemHealth_ implements the self-checks and health-checks of Igor

## Plugin Structure

A plugin generally contains either a Python module or a set of scripts (or both) to communicate with an external device or service. In addition a plugin can contain user-interface pages to allow the user to configure or operate the plugin (or the device it controls).

### igorplugin.py

A plugin can be implemented in Python. Then it must define a class (or factory function)

```
igorPlugin(igor, pluginName, pluginData)
``` 

which is called whenever any method of the plugin is to be called. This function should return an object on which the individual methods are looked up. The `igorPlugin` function is called every time a plugin method needs to be called, but it can of course return a singleton object. See the _watchdog_ plugin for an example. _igor_ is a pointer to the global Igor object (see below), _PluginName_
is the name under which the plugin has been installed, and _PluginData_ is filled from `/data/plugindata/_pluginname_`. 

Each operation will call a method on the object. There will always be an argument `token` which will be the current set of capabilities (or `None` if Igor is running without capability support) and which the plugin will have to pass to most Igor API calls.

Accessing `/plugin/pluginname` will call the `index()` method. 

Accessing `/plugin/pluginname/methodname` will call `methodname()`.  

The methods are called with `**kwargs` encoding the plugin arguments, and if there is a `user` argument there will be an additional argument `userData` which is filled from `/data/identities/_user_/plugindata/_pluginname_`.

Methods starting with an underscore `_` are not callable through the web interface but can be called by the plugin template pages or by other plugins.

The _igor_ object has a number of attributes that allow access to various aspects of Igor:

- `igor.database` is the XML database (implemented in `igor.xmlDatabase.DBImpl`)
- `igor.databaseAccessor` is a higher level, more REST-like interface to the database.
- `igor.internal` gives access to the set of commands implemented by `igor.__main__.IgorInternal`.
- `igor.app` is the web application (from `igor.webApp.WebApp`).
- `igor.plugins` is the plugin manager.

### scripts

A plugin can be (partially) implemented with shell scripts. Accessing `/pluginscript/pluginname/scriptname` will try to run `pluginname/scripts/scriptname.sh`.

Scripts get an environment variable `IGORSERVER_URL` set correctly so they can use the _igorVar_ command easily.

Each argument is passed to the script (in Python notation) with `igor_` prepended to the name. `igor_pluginName` contains the name under which the plugin is installed.

The per-plugin data from `/data/plugindata/_pluginname_` and (if the _user_ argument is present) the per-user per-plugin data from `/data/identities/_user_/plugindata/_pluginname_`
is encoded as a Python dictionary and passed in the `igor_pluginData` environment variable.

### database-fragment.xml

Many plugins require plugin-specific data in the database. Often there are one or more of the following items:

- plugin-specific actions that are needed to actually fire the plugin,
- plugin settings, for example to tell which host a specific device is connected to,
- boilerplate entries for where the plugin will store its data.

Usually these entries are explained in the plugin readme file, in the _schema_ section.

Usually there is a file `database-fragment.xml` that show the entries needed. Basically this file is the minimal set of elements that should be in the database for the plugin to function. 

This database fragment is overlayed onto the database when installing the plugin. Every occurrence of the exact string `{plugin}` is replaced by the name of the plugin before installing into the database.

The fragment overlay installation may be delayed until the next time the Igor server is restarted.

It may be necessary to do some hand editing of the database after installing, because you may have to modify some elements (such as hostname fields) and you may need to duplicate some (with modifications) for example if you want the _lan_ plugin to test different services.

### *.html

A plugin can contain a user interface through HTML pages. These are accessed with URLs `/plugin/_pluginname_/page/_pagename_.html`. Actually, these are [Jinja2](http://jinja.pocoo.org) templates. Within the template you have access to the following variables:

- _pluginName_ is the name under which the plugin has been installed.
- _pluginObject_ the plugin object (if the plugin has an `igorplugin.py` Python module).
- _token_ is the capability of the current user (the user visiting the page).
- _pluginData_ is the internal data of the plugin (from `/data/plugindata`).
- _user_ is the current user (if logged in).
- _userData_ is the per-plugin data for the current user (if logged in).
- all url parameters.

In general, the template should provide forms and such to allow the user to change settings, and then call methods in the plugin proper to implement those changes (because the plugin will run with a _token_ that allows read/write access to the plugin data).

## Included Igor Standard Plugins

### ble

Listens to Bluetooth Low Energy advertisements to determine which devices are in range. See [ble/readme.md](ble/readme.md) for details.

### buienradar

Stores rain forecast for the coming hour. See [buienradar/readme.md](buienradar/readme.md) for details.

### ca

Certificate Authority. Programming interface to the Igor SSL certificate authority that allows _https:_ access to local services (like Igor itself). See [ca/readme.md](ca/readme.md) for details.

### copytree

Copies subtree ```src``` to ```dst```. Both src and dst can be local or remote, allowing mirroring from one Igor to another (or actually between any two REST servers). Optional arguments ```mimetype``` and ```method``` are available.

### device

Low level API to add devices and their capabilities and secret keys, and allow devices to call certain actions. User interface is provided.
### dhcp

Queries database of DHCP server on local machine and stores all active dhcp leases. See [dhcp/readme.md](dhcp/readme.md) for details.

### _fitbit

Retrieves health data from Fitbit devices using the Fitbit cloud API and stores this in ```sensors/_fitbit```. See [_fitbit/readme.md](_fitbit/readme.md) for details.

Note the underscore: the plugin is called `_fitbit` because otherwise it would have a name clash with the underlying Python module it uses.

As of October 2018 this is the first plugin to have a user interface through a `setup.html` page, it can be used as an example of such. It is also currently the only plugin that implements _OAuth2_ to retrieve data from external websites.

### homey

Example Homey integration. See [homey/readme.md](homey/readme.md) for details.

Needs work.

### iirfid

Example RFID reader integration. See [iirfid/readme.md](iirfid/readme.md) for details.

### iotsaDiscovery

A plugin to discover devices based on the [iotsa](https://github.com/dis-git/iotsa) architecture and configure those devices (install certificates, install Igor capabilities, etc). The _NeoClock_, _Plant_ and _Smartmeter\_iotsa_ devices below are examples of _iotsa_ devices.
User interface is provided.

### kaku

Turns lights (or other devices) on and off using a KlikAanKlikUit device. See [kaku/readme.md](kaku/readme.md) for details.

### lan

Determines whether a local (or remote) internet service is up and running.
See [lan/readme.md](lan/readme.md) for details.

### lastFileAccess

Determine when a file was last modified or accessed (for example to check when some program was last used). 

### lcd

Displays messages on an LCD display. See [lcd/readme.md](lcd/readme.md) for details.

### logparse

Incomplete.

### neoclock

Driver for NeoClock internet-connected clock. See [neoclock/readme.md](neoclock/readme.md) for details.

### netatmo

Driver for NetAtmo weather stations. See [netatmo/readme.md](netatmo/readme.md) for details.

### philips

Example of controlling a Philips television. See [philips/readme.md](philips/readme.md) for details.

### plant

Move an internet-connected plant up and down. See [plant/readme.md](plant/readme.md) for details.

### say

Speaks messages to the user. See [say/readme.md](say/readme.md) for details.

### smartmeter_iotsa

Reads current energy use in the household using a iotsa SmartMeter reader. See [smartmeter_iotsa/readme.md](smartmeter_iotsa/readme.md) for details.

### smartmeter_rfduino

Older Bluetooth-based version of _smartmeter___iotsa_, reads current energy use in the household using a RFDuino-based SmartMeter reader.

### systemHealth

Collects error messages from `services/*`, `devices/*` and `sensors/*` and stores these in `environment/systemHealth`. See [systemHealth/readme.md](systemHealth/readme.md) for details.

### testPlugin

A Python-based plugin that simply shows all the arguments it has been passed. This can be used as the starting point for a python-based plugin.

### timemachine

Checks last time that Apple Time Machine backed up specific machines. See [timemachine/readme.md](timemachine/readme.md) for details.

### user

Low-level interface to add and delete users, including capabilities and such, and change passwords. User interface is provided.

### watchdog

Reboots the host system in case of problems. See [watchdog/readme.md](watchdog/readme.md) for details.

