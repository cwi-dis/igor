# philips - control a Philips TV set

This plugin controls a Philips TV set, allowing the TV to be turned on or off, channels to be switched, etc.

It is a proof of concept.

## requirements

* Turning the TV on or off requires an infrared transmitter with a USB interface. The schematics and software for the specific transmitter used will be made available later.
* Switching channels, controlling volume and such require a Philips TV with the JointSpace features, which allow control over the TV through a REST API. This is supported on most Philips TVs produced between 2009 and 2014, see [the JointSpace sourceforge page](http://jointspace.sourceforge.net) for details.
* Scripts _tvcmd.py_ to control the IR transmitter and _philips.py_ to use the REST api.

## schema

* `devices/tv/power`: boolean, true if TV is on (or should be on).
* `devices/tv/volume`: integer, TV sound volume.
* many more...

## actions
Three actions:

* Whenever `devices/tv/power` changes turn on or off the TV through the infrared transmitter.
* Whenever any other element in `devices/tv` changes forward that change to the TV through the REST interface.
* Every 60 seconds obtain the status of the TV and update the elements in `devices/tv`.