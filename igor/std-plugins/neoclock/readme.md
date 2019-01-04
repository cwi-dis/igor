# neoclock - use a NeoClock for showing status information

A NeoClock is a clock with 60 LEDs that shows the time, but additionally can show status information and alerts through a REST-like web service. It is built around an esp8266-based microprocessor board with NeoPixel LEDs.

Instructions for building (hardware and software) can be found at <https://github.com/cwi-dis/iotsaNeoClock>.

This plugin uses the NeoClock to show three types of status information:

* _Igor status_: if Igor does not update the NeoClock status for 5 minutes (for example because Igor has crashed) the inner LED circle will light up orange.
* _System status_: if any messages have been deposited in `environment/systemHealth` the inner LED circle will light up red.
* _Rain forecast_: the outer circle of LEDs will show rain intensity for the coming hour (if the [buienradar](../buienradar/readme) plugin is also installed).

## schema

* `environment/systemHealth/messages`: if non-empty the neoClock will show a warning status
* `sensors/buienradar`: if this exists it will be used to fill the rain forecast status
* `plugindata/neoclock/host`: host name for the neoclock
* `plugindata/neoclock/protocol`: protocol for accessing the neoclock (`http`, `https` or `coap`)

## requirements

Use of this plugin requires a [iotsa NeoClock], _URL to be provided later_.

## actions

Two actions:

* Update neoclock _temporalStatus_ (the outer ring) whenever `sensors/buienradar` changes.
* Update neoclock _status_ (the inner ring) every minute, with color depending on the content of `environment/systemHealth/messages`, a timeout of 5 minutes and a timeout color of orange.